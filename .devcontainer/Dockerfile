FROM python:3.8.1-buster

RUN apt-get update && \
    apt-get install -y pylint && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN pip --no-cache-dir install -U boto3 moto nose2