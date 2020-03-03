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
from ..aws.s3 import S3

"""
TODO: this whole section might serve in the future as test suite for this library
      The idea is to use moto to locally simulate the aws services so that the suite can run without
      actually connecting to the aws cloud, thus saving $$ and reducing the latency of the tests.
"""

TEST_BUCKET = "test_bucket"
TEST_PREFIX = "mock_prefix"


@mock_s3
class TestS3:
    @classmethod
    def setup_class(self,):
        # It seem that mock_s3 and classmethod decorators are not compatible, this is why context
        # manager of moto is used here.
        with mock_s3():
            self.s3_handler = S3()
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
                err = "{bucket} should not exist.".format(bucket=TEST_BUCKET)
                raise EnvironmentError(err)
            self.client.create_bucket(Bucket=TEST_BUCKET)

            # current_testcase = (
            #     os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0]
            # )

            current_dir = os.path.dirname(__file__)
            fixture_dir = os.path.join(current_dir, "test_s3_fixtures")

            # _upload_fixtures(TEST_BUCKET, fixture_dir)

    def tearDown(self):
        with mock_s3():
            bucket = self.resource.Bucket(TEST_BUCKET)
            for key in bucket.objects.all():
                key.delete()
            bucket.delete()

    def test_get_absolute_path(self):
        key = "test_file.test"

        # Test 1: file in a bucket, no prefix
        expected_path = "s3://test_bucket/test_file.test"
        obtained_path = self.s3_handler.get_absolute_path(bucket=TEST_BUCKET, key=key)
        assert obtained_path == expected_path

        # Test 2: file in a folder, prefix is the folder with /
        prefix = "folder/"
        expected_path = "s3://test_bucket/folder/test_file.test"
        obtained_path = self.s3_handler.get_absolute_path(
            bucket=TEST_BUCKET, key=key, prefix=prefix
        )
        assert obtained_path == expected_path

        # Test 3: file in folder, prefix is the folder without /
        prefix = "folder"
        expected_path = "s3://test_bucket/folder/test_file.test"
        obtained_path = self.s3_handler.get_absolute_path(
            bucket=TEST_BUCKET, key=key, prefix=prefix
        )
        assert obtained_path == expected_path

        # Test 4: prefix is not the folder
        prefix = "some_"
        expected_path = "s3://test_bucket/some_test_file.test"
        obtained_path = self.s3_handler.get_absolute_path(
            bucket=TEST_BUCKET, key=key, prefix=prefix, prefix_is_folder=False
        )
        assert obtained_path == expected_path

    def test_paginate(self, tmpdir):
        # Test setting limit to the number of returned element.
        args: Dict[str, Any] = {
            "Bucket": TEST_BUCKET,
            "PaginationConfig": {"MaxItems": 1},
        }
        generate_fixture_files(tmpdir, ["object1.json", "object2.json"], ["", ""])

        expected_objects: List[str] = ["object1.json"]
        obtained_objects: List[str] = []
        for result in self.s3_handler.paginate(
            method=self.client.list_objects_v2.__name__, **args
        ):
            obtained_objects.append(result["Key"])
        assert obtained_objects == expected_objects

    def test_list_objects(self, tmpdir):
        expected_objects: List[str] = ["object1.json", "object2.json"]
        generate_fixture_files(tmpdir, expected_objects, ["", ""])

        obtained_objects = list(self.s3_handler.list_objects(bucket=TEST_BUCKET))
        assert expected_objects == obtained_objects

    def test_key_exist(self, tmpdir):
        generate_fixture_files(tmpdir, ["object1.json", "object2.json"], ["", ""])

        obtained_result = self.s3_handler.key_exist(
            bucket=TEST_BUCKET, key="object2.json"
        )
        assert obtained_result == True

    def test_read_key_content(self, tmpdir):
        expected_content = "Content2"
        generate_fixture_files(
            tmpdir, ["read1.json", "read2.json"], ["Content1", expected_content]
        )

        obtained_content = self.s3_handler.read_key_content(
            bucket=TEST_BUCKET, key="read2.json"
        )
        assert obtained_content == expected_content

        # Test reading a key that does not exist.
        with pytest.raises(botocore.exceptions.ClientError) as e:
            obtained_content = self.s3_handler.read_key_content(
                bucket=TEST_BUCKET, key="does-not-exist.json"
            )

    def test_put_key(self, tmpdir):
        generate_fixture_files(tmpdir, [], [])
        key_to_write = "write.json"
        content_to_write = '{"test_write_key" = "test_write_value"}'
        self.s3_handler.put_key(
            bucket=TEST_BUCKET, key=key_to_write, content=content_to_write
        )

        read_object = self.resource.Object(bucket_name=TEST_BUCKET, key=key_to_write)
        content_read = read_object.get()["Body"].read().decode("utf-8")
        assert content_to_write == content_read

    def test_delete_file(self):
        file_to_delete = "test_delete_file/resource/delete.json"
        self.s3_handler.delete_file(TEST_BUCKET, file_to_delete)
        leftover = []
        paginator = self.client.get_paginator(self.client.list_objects_v2.__name__)
        for page in paginator.paginate(
            Bucket=TEST_BUCKET, Prefix="test_delete_file/resource"
        ).result_key_iters():
            for result in page:
                leftover.append(result["Key"])
        desired_leftover = ["test_delete_file/resource/do-not-delete.json"]
        self.assertCountEqual(leftover, desired_leftover)

    def test_delete_files(self):
        files_to_delete = [
            "test_delete_file/resource/delete.json",
            "test_delete_file/resource/delete-also.json",
        ]
        self.s3_handler.delete_files(TEST_BUCKET, files_to_delete)
        leftover = []
        paginator = self.client.get_paginator(self.client.list_objects_v2.__name__)
        for page in paginator.paginate(
            Bucket=TEST_BUCKET, Prefix="test_delete_file/resource"
        ).result_key_iters():
            for result in page:
                leftover.append(result["Key"])
        desired_leftover = ["test_delete_file/resource/do-not-delete.json"]
        self.assertCountEqual(leftover, desired_leftover)

    def test_write_dataframe_to_csv_file(self):
        file_to_write = "test_dataframe.csv"
        data = {"Column1": ["Value11", "Value21"], "Column2": ["Value12", "Value22"]}
        df = pd.DataFrame(data)
        self.s3_handler.write_dataframe_to_csv_file(df, TEST_BUCKET, file_to_write)
        file_obj = self.resource.Object(TEST_BUCKET, file_to_write)
        read_content = file_obj.get()["Body"].read().decode("utf-8")
        desired_content = "Column1,Column2\n" "Value11,Value12\n" "Value21,Value22\n"
        self.assertEqual(read_content, desired_content)

    def test_generate_correct_qs_manifest(self):
        file_paths = [
            "s3://bucket/file1.csv",
            "s3://bucket/file2.csv",
            "s3://bucket/file3.csv",
        ]
        folder_paths = [
            "s3://bucket/folder1/",
            "s3://bucket/folder2/",
            "s3://bucket/folder3/",
        ]
        upload_settings = {
            "format": "CSV",
            "delimiter": ",",
            "textqualifier": "'",
            "containsHeader": True,
        }

        data = {
            "fileLocations": [{"URIs": file_paths}, {"URIPrefixes": folder_paths}],
            "globalUploadSettings": upload_settings,
        }
        expected_manifest = json.dumps(data, indent=4, sort_keys=True)
        manifest_key = "test_generate_correct_qs_manifest/manifest.json"
        self.s3_handler.generate_quicksight_manifest(
            bucket=TEST_BUCKET,
            file_key=manifest_key,
            s3_path=file_paths,
            s3_prefix=folder_paths,
            set_format=upload_settings["format"],
            set_delimiter=upload_settings["delimiter"],
            set_qualifier=upload_settings["textqualifier"],
            set_header=upload_settings["containsHeader"],
        )
        generated_manifest_bytes = (
            self.resource.Object(TEST_BUCKET, manifest_key).get()["Body"].read()
        )
        # Load the JSON to a Python list & dump it back out as formatted JSON
        generated_manifest_dictionary = json.loads(generated_manifest_bytes)
        generated_manifest = json.dumps(
            generated_manifest_dictionary, indent=4, sort_keys=True
        )
        self.assertEqual(expected_manifest, generated_manifest)


def _upload_fixtures(bucket: str, fixture_dir: str) -> None:
    client = boto3.client("s3")
    fixture_paths = [
        os.path.join(path, filename)
        for path, _, files in os.walk(fixture_dir)
        for filename in files
    ]
    for path in fixture_paths:
        key = os.path.relpath(path, fixture_dir)
        client.upload_file(Filename=path, Bucket=bucket, Key=key)


def generate_fixture_files(
    tmpdir: py.path.local, keys_list: List[str], content_list: List[str]
) -> None:
    if len(keys_list) != len(content_list):
        raise ValueError(
            "Length of arguments keys_list and content_list must be equal."
        )
    for i in range(len(keys_list)):
        key = keys_list[i]
        fixture_file = tmpdir.join(key)
        fixture_file.write(content_list[i])
    _upload_fixtures(bucket=TEST_BUCKET, fixture_dir=tmpdir)

