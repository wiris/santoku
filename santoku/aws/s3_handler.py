import boto3
import json
import botocore
import pandas as pd
from typing import Any
from typing import Dict
from typing import Generator
from io import StringIO


class S3Handler:
    """
    Class to handle input/output operations with Amazon's S3 storage service.

    This class is intended to be run on AWS Glue jobs (Python Shell).
    """

    def __init__(self):
        self.client = boto3.client("s3")
        self.resource = boto3.resource("s3")

    @staticmethod
    def get_absolute_path(
        bucket: str, key: str, prefix: str = None, prefix_is_folder: bool = True
    ) -> str:
        """
        Absolute S3 path string (URI) of a file from its bucket, prefix and key
        :param bucket: S3 bucket to get the absolute path from.
        :param file_key: relative path inside the bucket. Relative path within the prefix if a prefix is passed.
        :param prefix: (optional) S3 prefix within the bucket.
        :param prefix_is_folder: (optional) whether the prefix marks a folder.
        """
        if prefix is not None:
            if prefix_is_folder:
                if prefix[-1] == "/":
                    return "s3://" + bucket + "/" + prefix + key
                else:
                    return "s3://" + bucket + "/" + prefix + "/" + key
            else:
                return "s3://" + bucket + "/" + prefix + key
        else:
            return "s3://" + bucket + "/" + key

    # This method can be shared by different services, not only s3.
    def paginate(self, method: str, **kwargs: Any):
        """
        Same as get_keys_as_generator but with generic syntax for other services other than s3 and methods other than
        list_objects_v2. It returns objects rather than keys. To get keys use result['Key'].
        More information on paginators:
        https://boto3.amazonaws.com/v1/documentation/api/latest/guide/paginators.html
        :param method: name of the method used to list the objects, here it will usually be self.client.list_objects_v2.
        :param kwargs: arguments for the specified method. Bucket property must be specified.
        :return: yields an iterable with the objects in the s3.
        """
        paginator = self.client.get_paginator(operation_name=method)
        for page in paginator.paginate(**kwargs).result_key_iters():
            for result in page:
                yield result

    def list_objects(
        self, bucket: str, prefix: str = None, **kwargs: Any
    ) -> Generator[str, None, None]:
        """
        Generates all object keys within a bucket, via boto3.client('s3').list_objects_v2.
        More information on list_objects_v2 method:
        https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#S3.Client.list_objects_v2
        :param bucket: S3 bucket to iterate in. Required since list-objects_v2 requires Bucket.
        :param prefix: (optional) prefix within the bucket.
        :param kwargs: other arguments for list_objects_v2, e.g. StartAfter.
        """
        args = {"Bucket": bucket}
        if prefix is not None:
            args.update({"Prefix": prefix})
        args.update(**kwargs)
        for result in self.paginate(
            method=self.client.list_objects_v2.__name__, **args
        ):
            yield result["Key"]

    def key_exist(self, bucket: str, key: str) -> bool:
        """
        Check whether a key exist in the bucket.
        :param bucket: S3 bucket to iterate in. Required since list-objects_v2 requires Bucket.
        :param key: (optional) prefix within the bucket.
        """
        try:
            self.resource.Object(bucket_name=bucket, key=key).load()
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            else:
                raise
        return True

    def read_key_content(self, bucket: str, key: str, encoding="utf-8") -> str:
        """
        Read file at S3 bucket with given key. Use provided encoding
        :param bucket: S3 bucket containing the file.
        :param file_key: key of the file to be read.
        :param encoding: encoding used in the content.
        :return: the decoded content of the file.
        """
        key_obj = self.resource.Object(bucket_name=bucket, key=key)
        file_content = key_obj.get()["Body"].read().decode(encoding)
        return file_content

    def put_key(self, bucket: str, key: str, content: bytes) -> None:
        """
        Write the contents of a file into S3
        :param content: content in bytes to be writen to the file.
        :param bucket: S3 bucket containing the file.
        :param file_key: key of the file to be writen.
        """
        self.client.put_object(Body=content, Bucket=bucket, Key=key)

    def delete_key(self, bucket: str, key: str) -> None:
        """
        Deletes an object from S3
        :param bucket: S3 bucket containing the file.
        :param file_key: object key to delete.
        :param mode: use resource (high level API) or client (low level, only if you know what you are doing)
        """
        self.resource.Object(bucket_name=bucket, key=key).delete()

    def delete_keys(self, bucket: str, keys: list) -> None:
        """
        Deletes a list of objects from a single bucket in S3
        :param bucket: S3 bucket containing the files.
        :param file_keys: iterable of object keys to delete.
        :param mode: use resource (high level API) or client (low level, only if you know what you are doing)
        """
        for key in keys:
            self.delete_key(bucket=bucket, key=key)

    def write_dataframe_to_csv_key(
        self,
        bucket: str,
        key: str,
        dataframe: pd.DataFrame,
        encoding: str = "utf-8",
        save_index: bool = False,
    ) -> None:
        """
        Write a pandas dataframe to an S3 location (bucket + key)
        :param dataframe: pandas dataframe to save
        :param bucket: S3 bucket where we wish to save
        :param file_key: local path of the file where we wish to save the dataframe
        :param encoding: (optional) save with a particular encoding, default is utf-8
        :param save_index: (optional) whether so save the index as a column, defaults to False
        """
        # Get pandas dataframe as CSV bytes
        csv_buffer = StringIO()
        dataframe.to_csv(csv_buffer, index=save_index)
        bytes_content = csv_buffer.getvalue().encode(encoding)
        self.put_key(bucket=bucket, key=key, content=bytes_content)

    def generate_quicksight_manifest(
        self,
        bucket: str,
        key: str,
        s3_path: str = None,
        s3_prefix: str = None,
        set_format: str = None,
        set_delimiter: str = None,
        set_qualifier: str = None,
        set_header: str = None,
    ):
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
        # Check for key.
        if s3_prefix is None and s3_path is None:
            raise Exception("no file nor prefix were specified")

        # Absolute paths of specific keys.
        uri = {}
        if s3_path is not None:
            uri["URIs"] = list(s3_path)

        # Prefixes to include all keys with that prefix.
        uri_prefixes = {}
        if s3_prefix is not None:
            uri_prefixes["URIPrefixes"] = list(s3_prefix)

        # Global upload settings (if any)
        upload_settings = {}
        if set_format is not None:
            upload_settings["format"] = set_format
        if set_delimiter is not None:
            upload_settings["delimiter"] = set_delimiter
        if set_qualifier is not None:
            upload_settings["textqualifier"] = set_qualifier
        if set_header is not None:
            upload_settings["containsHeader"] = set_header

        # Construct JSON file.
        data: Dict[str, Any] = {"fileLocations": []}
        if s3_path is not None:
            data["fileLocations"].append(uri)
        if s3_prefix is not None:
            data["fileLocations"].append(uri_prefixes)
        if upload_settings:
            data["globalUploadSettings"] = upload_settings
        json_content = json.dumps(data, indent=4, sort_keys=True)
        bytes_content = json_content.encode("utf-8")
        # save to specified location
        self.put_key(bucket=bucket, key=key, content=bytes_content)
