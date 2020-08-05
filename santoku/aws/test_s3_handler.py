import os
import json
import boto3
import pytest
import pandas as pd
import py
from typing import List, Dict
from moto import mock_s3
from botocore import exceptions
from io import StringIO, BytesIO
from ..aws.s3_handler import S3Handler
from ..aws.s3_handler import ManifestError

"""
TODO: this whole section might serve in the future as test suite for this library
      The idea is to use moto to locally simulate the aws services so that the suite can run without
      actually connecting to the aws cloud, thus saving $$ and reducing the latency of the tests.
"""


@pytest.fixture(scope="class")
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "eu-west-1"


@pytest.fixture(scope="class")
def s3_handler(aws_credentials):
    with mock_s3():
        s3_handler = S3Handler()
        yield s3_handler


@pytest.fixture(scope="function")
def bucket(s3_handler, request):
    bucket_name = "test_bucket"
    try:
        s3_handler.resource.meta.client.head_bucket(Bucket=bucket_name)
    except exceptions.ClientError:
        pass
    else:
        raise EnvironmentError(f"{test_bucket} should not exist.")
    s3_handler.client.create_bucket(Bucket=bucket_name)

    yield bucket_name

    def teardown() -> None:
        bucket = s3_handler.resource.Bucket(bucket_name)
        bucket.delete()

    request.addfinalizer(teardown)


@pytest.fixture(scope="function")
def delete_object_in_s3(bucket, s3_handler):
    def _delete_object_in_s3(key: str) -> None:
        s3_handler.client.delete_object(Bucket=bucket, Key=key)

    return _delete_object_in_s3


@pytest.fixture(scope="function")
def put_object_to_s3(bucket, s3_handler):
    object_keys = []

    def _put_object_to_s3(files_contents: Dict[str, str]) -> None:
        for file_name, file_content in files_contents.items():
            s3_handler.client.put_object(Body=file_content, Bucket=bucket, Key=file_name)

    yield _put_object_to_s3


@pytest.fixture(scope="function")
def files_with_no_common_prefix(put_object_to_s3, delete_object_in_s3, request):
    files_contents = {
        "first_object.json": "Content1",
    }

    put_object_to_s3(files_contents=files_contents)
    yield files_contents

    def teardown() -> None:
        try:
            delete_object_in_s3(key=list(files_contents.keys())[0])
        except:
            pass

    request.addfinalizer(teardown)


@pytest.fixture(scope="class")
def prefix():
    return "second_object"


@pytest.fixture(scope="function")
def files_with_common_prefix(put_object_to_s3, prefix, delete_object_in_s3, request):
    files_contents = {
        f"{prefix}1.json": "Content2",
        f"{prefix}2.json": "Content3",
    }

    put_object_to_s3(files_contents=files_contents)
    yield files_contents

    def teardown() -> None:
        for key in list(files_contents.keys()):
            try:
                delete_object_in_s3(key=key)
            except:
                pass

    request.addfinalizer(teardown)


@pytest.fixture(scope="function")
def fixture_objects(files_with_no_common_prefix, files_with_common_prefix):
    fixture_objects = files_with_no_common_prefix.copy()
    fixture_objects.update(files_with_common_prefix)
    return fixture_objects


@pytest.fixture(scope="function")
def dataframe():
    data = {
        "Column1": ["Value11", "Value21"],
        "Column2": ["Value12", "Value22"],
    }
    return pd.DataFrame(data)


class TestS3Handler:
    def test_get_uri(self, bucket, s3_handler):
        file_name = "test_file.test"

        # Bucket without folder nor file. Success expected.
        expected_path = f"s3://{bucket}/"
        obtained_path = s3_handler.get_uri(bucket=bucket)
        assert obtained_path == expected_path

        # File in a bucket without folder.
        expected_path = f"s3://{bucket}/{file_name}"
        obtained_path = s3_handler.get_uri(bucket=bucket, file_name=file_name)
        assert obtained_path == expected_path

        # Folder in a bucket without file. Success expected.
        folder = "folder"
        expected_path = f"s3://{bucket}/{folder}/"
        obtained_path = s3_handler.get_uri(bucket=bucket, folder_path=folder,)
        assert obtained_path == expected_path

        # Folder in a bucket with file. Success expected.
        expected_path = f"s3://{bucket}/{folder}/{file_name}"
        obtained_path = s3_handler.get_uri(bucket=bucket, folder_path=folder, file_name=file_name,)
        assert obtained_path == expected_path

        # Folder in a bucket with a / at the begining. Success expected.
        folder = "/folder"
        expected_path = f"s3://{bucket}{folder}/{file_name}"
        obtained_path = s3_handler.get_uri(bucket=bucket, folder_path=folder, file_name=file_name,)
        assert obtained_path == expected_path

        # Folder in a bucket with subfolder. Success expected.
        folder = "folder/subfolder"
        expected_path = f"s3://{bucket}/{folder}/{file_name}"
        obtained_path = s3_handler.get_uri(bucket=bucket, folder_path=folder, file_name=file_name,)
        assert obtained_path == expected_path

    def test_paginate(
        self, bucket, s3_handler, prefix, files_with_no_common_prefix, files_with_common_prefix
    ):
        # Call function without Bucket argument. Failure expected.
        args = {
            "PaginationConfig": {"MaxItems": 1},
        }
        with pytest.raises(exceptions.ParamValidationError) as e:
            list(s3_handler.paginate(method=s3_handler.client.list_objects_v2.__name__, **args))

        # Paginate by prefix. Success expected.
        args = {
            "Bucket": bucket,
            "Prefix": prefix,
        }
        common_prefix_object_keys = [object_key for object_key in files_with_common_prefix]
        obtained_objects = []
        for result in s3_handler.paginate(
            method=s3_handler.client.list_objects_v2.__name__, **args
        ):
            obtained_objects.append(result["Key"])
        assert obtained_objects == common_prefix_object_keys

        # Limit the number of returned element. Success expected.
        args = {
            "Bucket": bucket,
            "PaginationConfig": {"MaxItems": 1},
        }
        # `list_objects_v2` method lists objects in alphabetical order.
        expected_object = min(
            list(files_with_no_common_prefix.keys()) + common_prefix_object_keys
        )  # Get the first object name alphabetically.
        obtained_objects = []
        for result in s3_handler.paginate(
            method=s3_handler.client.list_objects_v2.__name__, **args
        ):
            obtained_objects.append(result["Key"])
        assert len(obtained_objects) == 1
        assert obtained_objects[0] == expected_object

    def test_list_objects(
        self, bucket, s3_handler, prefix, files_with_no_common_prefix, files_with_common_prefix
    ):
        # List objects by prefix. Success expected.
        args = {
            "Prefix": prefix,
        }
        common_prefix_object_keys = [object_key for object_key in files_with_common_prefix]
        obtained_objects = list(s3_handler.list_objects(bucket=bucket, **args))
        assert obtained_objects == common_prefix_object_keys

        # List objects starting from a specific key.
        args = {
            "StartAfter": common_prefix_object_keys[0],
        }
        obtained_objects = list(s3_handler.list_objects(bucket=bucket, **args))
        assert obtained_objects == common_prefix_object_keys[1:]

        # List all objects. Success expected.
        expected_objects = list(files_with_no_common_prefix.keys()) + common_prefix_object_keys
        expected_objects.sort()
        obtained_objects = list(s3_handler.list_objects(bucket=bucket))
        assert obtained_objects == expected_objects

    def test_check_object_exists(self, bucket, s3_handler, fixture_objects):
        # Test that an object exist in the bucket. Success expected.
        for object_key, _ in fixture_objects.items():
            obtained_result = s3_handler.check_object_exists(bucket=bucket, object_key=object_key,)
            assert obtained_result

        # Test that an object does not exist in the bucket. Success expected.
        obtained_result = s3_handler.check_object_exists(
            bucket=bucket, object_key="false_object.json"
        )
        assert not obtained_result

    def test_read_object_content(self, bucket, s3_handler, fixture_objects):
        # Test reading existing objects. Sucess expected.
        for object_key, content in fixture_objects.items():
            obtained_content = s3_handler.read_object_content(bucket=bucket, object_key=object_key)
            expected_content = content
            assert obtained_content == expected_content

        # Test reading an object that does not exist. Failure expected.
        with pytest.raises(exceptions.ClientError) as e:
            obtained_content = s3_handler.read_object_content(
                bucket=bucket, object_key="false_object.json"
            )

    def test_put_object(self, bucket, s3_handler, files_with_no_common_prefix, delete_object_in_s3):
        # Put content to a new object. Success expected.
        new_object_key = "second_object.json"
        content_to_write = "Content2"
        s3_handler.put_object(bucket=bucket, object_key=new_object_key, content=content_to_write)

        read_object = s3_handler.resource.Object(bucket_name=bucket, key=new_object_key)
        content_read = read_object.get()["Body"].read().decode("utf-8")
        assert content_read == content_to_write

        # Put content to an object that already exist. Verify the content is overwriten.
        # Success expected.
        object_key = list(files_with_no_common_prefix.keys())[0]
        original_content = files_with_no_common_prefix[object_key]
        read_object = s3_handler.resource.Object(bucket_name=bucket, key=object_key)
        content_read = read_object.get()["Body"].read().decode("utf-8")
        assert content_read == original_content

        content_to_write = "Content3"
        s3_handler.put_object(bucket=bucket, object_key=object_key, content=content_to_write)

        read_object = s3_handler.resource.Object(bucket_name=bucket, key=object_key)
        content_read = read_object.get()["Body"].read().decode("utf-8")
        assert content_read == content_to_write

        # Remove the new object.
        delete_object_in_s3(key=new_object_key)

    def test_delete_key(self, bucket, s3_handler, files_with_no_common_prefix):
        # Validate that an object does not exist anymore after being deleted. Failure expected.
        object_key = list(files_with_no_common_prefix.keys())[0]
        s3_handler.resource.Object(bucket_name=bucket, key=object_key).get()
        s3_handler.delete_key(bucket=bucket, object_key=object_key)

        with pytest.raises(exceptions.ClientError) as e:
            s3_handler.resource.Object(bucket_name=bucket, key=object_key).get()

    def test_write_dataframe_to_csv_object(
        self, bucket, s3_handler, delete_object_in_s3, dataframe
    ):
        # Validate that a dataframe can be written and read correctly in csv format.
        # Success expected.
        new_object_key = "dataframe.csv"
        s3_handler.write_dataframe_to_csv_object(
            bucket=bucket, object_key=new_object_key, dataframe=dataframe
        )

        read_object = s3_handler.resource.Object(bucket_name=bucket, key=new_object_key)
        object_content = read_object.get()["Body"].read().decode("utf-8")
        obtained_df = pd.read_csv(filepath_or_buffer=StringIO(object_content))
        assert obtained_df.equals(dataframe)

        # Remove the new object.
        delete_object_in_s3(key=new_object_key)

    def test_write_dataframe_to_parquet_object(
        self, bucket, s3_handler, delete_object_in_s3, dataframe
    ):
        # Validate that a dataframe can be written and read correctly in parquet format.
        # Success expected.
        new_object_key = "dataframe.parquet"
        s3_handler.write_dataframe_to_parquet_object(
            bucket=bucket, object_key=new_object_key, dataframe=dataframe
        )

        read_object = s3_handler.resource.Object(bucket_name=bucket, key=new_object_key)
        object_content = read_object.get()["Body"].read()
        obtained_df = pd.read_parquet(path=BytesIO(object_content))
        assert obtained_df.equals(dataframe)

        # Remove the new object.
        delete_object_in_s3(key=new_object_key)

    def test_generate_quicksight_manifest(
        self,
        bucket,
        s3_handler,
        files_with_no_common_prefix,
        prefix,
        files_with_common_prefix,
        delete_object_in_s3,
    ):
        manifest_key = "manifest.json"
        key_paths = [f"s3://{bucket}/{list(files_with_no_common_prefix.keys())[0]}"]
        uri_prefix_paths = [f"s3://{bucket}/{prefix}"]
        upload_settings = {
            "format": "CSV",
            "delimiter": ",",
            "textqualifier": "'",
            "containsHeader": "True",
        }
        data = {
            "fileLocations": [{"URIs": key_paths}, {"URIPrefixes": uri_prefix_paths}],
            "globalUploadSettings": upload_settings,
        }

        # Test not specifying s3_uri_prefixes and s3_uris. Failure expected.
        with pytest.raises(ManifestError) as e:
            s3_handler.generate_quicksight_manifest(
                bucket=bucket,
                object_key=manifest_key,
                file_format=upload_settings["format"],
                delimiter=upload_settings["delimiter"],
                qualifier=upload_settings["textqualifier"],
                header_row=upload_settings["containsHeader"],
            )

        # Validate manifest file can be generated correctlty. Success expected.
        expected_manifest = json.dumps(data, indent=4, sort_keys=True)
        s3_handler.generate_quicksight_manifest(
            bucket=bucket,
            object_key=manifest_key,
            s3_uris=key_paths,
            s3_uri_prefixes=uri_prefix_paths,
            file_format=upload_settings["format"],
            delimiter=upload_settings["delimiter"],
            qualifier=upload_settings["textqualifier"],
            header_row=upload_settings["containsHeader"],
        )

        obtained_manifest_bytes = (
            s3_handler.resource.Object(bucket_name=bucket, key=manifest_key).get()["Body"].read()
        )

        # Load the JSON to a Python list and dump it back out as formatted JSON
        obtained_manifest_dictionary = json.loads(obtained_manifest_bytes)
        obtained_manifest = json.dumps(obtained_manifest_dictionary, indent=4, sort_keys=True)
        assert obtained_manifest == expected_manifest

        # Remove the new object.
        delete_object_in_s3(key=manifest_key)
