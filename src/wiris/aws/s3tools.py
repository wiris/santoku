import boto3
from io import StringIO

class s3tools:
    '''
    Class to handle input/output operations with Amazon's S3 storage service.

    This class is intended to be run on AWS Glue job (Python Shell).
    '''

    def __init__(self):
        self.client = boto3.client('s3')
        self.resource = boto3.resource('s3')

    # Function to get all keys (files) from S3 bucket and prefix
    def get_keys_as_generator(self, bucket, prefix):
        kwargs = {'Bucket': bucket, 'Prefix': prefix}
        while True:
            resp = self.client.list_objects_v2(**kwargs)
            for obj in resp['Contents']:
                yield obj['Key']

            try:
                kwargs['ContinuationToken'] = resp['NextContinuationToken']
            except KeyError:
                break

    # Read file at s3 bucket with given key. Use provided encoding
    def get_file_content(self, bucket, file_key, encoding='utf-8'):
        file_obj = self.resource.Object(bucket, file_key)
        file_content = file_obj.get()['Body'].read().decode(encoding)
        return file_content

    def write_file(self, content, bucket, file_key):
        self.client.put_object(Body=content, Bucket=bucket, Key=file_key)

    def write_dataframe_to_csv_file(self, dataframe, bucket, file_key, encoding='utf-8'):
        # Get pandas dataframe as CSV bytes
        csv_buffer = StringIO()
        dataframe.to_csv(csv_buffer)
        bytes_content = csv_buffer.getvalue().encode(encoding)

        self.write_file(bytes_content, bucket, file_key)
