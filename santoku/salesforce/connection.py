import argparse
import logging
import os
import sys
import json
import re

import requests

from typing import List, Dict, Any, Optional, cast

# load global logger
logger = logging.getLogger(__name__)
logging.basicConfig(format="%(asctime)s %(message)s")


class SalesforceConnection:
    def __init__(
        self,
        auth_url: str,
        username: str,
        password: str,
        client_id: str,
        client_secret: str,
        api_version: float = 47.0,
        grant_type: str = "password",
    ) -> None:

        self.__url_to_format = "{}/services/data/v{:.1f}/{}"

        self.__auth_url = auth_url
        self.__api_version = api_version
        self.__grant_type = grant_type
        self.__username = username
        self.__password = password
        self.__client_id = client_id
        self.__client_secret = client_secret

        self.__instance_scheme_and_authority = ""
        self.__access_token = ""

        self.__standard_object_names_cache: List[str] = []
        self.__standard_object_fields_cache: Dict[str, List[str]] = {}

        self.request_headers = {
            "Authorization": "OAuth",
            "Content-type": "application/json",
        }

        self.__validate_standard_object = True
        self.__is_authenticated = False

    def __authenticate(self) -> None:
        logger.debug("Authenticating...")
        try:
            response = requests.post(
                self.__auth_url,
                data={
                    "grant_type": self.__grant_type,
                    "username": self.__username,
                    "password": self.__password,
                    "client_id": self.__client_id,
                    "client_secret": self.__client_secret,
                },
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as err:
            raise
        else:
            logger.debug("Done.")
            self.__is_authenticated = True

            response_as_dict = response.json()

            self.__instance_scheme_and_authority = response_as_dict["instance_url"]
            self.__access_token = response_as_dict["access_token"]
            # Update header with OAuth access token
            self.request_headers["Authorization"] = "OAuth {}".format(
                self.__access_token
            )

    def __get_salesforce_standard_object_names(self) -> List[str]:
        logger.debug("__get_salesforce_standard_object_names...")

        if not self.__standard_object_names_cache:
            logger.debug("No cached, doing query.")
            self.__validate_standard_object = False

            # GET request to /sobjects returns a list with the valid standard objects
            response = self.do_request(method="GET", path="sobjects")

            self.__standard_object_names_cache = [
                standard_object["name"]
                for standard_object in json.loads(response)["sobjects"]
            ]

        return self.__standard_object_names_cache

    def __get_salesforce_standard_object_fields(
        self, standard_object_name: str
    ) -> List[str]:
        # Update cache if fields for current standard_object_name aren't in the cache
        logger.debug(
            "__get_salesforce_standard_object_fields for {}".format(
                standard_object_name
            )
        )

        if standard_object_name not in self.__standard_object_fields_cache:
            logger.debug("No cached, doing query.")
            self.__validate_standard_object = False
            response = self.do_request(
                method="GET", path="sobjects/{}/describe".format(standard_object_name)
            )

            self.__standard_object_fields_cache[standard_object_name] = [
                fields["name"] for fields in json.loads(response)["fields"]
            ]

        return self.__standard_object_fields_cache[standard_object_name]

    def __obtain_standard_object_name_from_path(self, path: str) -> str:
        # Extract standard_object_name taking into account that we'll find something like...
        if "describe" in path:
            # ...sobjects/Account/describe
            standard_object_name = path.split("/")[1]
        elif "query?q=SELECT" in path:
            # ...query?q=SELECT+one+or+more+fields+FROM+an+object+WHERE+filter+statements
            if "WHERE" in path:
                matches = re.search("{}(.*){}".format("FROM+", "+WHERE"), path)
                if matches:
                    standard_object_name = matches.group(1)
                else:
                    standard_object_name = ""
            else:
                matches = re.search("{}(.*)".format("FROM+"), path)
                if matches:
                    standard_object_name = matches.group(1)
                else:
                    standard_object_name = ""

            # standard_object_name = path.split("+")[-1]
        elif path == "sobjects":
            standard_object_name = ""
        else:
            # ...sobjects/Account
            standard_object_name = path.split("/")[-1]

        return standard_object_name

    def __validate_payload_content(
        self, payload: Dict[str, str], standard_object_fields: List[str]
    ) -> None:
        for field in payload.keys():
            if field not in standard_object_fields:
                raise ValueError("{} isn't a valid field".format(field))

    def do_request(
        self,
        method: str,
        path: str,
        id: str = None,
        payload: Optional[Dict[str, str]] = None,
    ) -> str:
        """
            Constructs and sends a request. Returns a string with a JSON object.

            Parameters
            ----------

            Returns
            -------

            Raises
            ------
            requests.exceptions.RequestException
                If the matrix is not numerically invertible.
        """

        assert method in ["POST", "GET", "PATCH", "DELETE"], "method isn't supported"

        if not self.__is_authenticated:
            self.__authenticate()

        if self.__validate_standard_object:
            standard_object_name = self.__obtain_standard_object_name_from_path(path)
            if standard_object_name:
                assert (
                    standard_object_name
                    in self.__get_salesforce_standard_object_names()
                ), "{} isn't a valid standard object".format(standard_object_name)

        url = self.__url_to_format.format(
            self.__instance_scheme_and_authority, self.__api_version, path,
        )

        try:
            if method in ["POST", "PATCH"]:
                assert payload, "payload must be defined for a POST, PATCH request"

                if self.__validate_standard_object:
                    standard_object_fields = self.__get_salesforce_standard_object_fields(
                        standard_object_name
                    )
                    self.__validate_payload_content(
                        payload=payload, standard_object_fields=standard_object_fields
                    )

                if method == "PATCH":
                    assert id, "{} method requires Id attribute.".format(method)
                    url = "{}/{}".format(url, id)

                # we use reflection to choose which method (POST or PATCH) to execute
                response = getattr(requests, method.lower())(
                    url=url, json=payload, headers=self.request_headers,
                )
            else:  # method == "GET" or method == "DELETE":
                if method == "DELETE":
                    assert id, "{} method requires Id attribute.".format(method)
                if id:
                    url = "{}/{}".format(url, id)

                response = getattr(requests, method.lower())(
                    url, headers=self.request_headers
                )

            # Call Response.raise_for_status method to raise exceptions from http errors (e.g. 401 Unauthorized)
            response.raise_for_status()
        except requests.exceptions.RequestException as err:
            raise
        else:
            self.__validate_standard_object = True
            # if method == "GET":
            #     return response.text

        # response is returned as is, it's caller responsability to do the parsing
        return response.text

    def do_query_with_SOQL(self, query="SELECT Name from Account") -> str:
        return self.do_request(
            method="GET", path="query?q={}".format(query.replace(" ", "+"))
        )


# def main():
#     try:
#         parser = argparse.ArgumentParser(description="My description")
#         parser.add_argument(
#             "-v", "--verbose", action="store_true", help="Increase output verbosity",
#         )

#         args = parser.parse_args()
#     except Exception:
#         logger.error("Error", exc_info=True)
#         return 2

#     # logging stuff
#     if args.verbose:
#         logger.setLevel(logging.DEBUG)

#     sc = SalesforceConnection(URL_AUTH)

#     # print(
#     #     sc.do_request(
#     #         method="GET", path="query?q=SELECT+Name+from+Account"
#     #     )
#     # )

#     # print(sc.do_request(method="GET", path="sobjects/Account"))

#     sc.do_request(method="POST", path="sobjects/Account", payload={"Name": "Alice Bob"})
#     print(sc.do_query_with_SOQL(query="SELECT Name, Id from Account"))


# if __name__ == "__main__":
#     sys.exit(main())
