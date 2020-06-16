import os
import requests
import pytest
import json

from moto import mock_secretsmanager
from ..salesforce.objects_handler import ObjectsHandler
from ..salesforce.objects_handler import SalesforceObjectError
from ..salesforce.objects_handler import SalesforceObjectFieldError
from ..salesforce.objects_handler import RequestMethodError
from ..aws import SecretsManagerHandler

SANDBOX_AUTH_URL = os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_AUTH_URL"]
SANDBOX_USR = os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_USR"]
SANDBOX_PSW = os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_PSW"]
SANDBOX_CLIENT_USR = os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_CLIENT_USR"]
SANDBOX_CLIENT_PSW = os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_CLIENT_PSW"]


@pytest.fixture(scope="class")
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "eu-west-1"


@pytest.fixture(scope="class")
def secrets_manager(aws_credentials):
    with mock_secretsmanager():
        secrets_manager = SecretsManagerHandler()
        yield secrets_manager


@pytest.fixture(scope="function")
def secret_with_default_keys(secrets_manager, request):
    secret_name = "test/secret_with_default_keys"
    secret_content = {
        "AUTH_URL": os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_AUTH_URL"],
        "USR": os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_USR"],
        "PSW": os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_PSW"],
        "CLIENT_USR": os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_CLIENT_USR"],
        "CLIENT_PSW": os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_CLIENT_PSW"],
    }
    secrets_manager.client.create_secret(Name=secret_name, SecretString=json.dumps(secret_content))
    yield secret_name

    def teardown():
        secrets_manager.client.delete_secret(SecretId=secret_name, ForceDeleteWithoutRecovery=True)

    request.addfinalizer(teardown)


@pytest.fixture(scope="function")
def secret_keys():
    return {
        "auth_url_key": "DATA_SCIENCE_SALESFORCE_SANDBOX_AUTH_URL",
        "username_key": "DATA_SCIENCE_SALESFORCE_SANDBOX_USR",
        "password_key": "DATA_SCIENCE_SALESFORCE_SANDBOX_PSW",
        "client_id_key": "DATA_SCIENCE_SALESFORCE_SANDBOX_CLIENT_USR",
        "client_secret_key": "DATA_SCIENCE_SALESFORCE_SANDBOX_CLIENT_PSW",
    }


@pytest.fixture(scope="function")
def secret_with_non_default_keys(secrets_manager, secret_keys, request):
    secret_name = "test/secret_with_non_default_keys"
    secret_content = {
        secret_keys["auth_url_key"]: os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_AUTH_URL"],
        secret_keys["username_key"]: os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_USR"],
        secret_keys["password_key"]: os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_PSW"],
        secret_keys["client_id_key"]: os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_CLIENT_USR"],
        secret_keys["client_secret_key"]: os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_CLIENT_PSW"],
    }
    secrets_manager.client.create_secret(Name=secret_name, SecretString=json.dumps(secret_content))
    yield secret_name

    def teardown():
        secrets_manager.client.delete_secret(SecretId=secret_name, ForceDeleteWithoutRecovery=True)

    request.addfinalizer(teardown)


def delete_records(oh: ObjectsHandler, sobject: str):
    obtained_records = oh.do_query_with_SOQL(f"SELECT Id from {sobject}")

    for obtained_record in obtained_records:
        record_id = obtained_record["Id"]
        oh.do_request(
            method="DELETE", path=f"sobjects/{sobject}/{record_id}",
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
            {"FirstName": "Janie", "LastName": "Goodman", "Email": "janie@example.com",},
        ]

        # Connect Salesforce with wrong credentials. Failure expected.
        oh = ObjectsHandler(
            auth_url=SANDBOX_AUTH_URL,
            username="false_username",
            password="false_password",
            client_id=SANDBOX_CLIENT_USR,
            client_secret=SANDBOX_CLIENT_PSW,
        )
        with pytest.raises(requests.exceptions.RequestException):
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
        with pytest.raises(requests.exceptions.RequestException):
            oh.do_request(
                method="POST", path="sobjects/Contact", payload=contact_payloads[0],
            )

    def test_salesforce_object_required_fields(self):
        oh = ObjectsHandler(
            auth_url=SANDBOX_AUTH_URL,
            username=SANDBOX_USR,
            password=SANDBOX_PSW,
            client_id=SANDBOX_CLIENT_USR,
            client_secret=SANDBOX_CLIENT_PSW,
        )

        # Test inserting an invalid field. Failure expected.
        invalid_field = "InvalidField"
        contact_payload = {
            invalid_field: "InvalidValue",
        }
        expected_message = f"`{invalid_field}` isn't a valid field."
        with pytest.raises(SalesforceObjectFieldError, match=expected_message):
            oh.do_request(
                method="POST", path="sobjects/Contact", payload=contact_payload,
            )

        # Test inserting a contact without a required field. Failure expected.
        contact_payload = {
            "FirstName": "Larry",
            "Email": "larry@example.com",
        }

        missing_field = "LastName"
        expected_message = (
            f"`{missing_field}` is a required field and does not appear in the payload."
        )
        with pytest.raises(SalesforceObjectFieldError, match=expected_message):
            oh.do_request(
                method="POST", path="sobjects/Contact", payload=contact_payload,
            )

        # Test inserting a contact with an empty required field. Failure expected.
        contact_payload[missing_field] = ""
        expected_message = f"`{missing_field}` is a required field and must not be empty."
        with pytest.raises(SalesforceObjectFieldError, match=expected_message):
            oh.do_request(
                method="POST", path="sobjects/Contact", payload=contact_payload,
            )

    def test_contact_insertion(self):
        oh = ObjectsHandler(
            auth_url=SANDBOX_AUTH_URL,
            username=SANDBOX_USR,
            password=SANDBOX_PSW,
            client_id=SANDBOX_CLIENT_USR,
            client_secret=SANDBOX_CLIENT_PSW,
        )

        # Insert n Contacts that do not exist. Success expected.
        contact_payloads = [
            {"FirstName": "Randall D.", "LastName": "Youngblood", "Email": "randall@example.com",},
            {"FirstName": "Amani Cantara", "LastName": "Fakhoury", "Email": "amani@example.com",},
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
        with pytest.raises(requests.exceptions.RequestException):
            response = oh.do_request(
                method="POST", path="sobjects/Contact", payload=contact_payloads[0],
            )
            assert response

    def test_init_handler_from_secrets_manager(
        self, secret_with_default_keys, secret_with_non_default_keys, secret_keys
    ):
        oh = ObjectsHandler.from_aws_secrets_manager(secret_name=secret_with_default_keys)

        # Initialize the handler from secrets using the default secret keys by convention and insert
        # a Contact that do not exist. Success expected.
        contact_payloads = [
            {"FirstName": "Abbie", "LastName": "Cochran", "Email": "abbie@example.com",},
        ]

        for contact_payload in contact_payloads:
            response = oh.do_request(
                method="POST", path="sobjects/Contact", payload=contact_payload
            )
            assert response

        # Initialize the handler from secrets using non default secret keys and insert a Contact
        # that do not exist. Success expected.
        oh = ObjectsHandler.from_aws_secrets_manager(
            secret_name=secret_with_non_default_keys, secret_keys=secret_keys
        )

        contact_payloads = [
            {"FirstName": "Mira", "LastName": "Berger", "Email": "mira@example.com",},
        ]

        for contact_payload in contact_payloads:
            response = oh.do_request(
                method="POST", path="sobjects/Contact", payload=contact_payload
            )
            assert response

        # Initialize the handler from secrets using secret keys different the default ones but with
        # an incorrect format. Failure expected.
        bad_secret_keys = {
            "wrong_auth_url_key": "AUTH_URL",
            "wrong_username_key": "USR",
            "wrong_password_key": "PSW",
            "wrong_client_id_key": "CLIENT_USR",
            "wrong_client_secret_key": "CLIENT_PSW",
        }

        expected_message = "The `secret_keys` argument does not contain the required key."
        with pytest.raises(ValueError, match=expected_message):
            ObjectsHandler.from_aws_secrets_manager(
                secret_name=secret_with_non_default_keys, secret_keys=bad_secret_keys
            )

    def test_different_query_syntaxes(self):
        oh = ObjectsHandler(
            auth_url=SANDBOX_AUTH_URL,
            username=SANDBOX_USR,
            password=SANDBOX_PSW,
            client_id=SANDBOX_CLIENT_USR,
            client_secret=SANDBOX_CLIENT_PSW,
        )

        # Do a query written in uppercase. Success expected.
        obtained_contacts = oh.do_query_with_SOQL("SELECT ID, NAME FROM CONTACT")
        assert not obtained_contacts

        # Do a query written in lowercase. Success expected.
        obtained_contacts = oh.do_query_with_SOQL("select id, name from contact")
        assert not obtained_contacts

        # Do a query to a non-existent object. Failure expected.
        wrong_object_name = "Contacts"
        expected_message = f"{wrong_object_name} isn't a valid object"
        with pytest.raises(SalesforceObjectError, match=expected_message):
            obtained_contacts = oh.do_query_with_SOQL(f"SELECT Id, Name From {wrong_object_name}")

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

        # Insert n Contacts.
        contact_payloads = [
            {"FirstName": "Angel", "LastName": "Collins", "Email": "angel@example.com",},
            {"FirstName": "June", "LastName": "Ross", "Email": "june@example.com",},
        ]

        for contact_payload in contact_payloads:
            oh.do_request(method="POST", path="sobjects/Contact", payload=contact_payload)

        # Read the n Contacts inserted with SOQL. Success expected.
        expected_names = []
        for contact_payload in contact_payloads:
            first_name = contact_payload["FirstName"]
            last_name = contact_payload["LastName"]
            expected_names.append(f"{first_name} {last_name}")

        obtained_contacts = oh.do_query_with_SOQL("SELECT Id, Name from Contact")
        assert len(obtained_contacts) == len(contact_payloads)

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
            f"SELECT Id, Name from contact WHERE Id = '{expected_id}'"
        )
        assert len(obtained_contacts) == 1 and obtained_contacts[0]["Name"] == expected_name

        # Read a specific contact with SOQL by Name. Success expected.
        obtained_contacts = oh.do_query_with_SOQL(
            f"SELECT Name from contact WHERE Name = '{expected_name}'"
        )
        assert len(obtained_contacts) == 1 and obtained_contacts[0]["Name"] == expected_name

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

        # Insert n Contacts.
        contact_payloads = [
            {"FirstName": "Ramon", "LastName": "Evans", "Email": "ramon@example.com",},
            {"FirstName": "Janis", "LastName": "Holmes", "Email": "janis@example.com",},
        ]

        for contact_payload in contact_payloads:
            oh.do_request(method="POST", path="sobjects/Contact", payload=contact_payload)

        # Modify an existing contact's FirstName and LastName. Success expected.
        first_name = contact_payloads[0]["FirstName"]
        last_name = contact_payloads[0]["LastName"]
        obtained_contacts = oh.do_query_with_SOQL(
            f"SELECT Id, Name from Contact WHERE Name = '{first_name} {last_name}'"
        )
        contact_payload = {"FirstName": "Ken", "LastName": "Williams"}

        contact_id = obtained_contacts[0]["Id"]
        oh.do_request(
            method="PATCH", path=f"sobjects/Contact/{contact_id}", payload=contact_payload,
        )

        contact_id = obtained_contacts[0]["Id"]
        obtained_contacts = oh.do_query_with_SOQL(
            f"SELECT Id, Name from Contact WHERE Id = '{contact_id}'"
        )

        first_name = contact_payload["FirstName"]
        last_name = contact_payload["LastName"]
        expected_contact_name = f"{first_name} {last_name}"
        assert obtained_contacts[0]["Name"] == expected_contact_name

        # Modify an existing contact's Email. Success expected.
        first_name = contact_payload["FirstName"].lower()
        contact_payload = {"Email": f"{first_name}@example.com"}

        contact_id = obtained_contacts[0]["Id"]
        oh.do_request(
            method="PATCH", path=f"sobjects/Contact/{contact_id}", payload=contact_payload,
        )

        contact_id = obtained_contacts[0]["Id"]
        obtained_contacts = oh.do_query_with_SOQL(
            f"SELECT Id, Name, Email from Contact WHERE Id = '{contact_id}'"
        )
        assert (
            obtained_contacts[0]["Name"] == expected_contact_name
            and obtained_contacts[0]["Email"] == contact_payload["Email"]
        )

        # Modify a Contact that does not exist. Failure expected.
        contact_payload = {"FirstName": "ANYNAME"}
        with pytest.raises(requests.exceptions.RequestException):
            oh.do_request(
                method="PATCH", path="sobjects/Contact/WRONGID", payload=contact_payload,
            )

    def test_contact_deletion(self):
        oh = ObjectsHandler(
            auth_url=SANDBOX_AUTH_URL,
            username=SANDBOX_USR,
            password=SANDBOX_PSW,
            client_id=SANDBOX_CLIENT_USR,
            client_secret=SANDBOX_CLIENT_PSW,
        )

        # Insert n Contacts.
        contact_payloads = [
            {"FirstName": "Brian", "LastName": "Cunningham", "Email": "brian@example.com",},
            {"FirstName": "Julius", "LastName": "Marsh", "Email": "julius@example.com",},
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
            method="DELETE", path=f"sobjects/Contact/{obtained_ids[0]}",
        )

        obtained_contacts = oh.do_query_with_SOQL(
            f"SELECT Name from Contact WHERE Name = '{obtained_names[0]}'"
        )
        assert len(obtained_contacts) == 0

        obtained_contacts = oh.do_query_with_SOQL(
            f"SELECT Name from contact WHERE Name = '{obtained_names[1]}'"
        )
        assert len(obtained_contacts) == len(contact_payloads) - 1

        # Delete a Contact that does not exist. Failure expected.
        with pytest.raises(requests.exceptions.RequestException):
            oh.do_request(
                method="DELETE", path=f"sobjects/Contact/{obtained_ids[0]}",
            )

    def test_contact_insertion_high_level(self):
        oh = ObjectsHandler(
            auth_url=SANDBOX_AUTH_URL,
            username=SANDBOX_USR,
            password=SANDBOX_PSW,
            client_id=SANDBOX_CLIENT_USR,
            client_secret=SANDBOX_CLIENT_PSW,
        )

        # Insert n Contacts that do not exist. Success expected.
        contact_payloads = [
            {"FirstName": "Kim", "LastName": "George", "Email": "kim@example.com",},
            {"FirstName": "Wilfred", "LastName": "Craig", "Email": "wilfred@example.com",},
            {"FirstName": "Whitney", "LastName": "Ross", "Email": "whitney@example.com",},
        ]

        for contact_payload in contact_payloads:
            response = oh.insert_record(sobject="Contact", payload=contact_payload)
            assert response

        # Insert a Contact that already exist with a new email. Success expected.
        contact_payloads[0]["Email"] = "rodriguez@example.com"
        response = oh.insert_record(sobject="Contact", payload=contact_payloads[0])
        assert response

        # Insert a Contact that already exist. Failure expected.
        with pytest.raises(requests.exceptions.RequestException):
            response = oh.insert_record(sobject="Contact", payload=contact_payload)
            assert response

    def test_contact_modification_high_level(self):
        oh = ObjectsHandler(
            auth_url=SANDBOX_AUTH_URL,
            username=SANDBOX_USR,
            password=SANDBOX_PSW,
            client_id=SANDBOX_CLIENT_USR,
            client_secret=SANDBOX_CLIENT_PSW,
        )

        # Insert n Contacts.
        contact_payloads = [
            {"FirstName": "Boyd", "LastName": "Johnston", "Email": "boyd@example.com",},
            {"FirstName": "Zachary", "LastName": "Singleton", "Email": "zachary@example.com",},
        ]

        for contact_payload in contact_payloads:
            response = oh.do_request(
                method="POST", path="sobjects/Contact", payload=contact_payload
            )

        # Modify an existing contact's FirstName and LastName. Success expected.
        first_name = contact_payloads[0]["FirstName"]
        last_name = contact_payloads[0]["LastName"]
        obtained_contacts = oh.do_query_with_SOQL(
            f"SELECT Id, Name from Contact WHERE Name = '{first_name} {last_name}'"
        )
        contact_payload = {"FirstName": "Ralph", "LastName": "Alexander"}

        expected_contact_id = obtained_contacts[0]["Id"]
        oh.modify_record(
            sobject="Contact", record_id=expected_contact_id, payload=contact_payload,
        )

        obtained_contacts = oh.do_query_with_SOQL(
            f"SELECT Id, Name from Contact WHERE Id = '{expected_contact_id}'"
        )
        first_name = contact_payload["FirstName"]
        last_name = contact_payload["LastName"]
        expected_contact_name = f"{first_name} {last_name}"
        assert obtained_contacts[0]["Name"] == expected_contact_name

        # Modify an existing contact's Email. Success expected.
        first_name = contact_payload["FirstName"].lower()
        contact_payload = {"Email": f"{first_name}@example.com"}

        oh.modify_record(
            sobject="Contact", record_id=expected_contact_id, payload=contact_payload,
        )

        obtained_contacts = oh.do_query_with_SOQL(
            f"SELECT Id, Name, Email from Contact WHERE Id = '{expected_contact_id}'"
        )
        assert (
            obtained_contacts[0]["Name"] == expected_contact_name
            and obtained_contacts[0]["Email"] == contact_payload["Email"]
        )

        # Modify a Contact that does not exist. Failure expected.
        contact_payload = {"FirstName": "ANYNAME"}
        with pytest.raises(requests.exceptions.RequestException):
            oh.modify_record(
                sobject="Contact", record_id="WRONGID", payload=contact_payload,
            )

    def test_contact_deletion_high_level(self):
        oh = ObjectsHandler(
            auth_url=SANDBOX_AUTH_URL,
            username=SANDBOX_USR,
            password=SANDBOX_PSW,
            client_id=SANDBOX_CLIENT_USR,
            client_secret=SANDBOX_CLIENT_PSW,
        )

        # Insert n Contacts.
        contact_payloads = [
            {"FirstName": "Elaine", "LastName": "Mullins", "Email": "elaine@example.com",},
            {"FirstName": "Tami", "LastName": "Joseph", "Email": "tami@example.com",},
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

        oh.delete_record(sobject="Contact", record_id=obtained_ids[0])

        obtained_contacts = oh.do_query_with_SOQL(
            f"SELECT Name from Contact WHERE Name = '{obtained_names[0]}'"
        )
        assert len(obtained_contacts) == 0

        obtained_contacts = oh.do_query_with_SOQL(
            f"SELECT Name from contact WHERE Name = '{obtained_names[1]}'"
        )
        assert len(obtained_contacts) == len(contact_payloads) - 1

        # Delete a Contact that does not exist. Failure expected.
        with pytest.raises(requests.exceptions.RequestException):
            oh.delete_record(sobject="Contact", record_id=obtained_ids[0])
