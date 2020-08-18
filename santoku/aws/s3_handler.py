import os
import json

import boto3
import pandas as pd

from io import StringIO, BytesIO
from typing import Any, Dict, List, Generator

from botocore import exceptions

from santoku.aws import utils


class ManifestError(Exception):
    def __init__(self, message):
        super().__init__(message)


class S3Handler:
    """
    Class to manage input/output operations of Amazon S3 storage services.

    This class is intended to be run on AWS Glue jobs (Python Shell). S3 is organized in buckets,
    that contains a collection of files identified by a path. The connection to the elements of S3
    are done using the services classes Client and Resource of the library boto3. This class
    provides methods to interact with S3 elements and makes easy some usual operations.

    """

    def __init__(self, **kwargs):
        """ Instantiate the services classes. """
        self.client = boto3.client(service_name="s3", **kwargs)
        self.resource = boto3.resource(service_name="s3")

    @staticmethod
    def get_uri(bucket: str, folder_path: str = "", file_name: str = "") -> str:
        """
        Absolute S3 path (URI) of a file.

        Build an absolute S3 path containing the `bucket`, the `folder_path`
        and the `file_name` of the file. This method can be useful when some methods require an
        absolute path of the files.

        Parameters
        ----------
        bucket : str
            Name of bucket to build the absolute path with.
        folder_path : str, optional
            Relative folder path to build the absolute path with.
        file_name : str, optional
            Name of the file object to build the absolute path with.

        Returns
        -------
        str
            Absolut S3 URI of the file.

        """
        # Prevent os.path.join from considering folder_path as absolute path.
        if folder_path and folder_path[0] == "/":
            folder_path = folder_path[1:]
        return os.path.join("s3://", bucket, folder_path, file_name)

    def list_objects(self, bucket: str, **kwargs: Dict[str, str]) -> Generator[str, None, None]:
        """
        Get all objects in a specific location.

        Get the object keys located in the `bucket`. Yields an iterable
        with the found object keys in alphabetical order.

        Parameters
        ----------
        bucket : str
            Name of the bucket to iterate in.
        kwargs : Any
            Additional arguments for the used method boto3.client.list_objects_v2. Some usual
            arguments are Prefix (str), that filters those object keys that begin with the specified
            string, or StartAfter (str), that indicates where must S3 start listing from.

        Yields
        ------
        Generator[str, None, None]
            The object keys located in the `bucket` in alphabetical order.

        Notes
        -----
        This method will never add objects partially, or all objects will be added or none of them.
        If there are multiple write requests of the same object simultaneously, it overwrites all
        but the last object written. More information on list_objects_v2 method: [1].

        References
        ----------
        [1] :
        https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#S3.Client.list_objects_v2

        """
        args: Dict[str, Any] = {"Bucket": bucket}
        args.update(**kwargs)
        for result in utils.paginate(
            client=self.client, method=self.client.list_objects_v2.__name__, **args
        ):
            for contents in result["Contents"]:
                yield contents["Key"]

    def check_object_exists(self, object_key: str, bucket: str) -> bool:
        """
        Check whether an object exist.

        Return true if the object `object_key` exist in the `bucket`.

        Parameters
        ----------
        bucket : str
            Name of bucket to find the object.
        object_key : str
            Identifier of the object in S3 to find in the bucket.

        Returns
        ------
        bool
            True if `object_key` is inside the `bucket`.

        """
        try:
            self.resource.Object(bucket_name=bucket, key=object_key).load()
        except exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            else:
                raise
        return True

    def read_object_content(self, bucket: str, object_key: str, encoding="utf-8") -> str:
        """
        Get the content of a file.

        Return the content of the object `object_key` in the `bucket` with the specific encoding.
        If the object `object_key` does not exist, an exception will be raised.

        Parameters
        ----------
        bucket : str
            Name of the bucket to read from.
        object_key : str
            Identifier of the object in the bucket to read from.
        encoding : str, optional
            Type of encoding used in the content (the default is 'utf-8').

        Returns
        ------
        str
            The content of the object decoded.

        Raises
        ------
        botocore.exceptions.ClientError
            If the object called `object_key` does not exist in the `bucket`.

        """
        object_to_read = self.resource.Object(bucket_name=bucket, key=object_key)
        file_content = object_to_read.get()["Body"].read().decode(encoding)
        return file_content

    def put_object(self, bucket: str, object_key: str, content: bytes) -> None:
        """
        Write in a file in a specific location.

        Write `content` into an object `object_key` and upload it to the `bucket`. If the object
        already exist, its content will be overwriten.

        Parameters
        ----------
        bucket : str
            Name of the bucket to put the object in.
        object_key : str
            Identifier of the object to put into the bucket.
        content : bytes
            The contet to be writen into the object.

        Returns
        -------
        None

        """
        self.client.put_object(Body=content, Bucket=bucket, Key=object_key)
        return None

    def delete_object(self, bucket: str, object_key: str) -> None:
        """
        Remove a file.

        Delete an object `object_key` from the `bucket`. This method assumes the object `object_key`
        exists in the `bucket`.

        Parameters
        ----------
        bucket : str
            Name of the bucket from where the object will be deleted.
        object_key: str
            Identifier of the object to be delted.

        Returns
        -------
        None

        Raises
        ------
        botocore.exceptions.ClientError
            If the object called `object_key` does not exist in the `bucket`.

        """
        self.resource.Object(bucket_name=bucket, key=object_key).delete()
        return None

    def write_dataframe_to_csv_object(
        self,
        bucket: str,
        object_key: str,
        dataframe: pd.DataFrame,
        encoding: str = "utf-8",
        save_index: bool = False,
        **kwargs,
    ) -> None:
        """
        Put a dataframe into a csv file.

        Write the content of a pandas dataframe into a csv file and upload it to the `bucket`. If
        the object already exists, its content will be overwriten.

        Parameters
        ----------
        bucket : str
            Name of the bucket to upload the file.
        object_key : str
            Identifier of the file to be uploaded to the bucket.
        dataframe : pd.DataFrame
            Pandas dataframe that contains the content to be writen in the file.
        encoding : str, optional
            Type of encoding used in the content (the default is 'utf-8').
        save_index : bool, optional
            Whether to save the index as a column, (the default is 'False').

        Return
        ------
        None

        """
        # Get pandas dataframe as CSV bytes
        csv_buffer = StringIO()
        dataframe.to_csv(path_or_buf=csv_buffer, index=save_index, **kwargs)
        bytes_content = csv_buffer.getvalue().encode(encoding)
        self.put_object(bucket=bucket, object_key=object_key, content=bytes_content)

    def write_dataframe_to_parquet_object(
        self,
        bucket: str,
        object_key: str,
        dataframe: pd.DataFrame,
        compression: str = "snappy",
        **kwargs,
    ) -> None:
        """
        Put a dataframe into a parquet file.

        Write the content of a pandas dataframe into a parquet file and upload it to the `bucket`.
        If the object already exists, its content will be overwriten. The dataframe will be
        converted into parquet with `pyarrow` engine.

        Parameters
        ----------
        bucket : str
            Name of the bucket to upload the file.
        object_key : str
            Identifier of the file to be uploaded to the bucket.
        dataframe : pd.DataFrame
            Pandas dataframe that contains the content to be writen in the file.
        engine : bool, optional
            Parquet library to use, (the default is 'auto').

        Return
        ------
        None

        """
        parquet_buffer = BytesIO()
        engine = "pyarrow"
        dataframe.to_parquet(path=parquet_buffer, engine=engine, compression=compression, **kwargs)
        bytes_content = parquet_buffer.getvalue()
        self.put_object(bucket=bucket, object_key=object_key, content=bytes_content)

    def generate_quicksight_manifest(
        self,
        bucket: str,
        object_key: str,
        s3_uris: List[str] = None,
        s3_uri_prefixes: List[str] = None,
        file_format: str = None,
        delimiter: str = None,
        qualifier: str = None,
        header_row: bool = None,
    ):
        """
        Generates a QS manifest JSON file.

        Generates a QS manifest JSON file from a list of `S3 URIs` and/or `S3 URI prefixes` that is
        uploaded to `bucket`

        Parameters
        ----------
        bucket : str
            Name of the bucket to save the generated manifest.
        object_key : str
            Identifier with which the manifest will have in the bucket.
        s3_uris : List[str], optional
            List of S3 uris of the files that will be used.
        s3_uri_prefixes : List[str], optional
            List of S3 uri prefixes that will be used. The uri_prefixes filters those object keys
            that begin with the specified string. Notice that an uri_prefix is different than an S3
            prefix, an uri_prefix contains also the first part of an absolute path:
            's3://bucket_name/..'.
        format : str, optional
            Format of manifest files to be imported (the default is 'CSV').
        delimiter : str, optional
            File field delimiter (the default is ',').
        qualifier : str, optional
            Text qualifier used in the file to specify the beginning of a text.
        header_row : str, optional
            Boolean string that has value 'True' if the file has a header row (the default is
            'True').

        Return
        -----
        None

        Raises
        ------
        ManifestError
            If the file or prefix are not specified.

        Notes
        -----
        More information on the JSON format of the QuickSight manifest files: [1].

        References
        ----------
        [1] :
        https://docs.aws.amazon.com/quicksight/latest/user/supported-manifest-file-format.html

        """
        if s3_uri_prefixes is None and s3_uris is None:
            raise ManifestError("No file or prefix were specified.")

        # Build the JSON with the not None attributes.
        # Build the 'fileLocations' part.
        uri: Dict[str, Any] = {}
        if s3_uris is not None:
            uri["URIs"] = list(s3_uris)

        uri_prefixes: Dict[str, Any] = {}
        if s3_uri_prefixes is not None:
            uri_prefixes["URIPrefixes"] = list(s3_uri_prefixes)

        data: Dict[str, Any] = {"fileLocations": []}
        if s3_uris is not None:
            data["fileLocations"].append(uri)
        if s3_uri_prefixes is not None:
            data["fileLocations"].append(uri_prefixes)

        # Build the 'globalUploadSettings' part.
        upload_settings: Dict[str, Any] = {}
        if file_format is not None:
            upload_settings["format"] = file_format
        if delimiter is not None:
            upload_settings["delimiter"] = delimiter
        if qualifier is not None:
            upload_settings["textqualifier"] = qualifier
        if header_row is not None:
            upload_settings["containsHeader"] = header_row

        if upload_settings:
            data["globalUploadSettings"] = upload_settings
        json_content = json.dumps(data, indent=4, sort_keys=True)
        bytes_content = json_content.encode("utf-8")

        self.put_object(bucket=bucket, object_key=object_key, content=bytes_content)
