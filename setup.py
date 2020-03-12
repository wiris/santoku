from setuptools import setup, find_packages

setup(
    name="Santoku",
    version="0.7",
    author="Didac Fernández, Daniel Martín-Albo and Henry Qiu",
    description="ETL Toolkit for handling AWS, Salesforce and many more things.",
    packages=find_packages(),
    install_requires=["boto3>=1.12.2"],
)
