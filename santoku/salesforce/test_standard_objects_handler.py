import os
import requests
import pytest
import json
from ..salesforce.standard_objects_handler import StandardObjectsHandler
from typing import List, Dict, Any

SANDBOX_AUTH_URL = os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_AUTH_URL"]
SANDBOX_USR = os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_USR"]
SANDBOX_PSW = os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_PSW"]
SANDBOX_CLIENT_USR = os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_CLIENT_USR"]
SANDBOX_CLIENT_PSW = os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_CLIENT_PSW"]


def delete_records(sc: StandardObjectsHandler, sobject: str):
    response = json.loads(
        sc.do_query_with_SOQL("SELECT Id, Name from {}".format(sobject))
    )
    obtained_contacts = response["records"]

    for obtained_contact in obtained_contacts:
        sc.do_request(
            method="DELETE", path="sobjects/Contact/{}".format(obtained_contact["Id"]),
        )


class TestStandardObjectsHandler:
    def teardown_method(cls):
        # Clean the sandbox each time a testcase is executed.
        sc = StandardObjectsHandler(
            auth_url=SANDBOX_AUTH_URL,
            username=SANDBOX_USR,
            password=SANDBOX_PSW,
            client_id=SANDBOX_CLIENT_USR,
            client_secret=SANDBOX_CLIENT_PSW,
        )
        delete_records(sc=sc, sobject="Contact")

    def test_wrong_credentials(self):
        # Connect Salesforce with wrong credentials. Failure expected.
        sc = StandardObjectsHandler(
            auth_url=SANDBOX_AUTH_URL,
            username=SANDBOX_USR,
            password=SANDBOX_PSW,
            client_id=SANDBOX_CLIENT_USR,
            client_secret=SANDBOX_CLIENT_PSW,
        )
        with pytest.raises(requests.exceptions.RequestException) as e:
            sc.do_request(
                method="POST",
                path="sobjects/Contact",
                payload={"Name": "Janie Goodman"},
            )

    def test_contact_insertion(self):
        sc = StandardObjectsHandler(
            auth_url=SANDBOX_AUTH_URL,
            username=SANDBOX_USR,
            password=SANDBOX_PSW,
            client_id=SANDBOX_CLIENT_USR,
            client_secret=SANDBOX_CLIENT_PSW,
        )

        # Insert 3 Contacts that do not exist. Success expected.
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

        for contact_payload in contact_payloads:
            response = sc.do_request(
                method="POST", path="sobjects/Contact", payload=contact_payload
            )
            assert response

        # Insert a Contact that already exist with a new email. Success expected.
        contact_payloads[0]["Email"] = "youngblood@example.com"
        response = sc.do_request(
            method="POST", path="sobjects/Contact", payload=contact_payloads[0],
        )
        assert response

        # Insert a Contact that already exist. Failure expected.
        with pytest.raises(requests.exceptions.RequestException) as e:
            response = sc.do_request(
                method="POST", path="sobjects/Contact", payload=contact_payloads[0],
            )
            assert response

    def test_contact_query(self):
        sc = StandardObjectsHandler(
            auth_url=SANDBOX_AUTH_URL,
            username=SANDBOX_USR,
            password=SANDBOX_PSW,
            client_id=SANDBOX_CLIENT_USR,
            client_secret=SANDBOX_CLIENT_PSW,
        )

        # Read 0 Contacts with SOQL.
        response = json.loads(sc.do_query_with_SOQL("SELECT Name from Contact"))
        assert response["totalSize"] == 0

        # Insert 2 Contacts.
        contact_payloads = [
            {
                "FirstName": "Angel",
                "LastName": "Collins",
                "Email": "angel@example.com",
            },
            {"FirstName": "June", "LastName": "Ross", "Email": "june@example.com",},
        ]

        for contact_payload in contact_payloads:
            sc.do_request(
                method="POST", path="sobjects/Contact", payload=contact_payload
            )

        # Read the 2 Contacts inserted with SOQL. Success expected.
        expected_names = ["Angel Collins", "June Ross"]
        response = json.loads(sc.do_query_with_SOQL("SELECT Id, Name from Contact"))
        assert response["totalSize"] == 2

        obtained_contacts = response["records"]
        obtained_names = []

        obtained_ids = []
        for obtained_contact in obtained_contacts:
            obtained_names.append(obtained_contact["Name"])
            obtained_ids.append(obtained_contact["Id"])

        for expected_name in expected_names:
            assert expected_name in obtained_names

        # Read a specific contact with SOQL by Id. Success expected.
        response = json.loads(
            sc.do_query_with_SOQL(
                "SELECT Id, Name from contact WHERE Id = '{}'".format(obtained_ids[0])
            )
        )
        assert response["totalSize"] == 1

        obtained_contacts = response["records"]
        assert obtained_contacts[0]["Name"] == obtained_names[0]

        # Read a specific contact with SOQL by Name. Success expected.
        response = json.loads(
            sc.do_query_with_SOQL(
                "SELECT Name from contact WHERE Name = '{}'".format(obtained_names[0])
            )
        )
        assert response["totalSize"] == 1

        obtained_contacts = response["records"]
        assert obtained_contacts[0]["Name"] == obtained_names[0]

        # Query a contact that does not exists with SOQL. Success expected.
        response = json.loads(
            sc.do_query_with_SOQL(
                "SELECT Name from contact WHERE Name = 'Nick Mullins'"
            )
        )
        assert response["totalSize"] == 0

    def test_contact_modification(self):
        sc = StandardObjectsHandler(
            auth_url=SANDBOX_AUTH_URL,
            username=SANDBOX_USR,
            password=SANDBOX_PSW,
            client_id=SANDBOX_CLIENT_USR,
            client_secret=SANDBOX_CLIENT_PSW,
        )

        # Insert 2 Contacts.
        contact_payloads = [
            {"FirstName": "Ramon", "LastName": "Evans", "Email": "ramon@example.com",},
            {"FirstName": "Janis", "LastName": "Holmes", "Email": "janis@example.com",},
        ]

        for contact_payload in contact_payloads:
            response = sc.do_request(
                method="POST", path="sobjects/Contact", payload=contact_payload
            )

        # Modify an existing contact's FirstName and LastName. Success expected.
        response = json.loads(
            sc.do_query_with_SOQL(
                "SELECT Id, Name from Contact WHERE Name = 'Ramon Evans'"
            )
        )
        obtained_contacts = response["records"]
        contact_payload = {"FirstName": "Ken", "LastName": "Williams"}

        sc.do_request(
            method="PATCH",
            path="sobjects/Contact/{}".format(obtained_contacts[0]["Id"]),
            payload=contact_payload,
        )

        response = json.loads(
            sc.do_query_with_SOQL(
                "SELECT Id, Name from Contact WHERE Id = '{}'".format(
                    obtained_contacts[0]["Id"]
                )
            )
        )
        obtained_contacts = response["records"]
        expected_contact_name = "{} {}".format(
            contact_payload["FirstName"], contact_payload["LastName"]
        )
        assert obtained_contacts[0]["Name"] == expected_contact_name

        # Modify an existing contact's Email. Success expected.
        contact_payload = {"Email": "ken@example.com"}

        sc.do_request(
            method="PATCH",
            path="sobjects/Contact/{}".format(obtained_contacts[0]["Id"]),
            payload=contact_payload,
        )

        response = json.loads(
            sc.do_query_with_SOQL(
                "SELECT Id, Name, Email from Contact WHERE Id = '{}'".format(
                    obtained_contacts[0]["Id"]
                )
            )
        )
        obtained_contacts = response["records"]
        assert obtained_contacts[0]["Name"] == expected_contact_name
        assert obtained_contacts[0]["Email"] == contact_payload["Email"]

        # Modify a Contact that does not exist. Failure expected.
        contact_payload = {"FirstName": "Marie"}
        with pytest.raises(requests.exceptions.RequestException) as e:
            response = sc.do_request(
                method="PATCH",
                path="sobjects/Contact/{}".format("WRONGID"),
                payload=contact_payload,
            )

    def test_contact_deletion(self):
        sc = StandardObjectsHandler(
            auth_url=SANDBOX_AUTH_URL,
            username=SANDBOX_USR,
            password=SANDBOX_PSW,
            client_id=SANDBOX_CLIENT_USR,
            client_secret=SANDBOX_CLIENT_PSW,
        )

        # Insert 2 Contacts.
        contact_payloads = [
            {
                "FirstName": "Brian",
                "LastName": "Cunningham",
                "Email": "brian@example.com",
            },
            {
                "FirstName": "Julius",
                "LastName": "Marsh",
                "Email": "julius@example.com",
            },
        ]

        for contact_payload in contact_payloads:
            response = sc.do_request(
                method="POST", path="sobjects/Contact", payload=contact_payload
            )

        # Delete an existing Contact. Success expected.
        response = json.loads(sc.do_query_with_SOQL("SELECT Id, Name from Contact"))
        obtained_contacts = response["records"]
        obtained_contacts_names = []
        obtained_contacts_ids = []

        for obtained_contact in obtained_contacts:
            obtained_contacts_names.append(obtained_contact["Name"])
            obtained_contacts_ids.append(obtained_contact["Id"])

        sc.do_request(
            method="DELETE",
            path="sobjects/Contact/{}".format(obtained_contacts_ids[0]),
        )

        response = json.loads(
            sc.do_query_with_SOQL(
                "SELECT Name from Contact WHERE Name = '{}'".format(
                    obtained_contacts_names[0]
                )
            )
        )
        assert response["totalSize"] == 0

        response = json.loads(
            sc.do_query_with_SOQL(
                "SELECT Name from contact WHERE Name = '{}'".format(
                    obtained_contacts_names[1]
                )
            )
        )
        assert response["totalSize"] == 1

        # Delete a Contact that does not exist. Failure expected.
        with pytest.raises(requests.exceptions.RequestException) as e:
            sc.do_request(
                method="DELETE",
                path="sobjects/Contact/{}".format(obtained_contacts_ids[0]),
            )
