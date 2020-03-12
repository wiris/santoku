import os
import requests
import pytest
import json
from ..salesforce.connection import SalesforceConnection


class TestConnect:
    # @classmethod
    # def setup_class(self):

    #     self.sc = SalesforceConnection(
    #         auth_url=URL_AUTH,
    #         username=os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_USR"],
    #         password=os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_PWD"],
    #         client_id=os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_CLIENT_USR"],
    #         client_secret=os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_CLIENT_PWD"],
    #     )

    # print(sc.do_query_with_SOQL(query="SELECT Name, Id from Account"))

    # def test_wrong_credentials(self):
    #     sc = SalesforceConnection(
    #         auth_url=URL_AUTH,
    #         username="wrong_user",
    #         password="wrong_password",
    #         client_id="wrong_client_id",
    #         client_secret="wrong_client_secret",
    #     )
    #     with pytest.raises(requests.exceptions.RequestException) as e:
    #         sc.do_request(
    #             method="POST", path="sobjects/Account", payload={"Name": "Alice Bob"}
    #         )

    def test_contact_insertion(self):
        sc = SalesforceConnection(
            auth_url=os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_AUTH_URL"],
            username=os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_USR"],
            password=os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_PWD"],
            client_id=os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_CLIENT_USR"],
            client_secret=os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_CLIENT_PWD"],
        )

        inserted_ids = []
        contact_payloads = [
            {
                "FirstName": "Randall D.",
                "LastName": "Youngblood",
                "Email": "randall@example.com",
            },
            {
                "FirstName": "Amani Cantara",
                "LastName": "Fakhoury",
                "Email": "amani@example.com",
            },
            {
                "FirstName": "Mika-Matti",
                "LastName": "Ridanpää",
                "Email": "mika-matti.ridanpaa@example.com",
            },
        ]

        # Insert 3 Contact that doesn't exist [OK]
        for contact_payload in contact_payloads:
            response = sc.do_request(
                method="POST", path="sobjects/Contact", payload=contact_payload
            )
            assert response
            inserted_ids.append(json.loads(response)["id"])

        # Insert 1 Contact that exists [NO]
        with pytest.raises(requests.exceptions.RequestException) as e:
            response = sc.do_request(
                method="POST", path="sobjects/Contact", payload=contact_payloads[0]
            )

        # Query by Id using sobjects/SOQL a previously inserted Contact [OK]

        # Query by LastName using SOQL a previously inserted Contact [OK]
        response = sc.do_query_with_SOQL(
            query="SELECT Email, Name FROM Contact WHERE LastName = 'Ridanpää'"
        )

        assert response
        print(response)

        # Query by Id using sobjects/SOQL a Contact that doesn't exists [NO]
        # Query by LastName using SOQL a Contact that doesn't exists [NO]
        # Modify an existing Contact [OK]
        # Modify an Contact that doesn't exists [NO]
        # Delete existing Contact [OK]
        # Delete an Contact that doesn't exist [NO]
        # Query using sobjects/SOQL Contact object [NO]
