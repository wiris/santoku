from typing import List

from ..google.bigquery import BigQueryHandler

"""
TODO: investigate the possibility of mocking BigQuery (and other Google services) for testing
"""


class TestS3Handler:
    def test_run_query(self):
        bigquery = BigQueryHandler.from_aws_secrets_manager(
            secret_name="gcloud/datascience_query_service_account"
        )
