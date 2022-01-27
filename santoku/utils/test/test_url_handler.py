from urllib.parse import ParseResult

import pytest
from santoku.utils.url_handler import URLHandler


@pytest.mark.parametrize(
    argnames=("input_subdomain", "expected_subdomain_list"),
    argvalues=(
        ("sub1.sub2", ["sub1", "sub2"]),
        ("SUB1.SUB2", ["sub1", "sub2"]),
        ("sub1", ["sub1"]),
        ("sub1.", ["sub1", ""]),
        ("sub1..", ["sub1", "", ""]),
        ("", []),
        (None, []),
    ),
    scope="function",
)
def test_string_subdomain_is_processed_as_expected(input_subdomain, expected_subdomain_list):
    output_subdomain_list = URLHandler.process_subdomain(subdomain=input_subdomain)
    assert output_subdomain_list == expected_subdomain_list


@pytest.mark.parametrize(
    argnames=("input_url", "expected_components"),
    argvalues=[
        (
            "https://sub2.sub1.example.com/path?query#fragment",
            ("https", ["sub2", "sub1"], "example", "com", "path"),
        ),
        (
            "https://sub1.example.com/PATH/",
            ("https", ["sub1"], "example", "com", "PATH"),
        ),
        ("http://sub2.sub1.example.es", ("http", ["sub2", "sub1"], "example", "es", None)),
        ("https://sub1.example.co.uk", ("https", ["sub1"], "example", "co.uk", None)),
        ("https://example.com", ("https", [], "example", "com", None)),
        # xn-- is prefixes an IDNA (Internationalizing Domain Names in Applications) encoding
        # (reference: https://en.wikipedia.org/wiki/Internationalized_domain_name)
        ("https://example.XN--1QQW23A", ("https", [], "example", "xn--1qqw23a", None)),
        ("https://user@example.co.uk:8000", ("https", [], "example", "co.uk", None)),
        # Note that com.uk isn't a valid TLD (but it is a valid URL), so it is expected that the
        # function would consider 'example' as subdomain, 'com' as domain, and 'uk' as suffix
        ("https://example.com.uk", ("https", ["example"], "com", "uk", None)),
        ("www.example.com", (None, ["www"], "example", "com", None)),
        ("https://localhost.example", ("https", ["localhost"], "example", None, None)),
        ("https://sub1.localhost.example", ("https", ["sub1", "localhost"], "example", None, None)),
        (
            "https://sub1..localhost.example",
            ("https", ["sub1", "", "localhost"], "example", None, None),
        ),
        ("localhost", (None, [], "localhost", None, None)),
        ("https://125.0.0.0", ("https", [], "125.0.0.0", None, None)),
        ("com", (None, [], None, "com", None)),
        ("*", (None, [], "*", None, None)),
        ("//", (None, [], None, None, None)),
        ("", (None, [], None, None, None)),
        ("https:///integration/ckeditor", ("https", [], None, None, "integration/ckeditor")),
        ("/quizzesproxy/quizzes/service", (None, [], None, None, "quizzesproxy/quizzes/service")),
    ],
    scope="function",
)
def test_url_is_split_into_components_as_expected(input_url, expected_components):
    output_components = URLHandler.split_url_into_components(url=input_url)
    assert output_components == expected_components


@pytest.mark.parametrize(
    argnames=("input_url", "expected_result"),
    argvalues=[
        ("https://sub2.sub1.example.com/path?query#fragment", True),
        ("https://sub2.sub1.example.com", True),
        ("https://example.com", True),
        ("https://example.co.uk", True),
        ("https://user@example.co.uk:8000", True),
        # Note that com.uk isn't a valid TLD (but it is a usable URL), so it is expected that the
        # funcition would consider 'example' as subdomain, 'com' as domain, and 'uk' as suffix
        ("https://example.com.uk", True),
        ("www.example.com", True),
        # Note that this URL is not usable because it doesn't contain suffix, so 'localhost' will be
        # be considered as subdomain, and 'example' as domain
        ("https://localhost.example", False),
        ("https://sub1.localhost.example", False),
        ("localhost", False),
        ("https://125.0.0.0", False),
        ("com", False),
        ("*", False),
        ("//", False),
        ("", False),
        ("https:///integration/ckeditor", False),
        ("/quizzesproxy/quizzes/service", False),
    ],
    scope="function",
)
def test_url_is_validated_as_expected(input_url, expected_result):
    output_result = URLHandler(url=input_url).url_is_usable()
    assert output_result == expected_result


@pytest.mark.parametrize(
    argnames=("input_component", "expected_filled_path"),
    argvalues=[
        ("here", "/here"),
        ("/here", "/here"),
        ("/here/", "/here/"),
        ("/", "/"),
        ("//", "//"),
        ("", None),
        (None, None),
    ],
)
def test_component_is_prepended_with_a_slash_correctly(input_component, expected_filled_path):
    output_filled_path = URLHandler.prepend_slash(component=input_component)
    assert output_filled_path == expected_filled_path


@pytest.mark.parametrize(
    argnames=("input_component", "expected_cleaned_path"),
    argvalues=[
        ("example.com", "example.com"),
        ("/example.com/", "example.com"),
        ("//example.com", "example.com"),
        ("here", "here"),
        ("/here/", "here"),
        ("//here/", "here"),
        ("/Here", "here"),
        ("/HERE", "here"),
        ("/", None),
        ("//", None),
        ("", None),
        (None, None),
    ],
)
def test_component_is_cleaned_properly_when_lowercase_is_set_to_true(
    input_component, expected_cleaned_path
):
    output_cleaned_path = URLHandler.clean_component(component=input_component, lowercase=True)
    assert output_cleaned_path == expected_cleaned_path


@pytest.mark.parametrize(
    argnames=("input_component", "expected_cleaned_path"),
    argvalues=[
        ("example.com", "example.com"),
        ("/example.com/", "example.com"),
        ("//example.com", "example.com"),
        ("here", "here"),
        ("/here/", "here"),
        ("//here/", "here"),
        ("/Here/", "Here"),
        ("/HERE/", "HERE"),
        ("/", None),
        ("//", None),
        ("", None),
        (None, None),
    ],
)
def test_component_is_cleaned_properly_when_lowercase_is_set_to_false(
    input_component, expected_cleaned_path
):
    output_cleaned_path = URLHandler.clean_component(component=input_component)
    assert output_cleaned_path == expected_cleaned_path


@pytest.mark.parametrize(
    argnames=("input_parsed_url", "expected_path"),
    argvalues=(
        (
            ParseResult(
                scheme="https",
                netloc="sub1.domain.com",
                path="/demo",
                params="",
                query="",
                fragment="",
            ),
            "demo",
        ),
        (
            ParseResult(
                scheme="https",
                netloc="sub1.domain.com",
                path="/demo/test",
                params="",
                query="",
                fragment="",
            ),
            "demo/test",
        ),
        (
            ParseResult(
                scheme="",
                netloc="domain.com",
                path="/demo",
                params="",
                query="courses=1",
                fragment="",
            ),
            "demo",
        ),
        (
            ParseResult(
                scheme="",
                netloc="domain.com",
                path="/demo/",
                params="",
                query="",
                fragment="",
            ),
            "demo",
        ),
        (
            ParseResult(
                scheme="",
                netloc="domain.com",
                path="/demo/test/",
                params="",
                query="",
                fragment="",
            ),
            "demo/test",
        ),
        (
            ParseResult(
                scheme="",
                netloc="domain.com",
                path="/DEmo/teST/",
                params="",
                query="",
                fragment="",
            ),
            "DEmo/teST",
        ),
        (
            ParseResult(
                scheme="https",
                netloc="",
                path="/demo",
                params="",
                query="courses=1",
                fragment="",
            ),
            "demo",
        ),
        (
            ParseResult(
                scheme="https",
                netloc="125.0.0.0",
                path="/demo",
                params="",
                query="",
                fragment="",
            ),
            "demo",
        ),
        (
            ParseResult(
                scheme="https",
                netloc="domain.com",
                path="",
                params="",
                query="courses=1",
                fragment="",
            ),
            None,
        ),
        (
            ParseResult(scheme="", netloc="", path="domain", params="", query="", fragment=""),
            None,
        ),
        (
            ParseResult(
                scheme="",
                netloc="",
                path="/quizzesproxy/quizzes/service",
                params="",
                query="",
                fragment="",
            ),
            "quizzesproxy/quizzes/service",
        ),
    ),
    scope="function",
)
def test_path_is_processed_as_expected(input_parsed_url, expected_path):
    output_path = URLHandler.process_path(parsed_url=input_parsed_url)
    assert output_path == expected_path


@pytest.mark.parametrize(
    argnames=("input_url", "num_subdomains", "expected_subdomains_list"),
    argvalues=(
        ("https://sub2.sub1.example.com/path?query#fragment", 1, ["sub1"]),
        ("https://sub2.sub1.example.com/path?query#fragment", 2, ["sub2", "sub1"]),
        ("https://sub2.sub1.example.com/path?query#fragment", 3, ["sub2", "sub1"]),
        ("https://SUB2.sub1.EXAMPLE.com/path?query#fragment", 3, ["sub2", "sub1"]),
        ("www.example.com", 1, ["www"]),
        ("www.example.com", 0, []),
        # Note that com.uk isn't a valid TLD (but it is a usable URL), so it is expected that the
        # funcition would consider 'example' as subdomain, 'com' as domain, and 'uk' as suffix
        ("https://example.com.uk", 1, ["example"]),
        ("https://example.com", 1, []),
        ("https://user@example.co.uk:8000", 1, []),
        ("125.0.0.0", 2, []),
        # Note that 125.0.0.0.0 isn't a valid IP, so the last 0 will be treated as base domain, and
        # the remaining part as subdomain
        ("125.0.0.0.0", 4, ["125", "0", "0", "0"]),
        ("", 1, []),
    ),
    scope="function",
)
def test_n_subdomains_are_gotten_correctly(input_url, num_subdomains, expected_subdomains_list):
    output_subdomains_list = URLHandler(url=input_url).get_n_subdomains(
        num_subdomains=num_subdomains
    )
    assert output_subdomains_list == expected_subdomains_list


@pytest.mark.parametrize(
    argnames=("input_url", "num_subdomains"),
    argvalues=(("https://sub2.sub1.example.com/path?query#fragment", -1),),
    scope="function",
)
def test_exception_is_raised_for_num_subdomain_smaller_than_0(input_url, num_subdomains):
    with pytest.raises(ValueError):
        URLHandler(url=input_url).get_n_subdomains(num_subdomains=num_subdomains)


@pytest.mark.parametrize(
    argnames=("input_base_domain", "input_suffix", "expected_base_domain_with_suffix"),
    argvalues=(
        ("domain", "es", "domain.es"),
        ("domain", "co.uk", "domain.co.uk"),
        ("DOMAIN", "co.UK", "domain.co.uk"),
        ("*", "es", "*.es"),
        ("/", None, None),
        (None, "/", None),
        ("domain", None, "domain"),
        ("125.0.0.0", None, "125.0.0.0"),
        ("*", None, "*"),
        (None, "es", "es"),
        (None, None, None),
    ),
    scope="function",
)
def test_base_domain_is_joined_with_suffix_properly(
    input_base_domain, input_suffix, expected_base_domain_with_suffix
):
    output_base_domain_with_suffix = URLHandler.join_base_domain_with_suffix(
        base_domain=input_base_domain, suffix=input_suffix
    )
    assert output_base_domain_with_suffix == expected_base_domain_with_suffix


@pytest.mark.parametrize(
    argnames=("input_domain", "input_path", "expected_joined_domain_and_path"),
    argvalues=[
        ("example.com", "here/there", "example.com/here/there"),
        ("example.com/", "here/there/", "example.com/here/there"),
        ("example.com", "here", "example.com/here"),
        ("example.com", "/here", "example.com/here"),
        ("EXAMPLE.com", "/HERE", "example.com/HERE"),
        ("example.com", "/", "example.com"),
        ("example.com", None, "example.com"),
        ("*", "here", "*/here"),
        (None, "here", "/here"),
        (None, "/here", "/here"),
        ("", "here", "/here"),
        ("", "/here", "/here"),
        ("//", "/here", "/here"),
        ("", "/", None),
        ("", "", None),
        ("", None, None),
        (None, "", None),
        (None, None, None),
    ],
)
def test_domain_and_path_are_joined_properly(
    input_domain, input_path, expected_joined_domain_and_path
):
    output_joined_domain_and_path = URLHandler.join_domain_with_path(
        domain=input_domain, path=input_path
    )

    assert output_joined_domain_and_path == expected_joined_domain_and_path


@pytest.mark.parametrize(
    argnames=("input_domains", "input_paths", "expected_joined_domain_and_path_list"),
    argvalues=(
        (["example.com"], ["here"], ["example.com", "example.com/here"]),
        (["example.com"], ["/here"], ["example.com", "example.com/here"]),
        (["EXAMPLE.com"], ["/HEre"], ["example.com", "example.com/HEre"]),
        (["example.com", "example.com"], ["/here", "/here"], ["example.com", "example.com/here"]),
        (["example.com"], ["/"], ["example.com"]),
        (
            ["example.com", "this.example.com"],
            ["here"],
            ["example.com", "example.com/here", "this.example.com", "this.example.com/here"],
        ),
        (
            ["example.com", "this.example.com"],
            ["here", "here/there"],
            [
                "example.com",
                "example.com/here",
                "example.com/here/there",
                "this.example.com",
                "this.example.com/here",
                "this.example.com/here/there",
            ],
        ),
        (["example.com", "this.example.com"], [], ["example.com", "this.example.com"]),
        ([], ["here", "there"], ["/here", "/there"]),
        (["example.com"], [None], ["example.com"]),
        (["*"], ["here"], ["*", "*/here"]),
        ([None], ["here"], ["/here"]),
        ([None], ["/here"], ["/here"]),
        ([""], ["here"], ["/here"]),
        ([""], ["/here"], ["/here"]),
        (["//"], ["/here"], ["/here"]),
        ([""], ["/"], []),
        ([""], [""], []),
        ([None], [""], []),
        ([""], [None], []),
        ([None], [None], []),
    ),
    scope="function",
)
def test_domains_and_paths_are_joined_properly(
    input_domains, input_paths, expected_joined_domain_and_path_list
):
    output_joined_domain_and_path_list = URLHandler.join_domains_with_paths(
        domains=input_domains, paths=input_paths
    )

    assert sorted(output_joined_domain_and_path_list) == sorted(
        expected_joined_domain_and_path_list
    )


@pytest.mark.parametrize(
    argnames=("input_subdomains", "input_base_domain_with_suffix", "expected_result"),
    argvalues=(
        (["sub2", "sub1"], "domain.es", "sub2.sub1.domain.es"),
        (["sub1"], "domain.es", "sub1.domain.es"),
        (["SUB1"], "domaIN.ES", "sub1.domain.es"),
        ([], "domain.es", "domain.es"),
        (["sub2", "sub1"], "*", "sub2.sub1.*"),
        ([], "domain", "domain"),
        ([], "*", "*"),
        ([], "es", "es"),
        (["sub2", "sub1"], None, "sub2.sub1"),
        ([], None, None),
    ),
    scope="function",
)
def test_subdomains_are_joined_with_base_domain_and_suffix_properly(
    input_subdomains, input_base_domain_with_suffix, expected_result
):
    output_result = URLHandler.join_subdomains_with_base_domain_and_suffix(
        subdomains=input_subdomains, base_domain_with_suffix=input_base_domain_with_suffix
    )
    assert expected_result == output_result


@pytest.mark.parametrize(
    argnames=("input_url", "num_subdomains", "expected_partial_domain"),
    argvalues=[
        ("https://sub2.sub1.example.com/path?query#fragment", 0, "example.com"),
        ("https://sub2.sub1.example.com", 1, "sub1.example.com"),
        ("https://sub2.sub1.example.com", 2, "sub2.sub1.example.com"),
        ("https://sub2.sub1.example.com", 3, "sub2.sub1.example.com"),
        ("https://sub2.SUB1.example.cOm", 3, "sub2.sub1.example.com"),
        ("https://sub2.sub1.example.com", None, "sub2.sub1.example.com"),
        ("https://example.com", 1, "example.com"),
        ("https://example.com", None, "example.com"),
        ("https://example.co.uk", 0, "example.co.uk"),
        ("https://user@example.co.uk:8000", 0, "example.co.uk"),
        # Note that com.uk isn't a valid TLD (but it is a usable URL), so it is expected that the
        # function would consider 'example' as subdomain, 'com' as domain, and 'uk' as suffix
        ("https://example.com.uk", 0, "com.uk"),
        ("www.example.com", 0, "example.com"),
        # Notice that this URL is not usable because it doesn't contain suffix, so 'localhost' will be
        # be considered as subdomain, and 'example' as domain
        ("https://localhost.example", 0, "example"),
        ("https://sub1.localhost.example", 1, "localhost.example"),
        ("https://sub1.localhost.example", 2, "sub1.localhost.example"),
        ("localhost", 0, "localhost"),
        ("localhost", None, "localhost"),
        ("localhost.example", None, "localhost.example"),
        ("https://125.0.0.0", 1, "125.0.0.0"),
        ("com", 0, "com"),
        ("*", 0, "*"),
        ("//", 0, None),
        ("", 1, None),
        ("https:///integration/ckeditor", 0, None),
        ("https:///integration/ckeditor", 1, None),
        ("https:///integration/ckeditor", None, None),
    ],
    scope="function",
)
def test_partial_domain_is_gotten_correctly(
    input_url,
    num_subdomains,
    expected_partial_domain,
):
    output_partial_domain = URLHandler(url=input_url).get_partial_domain(
        num_subdomains=num_subdomains
    )

    assert output_partial_domain == expected_partial_domain


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
    test_containing_ip_evaluation = URLHandler(url=input_url).contains_ip()
    assert test_containing_ip_evaluation == expected_result


@pytest.mark.parametrize(
    argnames=("input_url", "expected_exploded_domains"),
    argvalues=[
        (
            "http://sub2.sub1.example.com?query#fragment",
            ["example.com", "sub1.example.com", "sub2.sub1.example.com"],
        ),
        ("https://sub1.example.com/path?query#fragment", ["example.com", "sub1.example.com"]),
        ("https://example.com", ["example.com"]),
        ("https://EXAMPLE.com", ["example.com"]),
        ("https://example.co.uk", ["example.co.uk"]),
        ("https://user@example.co.uk:8000", ["example.co.uk"]),
        ("https://example.com.uk", ["com.uk", "example.com.uk"]),
        ("www.example.com", ["example.com", "www.example.com"]),
        ("https://localhost.example", ["example", "localhost.example"]),
        ("localhost", ["localhost"]),
        ("125.0.0.0", ["125.0.0.0"]),
        ("com", ["com"]),
        ("*", ["*"]),
        ("//", []),
        ("", []),
        ("https:///js", []),
        ("https:///integration/ckeditor", []),
    ],
    scope="function",
)
def test_domains_are_exploded_properly(input_url, expected_exploded_domains):
    output_exploded_domains = URLHandler(url=input_url).explode_domain()
    assert output_exploded_domains == expected_exploded_domains


@pytest.mark.parametrize(
    argnames=("input_data", "input_depth", "expected_exploded_paths"),
    argvalues=(
        ("/moodle", 1, ["moodle"]),
        ("/moodle", 2, ["moodle"]),
        ("/moodle", 0, []),
        ("/moodle", -1, []),
        ("/moodle/", 1, ["moodle"]),
        ("/MoodLE/", 1, ["MoodLE"]),
        ("/moodle/this", 1, ["moodle"]),
        ("/moodle/this/", 1, ["moodle"]),
        ("/moodle/this", 2, ["moodle", "moodle/this"]),
        ("/moodle/this/", 2, ["moodle", "moodle/this"]),
        ("/moodle/this", 3, ["moodle", "moodle/this"]),
        ("moodle/this", 1, ["moodle"]),
        ("/moodle/subpath1/subpath2", 2, ["moodle", "moodle/subpath1"]),
        (
            "/moodle/subpath1/subpath2",
            3,
            ["moodle", "moodle/subpath1", "moodle/subpath1/subpath2"],
        ),
        ("/", 1, []),
        ("/", 2, []),
        ("", 1, []),
        ("", 2, []),
    ),
    scope="function",
)
def test_explode_path(input_data, input_depth, expected_exploded_paths):
    output_exploded_paths = URLHandler.explode_path(path=input_data, max_depth=input_depth)
    assert output_exploded_paths == expected_exploded_paths
