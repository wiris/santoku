import json
import boto3
import pytest

from base64 import b64encode
from moto import mock_secretsmanager
from ..aws.secrets_manager_handler import SecretsManagerError
from ..aws.secrets_manager_handler import SecretsManagerHandler


class TestSecretsManagerHandler:
    def setup_method(self):
        self.mock_secretsmanager = mock_secretsmanager()
        self.mock_secretsmanager.start()

        self.secrets_manager_handler = SecretsManagerHandler()
        self.client = boto3.client("secretsmanager")

    def test_get_string_secret(self):
        secret_name = "test/secret_name"
        username = "test_user"
        password = "test_password"
        expected_secret = {"username": username, "password": password}
        self.client.create_secret(
            Name=secret_name, SecretString=json.dumps(expected_secret)
        )

        # Retrieve a string secret. Success expected.
        obtained_secret = self.secrets_manager_handler.get_secret_value(
            secret_name=secret_name
        )
        assert obtained_secret["username"] == expected_secret["username"]
        assert obtained_secret["password"] == expected_secret["password"]

    def test_get_binary_secret(self):
        secret_name = "test/secret_name"
        username = "test_user"
        password = "test_password"
        expected_secret = {"username": username, "password": password}

        secret_binary = b64encode(json.dumps(expected_secret).encode())
        self.client.create_secret(Name=secret_name, SecretBinary=secret_binary)

        # Retrieve a binary secret. Success expected.
        obtained_secret = self.secrets_manager_handler.get_secret_value(
            secret_name=secret_name
        )
        assert obtained_secret["username"] == expected_secret["username"]
        assert obtained_secret["password"] == expected_secret["password"]

    def test_get_non_existent_secret(self):
        secret_name = "test/secret_name"
        username = "test_user"
        password = "test_password"
        expected_secret = {"username": username, "password": password}

        secret_binary = b64encode(json.dumps(expected_secret).encode())
        self.client.create_secret(Name=secret_name, SecretBinary=secret_binary)

        # Retreive a secret that does not exist. Failure expected.
        expected_message = "Secrets Manager can't find the resource you asked for."
        with pytest.raises(SecretsManagerError, match=expected_message) as e:
            obtained_secret = self.secrets_manager_handler.get_secret_value(
                secret_name="wrong_name"
            )

    # TODO: Test with an KMS encripted key.
