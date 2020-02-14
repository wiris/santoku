import boto3
import base64
import json


class FirehoseTools:
    """
    Class to handle basic AWS Kinesis Firehose operations
    """

    def __init__(self):
        self.client = boto3.client('firehose')

    def encode_base_64(self, data):
        """
        Encodes a dictionary
        :param data: (dict) data to encode, must be serializable as JSON
        :return: (blob)
        """
        encoded_data = base64.b64encode(data)
        return encoded_data

    def put_record(self, stream: str, data):
        """
        Sends a piece of data to a specific Delivery Stream
        :param stream: (str)
        :param data: (blob)
        :return: (dict)
        """
        record = {'Data': data}
        response = self.client.put_record(DeliveryStreamName=stream, Record=record)
        return response

    def put_records(self, stream: str, data):
        """
        Sends a batch of several records to a specific Delivery Stream
        :param stream: (str)
        :param data: (blob)
        :return: (dict)
        """
        response = self.client.put_records(DeliveryStreamName=stream, Data=data)
        return response

