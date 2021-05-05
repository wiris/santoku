import os
import sys

import numpy as np
import pandas as pd
import pytest
from santoku.utils.url_handler import InvalidURLError, URLHandler


def get_raw_urls_num_subdomains_and_partial_domain():
    # Each tuple contains: the raw URL, number of subdomains to extract, the expected partial domain
    # that the test must return if `raise_exception_if_invalid_url` is set to `True` (None if an
    # error is expected to be raised), expected partial domain if `raise_exception_if_invalid_url`
    # is set to `False`
    return [
        ("https://sub2.sub1.example.com/path?query#fragment", 0, "example.com", "example.com"),
        ("https://sub2.sub1.example.com", 1, "sub1.example.com", "sub1.example.com"),
        ("https://sub2.sub1.example.com", 2, "sub2.sub1.example.com", "sub2.sub1.example.com"),
        ("https://sub2.sub1.example.com", 3, "sub2.sub1.example.com", "sub2.sub1.example.com"),
        ("https://example.com", 1, "example.com", "example.com"),
        ("https://example.co.uk", 0, "example.co.uk", "example.co.uk"),
        ("https://user@example.co.uk:8000", 0, "example.co.uk", "example.co.uk"),
        # Notice that com.uk isn't a valid tld (but it is a valid url), so it is expected that the
        # funcition would consider 'example' as subdomain, 'com' as domain, and 'uk' as suffix
        ("https://example.com.uk", 0, "com.uk", "com.uk"),
        ("www.example.com", 0, "example.com", "example.com"),
        # Notice that this url is invalid because it doesn't contain suffix, so 'localhost' will be
        # be considered as subdomain, and 'example' as domain
        ("https://localhost.example", 0, None, "example"),
        ("https://sub1.localhost.example", 1, None, "localhost.example"),
        ("https://sub1.localhost.example", 2, None, "sub1.localhost.example"),
        ("localhost", 0, None, "localhost"),
        ("https://125.0.0.0", 1, None, "125.0.0.0"),
        ("com", 0, None, "com"),
        ("*", 0, None, "*"),
        ("//", 0, None, "//"),
        ("", 0, None, ""),
    ]


def get_raw_urls_and_fully_qualified_domain():
    # Each tuple contains: the raw URL, the expected partial domain that the test must return if
    # `raise_exception_if_invalid_url` is set to `True` (None if an error is expected to be
    # raised), and the expected partial domain if `raise_exception_if_invalid_url` is set to `False`
    return [
        (
            "https://sub2.sub1.example.com/path?query#fragment",
            "sub2.sub1.example.com",
            "sub2.sub1.example.com",
        ),
        ("https://sub1.example.com", "sub1.example.com", "sub1.example.com"),
        ("https://example.com", "example.com", "example.com"),
        ("https://example.co.uk", "example.co.uk", "example.co.uk"),
        ("https://user@example.co.uk:8000", "example.co.uk", "example.co.uk"),
        ("https://example.com.uk", "example.com.uk", "example.com.uk"),
        ("www.example.com", "www.example.com", "www.example.com"),
        ("https://localhost.example", None, "localhost.example"),
        ("localhost", None, "localhost"),
        ("https://125.0.0.0", None, "125.0.0.0"),
        ("com", None, "com"),
        ("*", None, "*"),
        ("//", None, "//"),
        ("", None, ""),
    ]


def get_raw_url_and_containing_ip_evaluation():
    # Each tuple contains: the raw URL, whether the URL contains an IP idress or not
    return [
        ("https://sub1.example.com/path?query#fragment", False),
        ("https://125.0.0.0", True),
        ("https://277.0.0.0", False),
        ("125.0.0.0:8000", True),
        ("user@125.0.0.0:8000", True),
        ("125.0.0.0.0", False),
        ("1", False),
        ("0", False),
        ("", False),
    ]


def get_raw_url_and_exploded_domains():
    # Each tuple contains: the raw URL, the list of exploded domains that the test must return if
    # `raise_exception_if_invalid_url` is set to `True` (None if an error is expected to be
    # raised), and the list of exploded domains if `raise_exception_if_invalid_url` is set to `True`
    return [
        (
            "https://sub1.example.com/path?query#fragment",
            ["example.com", "sub1.example.com"],
            ["example.com", "sub1.example.com"],
        ),
        (
            "http://sub2.sub1.example.com?query#fragment",
            ["example.com", "sub1.example.com", "sub2.sub1.example.com"],
            ["example.com", "sub1.example.com", "sub2.sub1.example.com"],
        ),
        ("https://localhost.com", ["localhost.com"], ["localhost.com"]),
        ("https://example.co.uk", ["example.co.uk"], ["example.co.uk"]),
        ("https://user@example.co.uk:8000", ["example.co.uk"], ["example.co.uk"]),
        # Notice that com.uk isn't a valid tld, so it is expected that the funcition would consider
        # 'example' as subdomain, 'com' as domain, and 'uk' as suffix
        ("https://example.com.uk", ["com.uk", "example.com.uk"], ["com.uk", "example.com.uk"]),
        ("www.example.com", ["example.com", "www.example.com"], ["example.com", "www.example.com"]),
        ("localhost", None, ["localhost"]),
        ("125.0.0.0", None, ["125.0.0.0"]),
        ("com", None, ["com"]),
        ("//", None, ["//"]),
        ("", None, [""]),
    ]


@pytest.fixture(params=get_raw_urls_num_subdomains_and_partial_domain())
def raw_urls_num_subdomains_and_partial_domain(request):
    return request.param


@pytest.fixture(params=get_raw_urls_and_fully_qualified_domain())
def raw_urls_and_fully_qualified_domain(request):
    return request.param


@pytest.fixture(params=get_raw_url_and_containing_ip_evaluation())
def raw_url_and_containing_ip_evaluation(request):
    return request.param


@pytest.fixture(params=get_raw_url_and_exploded_domains())
def raw_url_and_exploded_domains(request):
    return request.param


@pytest.fixture(scope="function")
def raw_dataframe_and_exploded_dataframe():
    # Each element in the list consists of: the raw dataframe, exploded dataframe if
    # `raise_exception_if_invalid_url` is set to `True`, and the exploded dataframe if
    # `raise_exception_if_invalid_url` is set to `False`
    return [
        pd.DataFrame(
            {
                "referrer": [
                    "https://sub1.example.com/path?query#fragment",
                    "http://sub2.sub1.example.com?query#fragment",
                    "https://localhost.com",
                    "https://example.co.uk",
                    "https://example.com.uk",
                    "www.example.com",
                    "localhost",
                    "125.0.0.0",
                    "com",
                    "//",
                    "",
                ]
            }
        ),
        pd.DataFrame(
            {
                "domain": [
                    "example.com",
                    "sub1.example.com",
                    "example.com",
                    "sub1.example.com",
                    "sub2.sub1.example.com",
                    "localhost.com",
                    "example.co.uk",
                    "com.uk",
                    "example.com.uk",
                    "example.com",
                    "www.example.com",
                ]
            }
        ),
        pd.DataFrame(
            {
                "domain": [
                    "example.com",
                    "sub1.example.com",
                    "example.com",
                    "sub1.example.com",
                    "sub2.sub1.example.com",
                    "localhost.com",
                    "example.co.uk",
                    "com.uk",
                    "example.com.uk",
                    "example.com",
                    "www.example.com",
                    "localhost",
                    "125.0.0.0",
                    "com",
                    "//",
                    "",
                ]
            }
        ),
    ]


def test_get_partial_domain(raw_urls_num_subdomains_and_partial_domain):
    (
        input_url,
        num_subdomains,
        reference_partial_domain_raising_exception_for_invalid_url,
        reference_partial_domain_not_raising_exception_for_invalid_url,
    ) = raw_urls_num_subdomains_and_partial_domain

    # Test raising exception if URL is invalid
    if reference_partial_domain_raising_exception_for_invalid_url is None:
        with pytest.raises(InvalidURLError):
            URLHandler.get_partial_domain(
                url=input_url, num_subdomains=num_subdomains, raise_exception_if_invalid_url=True
            )
    else:
        test_partial_domain_raising_exception_for_invalid_url = URLHandler.get_partial_domain(
            url=input_url, num_subdomains=num_subdomains, raise_exception_if_invalid_url=True
        )
        assert (
            test_partial_domain_raising_exception_for_invalid_url
            == reference_partial_domain_raising_exception_for_invalid_url
        )

    # Test not raising exception if URL is invalid
    test_partial_domain_not_raising_exception_for_invalid_url = URLHandler.get_partial_domain(
        url=input_url, num_subdomains=num_subdomains, raise_exception_if_invalid_url=False
    )
    assert (
        test_partial_domain_not_raising_exception_for_invalid_url
        == reference_partial_domain_not_raising_exception_for_invalid_url
    )


def test_get_fully_qualified_domain(raw_urls_and_fully_qualified_domain):
    (
        input_url,
        reference_fully_qualified_domain_raising_exception_for_invalid_url,
        reference_fully_qualified_domain_not_raising_exception_for_invalid_url,
    ) = raw_urls_and_fully_qualified_domain

    # Test raising exception if URL is invalid
    if reference_fully_qualified_domain_raising_exception_for_invalid_url is None:
        with pytest.raises(InvalidURLError):
            URLHandler.get_fully_qualified_domain(
                url=input_url, raise_exception_if_invalid_url=True
            )
    else:
        test_fully_qualified_domain_raising_exception_for_invalid_url = (
            URLHandler.get_fully_qualified_domain(
                url=input_url, raise_exception_if_invalid_url=True
            )
        )
        assert (
            test_fully_qualified_domain_raising_exception_for_invalid_url
            == reference_fully_qualified_domain_raising_exception_for_invalid_url
        )

    # Test not raising exception if URL is invalid
    test_fully_qualified_domain_not_raising_exception_for_invalid_url = (
        URLHandler.get_fully_qualified_domain(url=input_url, raise_exception_if_invalid_url=False)
    )
    assert (
        test_fully_qualified_domain_not_raising_exception_for_invalid_url
        == reference_fully_qualified_domain_not_raising_exception_for_invalid_url
    )


def test_contains_ip(raw_url_and_containing_ip_evaluation):
    input_url, reference_containing_ip_evaluation = raw_url_and_containing_ip_evaluation
    test_containing_ip_evaluation = URLHandler.contains_ip(url=input_url)
    assert test_containing_ip_evaluation == reference_containing_ip_evaluation


def test_explode_domain(raw_url_and_exploded_domains):
    (
        input_url,
        reference_exploded_domains_raising_exception_for_invalid_url,
        reference_exploded_domains_not_raising_exception_for_invalid_url,
    ) = raw_url_and_exploded_domains

    # Test raising exception if URL is invalid
    if reference_exploded_domains_raising_exception_for_invalid_url is None:
        with pytest.raises(InvalidURLError):
            URLHandler.explode_domain(url=input_url, raise_exception_if_invalid_url=True)
    else:
        test_exploded_domains_raising_exception_for_invalid_url = URLHandler.explode_domain(
            url=input_url, raise_exception_if_invalid_url=True
        )
        assert (
            test_exploded_domains_raising_exception_for_invalid_url
            == reference_exploded_domains_raising_exception_for_invalid_url
        )

    # Test returning invalid urls
    test_exploded_domains_not_raising_exception_for_invalid_url = URLHandler.explode_domain(
        url=input_url, raise_exception_if_invalid_url=False
    )
    assert (
        test_exploded_domains_not_raising_exception_for_invalid_url
        == reference_exploded_domains_not_raising_exception_for_invalid_url
    )


def test_explode_domains(raw_dataframe_and_exploded_dataframe):
    (
        input_df,
        reference_df_raising_exception_for_invalid_url,
        reference_df_not_raising_exception_for_invalid_url,
    ) = raw_dataframe_and_exploded_dataframe

    # Test raising exception if URL is invalid
    test_df_raising_exception_for_invalid_url = URLHandler.explode_domains(
        df=input_df, raise_exception_if_invalid_url=True
    )
    assert test_df_raising_exception_for_invalid_url.equals(
        reference_df_raising_exception_for_invalid_url
    )

    # Test returning invalid urls
    test_df_not_raising_exception_for_invalid_url = URLHandler.explode_domains(
        df=input_df, raise_exception_if_invalid_url=False
    )
    assert test_df_not_raising_exception_for_invalid_url.equals(
        reference_df_not_raising_exception_for_invalid_url
    )

    # Test referrer column is removed
    assert "referrer" not in test_df_raising_exception_for_invalid_url.columns
    assert "referrer" not in test_df_not_raising_exception_for_invalid_url.columns

    # Test error is raised when referrer column contains nan values
    with pytest.raises(ValueError):
        URLHandler.explode_domains(df=pd.DataFrame({"referrer": [np.nan]}))
