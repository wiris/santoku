from slack import WebClient
from slack.errors import SlackApiError
from ..aws import SecretsManagerHandler


class SlackBotError(Exception):
    def __init__(self, message):
        super().__init__(message)


class SlackBotHandler:
    """
    Class to manage the connection with an application bot of slack and the real time messaging to
    a chanel.

    Notes
    -----
    More information on slack apps: [1]

    References
    ----------
    [1] :
    https://api.slack.com/authentication/basics

    """

    def __init__(self, api_token: str):
        """
        Initialize the slack client.

        Parameters
        ----------
        api_token : str
            The api token of the application bot.

        Notes
        -----
            More information on the Slack Web API: [1].
            More information on the Slack Client: [2].

        References
        ----------
        [1] :
        https://slack.dev/python-slackclient/basic_usage.html

        [2]:
        https://github.com/slackapi/python-slackclient

        """
        self.client = WebClient(token=api_token)

    @classmethod
    def from_aws_secrets_manager(cls, secret_name: str, secret_key: str = "API_TOKEN"):
        """
        Retrieve the secret id where the slack app oauth token is stored from AWS Secrets Manager.
        Requires that AWS credentials with the appropriate permissions are located somewhere on the
        AWS credential chain in the local machine.

        Paramaters
        ----------
        secret_name : str
            Name or ARN for the secret containing the JSON needed for the Slack bot authentication.

        secret_key : str, optional
            Key of the stored secret. By default "API_TOKEN" will be the convention we use to call
            the keys of the slack app oauth tokens.

        """
        secrets_manager = SecretsManagerHandler()
        credential_info = secrets_manager.get_secret_value(secret_name=secret_name)
        return cls(api_token=credential_info[secret_key])

    def send_message(self, channel: str, message: str):
        """
        Send a custom `message` to the `channel`.

        Parameters
        ----------
        channel : str
            To where the bot will send the message.
        message : str
            Custom message that will be sent to the chanel.

        Raises
        ------
        SlackBotError
            If the authentication token is invalid or if the specified channel cannot be found.

        Notes
        -----
            So that the sending of message can be successful, the bot must be added to the
            workspace, it also needs to have the scopes to send message to the specified channel
            approved, this can be configured in: [1].

        References
        ----------
        [1] :
        https://wiris.slack.com/apps/manage

        """

        try:
            response = self.client.chat_postMessage(channel=channel, text=message)
        except SlackApiError as e:
            # SlackApiError is raised if "ok" is False.
            if e.response["error"] == "invalid_auth":
                error_message = "The authentication token is invalid."
                raise SlackBotError(error_message)

            elif e.response["error"] == "channel_not_found":
                error_message = "The channel was not found."
                raise SlackBotError(error_message)
