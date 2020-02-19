import os
import json
import boto3
import botocore
import unittest
import nose2

from datetime import datetime
from moto import mock_s3
from ..aws.s3 import S3

"""
TODO: this whole section might serve in the future as test suite for this library
      The idea is to use moto to locally simulate the aws services so that the suite can run without actually
      connecting to the aws cloud, thus saving $$ and reducing the latency of the tests
"""

TEST_BUCKET = 'wiris-stats-data'
TEST_PREFIX = 'mock_prefix'



class TestS3(unittest.TestCase):
    """
    def setUp(self):
        self.s3tools = S3Tools()
        self.client = boto3.client('s3')
        try:
            self.s3 = boto3.resource('s3',
                                     region_name='eu-west-1',
                                     aws_access_key_id='fake_access_key',
                                     aws_secret_access_key='fake_secret_key')
            self.s3.meta.client.head_bucket(Bucket=TEST_BUCKET)
        except botocore.exceptions.ClientError:
            pass
        else:
            err = '{bucket} should not exist.'.format(bucket=TEST_BUCKET)
            raise EnvironmentError(err)
        self.client.create_bucket(Bucket=TEST_BUCKET)
        current_dir = os.path.dirname(__file__)
        fixture_dir = os.path.join(current_dir, 'test_s3tools_fixtures')
        _upload_fixtures(TEST_BUCKET, fixture_dir)
    """

    """
    def tearDown(self):
        bucket = self.s3.Bucket(TEST_BUCKET)
        for key in bucket.objects.all():
            key.delete()
        bucket.delete()
    """

    @mock_s3
    def test_generate_quicksight_manifest(self):

        s3 = S3()

        client = boto3.client('s3', region_name='eu-west-1',
                                    aws_access_key_id='fake_access_key',
                                    aws_secret_access_key='fake_secret_key')
        resource = boto3.resource('s3',
                                     region_name='eu-west-1',
                                     aws_access_key_id='fake_access_key',
                                     aws_secret_access_key='fake_secret_key')
        resource.meta.client.head_bucket(Bucket=TEST_BUCKET)
        client.create_bucket(Bucket=TEST_BUCKET)
        current_dir = os.path.dirname(__file__)
        fixture_dir = os.path.join(current_dir, 'test_s3tools_fixtures')

        """
        s3_bucket = 'wiris-stats-data'
        s3_prefix = 'mt_crash_dumps/processed_data/processed_dumps'

        manifest_key = 'quicksight_manifests/mt_crash_dumps_manifest_test.json'
        prefix = s3.get_absolute_path(s3_bucket, s3_prefix)
        print(prefix)
        s3.generate_quicksight_manifest(bucket=s3_bucket, file_key=manifest_key, s3_prefix=[prefix], set_format='CSV')
        """

    def test_get_absolute_path(self):
        file_key = 'test_file.test'

        # test 1: file in a bucket, no prefix
        true_path = 's3://test_bucket/test_file.test'
        generated_path = self.s3tools.get_absolute_path(TEST_BUCKET, file_key)
        self.assertEqual(true_path, generated_path)

        # test 2: file in a folder, prefix is the folder with /
        prefix = 'folder/'
        true_path = 's3://test_bucket/folder/test_file.test'
        generated_path = self.s3tools.get_absolute_path(bucket, file_key, prefix=prefix)
        self.assertEqual(true_path, generated_path)

        # test 3: file in folder, prefix is the folder without /
        prefix = 'folder'
        true_path = 's3://test_bucket/folder/test_file.test'
        generated_path = self.s3tools.get_absolute_path(bucket, file_key, prefix=prefix)
        self.assertEqual(true_path, generated_path)

        # test 4: prefix is not the folder
        prefix = 'some_'
        true_path = 's3://test_bucket/some_test_file.test'
        generated_path = self.s3tools.get_absolute_path(bucket, file_key, prefix=prefix, prefix_is_folder=False)
        self.assertEqual(true_path, generated_path)

    def test_get_keys_as_generator(self):
        self.assertEqual(True, True)

    def test_paginate(self):
        self.assertEqual(True, True)

    def test_list_objects(self):
        self.assertEqual(True, True)

    def test_get_file_content(self):
        self.assertEqual(True, True)

    def test_write_file(self):
        self.assertEqual(True, True)

    def test_delete_file(self):
        # test resource mode
        file_to_delete = 'test_delete_file/resource/delete.json'
        self.s3t.delete_file(TEST_BUCKET, file_to_delete, mode='resource')
        leftover = []
        paginator = self.client.get_paginator(self.client.list_objects_v2.__name__)
        for page in paginator.paginate(Bucket=TEST_BUCKET, Prefix='test_delete_file/resource').result_key_iters():
            for result in page:
                leftover.append(result['key'])
        desired_leftover = ['do-not-delete.json']
        self.assertCountEqual(leftover, desired_leftover)

        # test client mode
        file_to_delete = 'test_delete_file/client/delete.json'
        self.s3t.delete_file(TEST_BUCKET, file_to_delete, mode='resource')
        leftover = []
        paginator = self.client.get_paginator(self.client.list_objects_v2.__name__)
        for page in paginator.paginate(Bucket=TEST_BUCKET, Prefix='test_delete_file/client').result_key_iters():
            for result in page:
                leftover.append(result['key'])
        desired_leftover = ['do-not-delete.json']
        self.assertCountEqual(leftover, desired_leftover)

    def test_delete_files(self):
        self.assertEqual(True, True)

    def test_generate_correct_qs_manifest(self):
        file_paths = ["s3://bucket/file1.csv", "s3://bucket/file2.csv", "s3://bucket/file3.csv"]
        folder_paths = ["s3://bucket/folder1/", "s3://bucket/folder2/", "s3://bucket/folder3/"]
        upload_settings = {"format": "CSV",
                           "delimiter": ",",
                           "textqualifier": "'",
                           "containsHeader": True}

        data = {"fileLocations": [{"URIs": file_paths}, {"URIPrefixes": folder_paths}],
                "globalUploadSettings": upload_settings}
        expected_manifest = json.dumps(data, indent=4, sort_keys=True)
        manifest_key = 'test_generate_correct_qs_manifest/manifest.json'
        self.s3tools.generate_quicksight_manifest(bucket=TEST_BUCKET,
                                                  file_key=manifest_key,
                                                  s3_path=file_paths, s3_prefix=folder_paths, include_settings=True,
                                                  set_format=upload_settings['format'],
                                                  set_delimiter=upload_settings['delimiter'],
                                                  set_qualifier=upload_settings['textqualifier'],
                                                  set_header=upload_settings['containsHeader'])

        generated_manifest = self.resource.Object(TEST_BUCKET, manifest_key).get()['Body'].read()
        # generated_manifest = self.s3tools.get_file_content('bucket', 'manifest.json')
        # generated_manifest = json.dumps(generated_content, indent=4, sort_keys=True)

        self.assertEqual(expected_manifest, generated_manifest)

def _upload_fixtures(bucket: str, fixture_dir: str) -> None:
    #client = boto3.client('s3')
    fixture_paths = [
        os.path.join(path, filename)
        for path, _, files in os.walk(fixture_dir)
        for filename in files
    ]
    for path in fixture_paths:
        key = os.path.relpath(path, fixture_dir)
        self.client.upload_file(Filename=path, Bucket=bucket, Key=key)
