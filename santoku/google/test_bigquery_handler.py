from typing import List

from moto import mock_secretsmanager
from ..google.bigquery_handler import BigQueryHandler

"""
TODO: investigate the possibility of mocking BigQuery (and other Google services) for testing
"""


class TestS3Handler:
    def setup_method(self):
        pass

    def teardown_method(self):
        pass

    def test_run_query(self):
        pass
