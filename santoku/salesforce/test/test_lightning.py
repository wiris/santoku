import os
import json
import requests

import pytest

from typing import List, Dict
from moto import mock_secretsmanager

from santoku.aws.secretsmanager import SecretsManagerHandler
from santoku.exceptions import MissingEnvironmentVariables
from santoku.salesforce.lightning import (
    LightningRestApiHandler,
    SalesforceObjectError,
    SalesforceObjectFieldError,
    RequestMethodError,
)


"""
Note: This class necessitates a Salesforce instance up and running in order to pass the tests.
We at Wiris execute this tests against our own private Salesforce testing sandbox instance.
In order to pass those tests, simply setup Salesforce and pass the credentials below.
Be warned that the fixtures in the tests can and will create and destroy Salesforce objects in
your instance. We do try to only create sobjects with narrow names and only destroy the ones we
create, so that we don't affect the rest of the Salesforce environment. A good practice, however,
would be to periodically clean that instance in order to reduce chance of existing data leaking
into the tests.
"""


credentials_keys = [
    "DATA_SCIENCE_SALESFORCE_SANDBOX_AUTH_URL",
    "DATA_SCIENCE_SALESFORCE_SANDBOX_USR",
    "DATA_SCIENCE_SALESFORCE_SANDBOX_PSW",
    "DATA_SCIENCE_SALESFORCE_SANDBOX_CLIENT_USR",
    "DATA_SCIENCE_SALESFORCE_SANDBOX_CLIENT_PSW",
]

if not all(key in os.environ for key in credentials_keys):
    raise MissingEnvironmentVariables("Salesforce credentials environment variables are missing.")


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


@pytest.fixture(scope="class")
def sf_credentials():
    return {
        "AUTH_URL": os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_AUTH_URL"],
        "USR": os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_USR"],
        "PSW": os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_PSW"],
        "CLIENT_USR": os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_CLIENT_USR"],
        "CLIENT_PSW": os.environ["DATA_SCIENCE_SALESFORCE_SANDBOX_CLIENT_PSW"],
    }


@pytest.fixture(scope="function")
def sf_credentials_secret(secrets_manager, sf_credentials, request):
    secret_name = "test/sf_credentials_secret"
    secrets_manager.client.create_secret(Name=secret_name, SecretString=json.dumps(sf_credentials))

    yield secret_name

    def teardown() -> None:
        secrets_manager.client.delete_secret(SecretId=secret_name, ForceDeleteWithoutRecovery=True)

    request.addfinalizer(teardown)


@pytest.fixture(scope="class")
def api_handler(sf_credentials):
    return LightningRestApiHandler(
        auth_url=sf_credentials["AUTH_URL"],
        username=sf_credentials["USR"],
        password=sf_credentials["PSW"],
        client_id=sf_credentials["CLIENT_USR"],
        client_secret=sf_credentials["CLIENT_PSW"],
    )


@pytest.fixture(scope="function")
def contact_payloads():
    # Using Alice & Bob notation. More info at https://en.wikipedia.org/wiki/Alice_and_Bob
    names = ["Alice", "Bob", "Carol", "David"]
    last_names = ["Ackerman", "Bayes", "Cauchy", "Dijkstra"]
    emails = ["alice@test.com", "bob@test.com", "carol@test.com", "david@test.com"]

    payloads = []
    for contact in zip(names, last_names, emails):
        payloads.append({"FirstName": contact[0], "LastName": contact[1], "Email": contact[2]})

    return payloads


@pytest.fixture(scope="function")
def delete_record(api_handler):
    def _delete_record(sobject: str, record_id: str) -> None:
        api_handler.do_request(
            method="DELETE", path=f"sobjects/{sobject}/{record_id}",
        )

    return _delete_record


@pytest.fixture(scope="function")
def insert_record(api_handler):
    def _insert_record(sobject: str, payload: List[Dict[str, str]]) -> None:
        response_text = api_handler.do_request(
            method="POST", path=f"sobjects/{sobject}", payload=payload
        )
        record_id = json.loads(response_text)["id"]
        return record_id

    return _insert_record


@pytest.fixture(scope="function")
def contacts(contact_payloads, insert_record, delete_record, request):
    created_record_ids = []
    for payload in contact_payloads:
        created_record_ids.append(insert_record(sobject="Contact", payload=payload))
    yield created_record_ids

    def teardown() -> None:
        for record_id in created_record_ids:
            try:
                delete_record(sobject="Contact", record_id=record_id)
            except:
                pass

    request.addfinalizer(teardown)


class TestLightningRestApiHandler:
    def test_wrong_credentials(self, sf_credentials, contact_payloads):
        # Connect Salesforce with wrong credentials. Failure expected.
        api_handler = LightningRestApiHandler(
            auth_url=sf_credentials["AUTH_URL"],
            username="false_username",
            password="false_password",
            client_id=sf_credentials["CLIENT_USR"],
            client_secret=sf_credentials["CLIENT_PSW"],
        )
        with pytest.raises(requests.exceptions.RequestException):
            api_handler.do_request(
                method="POST", path="sobjects/Contact", payload=contact_payloads[0],
            )

        api_handler = LightningRestApiHandler(
            auth_url=sf_credentials["AUTH_URL"],
            username=sf_credentials["USR"],
            password=sf_credentials["PSW"],
            client_id="false_client_id",
            client_secret="false_client_secret",
        )
        with pytest.raises(requests.exceptions.RequestException):
            api_handler.do_request(
                method="POST", path="sobjects/Contact", payload=contact_payloads[0],
            )

    def test_salesforce_object_required_fields(self, api_handler):
        # Test inserting an invalid field. Failure expected.
        invalid_field = "InvalidField"
        bad_contact_payload = {invalid_field: "InvalidValue"}
        expected_message = f"`{invalid_field}` isn't a valid field."
        with pytest.raises(SalesforceObjectFieldError, match=expected_message):
            api_handler.do_request(
                method="POST", path="sobjects/Contact", payload=bad_contact_payload,
            )

        # Test inserting a contact without a required field. Failure expected.
        bad_contact_payload = {
            "FirstName": "Chuck",
            "Email": "chuck@test.com",
        }

        missing_field = "LastName"
        expected_message = (
            f"`{missing_field}` is a required field and does not appear in the payload."
        )
        with pytest.raises(SalesforceObjectFieldError, match=expected_message):
            api_handler.do_request(
                method="POST", path="sobjects/Contact", payload=bad_contact_payload,
            )

        # Test inserting a contact with an empty required field. Failure expected.
        bad_contact_payload[missing_field] = ""
        expected_message = f"`{missing_field}` is a required field and must not be empty."
        with pytest.raises(SalesforceObjectFieldError, match=expected_message):
            api_handler.do_request(
                method="POST", path="sobjects/Contact", payload=bad_contact_payload,
            )

    def test_contact_insertion(self, api_handler, contact_payloads, delete_record):
        created_record_ids = []

        # Insert n Contacts that do not exist. Success expected.
        for contact_payload in contact_payloads:
            response_text = api_handler.do_request(
                method="POST", path="sobjects/Contact", payload=contact_payload
            )
            response = json.loads(response_text)
            created_record_ids.append(response["id"])
            assert response["success"]

        # Insert a Contact that already exist. Failure expected.
        with pytest.raises(requests.exceptions.RequestException):
            api_handler.do_request(
                method="POST", path="sobjects/Contact", payload=contact_payloads[0],
            )

        # Insert a Contact that already exist with a new email. Success expected.
        new_contact_payload = contact_payloads[0].copy()
        new_contact_payload["Email"] = "new.email@example.com"
        response_text = api_handler.do_request(
            method="POST", path="sobjects/Contact", payload=new_contact_payload,
        )
        response = json.loads(response_text)
        created_record_ids.append(response["id"])
        assert response["success"]

        # Remove created records.
        for record_id in created_record_ids:
            delete_record(sobject="Contact", record_id=record_id)

    def test_init_handler_from_secrets_manager(
        self, sf_credentials_secret, contact_payloads, delete_record
    ):
        # Initialize the handler from secrets using the default secret keys by convention and insert
        # a Contact that does not exist. Success expected.
        api_handler = LightningRestApiHandler.from_aws_secrets_manager(
            secret_name=sf_credentials_secret
        )
        response_text = api_handler.do_request(
            method="POST", path="sobjects/Contact", payload=contact_payloads[0],
        )
        response = json.loads(response_text)
        assert response["success"]

        # Remove created records.
        delete_record(sobject="Contact", record_id=response["id"])

    def test_different_query_syntaxes(self, api_handler):
        # Do a query written in uppercase. Success expected.
        obtained_contacts = api_handler.do_query_with_SOQL("SELECT ID, NAME FROM CONTACT")
        assert len(obtained_contacts) == 0

        # Do a query written in lowercase. Success expected.
        obtained_contacts = api_handler.do_query_with_SOQL("select id, name from contact")
        assert len(obtained_contacts) == 0

        # Do a query to a non-existent object. Failure expected.
        wrong_object_name = "Contacts"
        expected_message = f"{wrong_object_name} isn't a valid object"
        with pytest.raises(SalesforceObjectError, match=expected_message):
            obtained_contacts = api_handler.do_query_with_SOQL(
                f"SELECT Id, Name From {wrong_object_name}"
            )

    def test_contact_query(self, api_handler, contact_payloads, contacts, delete_record):
        expected_names = []
        for contact_payload in contact_payloads:
            first_name = contact_payload["FirstName"]
            last_name = contact_payload["LastName"]
            expected_names.append(f"{first_name} {last_name}")

        # Read the Contacts inserted with SOQL. Success expected.
        obtained_contacts = api_handler.do_query_with_SOQL("SELECT Id, Name from Contact")

        # At least, all the inserted records should be in the result of the query.
        assert len(obtained_contacts) >= len(contact_payloads)

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
        obtained_contacts = api_handler.do_query_with_SOQL(
            f"SELECT Id, Name from contact WHERE Id = '{expected_id}'"
        )
        assert len(obtained_contacts) == 1
        assert obtained_contacts[0]["Name"] == expected_name

        # Query a contact that does not exists with SOQL. Success expected.
        delete_record(sobject="Contact", record_id=contacts[0])
        obtained_contacts = api_handler.do_query_with_SOQL(
            f"SELECT Name from contact WHERE Id = '{contacts[0]}'"
        )
        assert len(obtained_contacts) == 0

    def test_contact_modification(self, api_handler, contact_payloads, contacts):
        # Modify an existing contact's Name. Success expected.
        new_first_name = "Ken"
        new_last_name = "Williams"
        new_contact_payload = {"FirstName": new_first_name, "LastName": new_last_name}
        contact_id = contacts[0]
        api_handler.do_request(
            method="PATCH", path=f"sobjects/Contact/{contact_id}", payload=new_contact_payload,
        )

        obtained_contact = api_handler.do_query_with_SOQL(
            f"SELECT Id, Name from Contact WHERE Id = '{contact_id}'"
        )[0]

        expected_contact_name = f"{new_first_name} {new_last_name}"
        assert obtained_contact["Name"] == expected_contact_name

        # Modify an existing contact's Email. Success expected.
        new_email = f"{new_first_name.lower()}@example.com"
        new_contact_payload = {"Email": new_email}
        api_handler.do_request(
            method="PATCH", path=f"sobjects/Contact/{contact_id}", payload=new_contact_payload,
        )

        obtained_contact = api_handler.do_query_with_SOQL(
            f"SELECT Id, Name, Email from Contact WHERE Id = '{contact_id}'"
        )[0]
        assert obtained_contact["Name"] == expected_contact_name
        assert obtained_contact["Email"] == new_email

        # Modify a Contact that does not exist. Failure expected.
        new_contact_payload = {"FirstName": "NEWNAME"}
        with pytest.raises(requests.exceptions.RequestException):
            api_handler.do_request(
                method="PATCH", path="sobjects/Contact/WRONGID", payload=new_contact_payload,
            )

    def test_contact_deletion(self, api_handler, contacts):
        # Delete an existing Contact. Success expected.
        api_handler.do_request(
            method="DELETE", path=f"sobjects/Contact/{contacts[0]}",
        )

        obtained_contacts = api_handler.do_query_with_SOQL(
            f"SELECT Name from Contact WHERE Id = '{contacts[0]}'"
        )
        assert len(obtained_contacts) == 0

        # Delete a Contact that does not exist. Failure expected.
        with pytest.raises(requests.exceptions.RequestException):
            api_handler.do_request(
                method="DELETE", path=f"sobjects/Contact/{contacts[0]}",
            )

    def test_contact_insertion_high_level(self, api_handler, contact_payloads, delete_record):
        created_record_ids = []

        # Insert n Contacts that do not exist. Success expected.
        for contact_payload in contact_payloads:
            response_text = api_handler.insert_record(sobject="Contact", payload=contact_payload)
            response = json.loads(response_text)
            created_record_ids.append(response["id"])
            assert response["success"]

        # Insert a Contact that already exist. Failure expected.
        with pytest.raises(requests.exceptions.RequestException):
            api_handler.insert_record(
                sobject="Contact", payload=contact_payloads[0],
            )

        # Insert a Contact that already exist with a new email. Success expected.
        new_contact_payload = contact_payloads[0].copy()
        new_contact_payload["Email"] = "new.email@example.com"
        response_text = api_handler.insert_record(sobject="Contact", payload=new_contact_payload)
        response = json.loads(response_text)
        created_record_ids.append(response["id"])
        assert response["success"]

        # Insert a Contact that already exist. Failure expected.
        with pytest.raises(requests.exceptions.RequestException):
            response = api_handler.insert_record(sobject="Contact", payload=contact_payloads[0])
            assert response

        # Remove created records.
        for record_id in created_record_ids:
            delete_record(sobject="Contact", record_id=record_id)

    def test_contact_modification_high_level(self, api_handler, contacts):
        # Modify an existing contact's Name. Success expected.
        new_first_name = "Ralph"
        new_last_name = "Alexander"
        new_contact_payload = {"FirstName": new_first_name, "LastName": new_last_name}
        contact_id = contacts[0]
        api_handler.modify_record(
            sobject="Contact", record_id=contact_id, payload=new_contact_payload,
        )

        obtained_contact = api_handler.do_query_with_SOQL(
            f"SELECT Id, Name from Contact WHERE Id = '{contact_id}'"
        )[0]
        expected_contact_name = f"{new_first_name} {new_last_name}"
        assert obtained_contact["Name"] == expected_contact_name

        # Modify an existing contact's Email. Success expected.
        new_email = f"{new_first_name.lower()}@example.com"
        new_contact_payload = {"Email": new_email}
        api_handler.modify_record(
            sobject="Contact", record_id=contact_id, payload=new_contact_payload,
        )

        obtained_contact = api_handler.do_query_with_SOQL(
            f"SELECT Id, Name, Email from Contact WHERE Id = '{contact_id}'"
        )[0]
        assert obtained_contact["Name"] == expected_contact_name
        assert obtained_contact["Email"] == new_email

        # Modify a Contact that does not exist. Failure expected.
        new_contact_payload = {"FirstName": "NEWNAME"}
        with pytest.raises(requests.exceptions.RequestException):
            api_handler.modify_record(
                sobject="Contact", record_id="WRONGID", payload=new_contact_payload,
            )

    def test_contact_deletion_high_level(self, api_handler, contacts):
        # Delete an existing Contact. Success expected.
        api_handler.delete_record(sobject="Contact", record_id=contacts[0])

        obtained_contacts = api_handler.do_query_with_SOQL(
            f"SELECT Name from Contact WHERE Id = '{contacts[0]}'"
        )
        assert len(obtained_contacts) == 0

        obtained_contacts = api_handler.do_query_with_SOQL(
            f"SELECT Name from contact WHERE Id = '{contacts[1]}'"
        )
        assert len(obtained_contacts) == 1

        # Delete a Contact that does not exist. Failure expected.
        with pytest.raises(requests.exceptions.RequestException):
            api_handler.delete_record(sobject="Contact", record_id=contacts[0])
