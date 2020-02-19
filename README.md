# Santoku: ETL Toolkit for handling AWS, Salesforce and many more things written in Python

This repository contains a set of tools to be used in AWS services like Amazon's ETL: AWS Glue.

## Packaging

To create the package execute:

```bash
python3 setup.py bdist_wheel
```

The output of this command is the file `dist/santoku-*.whl`.

This file can be uploaded to S3 and included in the list of Python library path for certain job. Several libraries can be provided as dependencies using a comma-separated list.

## Installing the wheel package

The wheel can be installed with the following command:

```bash
pip install --upgrade --force-reinstall dist/santoku-0.1-py3-none-any.whl
```

`--upgrade --force-reinstall` flags are used to force the reinstallation of the package when it's installed already.

## Usage

We can use the package by using the following command:

```python
from santoku.aws import S3

s3_handler = S3()

# do something
```
