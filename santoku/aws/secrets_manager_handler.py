import json
import boto3

from base64 import b64decode
from typing import Dict, Any

from botocore.exceptions import ClientError


class SecretsManagerError(Exception):
    def __init__(self, message):
        super().__init__(message)


class SecretsManagerHandler:
    """
    Class to manage operations of AWS Secrets Manager Service (SQS).

    This class is intended to be used in other projects when the use of secrets is required.
    Secrets Manager allows the storage and retreiving of secrets in a safe way. The
    connection to the Secrets Manager service is done using the service class Client of the boto3
    library.

    """

    def __init__(self, **kwargs):
        """
        Initializes the services classes.

        Notes
        -----
            More information on the available regions: [1]

        References
        ----------
        [1] :
        https://aws.amazon.com/about-aws/global-infrastructure/regions_az/

        """
        self.client = boto3.client(service_name="secretsmanager", **kwargs)

    def get_secret_value(self, secret_name: str) -> Dict[str, Any]:
        """
        Retreive the content of the secret with name `secret_name`.

        Parameters
        ----------
        secret_name : str
            Id of secret to retreive.

        Raises
        ------
        SecretsManagerError
            If the secret cannot be decrypted correctly, if there was an error on the server side,
            if there were invalid parameters, if a parameter is not valid for the current state of
            the resource, if the secret was not found.

        Returns
        -------
        Dict[str, Any]
            The content of the secret with its correspondent key and value.

        """

        try:
            secret_value_response = self.client.get_secret_value(SecretId=secret_name)
        except ClientError as e:
            if e.response["Error"]["Code"] == "DecryptionFailureException":
                error_message = (
                    "Secrets Manager can't decrypt the protected secret using the provided KMS key."
                )
                raise SecretsManagerError(error_message)
            elif e.response["Error"]["Code"] == "InternalServiceErrorException":
                error_message = "An error occured on the server side."
                raise SecretsManagerError(error_message)
            elif e.response["Error"]["Code"] == "InvalidParameterException":
                error_message = "You provided an invalid value for a parameter."
                raise SecretsManagerError(error_message)
            elif e.response["Error"]["Code"] == "InvalidRequestException":
                error_message = "You provided a parameter value that is not valid for the current state of the resource."
                raise SecretsManagerError(error_message)
            elif e.response["Error"]["Code"] == "ResourceNotFoundException":
                error_message = "Secrets Manager can't find the resource you asked for."
                raise SecretsManagerError(error_message)
            else:
                # unknown error
                raise e
        else:
            # Depending on whether the secret is binary or string one of these fields will be populated.
            if "SecretString" in secret_value_response:
                secret_str = secret_value_response["SecretString"]
            else:
                secret_str = b64decode(secret_value_response["SecretBinary"])
            secret = json.loads(secret_str)
        return secret
