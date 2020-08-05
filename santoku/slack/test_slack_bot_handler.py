import os
import json
import pytest

from moto import mock_secretsmanager
from ..slack import SlackBotHandler
from ..slack import SlackBotError
from ..aws import SecretsManagerHandler
from ..exceptions import MissingEnvironmentVariables

if "SLACK_BOT_API_TOKEN" not in os.environ:
    raise MissingEnvironmentVariables("Slack bot api token environment variable is missing.")


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
    return os.environ["SLACK_BOT_API_TOKEN"]


@pytest.fixture(scope="class")
def slack_bot(secret_token):
    return SlackBotHandler(api_token=secret_token)


@pytest.fixture(scope="function")
def secret_with_default_key(secrets_manager, secret_token, request):
    secret_name = "test/secret_with_default_key"
    secret_key = "API_TOKEN"
    secret_content = {secret_key: secret_token}
    secrets_manager.client.create_secret(Name=secret_name, SecretString=json.dumps(secret_content))

    yield secret_name

    def teardown() -> None:
        secrets_manager.client.delete_secret(SecretId=secret_name, ForceDeleteWithoutRecovery=True)

    request.addfinalizer(teardown)


@pytest.fixture(scope="function")
def secret_with_non_default_key(secrets_manager, secret_token, request):
    secret_name = "test/secret_with_non_default_keys"
    secret_key = "SLACK_BOT_API_TOKEN"
    secret_content = {secret_key: secret_token}
    secrets_manager.client.create_secret(Name=secret_name, SecretString=json.dumps(secret_content))

    yield secret_name, secret_key

    def teardown() -> None:
        secrets_manager.client.delete_secret(SecretId=secret_name, ForceDeleteWithoutRecovery=True)

    request.addfinalizer(teardown)


@pytest.fixture(scope="class")
def channel_name():
    return "bi-notifications-test"


class TestSlackBotHandler:
    def test_send_message_to_channel(self, channel_name, slack_bot):
        # Test sending a message to the testing channel. Success expected.
        message = "`test_send_message_to_channel` is running."
        try:
            slack_bot.send_message(channel=channel_name, message=message)
        except:
            assert False
        else:
            assert True

    def test_init_handler_from_secrets_manager(
        self, secret_with_default_key, secret_with_non_default_key, channel_name
    ):
        # Test sending a message to the test channel from a secret created in secrets manager using
        # the default secret key by convention. Success expected.
        slack_bot = SlackBotHandler.from_aws_secrets_manager(secret_name=secret_with_default_key)
        message = (
            "`test_init_handler_from_secrets_manager` using the default secret key is running."
        )
        try:
            slack_bot.send_message(channel=channel_name, message=message)
        except:
            assert False
        else:
            assert True

        # Test sending a message to the test channel from a secret created in secrets manager using
        # a secret key different that the default one. Success expected.
        message = (
            "`test_init_handler_from_secrets_manager` using non-default secret key is running."
        )
        slack_bot = SlackBotHandler.from_aws_secrets_manager(
            secret_name=secret_with_non_default_key[0], secret_key=secret_with_non_default_key[1]
        )
        try:
            slack_bot.send_message(channel=channel_name, message=message)
        except:
            assert False
        else:
            assert True

    def test_send_message_with_invalid_auth(self, channel_name):
        # Test sending a message using invalid slack credentials. Failure expected.
        slack_bot = SlackBotHandler(api_token="wrong_token")
        expected_message = "The authentication token is invalid."
        message = "`test_send_message_with_invalid_auth` test is running."
        with pytest.raises(SlackBotError, match=expected_message) as e:
            slack_bot.send_message(channel=channel_name, message=message)

    def test_send_message_to_wrong_channel(self, slack_bot):
        # Test sending a message to a channel that does not exist. Failure expected.
        expected_message = "The channel was not found."
        message = "`test_send_message_to_wrong_channel` test is running."
        with pytest.raises(SlackBotError, match=expected_message) as e:
            slack_bot.send_message(channel="wrong_channel", message=message)
