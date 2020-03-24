import os
import json
import boto3
import botocore
import pytest
import pandas as pd
import py
from typing import List
from datetime import datetime
from moto import mock_s3
from ..aws.s3_handler import S3Handler

"""
TODO: this whole section might serve in the future as test suite for this library
      The idea is to use moto to locally simulate the aws services so that the suite can run without
      actually connecting to the aws cloud, thus saving $$ and reducing the latency of the tests.
"""

TEST_BUCKET = "test_bucket"
TEST_PREFIX = "mock_prefix"


class TestS3Handler:
    def setup_method(self):
        self.mock_s3 = mock_s3()
        self.mock_s3.start()

        self.s3_handler = S3Handler()
        self.client = boto3.client("s3")
        self.resource = boto3.resource(
            "s3",
            region_name="eu-west-1",
            aws_access_key_id="fake_access_key",
            aws_secret_access_key="fake_secret_key",
        )
        try:
            self.resource.meta.client.head_bucket(Bucket=TEST_BUCKET)
        except botocore.exceptions.ClientError:
            pass
        else:
            raise EnvironmentError(
                "{bucket} should not exist.".format(bucket=TEST_BUCKET)
            )
        self.client.create_bucket(Bucket=TEST_BUCKET)

    def teardown_method(self):
        bucket = self.resource.Bucket(TEST_BUCKET)
        for key in bucket.objects.all():
            key.delete()
        bucket.delete()
        self.mock_s3.stop()

    def test_get_uri(self):
        file_name = "test_file.test"

        # Bucket without folder nor file. Success expected.
        expected_path = "s3://test_bucket/"
        obtained_path = self.s3_handler.get_uri(bucket=TEST_BUCKET)
        assert obtained_path == expected_path

        # File in a bucket without folder.
        expected_path = "s3://test_bucket/test_file.test"
        obtained_path = self.s3_handler.get_uri(bucket=TEST_BUCKET, file_name=file_name)
        assert obtained_path == expected_path

        # Folder in a bucket without file. Success expected.
        folder = "folder"
        expected_path = "s3://test_bucket/folder/"
        obtained_path = self.s3_handler.get_uri(bucket=TEST_BUCKET, folder_path=folder,)
        assert obtained_path == expected_path

        # Folder in a bucket with file. Success expected.
        expected_path = "s3://test_bucket/folder/test_file.test"
        obtained_path = self.s3_handler.get_uri(
            bucket=TEST_BUCKET, folder_path=folder, file_name=file_name,
        )
        assert obtained_path == expected_path

        # Folder in a bucket with a / at the begining. Success expected.
        folder = "/folder"
        expected_path = "s3://test_bucket/folder/test_file.test"
        obtained_path = self.s3_handler.get_uri(
            bucket=TEST_BUCKET, folder_path=folder, file_name=file_name,
        )
        assert obtained_path == expected_path

        # Folder in a bucket with subfolder. Success expected.
        folder = "folder/subfolder"
        expected_path = "s3://test_bucket/folder/subfolder/test_file.test"
        obtained_path = self.s3_handler.get_uri(
            bucket=TEST_BUCKET, folder_path=folder, file_name=file_name,
        )
        assert obtained_path == expected_path

    def test_paginate(self, tmpdir):
        file_names: List[str] = ["first_object.json", "second_object.json"]
        contents: List[str] = ["", ""]
        generate_fixture_files(
            s3_client=self.client,
            tmpdir=tmpdir,
            file_names=file_names,
            contents=contents,
        )

        # Call function without Bucket argument. Failure expected.
        args: Dict[str, Any] = {
            "PaginationConfig": {"MaxItems": 1},
        }
        with pytest.raises(AssertionError) as e:
            list(
                self.s3_handler.paginate(
                    method=self.client.list_objects_v2.__name__, **args
                )
            )

        # Paginate by prefix. Success expected.
        args: Dict[str, Any] = {
            "Bucket": TEST_BUCKET,
            "Prefix": "test_paginate/second",
        }
        expected_objects: List[str] = ["test_paginate/{}".format(file_names[1])]
        obtained_objects: List[str] = []
        for result in self.s3_handler.paginate(
            method=self.client.list_objects_v2.__name__, **args
        ):
            obtained_objects.append(result["Key"])
        assert obtained_objects == expected_objects

        # Limit the number of returned element. Success expected.
        args: Dict[str, Any] = {
            "Bucket": TEST_BUCKET,
            "PaginationConfig": {"MaxItems": 1},
        }
        expected_objects: List[str] = ["test_paginate/{}".format(file_names[0])]
        obtained_objects: List[str] = []
        for result in self.s3_handler.paginate(
            method=self.client.list_objects_v2.__name__, **args
        ):
            obtained_objects.append(result["Key"])
        assert obtained_objects == expected_objects

    def test_list_objects(self, tmpdir):
        file_names: List[str] = [
            "first_object.json",
            "second_object1.json",
            "second_object2.json",
        ]
        contents: List[str] = ["", "", ""]
        generate_fixture_files(
            s3_client=self.client,
            tmpdir=tmpdir,
            file_names=file_names,
            contents=contents,
        )

        # List objects by prefix. Success expected.
        args: Dict[str, Any] = {
            "Prefix": "test_list_objects/second",
        }
        expected_objects: List[str] = [
            "test_list_objects/{}".format(file_names[1]),
            "test_list_objects/{}".format(file_names[2]),
        ]
        obtained_objects: List[str] = list(
            self.s3_handler.list_objects(bucket=TEST_BUCKET, **args)
        )
        assert expected_objects == obtained_objects

        # List objects starting from a specific key. Success expected.
        args: Dict[str, Any] = {
            "StartAfter": "test_list_objects/{}".format(file_names[1]),
        }
        expected_objects: List[str] = [
            "test_list_objects/{}".format(file_names[2]),
        ]
        obtained_objects: List[str] = list(
            self.s3_handler.list_objects(bucket=TEST_BUCKET, **args)
        )
        assert expected_objects == obtained_objects

        # List all objects. Success expected.
        expected_objects: List[str] = [
            "test_list_objects/{}".format(file_names[0]),
            "test_list_objects/{}".format(file_names[1]),
            "test_list_objects/{}".format(file_names[2]),
        ]
        obtained_objects: List[str] = list(
            self.s3_handler.list_objects(bucket=TEST_BUCKET,)
        )
        assert expected_objects == obtained_objects

    def test_object_key_exist(self, tmpdir):
        file_names: List[str] = ["first_object.json", "second_object.json"]
        contents: List[str] = ["", ""]
        generate_fixture_files(
            s3_client=self.client,
            tmpdir=tmpdir,
            file_names=file_names,
            contents=contents,
        )

        # The method gives true when an object exist in the bucket. Success expected.
        obtained_result = self.s3_handler.object_key_exist(
            bucket=TEST_BUCKET,
            object_key="test_object_key_exist/{}".format(file_names[0]),
        )
        assert obtained_result

        obtained_result = self.s3_handler.object_key_exist(
            bucket=TEST_BUCKET,
            object_key="test_object_key_exist/{}".format(file_names[1]),
        )
        assert obtained_result

        # The method gives false when an object does not exist in the bucket. Success expected.
        obtained_result = self.s3_handler.object_key_exist(
            bucket=TEST_BUCKET, object_key=file_names[1]
        )
        assert not obtained_result

    def test_read_object_content(self, tmpdir):
        file_names: List[str] = ["first_object.json", "second_object.json"]
        contents: List[str] = ["Content1", "Content2"]
        generate_fixture_files(
            s3_client=self.client,
            tmpdir=tmpdir,
            file_names=file_names,
            contents=contents,
        )

        # Test reading a key that does not exist. Sucess expected.
        obtained_content = self.s3_handler.read_object_content(
            bucket=TEST_BUCKET,
            object_key="test_read_object_content/{}".format(file_names[1]),
        )
        expected_content = contents[1]
        assert obtained_content == expected_content

        # Test reading a key that does not exist. Failure expected.
        with pytest.raises(botocore.exceptions.ClientError) as e:
            obtained_content = self.s3_handler.read_object_content(
                bucket=TEST_BUCKET, object_key=file_names[0]
            )

    def test_put_object(self, tmpdir):
        file_names: List[str] = ["first_object.json"]
        contents: List[str] = ["Content1"]
        generate_fixture_files(
            s3_client=self.client,
            tmpdir=tmpdir,
            file_names=file_names,
            contents=contents,
        )

        # Put content to a new object. Success expected.
        new_object_key = "{}/second_object.json".format("test_put_object")
        content_to_write = "Content2"
        self.s3_handler.put_object(
            bucket=TEST_BUCKET, object_key=new_object_key, content=content_to_write
        )

        read_object = self.resource.Object(bucket_name=TEST_BUCKET, key=new_object_key)
        content_read = read_object.get()["Body"].read().decode("utf-8")
        assert content_read == content_to_write

        # Put content to an object that already exist. Verify the content is overwriten.
        # Success expected.
        object_key = "test_put_object/{}".format(file_names[0])
        read_object = self.resource.Object(bucket_name=TEST_BUCKET, key=object_key)
        content_read = read_object.get()["Body"].read().decode("utf-8")
        assert content_read == contents[0]

        content_to_write = "Content3"
        self.s3_handler.put_object(
            bucket=TEST_BUCKET, object_key=object_key, content=content_to_write
        )

        read_object = self.resource.Object(bucket_name=TEST_BUCKET, key=object_key)
        content_read = read_object.get()["Body"].read().decode("utf-8")
        assert content_read == content_to_write

    def test_delete_key(self, tmpdir):
        file_names: List[str] = ["first_object.json"]
        contents: List[str] = [""]
        generate_fixture_files(
            s3_client=self.client,
            tmpdir=tmpdir,
            file_names=file_names,
            contents=contents,
        )

        # Validate that an object does not exist anymore after being deleted. Failure expected.
        object_key = "test_delete_key/{}".format(file_names[0])
        self.resource.Object(bucket_name=TEST_BUCKET, key=object_key).get()
        self.s3_handler.delete_key(bucket=TEST_BUCKET, object_key=object_key)

        with pytest.raises(botocore.exceptions.ClientError) as e:
            self.resource.Object(bucket_name=TEST_BUCKET, key=object_key).get()

    def test_write_dataframe_to_csv_object(self, tmpdir):
        generate_fixture_files(
            s3_client=self.client, tmpdir=tmpdir, file_names=[], contents=[]
        )
        object_key = "test_write_dataframe_to_csv_object/dataframe.csv"
        data: Dict[str, List[str]] = {
            "Column1": ["Value11", "Value21"],
            "Column2": ["Value12", "Value22"],
        }
        df = pd.DataFrame(data)
        self.s3_handler.write_dataframe_to_csv_object(
            bucket=TEST_BUCKET, object_key=object_key, dataframe=df
        )

        data_keys = list(data.keys())
        expected_content = "Column1,Column2\n" "Value11,Value12\n" "Value21,Value22\n"
        read_object = self.resource.Object(bucket_name=TEST_BUCKET, key=object_key)
        obtained_content = read_object.get()["Body"].read().decode("utf-8")
        assert expected_content == obtained_content

    def test_generate_quicksight_manifest(self, tmpdir):
        file_names: List[str] = [
            "first_object.json",
            "second_object1.json",
            "second_object2.json",
        ]
        contents: List[str] = ["", "", ""]

        generate_fixture_files(
            s3_client=self.client, tmpdir=tmpdir, file_names=[], contents=[]
        )
        key_paths: List[str] = [
            "s3://{}/{}/{}".format(
                TEST_BUCKET, "test_generate_quicksight_manifest", file_names[0]
            ),
        ]
        uri_prefix_paths: List[str] = [
            "s3://{}/{}/{}".format(
                TEST_BUCKET, "test_generate_quicksight_manifest", "second"
            ),
        ]
        upload_settings: Dict[str, Any] = {
            "format": "CSV",
            "delimiter": ",",
            "textqualifier": "'",
            "containsHeader": "True",
        }
        data: Dict[str, Any] = {
            "fileLocations": [{"URIs": key_paths}, {"URIPrefixes": uri_prefix_paths}],
            "globalUploadSettings": upload_settings,
        }

        expected_manifest = json.dumps(data, indent=4, sort_keys=True)
        manifest_key = "{}/manifest.json".format("test_generate_quicksight_manifest")
        self.s3_handler.generate_quicksight_manifest(
            bucket=TEST_BUCKET,
            object_key=manifest_key,
            absolute_paths=key_paths,
            uri_prefix_paths=uri_prefix_paths,
            file_format=upload_settings["format"],
            delimiter=upload_settings["delimiter"],
            qualifier=upload_settings["textqualifier"],
            header_row=upload_settings["containsHeader"],
        )

        obtained_manifest_bytes = (
            self.resource.Object(bucket_name=TEST_BUCKET, key=manifest_key)
            .get()["Body"]
            .read()
        )

        # Load the JSON to a Python list & dump it back out as formatted JSON
        obtained_manifest_dictionary = json.loads(obtained_manifest_bytes)
        obtained_manifest = json.dumps(
            obtained_manifest_dictionary, indent=4, sort_keys=True
        )
        assert expected_manifest == obtained_manifest


def _upload_fixture_files(
    s3_client: botocore.client, bucket: str, fixture_dir: str
) -> None:
    fixture_paths = [
        os.path.join(path, filename)
        for path, _, files in os.walk(fixture_dir)
        for filename in files
    ]
    # The uploaded files will have the name of the calling method in their object key.
    for path in fixture_paths:
        key = "{}/{}".format(
            os.path.basename(fixture_dir)[:-1], os.path.relpath(path, fixture_dir),
        )
        s3_client.upload_file(Filename=path, Bucket=bucket, Key=key)


def generate_fixture_files(
    s3_client: botocore.client,
    tmpdir: py.path.local,
    file_names: List[str],
    contents: List[str],
) -> None:
    assert len(file_names) == len(
        contents
    ), "Length of 'file_names' and 'contents' must be equal."

    for i in range(len(file_names)):
        key = file_names[i]
        fixture_file = tmpdir.join(key)
        fixture_file.write(contents[i])
    _upload_fixture_files(s3_client=s3_client, bucket=TEST_BUCKET, fixture_dir=tmpdir)
