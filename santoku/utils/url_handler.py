import enum
import ipaddress
import itertools
from typing import List, Optional, Tuple
from urllib.parse import ParseResult, urlparse

import tldextract


class URLHandler:
    """
    This class provides URL parsing and transformation functionality to different forms.

    A URL is split into different components: `scheme`, `subdomains`, `base_domain`, `suffix` and
    `path`.

    - We use the same definition of scheme as in the standards: what precedes `:`.
    - A subdomain is a domain that is part of a larger domain. Here, for convenience reasons,
    we define as subdomains each component (split on `.`) of the domain, excluding the base_domain
    and suffix.
    - We define as base_domain the part of the domain right before the suffix.
    - We define as suffix the tld component (note that in some cases it is formed by top + second
    level domain, as in 'example.co.uk', where it is 'co.uk').
    - We define as path the part after the '/' after the domain, up until the '?' (which defines the
    start of the query) or '#' character (which defines the start of the fragment).

    Example
    -----
    Given the URL 'https://sub2.sub1.example.com/path?query#fragment':

    - The scheme is 'https'
    - The subdomains are 'sub1' and 'sub2'
    - The base_domain is 'example'
    - The suffix is 'com'
    - The path is 'path'

    Notes
    -----
    - The naming of the components does not follow URL standard specifications, and is slightly
    adapted for convenience reasons.
    - If you provide an invalid URL, you might get unexpected results for some of the methods.
    - When a non-valid URL such as 'fakedomain' is provided, it is considered as `base_domain`.
    - Some components in the URL like 'userinfo' (what goes right before @) will be ignored.

    References
    ----------
    [1] :
    https://datatracker.ietf.org/doc/html/rfc3986

    """

    def __init__(self, url: str) -> None:
        """
        Stores the URL and the different components of this URL.

        Parameters
        ----------
        url : str
            The URL to be handled.

        See also
        --------
        split_url_into_components
            Called to obtain the components of the URL.

        """
        self.url = url
        (
            self.scheme,
            self.subdomains,
            self.base_domain,
            self.suffix,
            self.path,
        ) = self.split_url_into_components(url=self.url)

    @classmethod
    def split_url_into_components(
        cls, url: str
    ) -> Tuple[Optional[str], List[str], Optional[str], Optional[str], Optional[str]]:
        """
        Generates components by separating the URL into different parts and perfom some parsing on
        these parts.

        Parameters
        ----------
        url : str
            The URL to be split.

        Returns
        -------
        Tuple[Optional[str], List[str], Optional[str], Optional[str], Optional[str]]
            Returns the `scheme`, `subdomains`, `base_domain`, `suffix` and `path`. For the
            `scheme`, `base_domain`, `suffix` and `path`, `None` will be returned if not found.
            For the `subdomains`, an empty list will be returned if not found.

        See also
        --------
        process_subdomains
            Called to obtain the subdomains in the desired format.
        process_path
            Called to obtain the path in the desired format.

        Example
        -------
        E.g: https://sub1.sub2.example.co.uk/demo?course=1 is converted into:
        - scheme -> https
        - subdomains -> ["sub1", "sub2"]
        - base_domain -> example
        - suffix -> co.uk
        - path -> /demo?course=1

        """
        scheme = None
        subdomains = []
        domain = None
        suffix = None
        path = None
        if url:
            parsed_url = urlparse(url=url)
            extracted_url = tldextract.extract(url=url)
            subdomains = cls.process_subdomain(subdomain=extracted_url.subdomain)
            path = cls.process_path(parsed_url=parsed_url)
            if parsed_url.scheme:
                scheme = parsed_url.scheme
            if extracted_url.domain:
                domain = extracted_url.domain
            if extracted_url.suffix:
                suffix = extracted_url.suffix

        return scheme, subdomains, domain, suffix, path

    @classmethod
    def process_subdomain(cls, subdomain: str) -> List[str]:
        """
        Processes a subdomain by splitting its components on `.`.

        Parameters
        ----------
        subdomain : str
            The subdomain to be processed.

        Returns
        -------
        List[str]
            The list of split subdomain components. If the subdomain is empty, it returns an empty
            list.

        Examples
        --------
        "sub2.sub1" -> ["sub2", "sub1"]
        "sub2.sub1." -> ["sub2", "sub1", ""]
        "" -> []

        """
        if not subdomain:
            return []

        return subdomain.split(".")

    def url_is_usable(self) -> bool:
        """
        Checks whether the `url` attribute is usable or not. We define as usable a URL that has at
        least a `base_domain` and a `suffix`.

        Returns
        -------
        bool
            True if the `url` attribute is usable, False otherwise.

        Notes
        -----
        A URL that is usable is not necessarily valid (URL specifications state that the only
        mandatory component of a URL is the scheme), and a valid URL is not necessarily usable.

        Examples
        --------
        "www.example.com" -> True
        "example.com" -> True
        "example" -> False
        "com" -> False
        "https://example" -> False

        """
        if not self.base_domain or not self.suffix:
            return False

        return True

    @classmethod
    def process_path(cls, parsed_url: ParseResult) -> Optional[str]:
        """
        Returns the path component from a given parsed url.

        Parameters
        ----------
        parsed_url : ParseResult
            A parsed url resulting from calling the urllib.parse.urlparse method.

        Returns
        -------
        Optional[str]
            The path component of `parsed_url` or `None`. If the parsed url does not contain a
            scheme or a domain, `None` is returned instead.

        """
        # When something like "fakedomain" is passed to urllib.parse.urlparse, "fakedomain" will be
        # parsed as path, which is not desired for us (we) prefer considering "fakedomain" as
        # basedomain
        if not (parsed_url.scheme or parsed_url.netloc):
            return None

        return parsed_url.path or None

    def get_n_subdomains(self, num_subdomains: int) -> List[str]:
        """
        Gets up to `num_subdomains` subdomains from the `subdomains` attribute.

        Parameters
        ----------
        num_subdomains : int
            The number of subdomains to be got. It must be a non-negative integer.

        Returns
        -------
        List[str]
            A list of subdomains up to `num_subdomains`, or an empty list if `num_subdomains` is 0.
            If `num_subdomains` is greater than the actual number of subdomains, just return all
            subdomains.

        Raises
        ------
        ValueError
            If `num_subdomains` is smaller than 0.

        """
        if num_subdomains < 0:
            raise ValueError("`num_subdomains` must be a non-negative integer.")

        if num_subdomains == 0:
            return []

        return self.subdomains[-num_subdomains:]

    @classmethod
    def join_domain_with_path(cls, domains: List[str], paths: List[str]) -> List[str]:
        """
        Returns a list of URLs consisting of all possible combinations of domains and paths,
        *including* no path.

        Examples
        --------
        domains=["example.com", "this.example.com"], paths=["here", "here/there"] yields
        [
            "example.com", "this.example.com", "example.com/here", "example.com/here/there",
            "this.example.com/here", "this.example.com/here/there"
        ]
        """
        if not paths:
            return domains

        domains_with_paths: List[str] = domains.copy()

        for domain, path in itertools.product(domains, paths):
            domains_with_paths.append(f"{domain}/{path}")

        # Ensure there are no repeated values
        return list(set(domains_with_paths))

    @classmethod
    def join_base_domain_with_suffix(
        cls, base_domain: Optional[str], suffix: Optional[str]
    ) -> Optional[str]:
        """
        Concatenates `base_domain` with `suffix` if found in the `url` attribute.

        Parameters
        ----------
        base_domain : Optional[str]
            The base domain to be concatenated.

        suffix : Optional[str]
            The suffix to be concatenated.

        Returns
        -------
        Optional[str]
            The contatenated `base_domain` with `suffix`. Returns `base_domain` or `suffix` if one
            of them is `None`, or `None` if both are `None`.

        """
        components = []
        if base_domain:
            components += [base_domain]
        if suffix:
            components += [suffix]

        return ".".join(components) or None

    @classmethod
    def join_subdomains_with_base_domain_and_suffix(
        cls, subdomains: List[str], base_domain_with_suffix: Optional[str]
    ) -> Optional[str]:
        """
        Concatenates `subdomains` with `base_domain_with_suffix` if both or them are not `None`.

        Parameters
        ----------
        subdomains : List[str]
            The list of subdomains to be concatenated.

        base_domain_with_suffix : Optional[str]
            The base domain with suffix to be concatenated.

        Returns
        -------
        Optional[str]
            The contatenated `subdomains` with `base_domain_with_suffix`. Returns `subdomains` or
            `base_domain_with_suffix` if one of them is `None`, or `None` if both are `None`.

        """
        components: List[str] = []
        if subdomains:
            components += subdomains

        if base_domain_with_suffix:
            components += [base_domain_with_suffix]

        return ".".join(components) or None

    def get_partial_domain(self, num_subdomains: Optional[int] = None) -> Optional[str]:
        """
        Return the domain name from the `url` attribute, up to a particular number of subdomains.

        We define a partial domain as a domain with a subset of the last subdomains. If no
        `num_subdomains` is provided, get the fully qualified domain (without final dot) with all
        its subdomains.

        Parameters
        ----------
        num_subdomains : Optional[int], Optional
            Number of subdomains that are got. By default, all available subdomains are got.

        Returns
        -------
        Optional[str]
            The partial domain of the `url` following the aforementioned criteria, or `None`.

        See also
        --------
        get_n_subdomains
            Called to obtain the left part of the URL.
        join_base_domain_with_suffix
            Called to obtain the right part of the URL.
        join_subdomains_with_base_domain_and_suffix
            Called to join the left part and the right part to build the partial domain.

        Examples
        --------
        https://sub2.sub1.example.com.es/path, 0 -> example.com.es
        https://sub2.sub1.example.com.es/path, 1 -> sub1.example.com.es
        https://sub2.sub1.example.com.es/path, 2 -> sub2.sub1.example.com.es
        https://sub2.sub1.example.com.es/path, 3 -> sub2.sub1.example.com.es
        https://sub2.sub1.example.com.es/path, None -> sub2.sub1.example.com.es

        """
        if num_subdomains is None:
            subdomains = self.subdomains
        else:
            subdomains = self.get_n_subdomains(num_subdomains=num_subdomains)

        base_domain_with_suffix = self.join_base_domain_with_suffix(
            base_domain=self.base_domain, suffix=self.suffix
        )
        subdomains_with_base_domain_and_suffix = self.join_subdomains_with_base_domain_and_suffix(
            subdomains=subdomains, base_domain_with_suffix=base_domain_with_suffix
        )

        return subdomains_with_base_domain_and_suffix or None

    def contains_ip(self) -> bool:
        """
        Checks whether the `base_domain` attribute contains a valid IP address.

        Returns
        -------
        bool
            True if the `base_domain` attribute contains a valid IP address, False otherwise.

        Notes
        -----
        The verification of IP has been done using the `ipaddress` module of python. More
        information on the ipaddress module: [1]

        References
        ----------
        [1] :
        https://docs.python.org/3/library/ipaddress.html

        """

        # If it is a valid IP, the initialization of the IP class should be successful.
        try:
            ipaddress.ip_address(self.base_domain)
        except ValueError:
            return False

        return True

    def explode_domain(self) -> List[str]:
        """
        Computes all possible levels of partial domains including the top level domain, from less
        complete to more, from the `url` attribute.

        Returns
        -------
        List[str]
            The exploded domains from less complete to more, following the aforementioned criteria.

        See also
        --------
        get_partial_domain
            Called each time with different number of subdomains to obtain all partial domains.

        Example
        -------
        'www.s1.s2.example.com' -> ['example.com', 's2.example.com', 's1.s2.example.com',
        'www.s1.s2.example.com']

        """
        exploded_domains: List[str] = []
        full_domain = self.get_partial_domain()

        if full_domain:
            exploded_domains.append(full_domain)

        for _ in range(len(self.subdomains)):
            exploded_domains.append(exploded_domains[-1].split(".", maxsplit=1)[1])

        # Revert to return a list with increasing number of subdomains
        return list(reversed(exploded_domains))

    @classmethod
    def explode_path(cls, path: str, max_depth: int = 1) -> List[str]:
        """Given a path, returns a list with exploded paths up to the specified `max_depth`.

        Examples
        --------
        "here/there", 1 -> ["here"]
        "here/there", 2 -> ["here", "here/there"]
        """
        if path is None or path in ["", "/"]:
            return []

        path_parts = path.strip("/").split("/")
        return ["/".join(path_parts[: i + 1]) for i in range(min(max_depth, len(path_parts)))]
