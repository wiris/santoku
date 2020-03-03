FROM python:3.8.1-buster

RUN pip --no-cache-dir install -U boto3 moto pandas nose2 black mypy

# This enables git autocomplete.
RUN source /usr/share/bash-completion/completions/git