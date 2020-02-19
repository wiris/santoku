import boto3
import json
from io import StringIO


class S3:
    """
    Class to handle input/output operations with Amazon's S3 storage service.

    This class is intended to be run on AWS Glue jobs (Python Shell).
    """

    def __init__(self):
        self.client = boto3.client('s3', aws_access_key_id='AKIAYQXDKERZA5644OGN', aws_secret_access_key='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')
        self.resource = boto3.resource('s3')


    @staticmethod
    def get_absolute_path(bucket, file_key, prefix=None, prefix_is_folder=True):
        """
        Absolute S3 path string (URI) of a file from its bucket, prefix and key
        :param bucket: S3 bucket
        :param file_key: relative path inside the bucket. relative path within the prefix if a prefix is passed
        :param prefix: (optional) S3 prefix within the bucket
        :param prefix_is_folder: (optional) whether the prefix marks a folder
        """
        if prefix is not None:
            if prefix_is_folder:
                if prefix[-1] == '/':
                    return 's3://' + bucket + '/' + prefix + file_key
                else:
                    return 's3://' + bucket + '/' + prefix + '/' + file_key
            else:
                return 's3://' + bucket + '/' + prefix + file_key
        else:
            return 's3://' + bucket + '/' + file_key

    def get_keys_as_generator(self, bucket, prefix, start_after=None):
        """
        Generates all keys (files) given S3 bucket and prefix
        :param bucket:
        :param prefix:
        :param start_after:
        :return:
        """
        kwargs = {}
        if start_after is None:
            kwargs = {'Bucket': bucket, 'Prefix': prefix}
        else:
            kwargs = {'Bucket': bucket, 'Prefix': prefix, 'StartAfter': start_after}
        while True:
            resp = self.client.list_objects_v2(**kwargs)
            for obj in resp['Contents']:
                yield obj['Key']

            try:
                kwargs['ContinuationToken'] = resp['NextContinuationToken']
            except KeyError:
                break

    def paginate(self, method, **kwargs):
        """
        Same as get_keys_as_generator but with generic syntax for other services other than s3 and methods other than
        list_objects_v2. It returns objects rather than keys. To get keys use result['Key'].
        More information on paginators:
        https://boto3.amazonaws.com/v1/documentation/api/latest/guide/paginators.html
        :param method: method used to list the objects, here it will usually be self.client.list_objects_v2
        :param kwargs: arguments for the specified method
        :return: yields an iterable with the objects in the s3
        """
        paginator = self.client.get_paginator(method.__name__)
        for page in paginator.paginate(**kwargs).result_key_iters():
            for result in page:
                yield result

    def list_objects(self, bucket, prefix=None, **kwargs):
        """
        Generates all object keys within a bucket, via boto3.client('s3').list_objects_v2
        :param bucket: S3 bucket to iterate in. Required since list-objects_v2 requires Bucket
        :param prefix: (optional) prefix within the bucket
        :param kwargs: other arguments for list_objects_v2, e.g. StartAfter. More information:
        https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#S3.Client.list_objects_v2
        """
        args = {'Bucket': bucket}
        if prefix is not None:
            args.update({'Prefix': prefix})
        args.update(**kwargs)
        for result in self.paginate(self.client.list_objects_v2, **args):
            yield result['Key']

    def get_file_content(self, bucket, file_key, encoding='utf-8'):
        """
        Read file at S3 bucket with given key. Use provided encoding
        :param bucket:
        :param file_key:
        :param encoding:
        :return:
        """
        file_obj = self.resource.Object(bucket, file_key)
        file_content = file_obj.get()['Body'].read().decode(encoding)
        return file_content

    def write_file(self, content, bucket, file_key):
        """
        Write the contents of a file into S3
        :param content:
        :param bucket:
        :param file_key:
        :return:
        """
        self.client.put_object(Body=content, Bucket=bucket, Key=file_key)

    def delete_file(self, bucket, file_key, mode='resource'):
        """
        Deletes an object from S3
        :param bucket: S3 bucket
        :param file_key: object key to delete
        :param mode: use resource (high level API) or client (low level, only if you know what you are doing)
        """
        if mode == 'resource':
            self.resource.Object(bucket, file_key).delete()
        elif mode == 'client':
            # low level version. needs the object to be null
            self.client.delete_object(Bucket=bucket, Key=file_key)
        else:
            raise Exception('invalid mode value: {}'.format(mode))

    def delete_files(self, bucket, file_keys, mode='resource'):
        """
        Deletes a list of objects from a single bucket in S3
        :param bucket: S3 bucket
        :param file_keys: iterable of object keys to delete
        :param mode: use resource (high level API) or client (low level, only if you know what you are doing)
        """
        if mode == 'resource':
            # high level version, might be inefficient
            for key in file_keys:
                self.delete_file(bucket, key, mode=mode)
        elif mode == 'client':
            # low level version, needs the objects to be null
            objects = [{'Key': key, 'VersionId': 'null'} for key in file_keys]
            delete_dict = {'Objects': objects, 'Quiet': True}
            self.client.delete_objects(Bucket=bucket, Delete=delete_dict)
        else:
            raise Exception('invalid mode value: {}'.format(mode))

    def write_dataframe_to_csv_file(self, dataframe, bucket, file_key, encoding='utf-8', save_index=False):
        """
        Write a pandas dataframe to an S3 location (bucket + key)
        :param dataframe: pandas dataframe to save
        :param bucket: S3 bucket where we wish to save
        :param file_key: local path of the file where we wish to save the dataframe
        :param encoding: (optional) save with a particular encoding, default is utf-8
        :param save_index: (optional) whether so save the index as a column, defaults to False
        :return:
        """
        # Get pandas dataframe as CSV bytes
        csv_buffer = StringIO()
        dataframe.to_csv(csv_buffer, index=save_index)
        bytes_content = csv_buffer.getvalue().encode(encoding)

        self.write_file(bytes_content, bucket, file_key)

    def generate_quicksight_manifest(self, bucket, file_key, s3_path=None, s3_prefix=None,
                                     set_format=None, set_delimiter=None, set_qualifier=None, set_header=None):
        """
        Generates a QS manifest JSON file from a list of files and/or prefixes and saves it to a specified S3 location
        More info on format: https://docs.aws.amazon.com/quicksight/latest/user/supported-manifest-file-format.html
        :param bucket: bucket to save the generated manifest
        :param file_key: file key to save the manifest in the specified bucket (.json)
        :param s3_path: list or tuple of S3 absolute paths to specific files. Check the link above for valid formats
        :param s3_prefix: list or tuple of S3 prefixes. Check the link above for valid formats
        :param set_format: (optional) format of files to be imported (e.g. "CSV"). Check AWS docs link for valid formats
        :param set_delimiter: (optional) file field delimiter (e.g. ","). Must map to the above format
        :param set_qualifier: (optional) file text qualifier (e.g. "'").  Check AWS docs link for allowed values
        :param set_header: (optional) whether the files have a header row. Valid values are True of False
        """
        # check for files
        if s3_prefix is None and s3_path is None:
            raise Exception('no file nor prefix were specified')

        # absolute paths of specific files
        uri = {}
        if s3_path is not None:
            uri["URIs"] = list(s3_path)

        # prefixes to include all files with that prefix
        uri_prefixes = {}
        if s3_prefix is not None:
            uri_prefixes["URIPrefixes"] = list(s3_prefix)

        # global upload settings (if any)
        upload_settings = {}
        if set_format is not None:
            upload_settings["format"] = set_format
        if set_delimiter is not None:
            upload_settings["delimiter"] = set_delimiter
        if set_qualifier is not None:
            upload_settings["textqualifier"] = set_delimiter
        if set_header is not None:
            upload_settings['containsHeader'] = set_header

        # construct JSON file
        data = {"fileLocations": []}
        if s3_path is not None:
            data["fileLocations"].append(uri)
        if s3_prefix is not None:
            data['fileLocations'].append(uri_prefixes)
        if upload_settings:
            data["globalUploadSettings"] = upload_settings
        json_content = json.dumps(data, indent=4, sort_keys=True)

        # save to specified location
        self.write_file(json_content, bucket, file_key)
