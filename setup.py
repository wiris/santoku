from setuptools import setup, find_packages
from pip._internal.req import parse_requirements


def load_requirements(fname):
    reqs = parse_requirements(fname, session="test")
    return [str(ir.requirement) for ir in reqs]


setup(
    name="santoku",
    version="200616.2",
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
)

# TODO: update this when doc is set up
# "Topic :: Documentation :: Sphinx"
