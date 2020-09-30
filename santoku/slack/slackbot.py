import json

from typing import List

from slack import WebClient
from slack.errors import SlackApiError

from santoku.aws.secretsmanager import SecretsManagerHandler


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
        Retrieve the slack app oauth token from AWS Secrets Manager and initialize the slack client.
        Requires that AWS credentials with the appropriate permissions are located somewhere on the
        AWS credential chain in the local machine.

        Paramaters
        ----------
        secret_name : str
            Name or ARN for the secret containing the token needed for the Slack bot authentication.

        secret_key : str, optional
            Key of the stored secret. (By default "API_TOKEN" will be the key that stores the slack
            app oauth token.)

        See Also
        --------
        __init__ : this method calls the constructor.

        """
        secrets_manager = SecretsManagerHandler()
        credential_info = secrets_manager.get_secret_value(secret_name=secret_name)
        return cls(api_token=credential_info[secret_key])

    def send_message(self, channel: str, **kwargs) -> None:
        """
        Send a custom `message` to the `channel`.

        Parameters
        ----------
        channel : str
            To where the bot will send the message.
        message : str
            Custom message that will be sent to the chanel.
        blocks : List[Dict[str, Any]]
            JSON formatted string for a block structure [2]

        Raises
        ------
        SlackBotError
            If the authentication token is invalid or if the specified channel cannot be found.

        Notes
        -----
            In order to successfully send the message, the bot must be added to the workspace, it
            also needs to have the scopes to send message to the specified channel approved, this
            can be configured in: [1].

        References
        ----------
        [1] :
        https://wiris.slack.com/apps/manage

        [2] :
        https://api.slack.com/block-kit
        """
        try:
            self.client.chat_postMessage(channel=channel, **kwargs)
        except SlackApiError as e:
            raise e

    def send_process_report(
        self,
        channel: str,
        process_name: str,
        messages: List[str],
        is_success: bool,
        context_message: str,
        context_url: str,
        context_img: str = "https://bitbucket-assetroot.s3.amazonaws.com/c/photos/2020/Aug/06/1924969399-7-lambda-moodle-referers-logo_avatar.png",
    ) -> None:
        """
        Posts a message to `channel`, using Slack's blocks API to

        Parameters
        ----------
        channel: str
            To where the bot will send the message.
        process_name: str
            ID of the process posting the report.
        messages: List[str]
            List of report messages to send to Slack
        is_success: bool
            Process success status
        context_url: str
            URL to include in the context
        context_message: str
            Message to display in the context
        context_img: str
            Image to include in the context thumbnail
        """

        blocks: List[dict] = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{process_name} {':heavy_check_mark:' if is_success else ':x:'}",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "\n".join([f"- {m}" for m in messages])},
            },
        ]

        if context_message and context_url and context_img:
            blocks.append(
                {
                    "type": "context",
                    "elements": [
                        {"type": "image", "image_url": context_img, "alt_text": "images"},
                        {"type": "mrkdwn", "text": f"<{context_url}|{context_message}>"},
                    ],
                }
            )

        self.send_message(channel=channel, blocks=blocks)
