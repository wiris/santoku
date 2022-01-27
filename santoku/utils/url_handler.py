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
    - The naming of the components does not follow URL standard specifications [1], and is slightly
    adapted for convenience reasons:
        - When defining `subdomain`, instead of including the 'main' part of the domain name
        (SLD+TLD [2][3]), we refer to a `subdomain` as each of the components (split on `.`), not
        including the 'main' part.
        - Istead of using the generic concept of domain that can include any number of components,
        we define the concept of base_domain, referring to the 'main' domain excluding the leftmost
        and the rightmost component(s) of the domain name. This component allows us to identify a
        URL. In most cases, this is the SLD, except for URLs which might also have a ccTLD [4].
        - Instead of usign the TLD concept, we are using the `suffix` concept as the rightmost
        part of the domain name. This might also be known as the TLD+ccTLD. A component is
        classified as a `suffix` according to a public suffix list [5].
    - If you provide an invalid URL, you might get unexpected results for some of the methods.
    - When a non-valid URL such as 'fakedomain' is provided, 'fakedomain' will be considered as the
    `base_domain`.
    - Some components in the URL like 'userinfo' (what goes right before @) will be ignored.
    - Some components that are case insensitive (scheme, subdomains, base_domain and suffix) are
    lowercased. However, the path component, which is case sensitive, is stored as it is.

    References
    ----------
    [1] :
    https://datatracker.ietf.org/doc/html/rfc3986

    [2]:
    https://en.wikipedia.org/wiki/Second-level_domain

    [3]:
    https://en.wikipedia.org/wiki/Top-level_domain

    [4]
    https://en.wikipedia.org/wiki/Country_code_top-level_domain

    [5] :
    https://www.publicsuffix.org/

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
        clean_component
            Called to clean the URL components.

        Example
        -------
        E.g: https://sub1.sub2.example.co.uk/demo?course=1 is converted into:
        - scheme -> https
        - subdomains -> ["sub1", "sub2"]
        - base_domain -> example
        - suffix -> co.uk
        - path -> demo

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
                scheme = cls.clean_component(component=parsed_url.scheme, lowercase=True)
            if extracted_url.domain:
                domain = cls.clean_component(component=extracted_url.domain, lowercase=True)
            if extracted_url.suffix:
                suffix = cls.clean_component(component=extracted_url.suffix, lowercase=True)

        return scheme, subdomains, domain, suffix, path

    @classmethod
    def process_subdomain(cls, subdomain: Optional[str]) -> List[str]:
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

        See also
        --------
        clean_component
            Called to clean the subdomain.

        Examples
        --------
        "sub2.sub1" -> ["sub2", "sub1"]
        "sub2.sub1." -> ["sub2", "sub1", ""]
        "" -> []

        """
        subdomain = cls.clean_component(component=subdomain, lowercase=True)

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

        See also
        --------
        clean_component
            Called to clean the path.

        """
        # When something like "fakedomain" is passed to urllib.parse.urlparse, "fakedomain" will be
        # parsed as path, which is not desired for us (we) prefer considering "fakedomain" as
        # basedomain
        # However, we still want to process the path for cases where only a path exists, such as
        # in "/quizzesproxy/quizzes/service"
        if not (parsed_url.scheme or parsed_url.netloc) and not parsed_url.path.startswith("/"):
            return None

        # Call to `clean_component` is required as `parsed_url.path` could contain a '/', which is
        # not desirable when dealing with paths
        return cls.clean_component(component=parsed_url.path, lowercase=False)

    @classmethod
    def prepend_slash(cls, component: Optional[str]) -> Optional[str]:
        """
        Adds a forward slash ('/') to the left of a given component if it doesn't have one.

        Parameters
        ----------
        component : Optional[str]
            The component to which a forward slash is added.

        Returns
        -------
        Optional[str]
            Returns the component with a forward slash in the first position of the string, or None
            if the component is empty.

        """
        if not component:
            return None
        if component.startswith("/"):
            return component

        return f"/{component}"

    @classmethod
    def clean_component(cls, component: Optional[str], lowercase: bool = False) -> Optional[str]:
        """
        Removes leading and trailing forward slashes ('/') from a given component, and lowercases it
        if `lowercase` is True.

        Parameters
        ----------
        component : Optional[str]
            The component to be cleaned.

        Returns
        -------
        Optional[str]
            Returns the component without any leading or trailing forward slashes, or None if the
            component is empty.

        """
        if not component:
            return None

        component = component.strip("/")
        if lowercase:
            component = component.lower()

        return component or None

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

        See also
        --------
        clean_component
            Called to clean the base_domain and suffix.

        """

        cleaned_base_domain = cls.clean_component(component=base_domain, lowercase=True)
        cleaned_suffix = cls.clean_component(component=suffix, lowercase=True)

        components = []
        if cleaned_base_domain:
            components += [cleaned_base_domain]
        if cleaned_suffix:
            components += [cleaned_suffix]

        return ".".join(components) or None

    @classmethod
    def join_domain_with_path(cls, domain: Optional[str], path: Optional[str]) -> Optional[str]:
        """
        Cleans and joins `domain` with `path` if both or them are not `None`.

        Parameters
        ----------
        domain : Optional[str]
            The domain to be joined.

        path : Optional[str]
            The path to be joined.

        Returns
        -------
        Optional[str]
            The joined `domain` with `path`. Returns `domain` or `path` if one of them is `None`, or
            `None` if both are `None`.

        See also
        --------
        clean_component
            Called to clean the base_domain and path.

        Examples
        --------
        "example.com", "here/there" -> "example.com/here/there"

        """
        domain_with_path = []

        cleaned_domain = cls.clean_component(component=domain, lowercase=True)
        cleaned_path = cls.clean_component(component=path, lowercase=False)

        if cleaned_domain:
            domain_with_path.append(cleaned_domain)
        if cleaned_path:
            if not cleaned_domain:
                cleaned_path = f"/{cleaned_path}"
            domain_with_path.append(cleaned_path)

        return "/".join(domain_with_path) or None

    @classmethod
    def join_domains_with_paths(
        cls, domains: List[Optional[str]], paths: List[Optional[str]]
    ) -> List[str]:
        """
        Returns the list of cleaned domains without path, and all possible combinations of domains
        and paths after being cleaned without repetitions.

        Parameters
        ----------
        domains : List[Optional[str]]
            The domains to be joined.

        paths : List[Optional[str]]
            The paths to be joined.

        Returns
        -------
        List[Optional[str]]
            List of unique cleaned domains, and the joined cleaned `domains` with cleaned `paths`.
            If both domains and paths are empty (or contain only empty domain and path), returns an
            empty list.

        See also
        --------
        clean_component
            Called to clean the domains and paths.

        Examples
        --------
        domains=["example.com", "this.example.com"], paths=["here", "here/there"] yields
        [
            "example.com", "this.example.com", "example.com/here", "example.com/here/there",
            "this.example.com/here", "this.example.com/here/there"
        ]

        """
        domains_with_paths = []
        for domain in domains:
            cleaned_domain = cls.clean_component(component=domain, lowercase=True)
            if cleaned_domain:
                domains_with_paths.append(cleaned_domain)

        # Avoid modifying original parameters
        domains_copy: List[Optional[str]] = []
        paths_copy: List[Optional[str]] = []

        # If one of domains or paths are empty lists, intertools would not iterate over the other
        # one. As solution we add a 'None' element to the list.
        if not domains:
            domains_copy = [None]
        else:
            domains_copy = domains
        if not paths:
            paths_copy = [None]
        else:
            paths_copy = paths

        for domain, path in itertools.product(domains_copy, paths_copy):
            domain_with_path = cls.join_domain_with_path(domain=domain, path=path)
            if domain_with_path:
                domains_with_paths.append(domain_with_path)

        # Ensure there are no repeated values
        return list(set(domains_with_paths))

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

        See also
        --------
        clean_component
            Called to clean the subdomains and the base_domain_with_suffix.

        Returns
        -------
        Optional[str]
            The contatenated `subdomains` with `base_domain_with_suffix`. Returns `subdomains` or
            `base_domain_with_suffix` if one of them is `None`, or `None` if both are `None`.

        Examples
        --------
        ["sub2", "sub1"], "domain.com" -> "sub2.sub1.domain.com"

        """
        cleaned_subdomains = []
        for subdomain in subdomains:
            cleaned_subdomain = cls.clean_component(component=subdomain, lowercase=True)
            if cleaned_subdomain:
                cleaned_subdomains.append(cleaned_subdomain)

        cleaned_base_domain_with_suffix = cls.clean_component(
            component=base_domain_with_suffix, lowercase=True
        )

        components: List[str] = []
        if cleaned_subdomains:
            components += cleaned_subdomains

        if cleaned_base_domain_with_suffix:
            components += [cleaned_base_domain_with_suffix]

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
    def explode_path(cls, path: Optional[str], max_depth: int = 1) -> List[str]:
        """
        Given a path, returns a list with exploded paths up to the specified `max_depth`.

        We consider the path depth as the number of components of a `path` split on '/'.

        Parameters
        ----------
        path : Optional[str]
            Path to be exploded.

        max_depth : int, Optional
            Depth of paths to be considered in the path exploitation. By default, 1 level of `path`
            is exploded.

        Returns
        -------
        List[str]
            The list of exploded paths up to `max_depth`, or an empty list if `path` is empty. If
            `max_depth` is greater than the number of components of the path, explodes the path with
            all components. If `max_depth` is smaller than 1, an empty list will be returned.

        See also
        --------
        clean_component
            Called to clean the path.

        Examples
        --------
        "here/there", 1 -> ["here"]
        "here/there", 2 -> ["here", "here/there"]

        """
        cleaned_path = cls.clean_component(component=path, lowercase=False)

        if max_depth < 1 or not cleaned_path:
            return []

        path_parts = cleaned_path.split("/")

        depth = min(max_depth, len(path_parts))
        exploded_paths = [path_parts[0]]

        for part in path_parts[1:depth]:
            last_path = exploded_paths[-1]
            new_path = "/".join((last_path, part))
            exploded_paths.append(new_path)

        return exploded_paths
