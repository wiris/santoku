import ipaddress
from typing import List

import pandas as pd
import tldextract


class URLHandler:
    @staticmethod
    def get_partial_domain(
        url: str, num_subdomains: int = 0, return_invalid_urls: bool = False
    ) -> str:
        """
        Given a URL, return the domain name up to a particular number of subdomains.

        Parameters
        ----------
        url : str
            The URL to get the partial domain from.

        num_subdomains : int
            Number of subdomains that are extracted.

        return_invalid_urls : bool
            We consider as invalid those URLs that do not contain domain or do not contain suffix,
            except for URLs containing IP addresses. Set to `False` by default.

        Returns
        -------
        str
            The partial domain of the `url`. If `return_invalid_urls` set to `False`, empty string
            will be returned for invalid urls, otherwise, if subdomain is detected, num_subdomains +
            domain will be returend, if no subdomain is detected, the URL will be returned as it is.

        Notes
        -----
        Notice that with our definition of invalid URLs, URLs containing IP addresses will be
        considered as invalid as they do not contain suffixes.

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
            if return_invalid_urls:

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

                # If URL doesn't contain anything identified as domain or suffix, return as it is
                return url

            return ""

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

    @staticmethod
    def get_fully_qualified_domain(url: str, return_invalid_urls: bool = False) -> str:
        """
        Given a URL return its fully qualified domain name without the trailing dot, defined as the
        domain name with all its subdomains.

        Parameters
        ----------
        url : str
            The URL to get the fully qualified domain.

        return_invalid_urls : bool
            We consider as invalid those URLs that do not contain domain or do not contain suffix,
            except for URLs containing IP addresses. Set to `False` by default.

        Returns
        -------
        str
            The fully qualified domain of the `url`. If `return_invalid_urls` set to `False`, empty
            string will be returned for invalid urls, otherwise, the URL without scheme, path, query
            and fragment will be returned.

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
            if return_invalid_urls:

                if res.domain:
                    # URL contain subdomain and domain, we return subdomain + domain
                    if res.subdomain:
                        return f"{res.subdomain}.{res.domain}"

                    # URL only contain domain, we return only the domain
                    return res.domain

                elif res.suffix:
                    # URL contain only sufix, we return only the suffix
                    return res.suffix

                # If URL doesn't contain anything identified as domain or suffix, return as it is
                return url

            return ""

        return ".".join(part for part in res if part)

    @staticmethod
    def contains_ip(url: str) -> bool:
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
        https://docs.python.org/3/library/ipaddress.html

        """
        domain = tldextract.extract(url=url).domain

        # If it is a valid IP, the initialization of the IP class should be successful.
        try:
            ipaddress.ip_address(domain)
        except ValueError:
            return False

        return True

    @staticmethod
    def explode_domain(url: str, return_invalid_urls: bool = False) -> List[str]:
        """
        Takes in a string with a URL and computes all possible levels of subdomain including top
        level domain, from less complete to more.

        Parameters
        ----------
        url : str
            The URL to get the fully qualified domain.

        return_invalid_urls : bool
            We consider as invalid those URLs that do not contain domain or do not contain suffix,
            except for URLs containing IP addresses. Set to `False` by default.

        Returns
        -------
        List[str]
            The exploded domains from less complete to more.

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
                if return_invalid_urls:
                    # A URL can be identified as suffix when it contains only tlds, i.e: 'com' or
                    # 'co.uk'
                    return [res.suffix]
        elif res.domain:
            if return_invalid_urls:
                return [res.domain]
        else:
            # If a URL isn't valid and no particle has been identified, the same invalid URL will be
            # returned. It's the case of: "", " ", "//", ".", etc
            if return_invalid_urls:
                return [url]

        return [""]
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

    @staticmethod
    def explode_domains(
        df: pd.DataFrame,
        referrer_column="referrer",
        exploded_domains_column="domain",
        return_invalid_urls: bool = False,
    ) -> pd.DataFrame:
        """
        Explode the referrers in a `referrer_column` into a `exploded_domains_column`, removing the
        `referrer_column`.

        Parameters
        ----------
        df : pd.DataFrame
            The dataframe to which the referrers will be exploded.

        referrer_column : str
            Name of the column containing the referrers to be exploded. Set to `referrer` by
            default.

        exploded_domains_column : str
            Name of the column containing the exploded domains. Set to `domain` by default.

        return_invalid_urls : bool
            We consider as invalid those URLs that do not contain domain or do not contain suffix,
            except for URLs containing IP addresses. Set to `False` by default.

        Returns
        -------
        pd.DataFrame
            A dataframe with exploded domains in `exploded_domains_column`, and `referrer_column`
            removed.

        Raises
        ------
        ValueError
            If `referrer_column` contains nan values.

        See Also
        --------
        explode_domain : called to explode the referrers into domains.

        Example
        -------
        'www.s1.s2.example.com' -> ['example.com', 's2.example.com', 's1.s2.example.com',
        'www.s1.s2.example.com'].
        """

        # Check that the `referrer_column` does not contain nan values
        if df[referrer_column].isna().values.any():
            raise ValueError(f"Column {referrer_column} must not contain nan values.")

        # We do a copy to prevent pandas SettingWithCopyWarning warning
        result = df.copy()

        # Transform the domain into the list of all possible subdomains
        result[exploded_domains_column] = result[referrer_column].apply(
            lambda referrer: URLHandler.explode_domain(
                url=referrer, return_invalid_urls=return_invalid_urls
            )
        )

        # Drop referrers, as they are not needed any more
        result.drop(columns=[referrer_column], inplace=True)

        # Explode the list into different rows
        result = result.explode(column=exploded_domains_column, ignore_index=True)

        return result
