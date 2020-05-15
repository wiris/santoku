from setuptools import setup, find_packages
from pip._internal.req import parse_requirements

PACKAGES_FOR_TESTING = ["moto", "pytest"]


def load_requirements(fname):
    reqs = parse_requirements(fname, session="test")
    return [
        str(ir.req)
        for ir in reqs
        if str(ir.req).split("==")[0] not in ["moto", "pytest"]
    ]


setup(
    name="santoku",
    version="0.19",
    author="Didac Fernández, Daniel Martín-Albo and Henry Qiu",
    description="ETL Toolkit for handling AWS, Salesforce and many more things.",
    packages=find_packages(),
    install_requires=load_requirements("requirements.txt"),
)
