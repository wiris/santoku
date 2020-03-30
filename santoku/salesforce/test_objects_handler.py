import os
import requests
import pytest
import json
from ..salesforce.objects_handler import ObjectsHandler
from typing import List, Dict, Any

SANDBOX_AUTH_URL = os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_AUTH_URL"]
SANDBOX_USR = os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_USR"]
SANDBOX_PSW = os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_PSW"]
SANDBOX_CLIENT_USR = os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_CLIENT_USR"]
SANDBOX_CLIENT_PSW = os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_CLIENT_PSW"]


def delete_records(oh: ObjectsHandler, sobject: str):
    obtained_sobjects = oh.do_query_with_SOQL("SELECT Id, Name from {}".format(sobject))

    for obtained_sobject in obtained_sobjects:
        oh.do_request(
            method="DELETE",
            path="sobjects/{}/{}".format(sobject, obtained_sobject["Id"]),
        )


class TestObjectsHandler:
    def setup_method(self):
        # Clean the sobject records in the sandbox before a testcase is executed.
        oh = ObjectsHandler(
            auth_url=SANDBOX_AUTH_URL,
            username=SANDBOX_USR,
            password=SANDBOX_PSW,
            client_id=SANDBOX_CLIENT_USR,
            client_secret=SANDBOX_CLIENT_PSW,
        )
        sobjects_to_clear = ["Contact"]
        for sobject in sobjects_to_clear:
            delete_records(oh=oh, sobject=sobject)

    def test_wrong_credentials(self):
        contact_payloads = [
            {
                "FirstName": "Janie",
                "LastName": "Goodman",
                "Email": "janie@example.com",
            },
        ]

        # Connect Salesforce with wrong credentials. Failure expected.
        oh = ObjectsHandler(
            auth_url=SANDBOX_AUTH_URL,
            username="false_username",
            password="false_password",
            client_id=SANDBOX_CLIENT_USR,
            client_secret=SANDBOX_CLIENT_PSW,
        )
        with pytest.raises(requests.exceptions.RequestException) as e:
            oh.do_request(
                method="POST", path="sobjects/Contact", payload=contact_payloads[0],
            )

        oh = ObjectsHandler(
            auth_url=SANDBOX_AUTH_URL,
            username=SANDBOX_USR,
            password=SANDBOX_PSW,
            client_id="false_client_id",
            client_secret="false_client_secret",
        )
        with pytest.raises(requests.exceptions.RequestException) as e:
            oh.do_request(
                method="POST", path="sobjects/Contact", payload=contact_payloads[0],
            )

    def test_contact_insertion(self):
        oh = ObjectsHandler(
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
            response = oh.do_request(
                method="POST", path="sobjects/Contact", payload=contact_payload
            )
            assert response

        # Insert a Contact that already exist with a new email. Success expected.
        contact_payloads[0]["Email"] = "youngblood@example.com"
        response = oh.do_request(
            method="POST", path="sobjects/Contact", payload=contact_payloads[0],
        )
        assert response

        # Insert a Contact that already exist. Failure expected.
        with pytest.raises(requests.exceptions.RequestException) as e:
            response = oh.do_request(
                method="POST", path="sobjects/Contact", payload=contact_payloads[0],
            )
            assert response

    def test_contact_query(self):
        oh = ObjectsHandler(
            auth_url=SANDBOX_AUTH_URL,
            username=SANDBOX_USR,
            password=SANDBOX_PSW,
            client_id=SANDBOX_CLIENT_USR,
            client_secret=SANDBOX_CLIENT_PSW,
        )

        # Read 0 Contacts with SOQL.
        obtained_contacts = oh.do_query_with_SOQL("SELECT Name from Contact")
        assert len(obtained_contacts) == 0

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
            oh.do_request(
                method="POST", path="sobjects/Contact", payload=contact_payload
            )

        # Read the 2 Contacts inserted with SOQL. Success expected.
        expected_names = [
            "{} {}".format(
                contact_payloads[0]["FirstName"], contact_payloads[0]["LastName"]
            ),
            "{} {}".format(
                contact_payloads[1]["FirstName"], contact_payloads[1]["LastName"]
            ),
        ]
        obtained_contacts = oh.do_query_with_SOQL("SELECT Id, Name from Contact")
        assert len(obtained_contacts) == 2

        obtained_names = []
        obtained_ids = []
        for obtained_contact in obtained_contacts:
            obtained_names.append(obtained_contact["Name"])
            obtained_ids.append(obtained_contact["Id"])

        for expected_name in expected_names:
            assert expected_name in obtained_names

        # Read a specific contact with SOQL by Id. Success expected.
        expected_id = obtained_ids[0]
        expected_name = obtained_names[0]
        obtained_contacts = oh.do_query_with_SOQL(
            "SELECT Id, Name from contact WHERE Id = '{}'".format(expected_id)
        )
        assert len(obtained_contacts) == 1
        assert obtained_contacts[0]["Name"] == expected_name

        # Read a specific contact with SOQL by Name. Success expected.
        obtained_contacts = oh.do_query_with_SOQL(
            "SELECT Name from contact WHERE Name = '{}'".format(expected_name)
        )
        assert len(obtained_contacts) == 1
        assert obtained_contacts[0]["Name"] == expected_name

        # Query a contact that does not exists with SOQL. Success expected.
        obtained_contacts = oh.do_query_with_SOQL(
            "SELECT Name from contact WHERE Name = 'Nick Mullins'"
        )
        assert len(obtained_contacts) == 0

    def test_contact_modification(self):
        oh = ObjectsHandler(
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
            response = oh.do_request(
                method="POST", path="sobjects/Contact", payload=contact_payload
            )

        # Modify an existing contact's FirstName and LastName. Success expected.
        obtained_contacts = oh.do_query_with_SOQL(
            "SELECT Id, Name from Contact WHERE Name = 'Ramon Evans'"
        )
        contact_payload = {"FirstName": "Ken", "LastName": "Williams"}

        oh.do_request(
            method="PATCH",
            path="sobjects/Contact/{}".format(obtained_contacts[0]["Id"]),
            payload=contact_payload,
        )

        obtained_contacts = oh.do_query_with_SOQL(
            "SELECT Id, Name from Contact WHERE Id = '{}'".format(
                obtained_contacts[0]["Id"]
            )
        )
        expected_contact_name = "{} {}".format(
            contact_payload["FirstName"], contact_payload["LastName"]
        )
        assert obtained_contacts[0]["Name"] == expected_contact_name

        # Modify an existing contact's Email. Success expected.
        contact_payload = {"Email": "ken@example.com"}

        oh.do_request(
            method="PATCH",
            path="sobjects/Contact/{}".format(obtained_contacts[0]["Id"]),
            payload=contact_payload,
        )

        obtained_contacts = oh.do_query_with_SOQL(
            "SELECT Id, Name, Email from Contact WHERE Id = '{}'".format(
                obtained_contacts[0]["Id"]
            )
        )
        assert obtained_contacts[0]["Name"] == expected_contact_name
        assert obtained_contacts[0]["Email"] == contact_payload["Email"]

        # Modify a Contact that does not exist. Failure expected.
        contact_payload = {"FirstName": "Marie"}
        with pytest.raises(requests.exceptions.RequestException) as e:
            response = oh.do_request(
                method="PATCH",
                path="sobjects/Contact/{}".format("WRONGID"),
                payload=contact_payload,
            )

    def test_contact_deletion(self):
        oh = ObjectsHandler(
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
            response = oh.do_request(
                method="POST", path="sobjects/Contact", payload=contact_payload
            )

        # Delete an existing Contact. Success expected.
        obtained_contacts = oh.do_query_with_SOQL("SELECT Id, Name from Contact")
        obtained_names = []
        obtained_ids = []

        for obtained_contact in obtained_contacts:
            obtained_names.append(obtained_contact["Name"])
            obtained_ids.append(obtained_contact["Id"])

        oh.do_request(
            method="DELETE", path="sobjects/Contact/{}".format(obtained_ids[0]),
        )

        obtained_contacts = oh.do_query_with_SOQL(
            "SELECT Name from Contact WHERE Name = '{}'".format(obtained_names[0])
        )
        assert len(obtained_contacts) == 0

        obtained_contacts = oh.do_query_with_SOQL(
            "SELECT Name from contact WHERE Name = '{}'".format(obtained_names[1])
        )
        assert len(obtained_contacts) == 1

        # Delete a Contact that does not exist. Failure expected.
        with pytest.raises(requests.exceptions.RequestException) as e:
            oh.do_request(
                method="DELETE", path="sobjects/Contact/{}".format(obtained_ids[0]),
            )

    def test_contact_insertion_high_level(self):
        oh = ObjectsHandler(
            auth_url=SANDBOX_AUTH_URL,
            username=SANDBOX_USR,
            password=SANDBOX_PSW,
            client_id=SANDBOX_CLIENT_USR,
            client_secret=SANDBOX_CLIENT_PSW,
        )

        # Insert 3 Contacts that do not exist. Success expected.
        contact_payloads = [
            {"FirstName": "Kim", "LastName": "George", "Email": "kim@example.com",},
            {
                "FirstName": "Wilfred",
                "LastName": "Craig",
                "Email": "wilfred@example.com",
            },
            {
                "FirstName": "Whitney",
                "LastName": "Ross",
                "Email": "whitney@example.com",
            },
        ]

        for contact_payload in contact_payloads:
            response = oh.insert_object(
                salesforce_object_name="Contact", payload=contact_payload
            )
            assert response

        # Insert a Contact that already exist with a new email. Success expected.
        contact_payloads[0]["Email"] = "rodriguez@example.com"
        response = oh.insert_object(
            salesforce_object_name="Contact", payload=contact_payloads[0]
        )
        assert response

        # Insert a Contact that already exist. Failure expected.
        with pytest.raises(requests.exceptions.RequestException) as e:
            response = oh.insert_object(
                salesforce_object_name="Contact", payload=contact_payload
            )
            assert response

    def test_contact_modification_high_level(self):
        oh = ObjectsHandler(
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
            response = oh.do_request(
                method="POST", path="sobjects/Contact", payload=contact_payload
            )

        # Modify an existing contact's FirstName and LastName. Success expected.
        obtained_contacts = oh.do_query_with_SOQL(
            "SELECT Id, Name from Contact WHERE Name = 'Ramon Evans'"
        )
        contact_payload = {"FirstName": "Ken", "LastName": "Williams"}

        expected_contact_id = obtained_contacts[0]["Id"]
        oh.modify_object(
            salesforce_object_name="Contact",
            record_id=expected_contact_id,
            payload=contact_payload,
        )

        obtained_contacts = oh.do_query_with_SOQL(
            "SELECT Id, Name from Contact WHERE Id = '{}'".format(expected_contact_id)
        )
        expected_contact_name = "{} {}".format(
            contact_payload["FirstName"], contact_payload["LastName"]
        )
        assert obtained_contacts[0]["Name"] == expected_contact_name

        # Modify an existing contact's Email. Success expected.
        contact_payload = {"Email": "ken@example.com"}

        oh.modify_object(
            salesforce_object_name="Contact",
            record_id=expected_contact_id,
            payload=contact_payload,
        )

        obtained_contacts = oh.do_query_with_SOQL(
            "SELECT Id, Name, Email from Contact WHERE Id = '{}'".format(
                expected_contact_id
            )
        )
        assert obtained_contacts[0]["Name"] == expected_contact_name
        assert obtained_contacts[0]["Email"] == contact_payload["Email"]

        # Modify a Contact that does not exist. Failure expected.
        contact_payload = {"FirstName": "Marie"}
        with pytest.raises(requests.exceptions.RequestException) as e:
            oh.modify_object(
                salesforce_object_name="Contact",
                record_id="WRONGID",
                payload=contact_payload,
            )

    def test_contact_deletion_high_level(self):
        oh = ObjectsHandler(
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
            response = oh.do_request(
                method="POST", path="sobjects/Contact", payload=contact_payload
            )

        # Delete an existing Contact. Success expected.
        obtained_contacts = oh.do_query_with_SOQL("SELECT Id, Name from Contact")
        obtained_names = []
        obtained_ids = []

        for obtained_contact in obtained_contacts:
            obtained_names.append(obtained_contact["Name"])
            obtained_ids.append(obtained_contact["Id"])

        oh.delete_object(salesforce_object_name="Contact", record_id=obtained_ids[0])

        obtained_contacts = oh.do_query_with_SOQL(
            "SELECT Name from Contact WHERE Name = '{}'".format(obtained_names[0])
        )
        assert len(obtained_contacts) == 0

        obtained_contacts = oh.do_query_with_SOQL(
            "SELECT Name from contact WHERE Name = '{}'".format(obtained_names[1])
        )
        assert len(obtained_contacts) == 1

        # Delete a Contact that does not exist. Failure expected.
        with pytest.raises(requests.exceptions.RequestException) as e:
            oh.do_request(
                method="DELETE", path="sobjects/Contact/{}".format(obtained_ids[0]),
            )
