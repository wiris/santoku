# What is Santoku?

Santoku is a toolkit written in Python for interacting with AWS services, Salesforce and many more things.

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

slack_bot = SlackBotHandler.from_aws_secrets_manager(...)
slack_bot.send_message(channel="channel", message="Message")

```

## Development

### Environment

We provide a development environment that uses Visual Studio Code Remote - Containers extension. This extension lets...

### Sharing Git credentials with your container

The containerized environment will automatically forward your local SSH agent if one is running.
More info [here](https://code.visualstudio.com/docs/remote/containers#_using-ssh-keys) and it works for Windows and Linux.

## Setting credentials as environment variables
The code for the tests contains everything the tests need to run with the exception of some credentials, which are (of course) not versioned.

The containerized environment will automatically forward your credentials stored in a .env file and set them as environment variables.

Notice that this means you must have a .env file in the root directory of this project no matter you require credentials or not (the file might be empty).

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
