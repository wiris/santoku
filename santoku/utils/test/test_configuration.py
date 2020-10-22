import json

import pytest

from copy import deepcopy

from jsonschema.exceptions import SchemaError
from santoku.utils.configuration import (
    ConfigurationError,
    ConfigurationManager,
    IllegalAccessPattern,
    SchemaViolation,
    SettingError,
)


@pytest.fixture(scope="function")
def valid_settings_A():
    return {
        "integer_setting": 1,
        "boolean_setting": True,
        "string_setting": "initial string value",
        "float_setting": 1.0,
        "dict_setting": {
            "nested_string_setting": "initial dict string value",
            "nested_boolean_setting": False,
        },
    }


@pytest.fixture(scope="function")
def valid_configuration_A(valid_settings_A):
    return {"name": "valid_configuration_A", "settings": valid_settings_A}


@pytest.fixture(scope="function")
def valid_settings_B():
    return {
        "integer_setting": 2,
        "boolean_setting": False,
        "string_setting": "test string value",
        "float_setting": 2.0,
        "dict_setting": {
            "nested_string_setting": "test dict string value",
            "nested_boolean_setting": True,
        },
    }


@pytest.fixture(scope="function")
def valid_configuration_B(valid_settings_B):
    return {"name": "valid_configuration_B", "settings": valid_settings_B}


@pytest.fixture(scope="function")
def schema():
    return {
        "type": "object",
        "properties": {
            "integer_setting": {"type": "integer"},
            "boolean_setting": {"type": "boolean"},
            "string_setting": {"type": "string"},
            "float_setting": {"type": "number"},
            "dict_setting": {
                "type": "object",
                "properties": {
                    "nested_string_setting": {"type": "string"},
                    "nested_boolean_setting": {"type": "boolean"},
                },
                "additionalProperties": False,
                "required": ["nested_string_setting", "nested_boolean_setting"],
            },
        },
        "additionalProperties": False,
        "required": [
            "integer_setting",
            "boolean_setting",
            "string_setting",
            "float_setting",
            "dict_setting",
        ],
    }


@pytest.fixture(scope="function")
def schema_with_spec():
    def get_schema_with_spec(draft: int):
        return {"$schema": f"http://json-schema.org/draft-0{draft}/schema#"}

    return get_schema_with_spec


@pytest.fixture(scope="function")
def schema_with_invalid_spec():
    return {"$schema": f"This is not a valid JSON Schema specification identifier"}


@pytest.fixture(scope="function")
def schema_violating_configuration():
    return {
        "name": "invalid_configuration",
        "settings": {},
    }


@pytest.fixture(scope="function")
def create_json_file(tmpdir):
    # creates a JSON file inside the tmpdir (provided by pytest)
    # tmpdir guarantees that any file inside it will be deleted automatically after the test
    # thus, no need to add a finalizer
    def _create_json_file(rel_path, content):
        path = tmpdir.join(rel_path)
        with open(path, "w") as f:
            json.dump(content, f)
        return path

    return _create_json_file


@pytest.fixture(scope="function")
def configurations_file(valid_configuration_A, valid_configuration_B, create_json_file):
    file_name = "configurations.json"
    configurations = [valid_configuration_A, valid_configuration_B]
    abs_path = create_json_file(rel_path=file_name, content=configurations)
    return abs_path


@pytest.fixture(scope="function")
def schema_file(tmpdir, schema, create_json_file):
    file_name = "schema.json"
    abs_path = create_json_file(rel_path=file_name, content=schema)
    return abs_path


@pytest.fixture(scope="function")
def configuration_manager(valid_configuration_A, valid_configuration_B, schema):
    configurations = [valid_configuration_A, valid_configuration_B]
    return ConfigurationManager(
        configurations=configurations,
        initial_configuration=valid_configuration_A["name"],
        schema=schema,
    )


class TestConfigurationManager:
    def test_init(
        self, valid_configuration_A, valid_configuration_B, schema, schema_violating_configuration
    ):
        # Initialize two configurations. Success expected.
        try:
            configuration_manager = ConfigurationManager(
                configurations=[valid_configuration_A, valid_configuration_B],
                schema=schema,
                initial_configuration=valid_configuration_A["name"],
            )
        except:
            assert False

        # Active configuration must be initial configuration. Success expected.
        expected_configuration_name = valid_configuration_A["name"]
        obtained_configuration_name = configuration_manager.active_configuration
        assert obtained_configuration_name == expected_configuration_name

        # Retrieve the stored settings after init. Success expected.
        expected_settings = valid_configuration_A["settings"]
        obtained_settings = configuration_manager.configurations[valid_configuration_A["name"]]
        assert obtained_settings == expected_settings

        expected_settings = valid_configuration_B["settings"]
        obtained_settings = configuration_manager.configurations[valid_configuration_B["name"]]
        assert obtained_settings == expected_settings

        # Initialize with a config that does not follow the schema. Failure expected.
        with pytest.raises(SchemaViolation):
            ConfigurationManager(configurations=[schema_violating_configuration], schema=schema)

        # Pass an initial configuration to an empty configuration manager. Failure expected.
        with pytest.raises(ConfigurationError):
            ConfigurationManager(initial_configuration=valid_configuration_A["name"])

    def test_from_json(self, configurations_file, schema_file):
        # Initialize a ConfigurationManager from a correct JSON file. Success expected.
        try:
            configuration_manager = ConfigurationManager.from_json(
                configurations_file_path=configurations_file, schema_file_path=schema_file,
            )
        except:
            assert False

    def test_check_schema(self, schema_with_spec, schema_with_invalid_spec):
        # We only check that the appropriate validators are used. The actual work of validating is
        # performed by the jsonschema package, which has its own set of tests.

        # Check valid schemas using supported specifications. Success expected.
        ConfigurationManager.check_schema(schema=schema_with_spec(draft=7))
        ConfigurationManager.check_schema(schema=schema_with_spec(draft=6))
        ConfigurationManager.check_schema(schema=schema_with_spec(draft=4))

        # Check valid schema without specifying the spec (uses the default). Success expected.
        ConfigurationManager.check_schema(schema={})

        # Check valid schemas with invalid/unsupported specs. Failure expected.
        with pytest.raises(SchemaError):
            ConfigurationManager.check_schema(schema=schema_with_invalid_spec)
        with pytest.raises(SchemaError):
            ConfigurationManager.check_schema(schema=schema_with_spec(237))

    def test_validate_schema(self, valid_settings_A, configuration_manager, schema):
        # Validate settings with less arguments than schema requires. Failure expected.
        settings_to_validate = deepcopy(valid_settings_A)
        removed_value = settings_to_validate.pop("integer_setting")
        with pytest.raises(SchemaViolation):
            configuration_manager.validate_schema(settings=settings_to_validate)

        # Validate settings with more arguments than the schema. Failure expected.
        settings_to_validate = deepcopy(valid_settings_A)
        settings_to_validate["new_setting"] = "new_value"
        with pytest.raises(SchemaViolation):
            configuration_manager.validate_schema(settings=settings_to_validate)

        # Validate settings with a differently named setting than the schema. Failure expected.
        settings_to_validate = deepcopy(valid_settings_A)
        settings_to_validate["new_integer_setting"] = settings_to_validate.pop("integer_setting")
        with pytest.raises(SchemaViolation):
            configuration_manager.validate_schema(settings=settings_to_validate)

        # Validate settings with a differently typed value than the schema. Failure expected.
        settings_to_validate = deepcopy(valid_settings_A)
        settings_to_validate["integer_setting"] = "1"
        with pytest.raises(SchemaViolation):
            configuration_manager.validate_schema(settings=settings_to_validate)

        # Validate nested setting with a different types than in the schema. Failure expected.
        settings_to_validate = deepcopy(valid_settings_A)
        settings_to_validate["dict_setting"]["nested_string_setting"] = 1
        with pytest.raises(SchemaViolation):
            configuration_manager.validate_schema(settings=settings_to_validate)

        # Validate settings that follow the schema. Success expected.
        settings_to_validate = deepcopy(valid_settings_A)
        try:
            configuration_manager.validate_schema(settings=settings_to_validate)
        except:
            assert False

    def test_define_configuration(self, valid_settings_A, schema, schema_violating_configuration):
        configuration_manager = ConfigurationManager(schema=schema)

        # Define a configuration in an empty configuration manager. Success expected.
        try:
            configuration_manager.define_configuration(
                name="configuration_name", settings=valid_settings_A
            )
        except:
            assert False

        # Configuration settings must be preserved upon insertion. Success expected.
        expected_settings = deepcopy(valid_settings_A)
        obtained_setting = configuration_manager.configurations["configuration_name"]
        assert obtained_setting == expected_settings

        # Override an existing configuration. Success expected.
        new_settings = deepcopy(valid_settings_A)
        new_settings["integer_setting"] = new_settings["integer_setting"] + 1
        configuration_manager.define_configuration(
            name="configuration_name", settings=new_settings, override=True,
        )
        obtained_settings = configuration_manager.configurations["configuration_name"]
        assert obtained_settings == new_settings

        # Define a configuration with settings that do not follow the schema. Failure expected.
        with pytest.raises(SchemaViolation):
            configuration_manager.define_configuration(
                name=schema_violating_configuration["name"],
                settings=schema_violating_configuration["settings"],
            )

        # Define an existent configuration without the override flag. Failure expected.
        with pytest.raises(ConfigurationError):
            configuration_manager.define_configuration(
                name="configuration_name", settings=valid_settings_A, override=False,
            )

    def test_list_configurations(self, configuration_manager):
        expected = list(configuration_manager.configurations)
        assert configuration_manager.list_configurations() == expected

    def test_get_configuration(self, valid_configuration_A, configuration_manager):
        # Retrieve an existing configuration. Success expected.
        expected_settings = valid_configuration_A["settings"]
        obtained_settings = configuration_manager.get_configuration(
            name=valid_configuration_A["name"]
        )
        assert obtained_settings == expected_settings

        # Retrieve an undefined configuration. Failure expected.
        with pytest.raises(ConfigurationError):
            configuration_manager.get_configuration(name="undefined_configuration")

    def test_apply_configuration(self, valid_configuration_A, configuration_manager):
        # Applied configuration must be the active one after applying. Success expected.
        configuration_manager.apply_configuration(name=valid_configuration_A["name"])
        expected_settings = valid_configuration_A["settings"]
        obtained_settings = configuration_manager.configurations[
            configuration_manager.active_configuration
        ]
        assert obtained_settings == expected_settings

        # Apply an unavailable configuration. Failure expected.
        with pytest.raises(ConfigurationError):
            configuration_manager.apply_configuration(name="unavailable_configuration")

    def test_get_active_configuration(self, valid_configuration_A, configuration_manager):
        # Check the active configuration is the expected one. Success expected.
        expected_configuration = valid_configuration_A["settings"]
        obtained_configuration = configuration_manager.get_active_configuration()
        assert obtained_configuration == expected_configuration

    def test_get_setting(self, valid_configuration_A, configuration_manager):
        # Retrieve a setting value of the active configuration. Success expected.
        expected_setting = valid_configuration_A["settings"]["integer_setting"]
        obtained_setting = configuration_manager.get_setting("integer_setting")
        assert expected_setting == obtained_setting

        # Retrieve an undefind setting. Failure expected.
        with pytest.raises(SettingError):
            configuration_manager.get_setting("undefined_setting")

        # Retrieve nested setting. Success expected.
        expected_setting = valid_configuration_A["settings"]["dict_setting"][
            "nested_boolean_setting"
        ]
        obtained_setting = configuration_manager.get_setting(
            "dict_setting", "nested_boolean_setting"
        )
        assert expected_setting == obtained_setting

        # Retrieve a nested collection of settings (forbidden access pattern). Failure expected.
        with pytest.raises(IllegalAccessPattern):
            configuration_manager.get_setting("dict_setting")

        # Retrieve an undefind nested setting. Failure expected.
        with pytest.raises(SettingError):
            configuration_manager.get_setting("dict_setting", "nested_undefined_setting")
