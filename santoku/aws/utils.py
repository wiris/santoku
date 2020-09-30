import boto3

from abc import ABC, abstractmethod
from typing import Any, Dict, Generator

from botocore import client


"""
Class to manage generic methods in AWS.

This class contains methods with generic syntax, the same method works for more than on service.
"""


def paginate(
    client: client, method: str, **kwargs: Dict[str, Any]
) -> Generator[Dict[str, Any], None, None]:
    """
    Iterates over the pages of an API operation results.

    Paginators act as an abstraction over the process of iterating over an entire result set of
    a truncated API operation. Yields an iterable with the response obtained from applying
    `method`.

    Parameters
    ----------
    method : str
        Name of the API operation request.
    kwargs : Dict[str, Any]
        Additional arguments for the specified method.

    Yields
    ------
    Generator[Dict[str, Any], None, None]
        Responses dictionaries of the `method`.

    Notes
    -----
    More information on the use of AWS paginators: [1].

    References
    ----------
    [1] :
    https://boto3.amazonaws.com/v1/documentation/api/latest/guide/paginators.html

    """
    paginator = client.get_paginator(operation_name=method)
    for page in paginator.paginate(**kwargs):
        yield page
