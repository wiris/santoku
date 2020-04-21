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


def upload_fixture_files(
    s3_client: botocore.client, bucket: str, fixture_dir: str
) -> None:
    fixture_paths = [
        os.path.join(path, filename)
        for path, _, files in os.walk(fixture_dir)
        for filename in files
    ]
    # The uploaded files will have the name of the calling method in their object key.
    for path in fixture_paths:
        base_name = os.path.basename(fixture_dir)[:-1]
        rel_path = os.path.relpath(path, fixture_dir)
        key = f"{base_name}/{rel_path}"
        s3_client.upload_file(Filename=path, Bucket=bucket, Key=key)


def generate_fixture_files(
    s3_client: botocore.client, tmpdir: py.path.local, file_names, contents,
) -> None:
    assert len(file_names) == len(
        contents
    ), "Length of 'file_names' and 'contents' must be equal."

    for i in range(len(file_names)):
        key = file_names[i]
        fixture_file = tmpdir.join(key)
        fixture_file.write(contents[i])
    upload_fixture_files(s3_client=s3_client, bucket=TEST_BUCKET, fixture_dir=tmpdir)


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
            raise EnvironmentError(f"{TEST_BUCKET} should not exist.")
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
        expected_path = f"s3://{TEST_BUCKET}/"
        obtained_path = self.s3_handler.get_uri(bucket=TEST_BUCKET)
        assert obtained_path == expected_path

        # File in a bucket without folder.
        expected_path = f"s3://{TEST_BUCKET}/{file_name}"
        obtained_path = self.s3_handler.get_uri(bucket=TEST_BUCKET, file_name=file_name)
        assert obtained_path == expected_path

        # Folder in a bucket without file. Success expected.
        folder = "folder"
        expected_path = f"s3://{TEST_BUCKET}/{folder}/"
        obtained_path = self.s3_handler.get_uri(bucket=TEST_BUCKET, folder_path=folder,)
        assert obtained_path == expected_path

        # Folder in a bucket with file. Success expected.
        expected_path = f"s3://{TEST_BUCKET}/{folder}/{file_name}"
        obtained_path = self.s3_handler.get_uri(
            bucket=TEST_BUCKET, folder_path=folder, file_name=file_name,
        )
        assert obtained_path == expected_path

        # Folder in a bucket with a / at the begining. Success expected.
        folder = "/folder"
        expected_path = f"s3://{TEST_BUCKET}{folder}/{file_name}"
        obtained_path = self.s3_handler.get_uri(
            bucket=TEST_BUCKET, folder_path=folder, file_name=file_name,
        )
        assert obtained_path == expected_path

        # Folder in a bucket with subfolder. Success expected.
        folder = "folder/subfolder"
        expected_path = f"s3://{TEST_BUCKET}/{folder}/{file_name}"
        obtained_path = self.s3_handler.get_uri(
            bucket=TEST_BUCKET, folder_path=folder, file_name=file_name,
        )
        assert obtained_path == expected_path

    def test_paginate(self, tmpdir):
        file_names = ["first_object.json", "second_object.json"]
        contents = ["", ""]
        generate_fixture_files(
            s3_client=self.client,
            tmpdir=tmpdir,
            file_names=file_names,
            contents=contents,
        )

        # Call function without Bucket argument. Failure expected.
        args = {
            "PaginationConfig": {"MaxItems": 1},
        }
        with pytest.raises(AssertionError) as e:
            list(
                self.s3_handler.paginate(
                    method=self.client.list_objects_v2.__name__, **args
                )
            )

        # Paginate by prefix. Success expected.
        args = {
            "Bucket": TEST_BUCKET,
            "Prefix": "test_paginate/second",
        }
        expected_objects = [f"test_paginate/{file_names[1]}"]
        obtained_objects = []
        for result in self.s3_handler.paginate(
            method=self.client.list_objects_v2.__name__, **args
        ):
            obtained_objects.append(result["Key"])
        assert obtained_objects == expected_objects

        # Limit the number of returned element. Success expected.
        args = {
            "Bucket": TEST_BUCKET,
            "PaginationConfig": {"MaxItems": 1},
        }
        expected_objects = [f"test_paginate/{file_names[0]}"]
        obtained_objects = []
        for result in self.s3_handler.paginate(
            method=self.client.list_objects_v2.__name__, **args
        ):
            obtained_objects.append(result["Key"])
        assert obtained_objects == expected_objects

    def test_list_objects(self, tmpdir):
        file_names = [
            "first_object.json",
            "second_object1.json",
            "second_object2.json",
        ]
        contents = ["", "", ""]
        generate_fixture_files(
            s3_client=self.client,
            tmpdir=tmpdir,
            file_names=file_names,
            contents=contents,
        )

        # List objects by prefix. Success expected.
        args = {
            "Prefix": "test_list_objects/second",
        }
        expected_objects = [
            f"test_list_objects/{file_names[1]}",
            f"test_list_objects/{file_names[2]}",
        ]
        obtained_objects = list(
            self.s3_handler.list_objects(bucket=TEST_BUCKET, **args)
        )
        assert obtained_objects == expected_objects

        # List objects starting from a specific key. Success expected.
        args = {
            "StartAfter": f"test_list_objects/{file_names[1]}",
        }
        expected_objects = [
            f"test_list_objects/{file_names[2]}",
        ]
        obtained_objects = list(
            self.s3_handler.list_objects(bucket=TEST_BUCKET, **args)
        )
        assert obtained_objects == expected_objects

        # List all objects. Success expected.
        expected_objects = [
            f"test_list_objects/{file_names[0]}",
            f"test_list_objects/{file_names[1]}",
            f"test_list_objects/{file_names[2]}",
        ]
        obtained_objects = list(self.s3_handler.list_objects(bucket=TEST_BUCKET,))
        assert obtained_objects == expected_objects

    def test_check_object_exists(self, tmpdir):
        file_names = ["first_object.json", "second_object.json"]
        contents = ["", ""]
        generate_fixture_files(
            s3_client=self.client,
            tmpdir=tmpdir,
            file_names=file_names,
            contents=contents,
        )

        # The method gives true when an object exist in the bucket. Success expected.
        obtained_result = self.s3_handler.check_object_exists(
            bucket=TEST_BUCKET, object_key=f"test_check_object_exists/{file_names[0]}",
        )
        assert obtained_result

        obtained_result = self.s3_handler.check_object_exists(
            bucket=TEST_BUCKET, object_key=f"test_check_object_exists/{file_names[1]}",
        )
        assert obtained_result

        # The method gives false when an object does not exist in the bucket. Success expected.
        obtained_result = self.s3_handler.check_object_exists(
            bucket=TEST_BUCKET, object_key=file_names[1]
        )
        assert not obtained_result

    def test_read_object_content(self, tmpdir):
        file_names = ["first_object.json", "second_object.json"]
        contents = ["Content1", "Content2"]
        generate_fixture_files(
            s3_client=self.client,
            tmpdir=tmpdir,
            file_names=file_names,
            contents=contents,
        )

        # Test reading an existing object. Sucess expected.
        obtained_content = self.s3_handler.read_object_content(
            bucket=TEST_BUCKET, object_key=f"test_read_object_content/{file_names[1]}",
        )
        expected_content = contents[1]
        assert obtained_content == expected_content

        # Test reading an object that does not exist. Failure expected.
        with pytest.raises(Exception) as e:
            obtained_content = self.s3_handler.read_object_content(
                bucket=TEST_BUCKET, object_key=file_names[0]
            )

    def test_put_object(self, tmpdir):
        file_names = ["first_object.json"]
        contents = ["Content1"]
        generate_fixture_files(
            s3_client=self.client,
            tmpdir=tmpdir,
            file_names=file_names,
            contents=contents,
        )

        # Put content to a new object. Success expected.
        new_object_key = "test_put_object/second_object.json"
        content_to_write = "Content2"
        self.s3_handler.put_object(
            bucket=TEST_BUCKET, object_key=new_object_key, content=content_to_write
        )

        read_object = self.resource.Object(bucket_name=TEST_BUCKET, key=new_object_key)
        content_read = read_object.get()["Body"].read().decode("utf-8")
        assert content_read == content_to_write

        # Put content to an object that already exist. Verify the content is overwriten.
        # Success expected.
        object_key = f"test_put_object/{file_names[0]}"
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
        file_names = ["first_object.json"]
        contents = [""]
        generate_fixture_files(
            s3_client=self.client,
            tmpdir=tmpdir,
            file_names=file_names,
            contents=contents,
        )

        # Validate that an object does not exist anymore after being deleted. Failure expected.
        object_key = f"test_delete_key/{file_names[0]}"
        self.resource.Object(bucket_name=TEST_BUCKET, key=object_key).get()
        self.s3_handler.delete_key(bucket=TEST_BUCKET, object_key=object_key)

        with pytest.raises(botocore.exceptions.ClientError) as e:
            self.resource.Object(bucket_name=TEST_BUCKET, key=object_key).get()

    def test_write_dataframe_to_csv_object(self, tmpdir):
        generate_fixture_files(
            s3_client=self.client, tmpdir=tmpdir, file_names=[], contents=[]
        )
        object_key = "test_write_dataframe_to_csv_object/dataframe.csv"
        data = {
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
        assert obtained_content == expected_content

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
        key_paths = [
            f"s3://{TEST_BUCKET}/test_generate_quicksight_manifest/{file_names[0]}"
        ]
        uri_prefix_paths = [
            f"s3://{TEST_BUCKET}/test_generate_quicksight_manifest/second"
        ]
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

        expected_manifest = json.dumps(data, indent=4, sort_keys=True)
        manifest_key = "test_generate_quicksight_manifest/manifest.json"
        self.s3_handler.generate_quicksight_manifest(
            bucket=TEST_BUCKET,
            object_key=manifest_key,
            s3_uris=key_paths,
            s3_uri_prefixes=uri_prefix_paths,
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
        assert obtained_manifest == expected_manifest
