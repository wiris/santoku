import boto3
from io import StringIO


class S3Tools:
    """
    Class to handle input/output operations with Amazon's S3 storage service.

    This class is intended to be run on AWS Glue job (Python Shell).
    """

    def __init__(self):
        self.client = boto3.client('s3')
        self.resource = boto3.resource('s3')

    # Function to get all keys (files) from S3 bucket and prefix
    def get_keys_as_generator(self, bucket, prefix, start_after='null'):
        kwargs = {'Bucket': bucket, 'Prefix': prefix, 'StartAfter': start_after}
        while True:
            resp = self.client.list_objects_v2(**kwargs)
            for obj in resp['Contents']:
                yield obj['Key']

            try:
                kwargs['ContinuationToken'] = resp['NextContinuationToken']
            except KeyError:
                break

    '''
    def paginate(self, method, **kwargs):
    """
    Same as get_keys_as_generator but not limited to 1k objects, generic syntax for other services other than s3 and
    other methods other than list_objects_v2. Needs testing
    :param method: method to list the objects, here it will usually be self.client.list_objects_v2
    :param kwargs: arguments for the above method, e.g.
    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#S3.Client.list_objects_v2
    in this case, for list_objects_v2 kwargs would need Bucket, Prefix and possibly StartAfter
    :return: yields an iterable with the objects in the s3
    """
    paginator = self.client.get_paginator(method.__name__)
    for page in paginator.paginate(**kwargs).result_key_iters():
        for result in page:
            yield result
    '''

    # Read file at s3 bucket with given key. Use provided encoding
    def get_file_content(self, bucket, file_key, encoding='utf-8'):
        file_obj = self.resource.Object(bucket, file_key)
        file_content = file_obj.get()['Body'].read().decode(encoding)
        return file_content

    def write_file(self, content, bucket, file_key):
        self.client.put_object(Body=content, Bucket=bucket, Key=file_key)

    def delete_file(self, bucket, file_key):
        # high level version
        self.resource.Object(bucket, file_key).delete()
        # low level version. needs the object to be null
        # self.client.delete_object(Bucket=bucket, Key=file_key)

    def delete_files(self, bucket, file_keys):
        # high level version, might be inefficient
        for key in file_keys:
            self.delete_file(bucket, key)
        # low level version, needs the objects to be null
        # objects = [{'Key': key, 'VersionId': 'null'} for key in file_keys]
        # delete_dict = {'Objects': objects, 'Quiet': True}
        # self.client.delete_objects(Bucket=bucket, Delete=delete_dict)

    def write_dataframe_to_csv_file(self, dataframe, bucket, file_key, encoding='utf-8'):
        # Get pandas dataframe as CSV bytes
        csv_buffer = StringIO()
        dataframe.to_csv(csv_buffer)
        bytes_content = csv_buffer.getvalue().encode(encoding)

        self.write_file(bytes_content, bucket, file_key)

    def generate_quicksight_manifest(self, files, save_to):
        """
        TO DO: generate and save a QS manifest from a list of file paths in S3
        :param save_to:
        :param files:
        :return:
        """
        return
