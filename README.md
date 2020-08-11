# What is Santoku?

Santoku is a toolkit written in Python for interacting with AWS, Google Cloud services, Salesforce and Slack.

The purpose of Santoku is to have the interactions with all the external services collected in a single package. The package contains wrappers to the APIs of the external services in order to make easy the handling of operations.

## Quickstart

### Installation

If you have a wheel, run the following command:

```bash
pip install --upgrade --force-reinstall dist/santoku-*.whl
```

### Installation with PIP

Run the following command:

```bash
pip install santoku
```

### How To Use It

You can use the package as follows:

```python
from santoku.slack import SlackBotHandler

slack_bot = SlackBotHandler.from_aws_secrets_manager("your_secret")
```

## Content

The package `santoku` contains several subpackages: `aws`, `google`, `salesforce` and `slack`. Each subpackage provides connection to different external services and are formed by a collection of modules, where each module consists of handlers for more specific services. Each handler class has unit tests to ensure the correct behaviour of the methods of these classes.

### AWS

The connection to AWS has been done through [boto3](https://github.com/boto/boto3). We provide wrappers of the `boto3` sdk to make easy the operations to interact with different services.

The use of this subpackage requires having AWS credentials somewhere. We provide flexibility to either keep credentials in AWS credentials/configuration file or to pass them directly as arguments in the initializer of each handler class. More info on AWS configurations and credentials [here](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html)

The unit tests in this subpackage implement mocks to the AWS services and do not pretended to access or modify the environment of your real account.

#### S3

We provide methods to easily list and delete objects inside buckets; read and write content into S3 objects; upload a dataframe into csv or parket format to a specific location; generate and upload a quicksight manifest in S3 in order to create analysis in Amazon Quickgsight, and so on.

Example of writing an object into S3:

```python
from aws.s3_handler import S3Handler

s3_handler = S3Handler()
s3_handler.put_object(bucket="your_bucket_name", object_key="your_object_key", content="Your object content.")
```

#### Secrets Manager

We provide methods to get the content of a created secret.

Example of use:

```python
from aws.secrets_manager_handler import SecretsManagerHandler

secrets_manager = SecretsManagerHandler()
secret_content = secrets_manager.get_secret_value(secret_name="your_secret_name")
```

This module is also used in other subpackages to simplify the instantiation: the needed credentials to initialize certain service can be retrieved from AWS Secrets Manager.

#### SQS

We provide methods to receive, delete, and send single or a batch of messages.

Example of use:

```python
from aws.sqs_handler import SQSHandler

sqs_handler = SQSHandler()
entries = [
    {
        "Id": "Id1",
        "MessageBody": "Your message 1",
    },
    {
        "Id": "Id2",
        "MessageBody": "Your message 1",
    }
]
entries.append(message)
sqs_handler.send_message_batch(queue_name="your_queue_name", entries=entries)
```

### Google

The connection to Google Cloud Services has been done using the [google-cloud-core](https://googleapis.dev/python/google-api-core/latest/index.html) package.

We provide a handler that allows doing queries on BigQuery services.

The use of this subpackage requires having Google Cloud Services credentials, these can be passed as argument in the initializer of the handler class directly, or you can store them in AWS Secrets Manager and retrieve them during the initialization using the `from_aws_secrets_manager` method instead.

Examples of initialization:

```python
from santoku.google import BigQueryHandler

bigquery_handler = BigQueryHandler(
    type="your_type",
    project_id="your_project_id"
    private_key_id="your_private_key_id"
    private_key="your_private_key"
    client_email="your_client_email"
    client_id="your_client_id"
    auth_uri="your_auth_uri"
    token_uri="your_token_uri"
    auth_provider_x509_cert_url="your_auth_provider_x509_cert_url"
    client_x509_cert_url="your_client_x509_cert_url"
)
```
or
```python
bigquery_handler = BigQueryHandler.from_aws_secrets_manager(
    secret_name="your_secret_name"
)
```

Examples of queries:
```python
query_results = bigquery_handler.get_query_results(query="SELECT * FROM `your_table`")
```

### Salesforce

The connection to Salesforce has been done using the [REST API of Salesforce](https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/quickstart.htm).

The use of this subpackage requires having Salesforce credentials, these can be passed as argument in the initializer of the handler class directly, or you can store them in AWS Secrets Manager and retrieve them during the initialization using the `from_aws_secrets_manager` method instead.

This subpackage provide methods to insert/modify/delete salesforce object records. You can perform operations by doing HTTP requests directly or using methods with higher level of abstraction easier to handle, the lasts ones are just wrappers of the HTTP request method. To obtain records you can perform queries using SOQL.

The unit tests requires valid Salesforce credentials to be executed. The tests are implemented in the way that no new data will remain in the account and no existent data will be modified. However, having Salesforce credentials for sandbox use is recommended.

Examples of initialization:

```python
from santoku.salesforce import ObjectsHandler

objects_handler = ObjectsHandler(
    auth_url="your_auth_url",
    username="your_username",
    password="your_password",
    client_id="your_client_id",
    client_secret="your_client_secret",
)
```
or
```python
objects_handler = ObjectsHandler.from_aws_secrets_manager(secret_name="your_salesforce_secret")
```

Examples of insertion with different methods:

```python
contact_payload = {"FirstName": "Alice", "LastName": "Ackerman", "Email": "alice@example.com"}

objects_handler.do_request(method="POST", path="sobjects/Contact", payload=contact_payload)
```
or
```python
objects_handler.insert_record(sobject="Contact", payload=contact_payload)
```

Examples of SOQL:

```python
records = objects_handler.do_query_with_SOQL("SELECT Id, Name from Contact")
```

### Slack

The connection to Slack has been done using [Slack Web API](https://slack.dev/python-slackclient/basic_usage.html)

The use of this subpackage requires having Slack API Token of a Slack Bot, which can be passed as argument in the initializer of the handler class directly, or you can store it in AWS Secrets Manager and retrieve it during the initialization using the `from_aws_secrets_manager` method instead.

This subpackage provide methods to send messages to a channel.

Examples of initialization:
```python
from santoku.slack import SlackBotHandler

slack_bot_handler = SlackBotHandler(api_token="your_api_token")
```
or
```python
slack_bot_handler = SlackBotHandler.from_aws_secrets_manager(secret_name="your_secret_name")
```

Examples of sending of message:

```python
slack_bot_handler.send_message(channel="your_chanel_name", message="Your message.")
```

## Development

### Environment

We provide a development environment that uses Visual Studio Code Remote - Containers extension. This extension lets you use a Docker container in order to have a consistent and easily reproducible development environment.

The files needed to build the container is located in the `.devcontainer` directory.
* `devcontainer.json` contains a set of configurations and tells how VSCode should access the container.
* `Dockerfile` defines instructions for the building of the container image.
* `requirements.txt` specifies the required dependencies for the development process.

More info [here](https://code.visualstudio.com/docs/remote/containers-tutorial)

### Sharing Git credentials with your container

The containerized environment will automatically forward your local SSH agent if one is running.
More info [here](https://code.visualstudio.com/docs/remote/containers#_using-ssh-keys) and it works for Windows and Linux.

### Setting credentials as environment variables

The code for the tests contains everything the tests need to run with the exception of some credentials, which are (of course) not versioned.

The containerized environment will automatically forward your credentials stored in a .env file and set them as environment variables.

Notice that this means you must have a .env file in the root directory of this project no matter you require credentials or not (the file might be empty).

### Running tests

The tests are implemented with pytest and there are unit tests for each of the handler modules. Tests in the `aws` subpackage implement mocks to S3 and do not require real credentials, however, the remaining tests in other subpackages do. To run the tests just run `pytest santoku`.

### Packaging

To create the package execute:

```bash
python3 setup.py bdist_wheel
```

The output of this command is the file `dist/santoku-*.whl`.

This file can be uploaded to S3 and included in the list of Python library path for certain job. Several libraries can be provided as dependencies using a comma-separated list.

## Why Santoku?

From Wikipedia:

```text
The Santoku bōchō (Japanese: 三徳包丁; "three virtues" or "three uses") or Bunka bōchō (文化包丁) is a general-purpose kitchen knife originating in Japan. Its blade is typically between 13 and 20 cm (5 and 8 in) long, and has a flat edge and a sheepsfoot blade that curves down an angle approaching 60 degrees at the point. The term Santoku may refer to the wide variety of ingredients that the knife can handle: meat, fish and vegetables, or to the tasks it can perform: slicing, chopping and dicing, either interpretation indicating a multi-use, general-purpose kitchen knife.
```
