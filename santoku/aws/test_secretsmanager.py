import os
import json

import pytest
import boto3

from base64 import b64encode

from moto import mock_secretsmanager

from santoku.aws.secretsmanager import SecretsManagerError, SecretsManagerHandler


@pytest.fixture(scope="class")
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "eu-west-1"


@pytest.fixture(scope="class")
def secrets_manager_handler(aws_credentials):
    with mock_secretsmanager():
        secrets_manager = SecretsManagerHandler()
        yield secrets_manager


@pytest.fixture(scope="class")
def secret_content():
    username = "test_user"
    password = "test_password"
    secret_content = {"username": username, "password": password}
    return secret_content


@pytest.fixture(scope="function")
def string_secret(secrets_manager_handler, secret_content, request):
    secret_name = "test/secret_name"
    secrets_manager_handler.client.create_secret(
        Name=secret_name, SecretString=json.dumps(secret_content)
    )
    yield secret_name

    def teardown():
        secrets_manager_handler.client.delete_secret(
            SecretId=secret_name, ForceDeleteWithoutRecovery=True
        )

    request.addfinalizer(teardown)


@pytest.fixture(scope="function")
def binary_secret(secrets_manager_handler, secret_content, request):
    secret_name = "test/secret_name"
    secret_binary = b64encode(json.dumps(secret_content).encode())
    secrets_manager_handler.client.create_secret(Name=secret_name, SecretBinary=secret_binary)
    yield secret_name

    def teardown():
        secrets_manager_handler.client.delete_secret(
            SecretId=secret_name, ForceDeleteWithoutRecovery=True
        )

    request.addfinalizer(teardown)


class TestSecretsManagerHandler:
    def test_get_string_secret(self, secrets_manager_handler, secret_content, string_secret):
        # Retrieve a string secret. Success expected.
        obtained_secret = secrets_manager_handler.get_secret_value(secret_name=string_secret)
        assert obtained_secret["username"] == secret_content["username"]
        assert obtained_secret["password"] == secret_content["password"]

    def test_get_binary_secret(self, secrets_manager_handler, secret_content, binary_secret):
        # Retrieve a string secret. Success expected.
        obtained_secret = secrets_manager_handler.get_secret_value(secret_name=binary_secret)
        assert obtained_secret["username"] == secret_content["username"]
        assert obtained_secret["password"] == secret_content["password"]

    def test_get_non_existent_secret(self, secrets_manager_handler):
        # Retreive a secret that does not exist. Failure expected.
        expected_message = "Secrets Manager can't find the resource you asked for."
        with pytest.raises(SecretsManagerError, match=expected_message) as e:
            obtained_secret = secrets_manager_handler.get_secret_value(secret_name="wrong_secret")

    # TODO: Test with an KMS encripted key.
