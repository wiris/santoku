import json
import re
import requests

from typing import List, Dict, Any, Optional


class ObjectsHandler:
    """
    Class to manage operations on Salesforce content.

    This class contains methods that interact with Salesforce objects and makes easy some
    usual operations. The connection is done by calling the Salesforce API Rest. This class is
    pretended to be used on AWS Glue jobs (Python Shell) directly or through a higher level API.

    Notes
    -----
    The functionalities of the private methods are the following:
        Pass authentication credentials to establish connection with salesforce.
        Collect the object names available in salesforce, which is used to verify the correctness
        of the parameters.
        Collect the object fields available of a specific salesforce object and store this
        information as a cache, which is used to verify the correctness of the parameters.
        Extract the object name from a given path.
        Verify if the introduced parameters are valid fields of a salesforce object.

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

        self._salesforce_object_names_cache: List[str] = []
        self._salesforce_object_fields_cache: Dict[str, List[str]] = {}

        self.request_headers: Dict[str, str] = {
            "Authorization": "OAuth",
            "Content-type": "application/json",
        }

        # Indicates if there is need to validate whether the requesting salesforce object is valid.
        self._validate_salesforce_object = True
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
            # Update header with OAuth access token.
            self.request_headers["Authorization"] = "OAuth {}".format(
                self._access_token
            )

    def get_salesforce_object_names(self) -> List[str]:

        if not self._salesforce_object_names_cache:
            self._validate_salesforce_object = False

            # GET request to /sobjects returns a list with the valid objects.
            response = self.do_request(method="GET", path="sobjects")

            self._salesforce_object_names_cache = [
                sobject["name"] for sobject in json.loads(response)["sobjects"]
            ]

        return self._salesforce_object_names_cache

    def get_salesforce_object_fields(self, salesforce_object_name: str) -> List[str]:

        if salesforce_object_name not in self._salesforce_object_fields_cache:
            self._validate_salesforce_object = False
            response = self.do_request(
                method="GET", path="sobjects/{}/describe".format(salesforce_object_name)
            )

            self._salesforce_object_fields_cache[salesforce_object_name] = [
                fields["name"] for fields in json.loads(response)["fields"]
            ]

        return self._salesforce_object_fields_cache[salesforce_object_name]

    def _obtain_salesforce_object_name_from_path(self, path: str) -> str:
        # Extract salesforce_object_name taking into account that we'll find something like...
        if "describe" in path:
            # ...sobjects/Account/describe
            salesforce_object_name = path.split("/")[1]
        elif "query?q=SELECT" in path:
            # ...query?q=SELECT+one+or+more+fields+FROM+an+object+WHERE+filter+statements
            if "WHERE" in path:
                matches = re.search("{}(.*){}".format("FROM+", "+WHERE"), path)
                if matches:
                    salesforce_object_name = matches.group(1)
                else:
                    salesforce_object_name = ""
            else:
                matches = re.search("{}(.*)".format("FROM+"), path)
                if matches:
                    salesforce_object_name = matches.group(1)
                else:
                    salesforce_object_name = ""
        elif "query" in path:
            # ...query/idnetifier
            salesforce_object_name = ""

        elif path == "sobjects" or path == "limits":
            salesforce_object_name = ""
        else:
            # ...sobjects/Account or ...sobjects/Account/ID
            salesforce_object_name = path.split("/")[path.index("sobjects") + 1]

        return salesforce_object_name

    def _validate_payload_content(
        self, payload: Dict[str, str], object_fields: List[str]
    ) -> None:
        for field in payload.keys():
            if field not in object_fields:
                raise ValueError("{} isn't a valid field".format(field))

    def do_request(
        self, method: str, path: str, payload: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Construct and send a request.

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
            If the method is not supported, or the object is not valid, or payload is missing when
            needed.

        requests.exceptions.RequestException
            If the connection with salesforce fails, e.g. the requesting resource does not exist.

        """
        assert method in ["POST", "GET", "PATCH", "DELETE"], "Method isn't supported."

        if not self._is_authenticated:
            self._authenticate()

        if self._validate_salesforce_object:
            salesforce_object_name = self._obtain_salesforce_object_name_from_path(path)
            if salesforce_object_name:
                assert (
                    salesforce_object_name in self.get_salesforce_object_names()
                ), "{} isn't a valid object".format(salesforce_object_name)

        url = self._url_to_format.format(
            self._instance_scheme_and_authority, self._api_version, path,
        )

        try:
            if method in ["POST", "PATCH"]:
                assert payload, "Payload must be defined for a POST, PATCH request."

                if self._validate_salesforce_object:
                    object_fields = self.get_salesforce_object_fields(
                        salesforce_object_name
                    )
                    self._validate_payload_content(
                        payload=payload, object_fields=object_fields
                    )

                # We use reflection to choose which method (POST or PATCH) to execute.
                response = getattr(requests, method.lower())(
                    url=url, json=payload, headers=self.request_headers,
                )
            else:  # method == "GET" or method == "DELETE":
                response = getattr(requests, method.lower())(
                    url=url, headers=self.request_headers
                )

            # Call Response.raise_for_status method to raise exceptions from http errors (e.g. 401
            # Unauthorized).
            response.raise_for_status()
        except requests.exceptions.RequestException as err:
            raise
        else:
            self._validate_salesforce_object = True

        # Response is returned as is, it's caller's responsability to do the parsing.
        return response.text

    def do_query_with_SOQL(
        self, query="SELECT Name from Account"
    ) -> List[Dict[str, Any]]:
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

        Raises
        ------
        requests.exceptions.RequestException
            If the request fails, e.g. the requesting attribute does not exist for the salesforce
            object class.

        See Also
        --------
        do_request : this method does a request of type GET.

        Notes
        ----
        Use this method when you know which objects the data resides in, and you want to
        retrieve data from a single salesforce object or from multiple objects that are related. The
        maximum number of records that a single SOQL request can return is 2000, when this limit is
        exceeded, the field `nextRecordsUrl` from the response of the query is used, this method
        already manages this problem, hence all the records of the query will be returned.
        For more information related to SOQL: [1]
        For a complete description of the SOQL syntax: [2].
        For more information about the SOQL requests URIs: [3].
        For more information about the limits of the SOQL requests: [4].

        References
        ----------
        [1] https://developer.salesforce.com/docs/atlas.en-us.soql_sosl.meta/soql_sosl/sforce_api_calls_soql.htm
        [2] https://developer.salesforce.com/docs/atlas.en-us.soql_sosl.meta/soql_sosl/sforce_api_calls_soql_select.htm
        [3] https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/resources_query.htm
        [4] https://developer.salesforce.com/docs/atlas.en-us.salesforce_app_limits_cheatsheet.meta/salesforce_app_limits_cheatsheet/salesforce_app_limits_platform_soslsoql.htm

        """
        response = self.do_request(
            method="GET", path="query?q={}".format(query.replace(" ", "+"))
        )
        response_dict = json.loads(response)
        records = response_dict["records"]
        while "nextRecordsUrl" in response_dict:
            next_url = response_dict["nextRecordsUrl"]
            query_identifier = next_url.split("/")[-1]
            response = self.do_request(
                method="GET", path="query/{}".format(query_identifier)
            )
            response_dict = json.loads(response)
            records.extend(response_dict["records"])
        return records

    def insert_record(self, sobject: str, payload: Dict[str, str]) -> str:
        """
        Create a new instance of a salesforce object.

        Create a new record of type `sobject` with the information in the payload.

        Parameters
        ----------
        sobject : str
            A salesforce object.
        payload : Dict[str, str]
            Payload that contains information to create the record.

        Returns
        -------
        str
            Response from Salesforce. This is a JSON encoded as text.

        Raises
        ------
        AssertionError
            If the object is not valid, or the payload contains fields that are not valid for this
            object.

        See Also
        --------
        do_request : this method does a request of type POST.

        """
        return self.do_request(
            method="POST", path="sobjects/{}".format(sobject), payload=payload,
        )

    def modify_record(
        self, sobject: str, record_id: str, payload: Dict[str, str],
    ) -> str:
        """
        Update an instance of a salesforce object.

        Modify a record of type `sobject` with id `record_id` using the new
        information in the `payload`.

        Parameters
        ----------
        sobject : str
            A salesforce object.
        record_id : str
            The identification of the record.
        payload : Dict[str, str]
            Payload that contains information to update the record.
        Returns
        -------
        str
            Response from Salesforce. This is a JSON encoded as text.

        Raises
        ------
        AssertionError
            If the object is not valid, or the payload contains fields that are not valid for this
            object.

        requests.exceptions.RequestException
            If the connection with salesforce fails, e.g. the record does not exist.

        See Also
        --------
        do_request : this method does a request of type PATCH.

        """
        return self.do_request(
            method="PATCH",
            path="sobjects/{}/{}".format(sobject, record_id),
            payload=payload,
        )

    def delete_record(self, sobject: str, record_id: str) -> str:
        """
        Remove an instance of a salesforce object.

        Delete a record of type `sobject` with id `record_id`.

        Parameters
        ----------
        sobject : str
            A salesforce object.
        record_id : str
            The identification of the record.
        Returns
        -------
        str
            Response from Salesforce. This is a JSON encoded as text.

        Raises
        ------
        AssertionError
            If the object is not valid, or the payload contains fields that are not valid for this
            object.

        requests.exceptions.RequestException
            If the connection with salesforce fails, e.g. the record does not exist.

        See Also
        --------
        do_request : this method does a request of type DELETE.

        """
        return self.do_request(
            method="DELETE", path="sobjects/{}/{}".format(sobject, record_id),
        )

    def get_remaining_daily_api_requests(self) -> int:
        """
        Return the number of calls still available in the current day.

        Returns
        -------
        int
            The number of remaining daily API requests.

        See Also
        --------
        do_request : this method does a request of type GET.

        Notes
        -----
        For more information about the salesforce organization limits: [1]

        References
        ----------
        [1] https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/dome_limits.htm

        """
        response = self.do_request(method="GET", path="limits")
        return int(json.loads(response)["DailyApiRequests"]["Remaining"])