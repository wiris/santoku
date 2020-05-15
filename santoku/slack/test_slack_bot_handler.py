import os
import json
import pytest

from moto import mock_secretsmanager
from ..slack import SlackBotHandler
from ..slack import SlackBotError
from ..aws import SecretsManagerHandler


@pytest.fixture(scope="class")
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "eu-west-1"


@pytest.fixture(scope="class")
def secrets_manager(aws_credentials):
    with mock_secretsmanager():
        secrets_manager = SecretsManagerHandler()
        yield secrets_manager


@pytest.fixture(scope="class")
def secret_token():
    yield os.environ["SLACK_BOT_API_TOKEN"]


@pytest.fixture(scope="function")
def secret_with_default_key(secrets_manager, secret_token, request):
    secret_name = "test/secret_with_default_key"
    secret_content = {"API_TOKEN": secret_token}
    secrets_manager.client.create_secret(Name=secret_name, SecretString=json.dumps(secret_content))
    yield secret_name

    def teardown():
        secrets_manager.client.delete_secret(SecretId=secret_name, ForceDeleteWithoutRecovery=True)

    request.addfinalizer(teardown)


@pytest.fixture(scope="function")
def secret_key():
    yield "SLACK_BOT_API_TOKEN"


@pytest.fixture(scope="function")
def secret_with_not_default_key(secrets_manager, secret_key, secret_token, request):
    secret_name = "test/secret_with_not_default_key"
    secret_content = {secret_key: secret_token}
    secrets_manager.client.create_secret(Name=secret_name, SecretString=json.dumps(secret_content))
    yield secret_name

    def teardown():
        secrets_manager.client.delete_secret(SecretId=secret_name, ForceDeleteWithoutRecovery=True)

    request.addfinalizer(teardown)


@pytest.fixture(scope="class")
def chanel_name():
    yield "bi-notifications-test"


class TestSlackBotHandler:
    def test_send_message_to_channel(self, chanel_name, secret_token):
        # Test sending a message to the testing chanel. Success expected.
        slack_bot = SlackBotHandler(api_token=secret_token)
        message = "`test_send_message_to_channel` is running."
        slack_bot.send_message(channel=chanel_name, message=message)

    def test_init_handler_from_secrets_manager(
        self, secret_with_default_key, secret_with_not_default_key, secret_key, chanel_name
    ):
        # Test sending a message to the test chanel from a secret created in secrets manager using
        # the default secret key by convention. Success expected.
        slack_bot = SlackBotHandler.from_aws_secrets_manager(secret_name=secret_with_default_key)
        message = (
            "`test_init_handler_from_secrets_manager` using the default secret key is running."
        )
        slack_bot.send_message(channel=chanel_name, message=message)

        # Test sending a message to the test chanel from a secret created in secrets manager using
        # a secret key different that the default one. Success expected.
        message = (
            "`test_init_handler_from_secrets_manager` not using the default secret key is running."
        )
        slack_bot = SlackBotHandler.from_aws_secrets_manager(
            secret_name=secret_with_not_default_key, secret_key=secret_key
        )
        slack_bot.send_message(channel=chanel_name, message=message)

    def test_send_message_with_invalid_auth(self, chanel_name):
        # Test sending a message using invalid slack credentials. Failure expected.
        slack_bot = SlackBotHandler(api_token="wrong_token")
        expected_message = "The authentication token is invalid."
        message = "`test_send_message_with_invalid_auth` test is running."
        with pytest.raises(SlackBotError, match=expected_message) as e:
            slack_bot.send_message(channel=chanel_name, message=message)

    def test_send_message_to_wrong_chanel(self, secret_token):
        # Test sending a message to a channel that does not exist. Failure expected.
        slack_bot = SlackBotHandler(api_token=secret_token)
        expected_message = "The channel was not found."
        message = "`test_send_message_to_wrong_chanel` test is running."
        with pytest.raises(SlackBotError, match=expected_message) as e:
            slack_bot.send_message(channel="wrong_chanel", message=message)
