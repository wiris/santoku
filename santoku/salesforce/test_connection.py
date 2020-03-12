import os
import requests
import pytest
from ..salesforce.connection import SalesforceConnection

URL_AUTH = "https://test.salesforce.com/services/oauth2/token"


class TestConnect:
    @classmethod
    def setup_class(self):

        self.sc = SalesforceConnection(
            auth_url=URL_AUTH,
            username=os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_USR"],
            password=os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_PWD"],
            client_id=os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_CLIENT_USR"],
            client_secret=os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_CLIENT_PWD"],
        )

        # print(sc.do_query_with_SOQL(query="SELECT Name, Id from Account"))

    def test_wrong_credentials(self):
        sc = SalesforceConnection(
            auth_url=URL_AUTH,
            username="wrong_user",
            password="wrong_password",
            client_id="wrong_client_id",
            client_secret="wrong_client_secret",
        )
        with pytest.raises(requests.exceptions.RequestException) as e:
            sc.do_request(
                method="POST", path="sobjects/Account", payload={"Name": "Alice Bob"}
            )

    def test_account_insertion(self):
        sc = SalesforceConnection(
            auth_url=URL_AUTH,
            username=os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_USR"],
            password=os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_PWD"],
            client_id=os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_CLIENT_USR"],
            client_secret=os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_CLIENT_PWD"],
        )

        # Insert 3 Accounts that doesn't exist [OK]
        response = sc.do_request(
            method="POST",
            path="objects/Account",
            payload={"Name": "Randall D. Youngblood"},
        )
        print(response)
        # sc.do_request(
        #     method="POST",
        #     path="objects/Account",
        #     payload={"Name": "Amani Cantara Fakhoury"},
        # )
        # sc.do_request(
        #     method="POST", path="objects/Account", payload={"Name": "Emmi Hyytiä"}
        # )

        # # Insert 1 Account that exists [NO]
        # with pytest.raises(requests.exceptions.RequestException) as e:
        #     sc.do_request(
        #         method="POST", path="objects/Account", payload={"Name": "Emmi Hyytiä"}
        #     )

        # # Query using sobjects/SOQL a previously inserted Account [OK]

        # # Query using sobjects/SOQL an Account that doesn't exists [NO]
        # with pytest.raises(requests.exceptions.RequestException) as e:
        #     sc.do_request(
        #         method="GET", path="objects/Account", payload={"Name": "Emmi Hyytiä"}
        #     )

        # Modify an existing Account [OK]
        # Modify an Account that doesn't exists [NO]
        # Delete existing Account [OK]
        # Delete an Account that doesn't exist [NO]
        # Query using sobjects/SOQL Account object [NO]

    def test_something(self):
        # Test POST method.
        response = self.sc.do_request(
            method="POST", path="sobjects/Account", payload={"Name": "Alice Bob"}
        )
        print("afsasf {}".format(response))
