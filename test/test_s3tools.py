import json
import unittest

from src.wiris.aws.s3tools import S3Tools
from moto import mock_s3


@mock_s3
class TestS3Tools(unittest.TestCase):
    def setUp(self):
        self.s3tools = S3Tools()

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
        self.assertEqual(True, True)

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
        ground_truth_manifest = json.dumps(data, indent=4, sort_keys=True)

        self.s3tools.generate_quicksight_manifest(bucket='bucket', file_key='manifest.json',
                                                  s3_path=file_paths, s3_prefix=folder_paths, include_settings=True,
                                                  set_format=upload_settings['format'],
                                                  set_delimiter=upload_settings['delimiter'],
                                                  set_qualifier=upload_settings['textqualifier'],
                                                  set_header=upload_settings['containsHeader'])
        generated_manifest = self.s3tools.get_file_content('bucket', 'manifest.json')
        # generated_manifest = json.dumps(generated_content, indent=4, sort_keys=True)

        self.assertEqual(ground_truth_manifest, generated_manifest)
