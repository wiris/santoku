from os import path
from setuptools import setup, find_packages
from pip._internal.req import parse_requirements

# Read the contents of the README file.
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, "README.md"), encoding="utf-8") as f:
    long_description = f.read()


def load_requirements(fname):
    reqs = parse_requirements(fname, session="test")
    return [str(ir.requirement) for ir in reqs]


setup(
    name="santoku",
    version="201005.14",
    description="Custom Python wrapper around many third party APIs, including AWS, BigQuery, Slack and Salesforce.",
    packages=find_packages(),
    install_requires=load_requirements("requirements.txt"),
    url="https://github.com/wiris/santoku",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Framework :: Pytest",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "Programming Language :: Python :: 3.8",
    ],
    python_requires="~=3.8",
    long_description=long_description,
    long_description_content_type="text/markdown",
)

# TODO: update this when doc is set up
# "Topic :: Documentation :: Sphinx"
