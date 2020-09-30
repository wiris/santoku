import boto3

from typing import Any, Dict, List

from botocore import exceptions


class MessageAttributeError(Exception):
    def __init__(self, message):
        super().__init__(message)


class MessageBatchError(Exception):
    def __init__(self, message):
        super().__init__(message)


class SQSHandler:
    """
    Class to manage operations of Amazon Simple Queue Service (SQS).

    This class is intended to be run on AWS Glue jobs (Python Shell). SQS consists in hosted queues
    that allow sending and receiving messages. This class provides methods to interact with SQS
    queues and makes easy some usual operations. The connection to the SQS queues is done using the
    service class Client of the boto3 library.

    """

    def __init__(self, **kwargs) -> None:
        """
        Instantiate the services classes.

        Parameters
        ----------
        region_name : str
            AWS Region in which to operate the service.

        Notes
        -----
            More information on the available regions: [1]

        References
        ----------
        [1] :
        https://aws.amazon.com/about-aws/global-infrastructure/regions_az/

        """
        self.client = boto3.client(service_name="sqs", **kwargs)
        # Cache to store the url of each queue.
        self.queue_url: Dict[str, str] = {}

    def check_queue_is_fifo(self, queue_name: str) -> bool:
        """
        Check if a queue is of type FIFO.

        Parameters
        ----------
        queue_name : str
            Name of queue.

        Returns
        -------
        bool
            True if the queue is of type FIFO, False if it is standard.

        """
        return queue_name[-5:] == ".fifo"

    def get_queue_url(self, queue_name: str) -> str:
        """
        Return the url of the queue.

        Parameters
        ----------
        queue_name : str
            Name of queue.

        Returns
        -------
        str
            The url of the queue called `queue_name`.

        Raises
        ------
        botocore.exceptions.ClientError
            If the queue does not exist.

        Notes
        -----
        The account url has the form: https://region_name.queue.amazonaws.com/account_number/queue_name
        More information on queue urls: [1]

        References
        ----------
        [1] :
        https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-general-identifiers.html

        """
        try:
            response = self.client.get_queue_url(QueueName=queue_name)
            queue_url = response["QueueUrl"]
            return queue_url
        except exceptions.ClientError as e:
            raise e

    def check_message_attributes_are_well_formed(
        self, message_attributes: Dict[str, Dict[str, str]]
    ) -> None:
        """
        Check whether the message attributes are correct.

        Check if the message attributes are following the structure that AWS SQS requires. A boolean
        will be returned together with an error message in case it is not correctly structured.

        Parameters
        ----------
        message_attributes : Dict[str, Dict[str, str]]
            Message attributes to send.

        Returns
        -------
        Tuple[bool, str]
            True and an empty message will be returned if the message attributes are correclty
            formed. False and an error message explaining the error will be returned otherwise.

        Raises
        ------
        MessageAttributeError
            If the message attributes are not correclty structured.

        Notes
        -----
        A message attribute can be of `DataType` Binary, Number and String.
        The `TypeValue` of the attribute must be StringValue if `DataType` is String or Number, and
        BinaryValue if `DataType` is Binary. StringListValues and BinaryListValues are
        options that should be accepted in the future but are not implemented yet. Strings are
        Unicode with UTF-8 binary encoding. Each message can have up to 10 message attributes.
        More information on the sqs message attributes: [1]

        References
        ----------
        [1] :
        https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-message-attributes.html

        """

        if len(message_attributes) > 10:
            error_message = "Messages can have up to 10 attributes."
            raise MessageAttributeError(error_message)

        for _, attribute_content in message_attributes.items():

            if not isinstance(attribute_content, dict):
                error_message = "Each message attribute must be a dictionary containing 'DataType' and 'StringValue' arguments."
                raise MessageAttributeError(error_message)

            if "DataType" not in attribute_content:
                error_message = "'DataType' argument is missing in message attribute."
                raise MessageAttributeError(error_message)

            if attribute_content["DataType"] not in ["Binary", "Number", "String"]:
                error_message = (
                    "The supported types for 'DataType' argument are: Binary, Number and String."
                )
                raise MessageAttributeError(error_message)

            if attribute_content["DataType"] == "String" and "StringValue" not in attribute_content:
                error_message = (
                    "'StringValue' argument is required for message attributes of type String."
                )
                raise MessageAttributeError(error_message)

            if attribute_content["DataType"] == "Number" and "StringValue" not in attribute_content:
                error_message = (
                    "'StringValue' argument is required for message attributes of type Number."
                )
                raise MessageAttributeError(error_message)

            if attribute_content["DataType"] == "Binary" and "BinaryValue" not in attribute_content:
                error_message = (
                    "'BinaryValue' argument is required for message attributes of type Binary."
                )
                raise MessageAttributeError(error_message)

        return None

    def send_message(
        self,
        queue_name: str,
        message_body: str,
        message_attributes: Dict[str, Dict[str, Any]] = {},
    ) -> Dict[str, Any]:
        """
        Deliver a message to a SQS Queue.

        A message with `message_body` and optionally `message_attributes` will be sent to the queue
        named `queue_name`.

        Parameters
        ----------
        queue_name : str
            Name of the queue to send the message.
        message_body : str
            Body of of the message to be sent.
        message_attributes : Dict[str, Dict[str, Any]], optional
            Attributes of the message to send. Will be empty by default.

        Returns
        -------
        Dict[str, Any]
            A response containing information about messages sent. In these information we can find
            the message id that identifies the message, and metadata containing the HTTP status code
            of each message.

        Raises
        ------
        MessageAttributeError
            If the message argument is not correctly structured.

        See Also
        --------
        get_queue_url : this method retrieves the queue url with the given queue name.
        check_message_attributes_are_well_formed : this method checks the given message attritutes.

        Notes
        -----
        The maximum size that a message can have is 256KB (message body and attributes all together).

        """

        # Update the urls if not registered yet.
        if queue_name in self.queue_url:
            queue_url = self.queue_url[queue_name]
        else:
            queue_url = self.get_queue_url(queue_name=queue_name)
            self.queue_url[queue_name] = queue_url

        if message_attributes:
            # Check whether the message attributes are correctly structured.
            try:
                self.check_message_attributes_are_well_formed(message_attributes=message_attributes)
            except MessageAttributeError:
                raise

            response = self.client.send_message(
                QueueUrl=queue_url, MessageBody=message_body, MessageAttributes=message_attributes,
            )

        else:
            response = self.client.send_message(QueueUrl=queue_url, MessageBody=message_body)

        return response

    def send_message_batch(self, queue_name: str, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Deliver a list of messages to a SQS Queue.

        A list of batch request `entries` containing details of the messages will be sent to the
        queue named `queue_name`.

        Parameters
        ----------
        queue_name : str
            Name of the queue to send the batch of messages.
        entries : List[Dict[str, Any]]
            List of messages containing a unique message Id, a message body and message attributes
            optionally.

        Returns
        -------
        Dict[str, Any]
            A response containing information about messages sent. In this information
            we can find the message id that identifies each message, and metadata containing the
            HTTP status code of each message.

        Raises
        ------
        MessageAttributeError
            If any message does not contain id or message body, if the ids are not unique, or if the
            message attributes are not correctly structured.

        See Also
        --------
        get_queue_url : this method retreives the queue url with the given queue name.
        check_message_attributes_are_well_formed : this method checks the message attributes given.

        Notes
        -----
        A batch can contain up to 10 messages.
        The maximum size that the batch of messages can have is 256KB, this means the sum of all
        messages (message body and attributes all together) cannot exceed 256KB.

        """
        if not entries:
            error_message = "The list of 'entries' cannot be emtpy."
            raise MessageBatchError(error_message)

        if len(entries) > 10:
            error_message = "The maximum number of messages allowed in a batch is 10."
            raise MessageBatchError(error_message)

        # Check if all message have the required attributes and if the message attributes are
        # correctly structured.
        entries_ids = []
        for entry in entries:

            if "Id" not in entry:
                error_message = "'Id' attribute is required for each message."
                raise MessageBatchError(error_message)
            entries_ids.append(entry["Id"])

            if "MessageBody" not in entry:
                error_message = "'MessageBody' attribute is required for each message."
                raise MessageBatchError(error_message)

            if "MessageAttributes" in entry:
                try:
                    self.check_message_attributes_are_well_formed(entry["MessageAttributes"])
                except MessageAttributeError:
                    raise

        # Check the message ids are unique along the batch.
        if len(entries_ids) != len(set(entries_ids)):
            error_message = "'ID' attribute must be unique along all the messages."
            raise MessageBatchError(error_message)

        # Update the urls if not registered yet.
        if queue_name in self.queue_url:
            queue_url = self.queue_url[queue_name]
        else:
            queue_url = self.get_queue_url(queue_name=queue_name)
            self.queue_url[queue_name] = queue_url

        response = self.client.send_message_batch(QueueUrl=queue_url, Entries=entries)
        return response

    def receive_message(self, queue_name: str) -> Dict[str, Any]:
        """
        Retrieves multiple messages from the SQS Queue.

        Parameters
        ----------
        queue_name : str
            Name of the queue to receive a message.

        Returns
        -------
        Dict[str, Any]
            A response containing information about the received messages. In these information we
            can find the message id that identifies each message, the receipt handle used to delte
            the message, and the content of the message such as the message body and message
            attributes.

        Raises
        ------
        MessageAttributeError
            If any message does not contain id or message body, if the ids are not unique, if the
            message attributes are not correctly structured.

        See Also
        --------
        get_queue_url : this method retreives the queue url with the given queue name.
        check_message_attributes_are_well_formed : this method checks the message attributes given.

        Notes
        -----
        The maximum number of messages we can receive in each call is 10.
        There is an attribute called visibility timeout, that is the time that SQS keep a message
        invisible after it has been received once. After that period of time the message will be
        visible again. This is why removing the message after receiving it is so important.

        References
        ----------
        [1] :
        https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sqs.html#SQS.Client.receive_message

        """
        # Update the urls if not registered yet.
        if queue_name in self.queue_url:
            queue_url = self.queue_url[queue_name]
        else:
            queue_url = self.get_queue_url(queue_name=queue_name)
            self.queue_url[queue_name] = queue_url

        response = self.client.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=10)
        return response

    def delete_message(self, queue_name: str, receipt_handle: str) -> None:
        """
        Remove a message from the queue.

        A message with the `receipt_handle` will be deleted from the queue with name `queue_name`.

        Parameters
        ----------
        queue_name : str
            Name of the queue to delete the message from.
        receipt_handle : str
            Identifier obtained from receiving the message to delete.

        Returns
        -------
        None

        See Also
        --------
        get_queue_url : this method retreives the queue url with the given queue name.

        Notes
        -----
        You must always receive a message before you can delete it (you can't put a message into the
        queue and then recall it.
        The difference between the receipt handle and the message id is that the first one is
        associated with the action of receiving the message and not the message itself.
        More information on the receipt handle: [1]

        References
        ----------
        [1]:
        https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-general-identifiers.html

        """
        # Update the urls if not registered yet.
        if queue_name in self.queue_url:
            queue_url = self.queue_url[queue_name]
        else:
            queue_url = self.get_queue_url(queue_name=queue_name)
            self.queue_url[queue_name] = queue_url

        self.client.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
        return None
