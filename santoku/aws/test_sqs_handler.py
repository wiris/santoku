import boto3
import pytest
import json
from botocore import client
from botocore import exceptions
from moto import mock_sqs
from ..aws.sqs_handler import SQSHandler

TEST_REGION = "eu-central-1"
TEST_SQS_QUEUE = "test_standard_queue"
TEST_SQS_QUEUE_FIFO = "test_fifo_queue.fifo"


def delete_queue(sqs_client: client, queue_name):
    queue_url = sqs_client.get_queue_url(QueueName=queue_name)["QueueUrl"]
    sqs_client.delete_queue(QueueUrl=queue_url)


class TestSQSHandler:
    def setup_method(self):
        self.mock_sqs = mock_sqs()
        self.mock_sqs.start()

        self.sqs_handler = SQSHandler(region_name=TEST_REGION)
        self.client = boto3.client(
            "sqs",
            region_name=TEST_REGION,
            aws_access_key_id="fake_access_key",
            aws_secret_access_key="fake_secret_key",
        )

        # Create a standard queue.
        try:
            self.client.get_queue_url(QueueName=TEST_SQS_QUEUE)
        except exceptions.ClientError:
            # By catching the exception we check the queue certainly do not exist.
            pass
        else:
            raise EnvironmentError(
                "{queue_name} should not exist.".format(queue_name=TEST_SQS_QUEUE)
            )
        self.client.create_queue(QueueName=TEST_SQS_QUEUE)

        # Create a FIFO queue.
        try:
            self.client.get_queue_url(QueueName=TEST_SQS_QUEUE_FIFO)
        except exceptions.ClientError:
            pass
        else:
            raise EnvironmentError(
                "{queue_name} should not exist.".format(queue_name=TEST_SQS_QUEUE_FIFO)
            )
        self.client.create_queue(
            QueueName=TEST_SQS_QUEUE_FIFO, Attributes={"FifoQueue": "true"}
        )

    def teardown_method(self):
        delete_queue(sqs_client=self.client, queue_name=TEST_SQS_QUEUE)
        delete_queue(sqs_client=self.client, queue_name=TEST_SQS_QUEUE_FIFO)
        self.mock_sqs.stop()

    def test_queue_exist(self):
        # Test an existing queue. Success expected.
        assert self.sqs_handler.queue_exist(queue_name=TEST_SQS_QUEUE)

        # Test a non-existent queue. Failure expected.
        assert not self.sqs_handler.queue_exist(queue_name="WRONG_QUEUE_NAME")

    def test_queue_is_fifo(self):
        # Test a fifo queue. Success expected.
        assert self.sqs_handler.queue_is_fifo(queue_name=TEST_SQS_QUEUE_FIFO)

        # Test a standard queue. Failure expected.
        assert not self.sqs_handler.queue_is_fifo(queue_name=TEST_SQS_QUEUE)

    def test_get_queue_url_by_name(self):
        # Test getting the name of a queue that does exist. Success expected.
        obtained_url = self.sqs_handler.get_queue_url_by_name(queue_name=TEST_SQS_QUEUE)
        moto_aws_account = "123456789012"
        expected_url = "https://{region}.queue.amazonaws.com/{account}/{queue}".format(
            region=TEST_REGION, account=moto_aws_account, queue=TEST_SQS_QUEUE
        )
        assert obtained_url == expected_url

        # Test getting the name of a queue that does not exist. Failure expected.
        with pytest.raises(Exception) as e:
            self.sqs_handler.get_queue_url_by_name(queue_name="WRONG_QUEUE_NAME")

    def test_message_attributes_well_formed(self):
        # Message attributes correctly structured. Success expected.
        message_attributes = {
            "TestAttribute1": {
                "DataType": "String",
                "StringValue": "Test string value",
            },
            "TestAttribute2": {"DataType": "Number", "StringValue": "1"},
            "TestAttribute3": {
                "DataType": "Binary",
                "BinaryValue": "Test binary value",
            },
        }
        well_formed, _ = self.sqs_handler.message_attributes_well_formed(
            message_attributes
        )
        assert well_formed

        # Message with more than 10 attributes. Failure expected.
        num_attributes = len(message_attributes)
        max_num_attributes = 10
        message_content = {
            "DataType": "String",
            "StringValue": "Test string value",
        }

        # Create 11 attributes.
        for i in range(num_attributes + 1, max_num_attributes + 2):
            message_attributes["TestAttribute{i}".format(i=i)] = message_content

        well_formed, obtained_message = self.sqs_handler.message_attributes_well_formed(
            message_attributes
        )
        expected_message = "Messages can have up to 10 attributes."
        assert not well_formed
        assert obtained_message == expected_message

        # Message attributes not correctly structured. Failure expected.
        message_attributes = {"WrongAttribute": "WrongValue"}
        well_formed, obtained_message = self.sqs_handler.message_attributes_well_formed(
            message_attributes
        )
        expected_message = "Each message attribute must be a dictionary containing 'DataType' and 'StringValue' arguments."
        assert not well_formed
        assert obtained_message == expected_message

        # Message attributes that does not contain the required arguments. Failure
        # expected.
        message_attributes = {"WrongAttribute": {"StringValue": "Test string Value"}}
        well_formed, obtained_message = self.sqs_handler.message_attributes_well_formed(
            message_attributes
        )
        expected_message = "'DataType' argument is missing in message attribute."
        assert not well_formed
        assert obtained_message == expected_message

        message_attributes = {
            "WrongAttribute": {"DataType": "String", "BinaryValue": "Test string value"}
        }
        well_formed, obtained_message = self.sqs_handler.message_attributes_well_formed(
            message_attributes
        )
        expected_message = (
            "'StringValue' argument is required for message attributes of type String."
        )
        assert not well_formed
        assert obtained_message == expected_message

        message_attributes = {
            "WrongAttribute": {"DataType": "Number", "BinaryValue": "1"}
        }
        well_formed, obtained_message = self.sqs_handler.message_attributes_well_formed(
            message_attributes
        )
        expected_message = (
            "'StringValue' argument is required for message attributes of type Number."
        )
        assert not well_formed
        assert obtained_message == expected_message

        message_attributes = {
            "WrongAttribute": {"DataType": "Binary", "StringValue": "Test binary value"}
        }
        well_formed, obtained_message = self.sqs_handler.message_attributes_well_formed(
            message_attributes
        )
        expected_message = (
            "'BinaryValue' argument is required for message attributes of type Binary."
        )
        assert not well_formed
        assert obtained_message == expected_message

    def test_send_message(self):
        # Send a message to a standard queue. Success expected.
        message_body = "Test message body."
        message_attributes = {
            "TestAttribute1": {
                "DataType": "String",
                "StringValue": "Test string value",
            },
            "TestAttribute2": {"DataType": "Number", "StringValue": "1"},
            "TestAttribute3": {
                "DataType": "Binary",
                "BinaryValue": "Test binary value",
            },
        }
        response = self.sqs_handler.send_message(
            queue_name=TEST_SQS_QUEUE,
            message_body=message_body,
            message_attributes=message_attributes,
        )
        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

        # Check whether the received message id coincide with the one sent.
        expected_message_id = response["MessageId"]

        queue_url = self.client.get_queue_url(QueueName=TEST_SQS_QUEUE)["QueueUrl"]
        response = self.client.receive_message(QueueUrl=queue_url)
        obtained_message_id = response["Messages"][0]["MessageId"]
        assert obtained_message_id == expected_message_id

    def test_send_message_batch(self):
        message_attributes = {
            "TestAttribute1": {
                "DataType": "String",
                "StringValue": "Test string value",
            },
            "TestAttribute2": {"DataType": "Number", "StringValue": "1"},
            "TestAttribute3": {
                "DataType": "Binary",
                "BinaryValue": "Test binary value",
            },
        }

        entries = []

        # Send a batch without messages to a standard queue. Failure expected.
        error_message = "The list of 'entries' cannot be emtpy."
        with pytest.raises(AssertionError, match=error_message):
            self.sqs_handler.send_message_batch(
                queue_name=TEST_SQS_QUEUE, entries=entries,
            )

        # Send a batch of n messages to a standard queue. Success expected.
        number_messages = 3
        for i in range(1, number_messages + 1):
            message_id = "ID{message_number}".format(message_number=i)
            message_body = "Test message body {message_number}.".format(
                message_number=i
            )
            message = {
                "Id": message_id,
                "MessageBody": message_body,
                "MessageAttributes": message_attributes,
            }
            entries.append(message)

        response = self.sqs_handler.send_message_batch(
            queue_name=TEST_SQS_QUEUE, entries=entries,
        )
        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

        # Check whether the received message ids coincide with the ones sent.

        # Collect the message ids.
        expected_message_ids = set()
        for message_response in response["Successful"]:
            expected_message_ids.add(message_response["MessageId"])

        # We use sets because the reception order is not guaranteed.
        obtained_message_ids = set()
        queue_url = self.client.get_queue_url(QueueName=TEST_SQS_QUEUE)["QueueUrl"]

        # Set the maximum number of messages, by default it was 1.
        response = self.client.receive_message(
            QueueUrl=queue_url, MaxNumberOfMessages=number_messages
        )

        for message in response["Messages"]:
            obtained_message_ids.add(message["MessageId"])
        assert obtained_message_ids == expected_message_ids

        # Send a batch with more than the maximum allowed. Failure expected.
        max_num_messages = 10
        for i in range(number_messages + 1, max_num_messages + 2):
            message_id = "ID{message_number}".format(message_number=i)
            message_body = "Test message body {message_number}.".format(
                message_number=i
            )
            message = {
                "Id": message_id,
                "MessageBody": message_body,
                "MessageAttributes": message_attributes,
            }
            entries.append(message)

        error_message = "The maximum number of messages allowed in a batch is 10."
        with pytest.raises(AssertionError, match=error_message):
            self.sqs_handler.send_message_batch(
                queue_name=TEST_SQS_QUEUE, entries=entries,
            )

        # Send a batch with repeated ids. Failure expected.
        entries = []
        message_id = "ID1"
        message_body = "Test message body."
        message = {
            "Id": message_id,
            "MessageBody": message_body,
            "MessageAttributes": message_attributes,
        }
        entries.append(message)
        entries.append(message)

        error_message = "'ID' attribute must be unique along all the messages."
        with pytest.raises(AssertionError, match=error_message):
            self.sqs_handler.send_message_batch(
                queue_name=TEST_SQS_QUEUE, entries=entries,
            )

    def test_receive_message(self):
        # Send a message to a standard queue. Success expected.
        message_body = "Test message body."
        message_attributes = {
            "TestAttribute1": {
                "DataType": "String",
                "StringValue": "Test string value",
            },
            "TestAttribute2": {"DataType": "Number", "StringValue": "1"},
            "TestAttribute3": {
                "DataType": "Binary",
                "BinaryValue": "Test binary value",
            },
        }
        self.sqs_handler.send_message(
            queue_name=TEST_SQS_QUEUE,
            message_body=message_body,
            message_attributes=message_attributes,
        )

        response = self.sqs_handler.receive_message(queue_name=TEST_SQS_QUEUE)
        message = response["Messages"][0]
        obtained_message_body = message["Body"]
        obtained_message_attributes = message["MessageAttributes"]
        assert obtained_message_body == message_body
        assert len(obtained_message_attributes) == len(message_attributes)
        for (
            obtained_attribute_name,
            obtained_attribute_content,
        ) in obtained_message_attributes.items():
            # In the received message attributes the binary values are transformed into binary
            if obtained_attribute_content["DataType"] == "Binary":
                assert (
                    obtained_attribute_content["BinaryValue"].decode("utf8")
                    == message_attributes[obtained_attribute_name]["BinaryValue"]
                )
            else:
                assert (
                    obtained_attribute_content
                    == message_attributes[obtained_attribute_name]
                )

    def test_delete_message(self):
        # Read a message after it is deleted in the queue. Failure expected.
        message_body = "Test message body."
        message_attributes = {
            "TestAttribute1": {
                "DataType": "String",
                "StringValue": "Test string value",
            },
            "TestAttribute2": {"DataType": "Number", "StringValue": "1"},
            "TestAttribute3": {
                "DataType": "Binary",
                "BinaryValue": "Test binary value",
            },
        }
        self.sqs_handler.send_message(
            queue_name=TEST_SQS_QUEUE,
            message_body=message_body,
            message_attributes=message_attributes,
        )

        # Get the receipt handler.
        queue_url = self.client.get_queue_url(QueueName=TEST_SQS_QUEUE)["QueueUrl"]
        response = self.client.receive_message(QueueUrl=queue_url)
        message = response["Messages"][0]
        receipt_handle = message["ReceiptHandle"]

        self.sqs_handler.delete_message(
            queue_name=TEST_SQS_QUEUE, receipt_handle=receipt_handle
        )

        # Read the messages in the queue.
        queue_url = self.client.get_queue_url(QueueName=TEST_SQS_QUEUE)["QueueUrl"]
        response = self.client.receive_message(QueueUrl=queue_url)
        assert "Messages" not in response
