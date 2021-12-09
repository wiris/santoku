import numpy as np
import pandas as pd
import pytest
from santoku.utils.url_handler import InvalidURLError, URLHandler


@pytest.mark.parametrize(
    argnames=("input_url", "num_subdomains", "expected_result"),
    argvalues=[
        ("https://sub2.sub1.example.com/path?query#fragment", 0, "example.com"),
        ("https://sub2.sub1.example.com", 1, "sub1.example.com"),
        ("https://sub2.sub1.example.com", 2, "sub2.sub1.example.com"),
        ("https://sub2.sub1.example.com", 3, "sub2.sub1.example.com"),
        ("https://example.com", 1, "example.com"),
        ("https://example.co.uk", 0, "example.co.uk"),
        ("https://user@example.co.uk:8000", 0, "example.co.uk"),
        # Note that com.uk isn't a valid tld (but it is a valid url), so it is expected that the
        # funcition would consider 'example' as subdomain, 'com' as domain, and 'uk' as suffix
        ("https://example.com.uk", 0, "com.uk"),
        ("www.example.com", 0, "example.com"),
    ],
    scope="function",
)
def test_get_partial_domain_does_not_raise_exception_when_parameter_is_true_for_valid_url(
    input_url,
    num_subdomains,
    expected_result,
):
    test_partial_domain_raising_exception_for_invalid_url = URLHandler.get_partial_domain(
        url=input_url, num_subdomains=num_subdomains, raise_exception_if_invalid_url=True
    )
    assert test_partial_domain_raising_exception_for_invalid_url == expected_result


@pytest.mark.parametrize(
    argnames=("input_url", "num_subdomains"),
    argvalues=[
        # Note that this url is invalid because it doesn't contain suffix, so 'localhost' will be
        # be considered as subdomain, and 'example' as domain
        ("https://localhost.example", 0),
        ("https://sub1.localhost.example", 1),
        ("https://sub1.localhost.example", 2),
        ("localhost", 0),
        ("https://125.0.0.0", 1),
        ("com", 0),
        ("*", 0),
        ("//", 0),
        ("", 0),
        ("https:///integration/ckeditor", 0),
    ],
    scope="function",
)
def test_get_partial_domain_raises_exception_when_parameter_is_true_for_invalid_url(
    input_url,
    num_subdomains,
):
    with pytest.raises(InvalidURLError):
        URLHandler.get_partial_domain(
            url=input_url, num_subdomains=num_subdomains, raise_exception_if_invalid_url=True
        )


@pytest.mark.parametrize(
    argnames=("input_url", "num_subdomains", "expected_result"),
    argvalues=[
        ("https://sub2.sub1.example.com/path?query#fragment", 0, "example.com"),
        ("https://sub2.sub1.example.com", 1, "sub1.example.com"),
        ("https://sub2.sub1.example.com", 2, "sub2.sub1.example.com"),
        ("https://sub2.sub1.example.com", 3, "sub2.sub1.example.com"),
        ("https://example.com", 1, "example.com"),
        ("https://example.co.uk", 0, "example.co.uk"),
        ("https://user@example.co.uk:8000", 0, "example.co.uk"),
        # Notice that com.uk isn't a valid tld (but it is a valid url), so it is expected that the
        # funcition would consider 'example' as subdomain, 'com' as domain, and 'uk' as suffix
        ("https://example.com.uk", 0, "com.uk"),
        ("www.example.com", 0, "example.com"),
        # Notice that this url is invalid because it doesn't contain suffix, so 'localhost' will be
        # be considered as subdomain, and 'example' as domain
        ("https://localhost.example", 0, "example"),
        ("https://sub1.localhost.example", 1, "localhost.example"),
        ("https://sub1.localhost.example", 2, "sub1.localhost.example"),
        ("localhost", 0, "localhost"),
        ("https://125.0.0.0", 1, "125.0.0.0"),
        ("com", 0, "com"),
        ("*", 0, "*"),
        ("//", 0, "//"),
        ("", 0, ""),
        ("https:///integration/ckeditor", 0, ""),
        ("https:///integration/ckeditor", 1, ""),
    ],
    scope="function",
)
def test_get_partial_domain_does_not_raise_exception_when_parameter_is_false_for_valid_or_invalid_url(
    input_url, num_subdomains, expected_result
):
    test_partial_domain_not_raising_exception_for_invalid_url = URLHandler.get_partial_domain(
        url=input_url, num_subdomains=num_subdomains, raise_exception_if_invalid_url=False
    )
    assert test_partial_domain_not_raising_exception_for_invalid_url == expected_result


@pytest.mark.parametrize(
    argnames=("input_url", "expected_result"),
    argvalues=[
        (
            "https://sub2.sub1.example.com/path?query#fragment",
            "sub2.sub1.example.com",
        ),
        ("https://sub1.example.com", "sub1.example.com"),
        ("https://example.com", "example.com"),
        ("https://example.co.uk", "example.co.uk"),
        ("https://user@example.co.uk:8000", "example.co.uk"),
        ("https://example.com.uk", "example.com.uk"),
        ("www.example.com", "www.example.com"),
    ],
)
def test_get_fully_qualified_domain_does_not_raise_exception_when_parameter_is_true_for_valid_url(
    input_url, expected_result
):
    test_fully_qualified_domain_raising_exception_for_invalid_url = (
        URLHandler.get_fully_qualified_domain(url=input_url, raise_exception_if_invalid_url=True)
    )
    assert test_fully_qualified_domain_raising_exception_for_invalid_url == expected_result


@pytest.mark.parametrize(
    argnames=("input_url"),
    argvalues=[
        ("https://localhost.example"),
        ("localhost"),
        ("https://125.0.0.0"),
        ("com"),
        ("*"),
        ("//"),
        (""),
        ("https:///js"),
        ("https:///integration/"),
        ("https:///integration/ckeditor"),
    ],
)
def test_get_fully_qualified_domain_raises_exception_when_parameter_is_true_for_invalid_url(
    input_url,
):
    with pytest.raises(InvalidURLError):
        URLHandler.get_fully_qualified_domain(url=input_url, raise_exception_if_invalid_url=True)


@pytest.mark.parametrize(
    argnames=("input_url", "expected_result"),
    argvalues=[
        (
            "https://sub2.sub1.example.com/path?query#fragment",
            "sub2.sub1.example.com",
        ),
        ("https://sub1.example.com", "sub1.example.com"),
        ("https://example.com", "example.com"),
        ("https://example.co.uk", "example.co.uk"),
        ("https://user@example.co.uk:8000", "example.co.uk"),
        ("https://example.com.uk", "example.com.uk"),
        ("www.example.com", "www.example.com"),
        ("https://localhost.example", "localhost.example"),
        ("localhost", "localhost"),
        ("https://125.0.0.0", "125.0.0.0"),
        ("com", "com"),
        ("*", "*"),
        ("//", "//"),
        ("", ""),
        ("https:///integration/ckeditor", ""),
        ("https:///js/", ""),
        ("https:///integration/", ""),
    ],
)
def test_get_fully_qualified_domain_does_not_raise_exception_when_parameter_is_false_for_valid_or_invalid_url(
    input_url, expected_result
):
    test_fully_qualified_domain_not_raising_exception_for_invalid_url = (
        URLHandler.get_fully_qualified_domain(url=input_url, raise_exception_if_invalid_url=False)
    )
    assert test_fully_qualified_domain_not_raising_exception_for_invalid_url == expected_result


@pytest.mark.parametrize(
    argnames=("input_url", "expected_result"),
    argvalues=[
        ("https://sub1.example.com/path?query#fragment", False),
        ("https://125.0.0.0", True),
        ("https://277.0.0.0", False),
        ("125.0.0.0:8000", True),
        ("user@125.0.0.0:8000", True),
        ("125.0.0.0.0", False),
        ("1", False),
        ("0", False),
        ("", False),
        ("https:///integration/ckeditor", False),
    ],
    scope="function",
)
def test_contains_ip_evaluates_valid_and_invalid_url_correctly(input_url, expected_result):
    test_containing_ip_evaluation = URLHandler.contains_ip(url=input_url)
    assert test_containing_ip_evaluation == expected_result


@pytest.mark.parametrize(
    argnames=("input_url", "expected_result"),
    argvalues=[
        (
            "http://sub2.sub1.example.com?query#fragment",
            ["example.com", "sub1.example.com", "sub2.sub1.example.com"],
        ),
        ("https://sub1.example.com/path?query#fragment", ["example.com", "sub1.example.com"]),
        ("https://example.com", ["example.com"]),
        ("https://example.co.uk", ["example.co.uk"]),
        ("https://user@example.co.uk:8000", ["example.co.uk"]),
        ("https://example.com.uk", ["com.uk", "example.com.uk"]),
        ("www.example.com", ["example.com", "www.example.com"]),
    ],
    scope="function",
)
def test_explode_domain_does_not_raise_exception_when_parameter_is_true_for_valid_url(
    input_url, expected_result
):
    test_exploded_domains_raising_exception_for_invalid_url = URLHandler.explode_domain(
        url=input_url, raise_exception_if_invalid_url=True
    )
    assert test_exploded_domains_raising_exception_for_invalid_url == expected_result


@pytest.mark.parametrize(
    argnames=("input_url"),
    argvalues=[
        ("https://localhost.example"),
        ("localhost"),
        ("125.0.0.0"),
        ("com"),
        ("*"),
        ("//"),
        (""),
        ("https:///js"),
        ("https:///integration/ckeditor"),
    ],
    scope="function",
)
def test_explode_domain_raises_exception_when_parameter_is_true_for_invalid_url(input_url):
    with pytest.raises(InvalidURLError):
        URLHandler.explode_domain(url=input_url, raise_exception_if_invalid_url=True)


@pytest.mark.parametrize(
    argnames=("input_url", "expected_result"),
    argvalues=[
        (
            "http://sub2.sub1.example.com?query#fragment",
            ["example.com", "sub1.example.com", "sub2.sub1.example.com"],
        ),
        (
            "https://sub1.example.com/path?query#fragment",
            ["example.com", "sub1.example.com"],
        ),
        ("https://example.com", ["example.com"]),
        ("https://example.co.uk", ["example.co.uk"]),
        ("https://user@example.co.uk:8000", ["example.co.uk"]),
        ("https://example.com.uk", ["com.uk", "example.com.uk"]),
        (
            "www.example.com",
            ["example.com", "www.example.com"],
        ),
        ("https://localhost.example", ["example", "localhost.example"]),
        ("localhost", ["localhost"]),
        ("125.0.0.0", ["125.0.0.0"]),
        ("com", ["com"]),
        ("*", ["*"]),
        ("//", ["//"]),
        ("", [""]),
        ("https:///js", [""]),
        ("https:///integration/ckeditor", [""]),
    ],
    scope="function",
)
def test_explode_domain_does_not_raise_exception_when_parameter_is_false_for_invalid_url(
    input_url, expected_result
):
    test_exploded_domains_not_raising_exception_for_invalid_url = URLHandler.explode_domain(
        url=input_url, raise_exception_if_invalid_url=False
    )
    assert test_exploded_domains_not_raising_exception_for_invalid_url == expected_result


@pytest.mark.parametrize(
    argnames=("input_url", "expected_path"),
    argvalues=(
        ("https://example.com/path", "/path"),
        ("https://example.com/path/", "/path/"),
        ("https://example.com.uk/demo/", "/demo/"),
        ("https://example.com.uk/demo?query#fragment", "/demo"),
        ("https:///integration/ckeditor/", "/integration/ckeditor/"),
        ("https://example.com/", "/"),
        ("https://example.com", ""),
        ("localhost", ""),
        ("*", ""),
        ("//", ""),
        ("", ""),
    ),
    scope="function",
)
def test_get_path_does_not_raise_exception_when_parameter_is_false_for_valid_and_invalid_url(
    input_url, expected_path
):
    output_path = URLHandler.get_path(url=input_url, raise_exception_if_invalid_url=False)
    assert output_path == expected_path


@pytest.mark.parametrize(
    argnames=("input_url", "expected_path"),
    argvalues=(
        ("https://example.com/path", "/path"),
        ("https://example.com/path/", "/path/"),
        ("https://example.com.uk/demo/", "/demo/"),
        ("https://example.com.uk/demo?query#fragment", "/demo"),
        ("https://example.com/", "/"),
        ("https://example.com", ""),
    ),
    scope="function",
)
def test_get_path_does_not_raise_exception_when_parameter_is_true_for_valid_url(
    input_url, expected_path
):
    output_path = URLHandler.get_path(url=input_url, raise_exception_if_invalid_url=True)
    assert output_path == expected_path


@pytest.mark.parametrize(
    argnames=("input_url"),
    argvalues=(
        ("https:///integration/ckeditor/"),
        ("localhost"),
        ("*"),
        ("//"),
        (""),
    ),
    scope="function",
)
def test_get_path_raises_exception_when_parameter_is_true_for_invalid_url(input_url):
    with pytest.raises(InvalidURLError):
        URLHandler.get_path(url=input_url, raise_exception_if_invalid_url=True)
