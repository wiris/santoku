import os

import boto3
import pytest

from botocore import exceptions
from moto import mock_sqs

from santoku.aws.sqs import SQSHandler, MessageAttributeError, MessageBatchError


@pytest.fixture(scope="class")
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "eu-west-1"


@pytest.fixture(scope="class")
def sqs_handler(aws_credentials):
    with mock_sqs():
        sqs_handler = SQSHandler()
        yield sqs_handler


@pytest.fixture(scope="function")
def standard_queue(sqs_handler, request):
    queue_name = "test_standard_queue"
    sqs_client = sqs_handler.client
    try:
        sqs_client.get_queue_url(QueueName=queue_name)
    except exceptions.ClientError:
        # By catching the exception we check the queue certainly does not exist.
        pass
    else:
        raise EnvironmentError(f"{queue_name} should not exist.")
    sqs_client.create_queue(QueueName=queue_name)
    yield queue_name

    def teardown():
        queue_url = sqs_client.get_queue_url(QueueName=queue_name)["QueueUrl"]
        sqs_client.delete_queue(QueueUrl=queue_url)

    request.addfinalizer(teardown)


@pytest.fixture(scope="function")
def fifo_queue(sqs_handler, request):
    queue_name = "test_fifo_queue.fifo"
    sqs_client = sqs_handler.client
    try:
        sqs_client.get_queue_url(QueueName=queue_name)
    except exceptions.ClientError:
        pass
    else:
        raise EnvironmentError(f"{queue_name} should not exist.")
    sqs_client.create_queue(QueueName=queue_name, Attributes={"FifoQueue": "true"})
    yield queue_name

    def teardown():
        queue_url = sqs_client.get_queue_url(QueueName=queue_name)["QueueUrl"]
        sqs_client.delete_queue(QueueUrl=queue_url)

    request.addfinalizer(teardown)


@pytest.fixture(scope="function")
def message_attributes():
    return {
        "StringAttribute": {"DataType": "String", "StringValue": "Test string value",},
        "NumberAttribute": {"DataType": "Number", "StringValue": "1000000000000000",},
        "BinaryAttribute": {"DataType": "Binary", "BinaryValue": "Test binary value",},
    }


class TestSQSHandler:
    def test_check_queue_existence(self, sqs_handler, standard_queue):
        # Test an existing queue. Success expected.
        assert sqs_handler.get_queue_url(queue_name=standard_queue)

        # Test a non-existent queue. Failure expected.
        with pytest.raises(exceptions.ClientError, match="The specified queue does not exist"):
            assert sqs_handler.get_queue_url(queue_name="WRONG_QUEUE_NAME")

    def test_check_queue_is_fifo(self, sqs_handler, standard_queue, fifo_queue):
        # Test a fifo queue. Success expected.
        assert sqs_handler.check_queue_is_fifo(queue_name=fifo_queue)

        # Test a standard queue. Failure expected.
        assert not sqs_handler.check_queue_is_fifo(queue_name=standard_queue)

    def test_get_queue_url(self, sqs_handler, standard_queue):
        # Test getting the name of a queue that does exist. Success expected.
        obtained_url = sqs_handler.get_queue_url(queue_name=standard_queue)
        region = os.environ["AWS_DEFAULT_REGION"]

        # Moto uses the following account id by default. Currently programatic access is not allowed,
        # there is an issue in Moto's github repository: https://github.com/spulec/moto/issues/850.
        # Currently Moto is supposed to allow mocking entire accounts but it’s bugged (check the
        # follow link: https://github.com/spulec/moto/issues/2634). We should be patching when
        # mocking accounts/profiles becomes stable.
        moto_aws_account = "123456789012"

        expected_url = f"https://{region}.queue.amazonaws.com/{moto_aws_account}/{standard_queue}"
        assert obtained_url == expected_url

        # Test getting the name of a queue that does not exist. Failure expected.
        with pytest.raises(exceptions.ClientError, match="The specified queue does not exist"):
            sqs_handler.get_queue_url(queue_name="WRONG_QUEUE_NAME")

    def test_check_message_attributes_are_well_formed(self, sqs_handler, message_attributes):
        # Message attributes correctly structured. Success expected.
        sqs_handler.check_message_attributes_are_well_formed(message_attributes)

        # Message with more than 10 attributes. Failure expected.
        num_attributes = len(message_attributes)
        max_num_attributes = 10
        message_attribute_content = message_attributes["StringAttribute"]

        # Create 11 attributes.
        attributes = message_attributes.copy()
        for i in range(num_attributes + 1, max_num_attributes + 2):
            attributes[f"TestAttribute{i}"] = message_attribute_content

        expected_message = "Messages can have up to 10 attributes."
        with pytest.raises(MessageAttributeError, match=expected_message):
            sqs_handler.check_message_attributes_are_well_formed(attributes)

        # Message attributes not correctly structured. Failure expected.
        attributes = {"WrongAttribute": "WrongValue"}
        expected_message = "Each message attribute must be a dictionary containing 'DataType' and 'StringValue' arguments."
        with pytest.raises(MessageAttributeError, match=expected_message):
            sqs_handler.check_message_attributes_are_well_formed(attributes)

        # Message attributes that does not contain the required arguments. Failure
        # expected.
        attributes = {"WrongAttribute": {"StringValue": "Test string Value"}}
        expected_message = "'DataType' argument is missing in message attribute."
        with pytest.raises(MessageAttributeError, match=expected_message):
            sqs_handler.check_message_attributes_are_well_formed(attributes)

        attributes = {"WrongAttribute": {"DataType": "String", "BinaryValue": "Test string value"}}
        expected_message = (
            "'StringValue' argument is required for message attributes of type String."
        )
        with pytest.raises(MessageAttributeError, match=expected_message):
            sqs_handler.check_message_attributes_are_well_formed(attributes)

        attributes = {"WrongAttribute": {"DataType": "Number", "BinaryValue": "1"}}
        expected_message = (
            "'StringValue' argument is required for message attributes of type Number."
        )
        with pytest.raises(MessageAttributeError, match=expected_message):
            sqs_handler.check_message_attributes_are_well_formed(attributes)

        attributes = {"WrongAttribute": {"DataType": "Binary", "StringValue": "Test binary value"}}
        expected_message = (
            "'BinaryValue' argument is required for message attributes of type Binary."
        )
        with pytest.raises(MessageAttributeError, match=expected_message):
            sqs_handler.check_message_attributes_are_well_formed(attributes)

    def test_send_message(self, sqs_handler, standard_queue, message_attributes):
        # Send a message to a standard queue. Success expected.
        message_body = "Test message body."
        response = sqs_handler.send_message(
            queue_name=standard_queue,
            message_body=message_body,
            message_attributes=message_attributes,
        )
        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

        # Check if the received ids match the sent ones.
        expected_message_id = response["MessageId"]

        queue_url = sqs_handler.client.get_queue_url(QueueName=standard_queue)["QueueUrl"]
        response = sqs_handler.client.receive_message(QueueUrl=queue_url)
        obtained_message_id = response["Messages"][0]["MessageId"]
        assert obtained_message_id == expected_message_id

    def test_send_message_batch(self, sqs_handler, standard_queue, message_attributes):
        entries = []

        # Send a batch without messages to a standard queue. Failure expected.
        error_message = "The list of 'entries' cannot be emtpy."
        with pytest.raises(MessageBatchError, match=error_message):
            sqs_handler.send_message_batch(
                queue_name=standard_queue, entries=entries,
            )

        # Send a batch of n messages to a standard queue. Success expected.
        number_messages = 3
        for i in range(1, number_messages + 1):
            message_id = f"ID{i}"
            message_body = f"Test message body {i}."
            message = {
                "Id": message_id,
                "MessageBody": message_body,
                "MessageAttributes": message_attributes,
            }
            entries.append(message)

        response = sqs_handler.send_message_batch(queue_name=standard_queue, entries=entries,)
        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

        # Check whether the received message ids coincide with the ones sent.

        # Collect the message ids.
        expected_message_ids = set()
        for message_response in response["Successful"]:
            expected_message_ids.add(message_response["MessageId"])

        # We use sets because the reception order is not guaranteed.
        obtained_message_ids = set()
        queue_url = sqs_handler.client.get_queue_url(QueueName=standard_queue)["QueueUrl"]

        # Set the maximum number of messages, by default it was 1.
        response = sqs_handler.client.receive_message(
            QueueUrl=queue_url, MaxNumberOfMessages=number_messages
        )

        for message in response["Messages"]:
            obtained_message_ids.add(message["MessageId"])
        assert obtained_message_ids == expected_message_ids

        # Send a batch with more than the maximum allowed. Failure expected.
        max_num_messages = 10
        for i in range(number_messages + 1, max_num_messages + 2):
            message_id = f"ID{i}"
            message_body = f"Test message body {i}."
            message = {
                "Id": message_id,
                "MessageBody": message_body,
                "MessageAttributes": message_attributes,
            }
            entries.append(message)

        error_message = "The maximum number of messages allowed in a batch is 10."
        with pytest.raises(MessageBatchError, match=error_message):
            sqs_handler.send_message_batch(
                queue_name=standard_queue, entries=entries,
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
        with pytest.raises(MessageBatchError, match=error_message):
            sqs_handler.send_message_batch(
                queue_name=standard_queue, entries=entries,
            )

    def test_receive_message(self, sqs_handler, standard_queue, message_attributes):
        # Send a message to a standard queue. Success expected.
        message_body = "Test message body."
        sqs_handler.send_message(
            queue_name=standard_queue,
            message_body=message_body,
            message_attributes=message_attributes,
        )

        response = sqs_handler.receive_message(queue_name=standard_queue)
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
                assert obtained_attribute_content == message_attributes[obtained_attribute_name]

    def test_delete_message(self, sqs_handler, standard_queue, message_attributes):
        # Read a message after it is deleted in the queue. Failure expected.
        message_body = "Test message body."
        sqs_handler.send_message(
            queue_name=standard_queue,
            message_body=message_body,
            message_attributes=message_attributes,
        )

        # Get the receipt handler.
        queue_url = sqs_handler.client.get_queue_url(QueueName=standard_queue)["QueueUrl"]
        response = sqs_handler.client.receive_message(QueueUrl=queue_url)
        message = response["Messages"][0]
        receipt_handle = message["ReceiptHandle"]

        sqs_handler.delete_message(queue_name=standard_queue, receipt_handle=receipt_handle)

        # Read the messages in the queue.
        queue_url = sqs_handler.client.get_queue_url(QueueName=standard_queue)["QueueUrl"]
        response = sqs_handler.client.receive_message(QueueUrl=queue_url)
        assert "Messages" not in response
