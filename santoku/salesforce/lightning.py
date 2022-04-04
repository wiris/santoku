import json
import re
from typing import Any, Dict, List, Optional
from urllib import parse

import pandas as pd
import requests
from santoku.aws import SecretsManagerHandler


class SalesforceObjectError(Exception):
    def __init__(self, message):
        super().__init__(message)


class SalesforceObjectFieldError(Exception):
    def __init__(self, message):
        super().__init__(message)


class RequestMethodError(Exception):
    def __init__(self, message):
        super().__init__(message)


class LightningRestApiHandler:
    """
    Class to manage operations on Salesforce content.

    This class contains methods that interact with Salesforce objects and makes easy some
    usual operations. The connection is done by calling the Salesforce REST API. This class is
    pretended to be used on AWS Glue jobs (Python Shell) directly or through a higher level API.

    Notes
    -----
    The functionalities of the private methods are the following:
        Pass authentication credentials to establish connection with Salesforce.
        Collect the object names available in Salesforce, which is used to verify the correctness
        of the parameters.
        Collect the object fields available of a specific Salesforce object and store this
        information as a cache, which is used to verify the correctness of the parameters.
        Extract the object name from a given path.
        Verify if the introduced parameters are valid fields of a Salesforce object.

    More information on the use of Salesforce REST API: [1]

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
        api_version: str = "47.0",
        grant_type: str = "password",
    ) -> None:
        """
        Initialize the private variables of the class.

        Parameters
        ----------
        auth_url : str
            Url used to authenticate with Salesforce.
        username : str
            Username used to authenticate with Salesforce.
        password : str
            Password used to authenticate with Salesforce.
        client_id : str
            Consumer key used to authenticate with Salesforce.
        client_secret : str
            Consumer secret used to authenticate with Salesforce.
        api_version : str, optional
            Version of the Salesforce API used (the default is 47.0).
        grant_type : str, optional
            Type of credentials used to authenticate with Salesforce(the default is 'password').

        """
        self._url_to_format = "{}/services/data/v{}/{}"

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
        self._salesforce_object_required_fields_cache: Dict[str, List[str]] = {}

        self.request_headers: Dict[str, str] = {
            "Authorization": "OAuth",
            "Content-type": "application/json",
            "Accept-Encoding": "gzip",
        }

        # Indicates if there is need to validate whether the requesting Salesforce object is valid.
        self._validate_salesforce_object = True
        self._is_authenticated = False

    @classmethod
    def from_aws_secrets_manager(
        cls,
        secret_name: str,
        secret_keys: Dict[str, str] = {
            "auth_url_key": "AUTH_URL",
            "username_key": "USR",
            "password_key": "PSW",
            "client_id_key": "CLIENT_USR",
            "client_secret_key": "CLIENT_PSW",
        },
        api_version: str = "47.0",
        grant_type: str = "password",
    ) -> "LightningRestApiHandler":
        """
        Retrieve the Salesforce credentials from AWS Secrets Manager and initialize the class.
        Requires that AWS credentials with the appropriate permissions are located somewhere on the
        AWS credential chain in the local machine.

        Parameters
        ----------
        secret_name : str
            Name or ARN for the secret containing the JSON needed for the Salesforce authentication.
        secret_keys : Dict[str, str], optional
            Sepecification of the secret keys used in AWS Secrets Manager to store the credentials.
            (By default "AUTH_URL", "USR", "PSW", "CLIENT_USR", "CLIENT_PSW" will be the keys that
            stores the Salesforce credentials.)
        api_version : str, optional
            Version of the Salesforce API used (the default is 47.0).
        grant_type : str, optional
            Type of credentials used to authenticate with Salesforce(the default is 'password').

        Raises
        ------
        ValueError
            If the `secret_keys` argument does not contain the required attributes.

        See Also
        --------
        __init__ : this method calls the constructor.

        Notes
        -----
        The `secret_keys` parameter must be a JSON containing fixed attributes:
        ```
        {
            "auth_url_key": <auth url>,
            "username_key": <username>,
            "password_key": <password>,
            "client_id_key": <client id>,
            "client_secret_key": <clientsecret>,
        }
        ```

        """
        for key in [
            "auth_url_key",
            "username_key",
            "password_key",
            "client_id_key",
            "client_secret_key",
        ]:
            if key not in secret_keys:
                raise ValueError("The `secret_keys` argument does not contain the required keys.")

        secrets_manager = SecretsManagerHandler()
        credential_info = secrets_manager.get_secret_value(secret_name=secret_name)

        return cls(
            auth_url=credential_info[secret_keys["auth_url_key"]],
            username=credential_info[secret_keys["username_key"]],
            password=credential_info[secret_keys["password_key"]],
            client_id=credential_info[secret_keys["client_id_key"]],
            client_secret=credential_info[secret_keys["client_secret_key"]],
            api_version=api_version,
            grant_type=grant_type,
        )

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
            self.request_headers["Authorization"] = f"OAuth {self._access_token}"

    def get_salesforce_object_names(self) -> List[str]:
        """
        Return the sobjects in the organization.

        Return
        ------
        List[str]
            List of names of the Salesforce object in the organization.

        """
        if not self._salesforce_object_names_cache:
            self._validate_salesforce_object = False

            # GET request to /sobjects returns a list with the valid objects.
            response = self.do_request(method="GET", path="sobjects")

            self._salesforce_object_names_cache = [
                sobject["name"] for sobject in json.loads(response)["sobjects"]
            ]

        return self._salesforce_object_names_cache

    def get_salesforce_object_fields(self, salesforce_object_name: str) -> List[str]:
        """
        Return the arguments that an sobject has.

        Parameters
        ----------
        salesforce_object_name : str, optional
            A Salesforce object.

        Return
        ------
        List[str]
            List of all the fields that a Salesforce object has.

        """
        if salesforce_object_name not in self._salesforce_object_fields_cache:
            self._validate_salesforce_object = False
            response = self.do_request(
                method="GET", path=f"sobjects/{salesforce_object_name}/describe"
            )

            self._salesforce_object_fields_cache[salesforce_object_name] = [
                fields["name"] for fields in json.loads(response)["fields"]
            ]

            # Update also the required fields to save a call to the API.
            self._salesforce_object_required_fields_cache[salesforce_object_name] = [
                fields["name"]
                for fields in json.loads(response)["fields"]
                if not fields["nillable"]
                and not fields["defaultedOnCreate"]
                and fields["createable"]
            ]

        return self._salesforce_object_fields_cache[salesforce_object_name]

    def get_salesforce_object_required_fields(self, salesforce_object_name: str) -> List[str]:
        """
        Return the mandatory arguments that an sobject needs to be created.

        Parameters
        ----------
        salesforce_object_name : str, optional
            A Salesforce object.

        Return
        ------
        List[str]
            List of the required fields that a Salesforce object needs to be created.

        Notes
        -----
        Salesforce has not made a definition of what should be `required`. However, we have found
        that some records of objects need specific fields to be given when they are created. We have
        observed that fields are `required` when they cannot be null and their value can only be
        assigned manually by the user.
        For more information about sobject fields: [1]

        References
        ----------
        [1] :
        https://developer.salesforce.com/docs/atlas.en-us.api.meta/api/sforce_api_objects_list.htm

        """
        if salesforce_object_name not in self._salesforce_object_required_fields_cache:
            self._validate_salesforce_object = False
            response = self.do_request(
                method="GET", path=f"sobjects/{salesforce_object_name}/describe"
            )

            # A required field cannot be null, its value will not be assigned automatically by
            # Salesforce when the record is created, and its value can be assigned by the user.
            self._salesforce_object_required_fields_cache[salesforce_object_name] = [
                fields["name"]
                for fields in json.loads(response)["fields"]
                if not fields["nillable"]
                and not fields["defaultedOnCreate"]
                and fields["createable"]
            ]

        return self._salesforce_object_required_fields_cache[salesforce_object_name]

    def _obtain_salesforce_object_name_from_path(self, path: str) -> str:
        # Extract Salesforce_object_name taking into account that we'll find something like...
        if "describe" in path:
            # ...sobjects/Account/describe
            salesforce_object_name = path.split("/")[1]

        elif "query?q=" in path:
            # ...query?q=SELECT+one+or+more+fields+FROM+an+object+WHERE+filter+statements
            query_start_pos = path.find("query?q=") + len("query?q=")
            query = path[query_start_pos:]

            if "WHERE" in query.upper():
                pattern = "FROM\+(.*)\+WHERE"
            else:
                pattern = "FROM\+(.*)"

            matches = re.search(pattern, query, re.IGNORECASE)
            if matches:
                salesforce_object_name = matches.group(1)
            else:
                salesforce_object_name = ""

        elif "query/" in path:
            # ...query/identifier to get the next rows of a SOQL.
            salesforce_object_name = ""

        elif path == "sobjects" or path == "limits":
            salesforce_object_name = ""

        else:
            # ...sobjects/Account or ...sobjects/Account/ID
            salesforce_object_name = path.split("/")[path.index("sobjects") + 1]

        return salesforce_object_name

    def _validate_payload_fields(self, payload: Dict[str, str], object_fields: List[str]) -> None:
        for field in payload:
            if field not in object_fields:
                raise SalesforceObjectFieldError(f"`{field}` isn't a valid field.")

    def _validate_required_fields_in_payload(
        self, payload: Dict[str, str], object_required_fields: List[str]
    ) -> None:
        for field in object_required_fields:
            if field not in payload:
                raise SalesforceObjectFieldError(
                    f"`{field}` is a required field and does not appear in the payload."
                )
            else:
                if not payload[field]:
                    raise SalesforceObjectFieldError(
                        f"`{field}` is a required field and must not be empty."
                    )

    @staticmethod
    def _soql_response_to_dataframe(
        response: List[dict],
        column_mapping: Dict[str, str] = None,
        drop_columns_containing: str = None,
    ) -> pd.DataFrame:

        df = pd.json_normalize(data=response)

        if column_mapping:
            df.rename(columns=column_mapping, errors="raise", inplace=True)

        if drop_columns_containing:
            df.drop(
                columns=[column for column in df.columns if drop_columns_containing in column],
                axis=1,
                inplace=True,
            )

        return df

    def do_request(self, method: str, path: str, payload: Optional[Dict[str, str]] = None) -> str:
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
        SalesforceObjectFieldError
            If any field in the payload is invalid, any required field is empty or missing.

        SalesforceObjectError
            If the object in the query is not a valid Salesforce object.

        RequestMethodError
            If the method is not supported, or the payload is missing when needed.

        requests.exceptions.RequestException
            If the connection with Salesforce fails, e.g. the requesting resource does not exist.

        """
        if method not in ["POST", "GET", "PATCH", "DELETE"]:
            raise RequestMethodError("Method isn't supported.")

        if not self._is_authenticated:
            self._authenticate()

        if self._validate_salesforce_object:
            path_salesforce_object = self._obtain_salesforce_object_name_from_path(path)
            if path_salesforce_object:
                # SOQL is case insensitive, thus comparing in uppercase is fine.
                if path_salesforce_object.upper() not in (
                    object_name.upper() for object_name in self.get_salesforce_object_names()
                ):
                    raise SalesforceObjectError(f"{path_salesforce_object} isn't a valid object")

        url = self._url_to_format.format(
            self._instance_scheme_and_authority, self._api_version, path
        )

        try:
            if method in ["POST", "PATCH"]:
                if not payload:
                    raise RequestMethodError("Payload must be defined for a POST, PATCH request.")

                if self._validate_salesforce_object:
                    object_fields = self.get_salesforce_object_fields(path_salesforce_object)
                    self._validate_payload_fields(payload=payload, object_fields=object_fields)
                    if method == "POST":
                        object_required_fields = self.get_salesforce_object_required_fields(
                            path_salesforce_object
                        )
                        self._validate_required_fields_in_payload(
                            payload=payload,
                            object_required_fields=object_required_fields,
                        )

                # We use reflection to choose which method (POST or PATCH) to execute.
                response = getattr(requests, method.lower())(
                    url=url, json=payload, headers=self.request_headers
                )
            else:  # method == "GET" or method == "DELETE":
                response = getattr(requests, method.lower())(url=url, headers=self.request_headers)

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
        self,
        query: str,
        column_mapping: Dict[str, str] = None,
        drop_columns_containing: str = "attributes",
        drop_empty_columns: bool = False,
    ) -> pd.DataFrame:
        """
        Constructs and sends a request using SOQL.

        Use the Salesforce Object Query Language (SOQL) to search Salesforce data for specific
        information. Once the query is done, the response is flattened and transformed into a pandas
        DataFrame.

        Parameters
        ----------
        query : str
            SOQL with the desired query.

        column_mapping: Dict[str, str], Optional
            Dictionary containing the names of the columns to map, being the key the Salesforce
            Object field name and the value the name of the dataframe. If not given, the Salesforce
            Object field name will be set as column name in the dataframe by default.

        drop_columns_containing: str, Optional
            Columns containing this string will be dropped. By default we drop columns containing
            `attributes`, because SOQL response contains additional `attributes` fields when the
            query contains a selection of a field through relationship.

        drop_empty_columns: bool, Optional
            Columns that do not contain any value will be removed. Set to false by default.

        Returns
        -------
        pd.DataFrame
            A dataframe containing the results of the query.

        Raises
        ------
        requests.exceptions.RequestException
            If the request fails, e.g. the requesting attribute does not exist for the Salesforce
            object class.

        See Also
        --------
        do_request : this method does a request of type GET.

        Notes
        -----
        Use this method when you know which objects the data resides in, and you want to
        retrieve data from a single Salesforce object or from multiple objects that are related.

        The maximum number of records that a single SOQL request can return is 2000, when this limit
        is exceeded, the field `nextRecordsUrl` from the response of the query is used, this method
        already manages this problem, hence all the records of the query will be returned.

        Salesforce object relationships stands for associations between different Salesforce
        objects, when objects are related, their fields can be accessed directly in the SOQL query.

        This method calls the private method _soql_response_to_dataframe. The response JSON object
        is flattened using the Pandas json_normalize method.

        For more information related to SOQL: [1]
        For a complete description of the SOQL syntax: [2]
        For more information about the SOQL requests URIs: [3]
        For more information about the limits of the SOQL requests: [4]
        For more information about Salesforce objects relationships: [5]
        For more information about the json_normalize method: [6]

        References
        ----------
        [1] :
        https://developer.salesforce.com/docs/atlas.en-us.soql_sosl.meta/soql_sosl/sforce_api_calls_soql.htm

        [2] :
        https://developer.salesforce.com/docs/atlas.en-us.soql_sosl.meta/soql_sosl/sforce_api_calls_soql_select.htm

        [3] :
        https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/resources_query.htm

        [4] :
        https://developer.salesforce.com/docs/atlas.en-us.salesforce_app_limits_cheatsheet.meta/salesforce_app_limits_cheatsheet/salesforce_app_limits_platform_soslsoql.htm

        [5] :
        https://developer.salesforce.com/docs/atlas.en-us.api.meta/api/relationships_among_objects.htm

        [6] :
        https://pandas.pydata.org/docs/reference/api/pandas.json_normalize.html

        """
        # Encode the query to clean possible special characters to fit in the url.
        encoded_query = parse.quote_plus(query)
        query = parse.unquote(encoded_query)
        response = self.do_request(method="GET", path=f"query?q={query}")
        response_dict = json.loads(response)
        records = response_dict["records"]

        # Salesforce returns records in batches. Here we collect all the batches.
        while "nextRecordsUrl" in response_dict:
            next_url = response_dict["nextRecordsUrl"]
            # The nextRecordsUrl field has the form .../query/query_identifier
            query_identifier = next_url.split("/")[-1]
            response = self.do_request(method="GET", path=f"query/{query_identifier}")
            response_dict = json.loads(response)
            records.extend(response_dict["records"])

        df = self._soql_response_to_dataframe(
            response=records,
            column_mapping=column_mapping,
            drop_columns_containing=drop_columns_containing,
        )

        if drop_empty_columns:
            df.dropna(axis=1, how="all", inplace=True)

        return df

    def insert_record(self, sobject: str, payload: Dict[str, str]) -> str:
        """
        Create a new instance of a Salesforce object.

        Create a new record of type `sobject` with the information in the payload.

        Parameters
        ----------
        sobject : str
            A Salesforce object.
        payload : Dict[str, str]
            Payload that contains information to create the record.

        Returns
        -------
        str
            Response from Salesforce. This is a JSON encoded as text.

        See Also
        --------
        do_request : this method does a request of type POST.

        """
        return self.do_request(method="POST", path=f"sobjects/{sobject}", payload=payload)

    def modify_record(self, sobject: str, record_id: str, payload: Dict[str, str]) -> str:
        """
        Update an instance of a Salesforce object.

        Modify a record of type `sobject` with id `record_id` using the new
        information in the `payload`.

        Parameters
        ----------
        sobject : str
            A Salesforce object.
        record_id : str
            The record identifier.
        payload : Dict[str, str]
            Payload that contains information to update the record.
        Returns
        -------
        str
            Response from Salesforce. This is a JSON encoded as text.

        requests.exceptions.RequestException
            If the connection with Salesforce fails, e.g. the record does not exist.

        See Also
        --------
        do_request : this method does a request of type PATCH.

        """
        return self.do_request(
            method="PATCH",
            path=f"sobjects/{sobject}/{record_id}",
            payload=payload,
        )

    def delete_record(self, sobject: str, record_id: str) -> str:
        """
        Remove an instance of a Salesforce object.

        Delete a record of type `sobject` with id `record_id`.

        Parameters
        ----------
        sobject : str
            A Salesforce object.
        record_id : str
            The identification of the record.
        Returns
        -------
        str
            Response from Salesforce. This is a JSON encoded as text.

        requests.exceptions.RequestException
            If the connection with Salesforce fails, e.g. the record does not exist.

        See Also
        --------
        do_request : this method does a request of type DELETE.

        """
        return self.do_request(method="DELETE", path=f"sobjects/{sobject}/{record_id}")

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
        For more information about the Salesforce organization limits: [1]

        References
        ----------
        [1] :
        https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/dome_limits.htm

        """
        response = self.do_request(method="GET", path="limits")
        return int(json.loads(response)["DailyApiRequests"]["Remaining"])
