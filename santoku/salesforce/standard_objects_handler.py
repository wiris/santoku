import json
import re
import requests

from typing import List, Dict, Any, Optional


class StandardObjectsHandler:
    """
    Class to manage operations on Salesforce content.

    This class contains methods that interact with Salesforce standard objects and makes easy some
    usual operations. The connection is done by calling the Salesforce API Rest. This class is
    pretended to be used on AWS Glue jobs (Python Shell) directly or through a higher level API.

    Notes
    -----
    The functionalities of the private methods are the following:
        Pass authentication credentials to establish connection with salesforce.
        Collect the sobject names available in salesforce, which is used to verify the correctness
        of the parameters.
        Collect the sobject fields available of a specific sobject and store this information as a
        cache, which is used to verify the correctness of the parameters.
        Extract the standard object name from a given path.
        Verify if the introduced parameters are valid fields of an sobject.

    More information on the use of Salesforce API Rest: [1]

    References
    ----------
    [1] :
        https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/quickstart.htm

    """

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
        """
        Initialize the private variables of the class.

        Parameters
        ----------
        auth_url : str
            Url used to authenticate with salesforce.
        username : str
            Username used to authenticate with salesforce.
        password : str
            Password used to authenticate with salesforce.
        client_id : str
            Consumer key used to authenticate with salesforce.
        client_secret : str
            Consumer secret used to authenticate with salesforce.
        api_version : float, optional
            Version of the Salesforce API used (the default is 47.0).
        grant_type : str, optional
            Type of credentials used to authenticate with salesforce(the default is 'password').

        Return
        ------
        None

        """

        self._url_to_format = "{}/services/data/v{:.1f}/{}"

        self._auth_url = auth_url
        self._api_version = api_version
        self._grant_type = grant_type
        self._username = username
        self._password = password
        self._client_id = client_id
        self._client_secret = client_secret

        self._instance_scheme_and_authority = ""
        self._access_token = ""

        self._standard_object_names_cache: List[str] = []
        self._standard_object_fields_cache: Dict[str, List[str]] = {}

        self.request_headers: Dict[str, str] = {
            "Authorization": "OAuth",
            "Content-type": "application/json",
        }

        # Indicates if there is need to validate whether the requesting standard object is valid
        self._validate_standard_object = True
        self._is_authenticated = False

    def _authenticate(self) -> None:
        try:
            response = requests.post(
                self._auth_url,
                data={
                    "grant_type": self._grant_type,
                    "username": self._username,
                    "password": self._password,
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as err:
            raise
        else:
            self._is_authenticated = True

            response_as_dict = response.json()

            self._instance_scheme_and_authority = response_as_dict["instance_url"]
            self._access_token = response_as_dict["access_token"]
            # Update header with OAuth access token
            self.request_headers["Authorization"] = "OAuth {}".format(
                self._access_token
            )

    def _get_salesforce_standard_object_names(self) -> List[str]:

        if not self._standard_object_names_cache:
            self._validate_standard_object = False

            # GET request to /sobjects returns a list with the valid standard objects
            response = self.do_request(method="GET", path="sobjects")

            self._standard_object_names_cache = [
                standard_object["name"]
                for standard_object in json.loads(response)["sobjects"]
            ]

        return self._standard_object_names_cache

    def _get_salesforce_standard_object_fields(
        self, standard_object_name: str
    ) -> List[str]:

        if standard_object_name not in self._standard_object_fields_cache:
            self._validate_standard_object = False
            response = self.do_request(
                method="GET", path="sobjects/{}/describe".format(standard_object_name)
            )

            self._standard_object_fields_cache[standard_object_name] = [
                fields["name"] for fields in json.loads(response)["fields"]
            ]

        return self._standard_object_fields_cache[standard_object_name]

    def _obtain_standard_object_name_from_path(self, path: str) -> str:
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

        elif path == "sobjects":
            standard_object_name = ""
        else:
            # ...sobjects/Account or ...sobjects/Account/ID
            standard_object_name = path.split("/")[path.index("sobjects") + 1]

        return standard_object_name

    def _validate_payload_content(
        self, payload: Dict[str, str], standard_object_fields: List[str]
    ) -> None:
        for field in payload.keys():
            if field not in standard_object_fields:
                raise ValueError("{} isn't a valid field".format(field))

    def do_request(
        self, method: str, path: str, payload: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Constructs and sends a request.

        Parameters
        ----------
        method : str {'POST', 'GET', 'PATCH', 'DELETE'}
            An HTTP Request Method.
        path : str
            Relative path of requesting service.
        payload : `Dict[str, str]`, optional
            Payload that contains information that complements the requesting operation.

        Returns
        -------
        str
            Response from Salesforce. This is a JSON encoded as text.

        Raises
        ------
        AssertionError
            If the method is not supported, or the sobject is not valid, or payload is missing when
            needed.

        requests.exceptions.RequestException
            If the connection with salesforce fails, e.g. the requesting resource does not exist.

        """

        assert method in ["POST", "GET", "PATCH", "DELETE"], "Method isn't supported."

        if not self._is_authenticated:
            self._authenticate()

        if self._validate_standard_object:
            standard_object_name = self._obtain_standard_object_name_from_path(path)
            if standard_object_name:
                assert (
                    standard_object_name in self._get_salesforce_standard_object_names()
                ), "{} isn't a valid standard object".format(standard_object_name)

        url = self._url_to_format.format(
            self._instance_scheme_and_authority, self._api_version, path,
        )

        try:
            if method in ["POST", "PATCH"]:
                assert payload, "Payload must be defined for a POST, PATCH request."

                if self._validate_standard_object:
                    standard_object_fields = self._get_salesforce_standard_object_fields(
                        standard_object_name
                    )
                    self._validate_payload_content(
                        payload=payload, standard_object_fields=standard_object_fields
                    )

                # we use reflection to choose which method (POST or PATCH) to execute
                response = getattr(requests, method.lower())(
                    url=url, json=payload, headers=self.request_headers,
                )
            else:  # method == "GET" or method == "DELETE":
                response = getattr(requests, method.lower())(
                    url=url, headers=self.request_headers
                )

            # Call Response.raise_for_status method to raise exceptions from http errors (e.g. 401
            # Unauthorized)
            response.raise_for_status()
        except requests.exceptions.RequestException as err:
            raise
        else:
            self._validate_standard_object = True

        # response is returned as is, it's caller's responsability to do the parsing
        return response.text

    def do_query_with_SOQL(self, query="SELECT Name from Account") -> str:
        """
        Constructs and sends a request using SOQL.

        Use the Salesforce Object Query Language (SOQL) to search Salesforce data for specific
        information.

        Parameters
        ----------
        query : str
            SOQL with the desired query.

        Returns
        -------
        str
            Response from Salesforce. This is a JSON encoded as text.

        Notes
        ----
        Use this method when you know which objects the data resides in, and you want to
        retrieve data from a single object or from multiple objects that are related.
        For more information related to SOQL: [1]
        For a complete description of the SOQL syntax: [2].

        References
        ----------
        [1] https://developer.salesforce.com/docs/atlas.en-us.soql_sosl.meta/soql_sosl/sforce_api_calls_soql.htm
        [2] https://developer.salesforce.com/docs/atlas.en-us.soql_sosl.meta/soql_sosl/sforce_api_calls_soql_select.htm

        Raises
        ------
        requests.exceptions.RequestException
            If the request fails, e.g. the requesting attribute does not exist for the sobject
            class.

        """

        return self.do_request(
            method="GET", path="query?q={}".format(query.replace(" ", "+"))
        )
