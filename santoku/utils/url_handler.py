import ipaddress
from typing import List
from urllib.parse import urlparse

import tldextract


class InvalidURLError(Exception):
    def __init__(self, message):
        super().__init__(message)


class URLHandler:
    @classmethod
    def get_partial_domain(
        cls, url: str, num_subdomains: int = 0, raise_exception_if_invalid_url: bool = True
    ) -> str:
        """
        Given a URL, return the domain name up to a particular number of subdomains.

        When the given URL is invalid, if `raise_exception_if_invalid_url` is set to `True`,
        `InvalidURLError` exception will be raised. Otherwise, if the URL contains subdomain,
        num_subdomains + domain will be returned, if the URL does not contain subdomain, an empty
        string will be returned if the scheme is detected, otherwise, the URL will be returned as it
        is.

        Parameters
        ----------
        url : str
            The URL to get the partial domain from.

        num_subdomains : int, Optional
            Number of subdomains that are extracted. No subdomains are extracted by default.

        raise_exception_if_invalid_url : bool, Optional
            We consider as invalid those URLs in which some particles are missing in the fully
            qualified domain name. Set to `True` by default.

        Returns
        -------
        str
            The partial domain of the `url` following the aforementioned criteria.

        Raises
        ------
        InvalidURLError
            If `url` is invalid.

        Notes
        -----
        Notice that with our definition of invalid URLs, URLs containing IP addresses will be
        considered as invalid as they do not contain top level domains.

        Examples
        --------
        https://sub2.sub1.example.com.es/path, 0 -> example.com.es
        https://sub2.sub1.example.com.es/path, 1 -> sub1.example.com.es
        https://sub2.sub1.example.com.es/path, 2 -> sub2.sub1.example.com.es
        https://sub2.sub1.example.com.es/path, 3 -> sub2.sub1.example.com.es

        """
        res = tldextract.extract(url)

        # When URL is invalid
        if not res.domain or not res.suffix:

            # If URL contain a domain or a suffix, we remove the scheme and path
            if not raise_exception_if_invalid_url:

                if res.domain:
                    if res.subdomain and num_subdomains > 0:
                        # URL contain subdomain and domain, we return the last n subdomains + domain
                        component = res.subdomain.split(".")[-num_subdomains:] + [res.domain]
                        return ".".join(component)

                    # URL only contain domain, we return only the domain
                    return res.domain

                elif res.suffix:
                    # URL contain only sufix, we return only the suffix
                    return res.suffix

                # If URL doesn't contain anything identified as domain or suffix, check whether it
                # contains scheme. If so, return an empty domain, otherwise, return the url as it is
                # e.g.: for `http:///integration/...` an empty domain will be returned, while for
                # `fakedomain`, the whole `fakedomain` will be returned.
                if urlparse(url).scheme:
                    return ""

                return url

            raise InvalidURLError(f"The {url} URL does not contain top level domain")

        components = []
        # If the url contains subdomains and subdomains are needed
        if res.subdomain and num_subdomains > 0:
            # Split the subdomains and keep the last n
            components += res.subdomain.split(".")[-num_subdomains:]
        if res.domain:
            components.append(res.domain)
        if res.suffix:
            components.append(res.suffix)

        return ".".join(components)

    @classmethod
    def get_fully_qualified_domain(
        cls, url: str, raise_exception_if_invalid_url: bool = True
    ) -> str:
        """
        Given a URL, return its fully qualified domain name without the trailing dot.

        The fully qualified domain name is  defined as the domain name with all its subdomains.
        When the given URL is invalid, if `raise_exception_if_invalid_url` is set to `True`,
        `InvalidURLError` exception will be raised. Otherwise, if any particle of the fully
        qualified domain is present, the URL without scheme, path, query and fragment will be
        returned; else, if the URL contains a scheme, an empty string will be returned;
        otherwise, the url will be returned as it is.

        Parameters
        ----------
        url : str
            The URL to get the fully qualified domain from.

        raise_exception_if_invalid_url : bool, Optional
            We consider as invalid those URLs in which some particles are missing in the fully
            qualified domain name. Set to `True` by default.

        Returns
        -------
        str
            The fully qualified domain of the `url`, following the aforementioned criteria.

        Raises
        ------
        InvalidURLError
            If `url` is invalid.

        Notes
        -----
        This method is more useful than get_partial_domain when you don't know how many subdomains
        the URL contains.

        More information on fully qualified domain name: [1]

        References
        ----------
        [1] :
        https://en.wikipedia.org/wiki/Fully_qualified_domain_name

        Example
        -------
        https://sub.example.com.es/path -> sub.example.com.es

        """
        res = tldextract.extract(url)

        # When URL is invalid
        if not res.domain or not res.suffix:

            # If URL contain a domain or a suffix, we remove the scheme and path
            if not raise_exception_if_invalid_url:

                if res.domain:
                    # URL contain subdomain and domain, we return subdomain + domain
                    if res.subdomain:
                        return f"{res.subdomain}.{res.domain}"

                    # URL only contain domain, we return only the domain
                    return res.domain

                elif res.suffix:
                    # URL contain only sufix, we return only the suffix
                    return res.suffix

                # If URL doesn't contain anything identified as domain or suffix, check whether it
                # contains scheme. If so, return an empty domain, otherwise, return the url as it is
                # e.g.: for `http:///integration/...` an empty domain will be returned, while for
                # `fakedomain`, the whole `fakedomain` will be returned.
                if urlparse(url).scheme:
                    return ""

                return url

            raise InvalidURLError(f"The {url} URL does not contain domain or suffix")

        return ".".join(part for part in res if part)

    @classmethod
    def contains_ip(cls, url: str) -> bool:
        """
        Return true if the given string contains an IP address.

        Parameters
        ----------
        url : str
            The URL to check.

        Returns
        -------
        bool
            True if the given `url` contains an IP address.

        Notes
        -----
        The verification of IP has been done using the `ipaddress` module of python. More
        information on the ipaddress module: [1]

        References
        ----------
        [1] :
        https://docs.python.org/3/library/ipaddress.html

        """
        domain = tldextract.extract(url=url).domain

        # If it is a valid IP, the initialization of the IP class should be successful.
        try:
            ipaddress.ip_address(domain)
        except ValueError:
            return False

        return True

    @classmethod
    def explode_domain(cls, url: str, raise_exception_if_invalid_url: bool = True) -> List[str]:
        """
        Takes in a string with a URL and computes all possible levels of subdomain including the top
        level domain, from less complete to more.

        When the given URL is invalid, if `raise_exception_if_invalid_url` is set to `True`,
        `InvalidURLError` exception will be raised, otherwise, a list containing exploded subdomains
        of the invalid URL will be returned.

        Parameters
        ----------
        url : str
            The URL to explode the domain from.

        raise_exception_if_invalid_url : bool, Optional
            We consider as invalid those URLs in which some particles are missing in the fully
            qualified domain name. Set to `True` by default.

        Returns
        -------
        List[str]
            The exploded domains from less complete to more, following the aforementioned criteria.

        Raises
        ------
        InvalidURLError
            If `url` is invalid.

        Example
        -------
        'www.s1.s2.example.com' -> ['example.com', 's2.example.com', 's1.s2.example.com',
        'www.s1.s2.example.com'].

        """
        res = tldextract.extract(url)

        if res.suffix:
            if res.domain:
                domain = f"{res.domain}.{res.suffix}"
                exploded_subdomains = [domain]

                if res.subdomain:
                    # Append splitted subdomains successively
                    for subdomain in reversed(res.subdomain.split(".")):
                        exploded_subdomains.append(f"{subdomain}.{exploded_subdomains[-1]}")

                # If the URL doesn't contain subdomain, return only the domain
                return exploded_subdomains

            else:
                if not raise_exception_if_invalid_url:
                    # A URL can be identified as suffix when it contains only tlds, i.e: 'com' or
                    # 'co.uk'
                    return [res.suffix]

        elif res.domain:
            if not raise_exception_if_invalid_url:
                exploded_subdomains = [res.domain]
                if res.subdomain:
                    # Append splitted subdomains successively
                    for subdomain in reversed(res.subdomain.split(".")):
                        exploded_subdomains.append(f"{subdomain}.{exploded_subdomains[-1]}")

                return exploded_subdomains
        else:
            if not raise_exception_if_invalid_url:
                # If URL doesn't contain anything identified as domain or suffix, check whether it
                # contains scheme. If so, return an empty domain, e.g.: for
                # `http:///integration/...`, an empty domain will be returned. Otherwise
                #  return the url as it is: it's the case of: "fakedomain", " ", "//", ".", etc.

                if urlparse(url).scheme:
                    return [""]

                return [url]

        raise InvalidURLError(f"The {url} URL does not contain domain or suffix")
        # We comment this code block out until we are sure of what to do
        # try:
        #     res = tld.get_tld(url, fix_protocol=True, as_object=True)
        # except (tld.exceptions.TldDomainNotFound, tld.exceptions.TldBadUrl) as error:
        #     # get_tld raises an exception when the top level domain (tld) is unknown
        #     # For example, we might find an unknown tld if someone uses ".devel" during development
        #     # The code below is an attempt to "clean" the domain by doing
        #     # - Remove http:// and https://
        #     # - Split by "/" and return position 0 of the list
        #     # - Split by "?" and return position 0
        #     # - Split by "#" and return position 0
        #     parsed_url = url.replace("http://", "").replace("https://", "").replace("//", "")
        #     parsed_url = parsed_url.split("/")[0].split("?")[0].split("#")[0]
        #     return [parsed_url]
        # exploded_subdomains = [res.fld]

    @classmethod
    def get_path(cls, url: str, raise_exception_if_invalid_url: bool = True) -> str:
        """
        Given a URL, return the path.

        When the given URL is invalid, if `raise_exception_if_invalid_url` is set to `True`,
        `InvalidURLError`exception will be raised. If the url does not contain a scheme or a domain,
        an empty string will be returned instead.

        Parameters
        ----------
        url : str
            The URL to get the path from.

        raise_exception_if_invalid_url : bool, Optional
            We consider as invalid those URLs in which some particles are missing in the fully
            qualified domain name. Set to `True` by default.

        Returns
        -------
        str
            The path fragment of the URL or an empty string, following the aforementioned criteria.

        Raises
        ------
        InvalidURLError
            If `url` is invalid.

        Example
        -------
        'https://example.com/path/' -> '/path/'

        """
        res = tldextract.extract(url)

        # When URL is invalid
        if not res.domain or not res.suffix:
            if raise_exception_if_invalid_url:
                raise InvalidURLError(f"The {url} URL does not contain domain or suffix")

        parsed_url = urlparse(url)
        if parsed_url.scheme or parsed_url.netloc:
            return parsed_url.path
        else:
            return ""
