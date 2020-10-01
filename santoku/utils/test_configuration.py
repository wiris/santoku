import json

import pytest

from collections import namedtuple

from santoku.utils.configuration import (
    ConfigurationAlreadyDefined,
    ConfigurationManager,
    SchemaViolation,
    UndefinedConfiguration,
    UndefinedSetting,
)


@pytest.fixture(scope="class")
def initial_settings():
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
def initial_configuration(initial_settings):
    return {"name": "initial_configuration", "settings": initial_settings}


@pytest.fixture(scope="class")
def test_settings():
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
def test_configuration(test_settings):
    return {"name": "test_configuration", "settings": test_settings}


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

    yield _create_json_file


@pytest.fixture(scope="function")
def configurations_file(initial_configuration, test_configuration, create_json_file):
    file_name = "configurations.json"
    configurations = [initial_configuration, test_configuration]
    abs_path = create_json_file(rel_path=file_name, content=configurations)
    return abs_path


@pytest.fixture(scope="function")
def schema_file(tmpdir, schema, create_json_file):
    file_name = "schema.json"
    abs_path = create_json_file(rel_path=file_name, content=schema)
    return abs_path


@pytest.fixture(scope="function")
def configuration_manager(initial_configuration, test_configuration, schema):
    initial_configuration_name = initial_configuration["name"]
    configurations = [initial_configuration, test_configuration]
    return ConfigurationManager(
        configurations=configurations,
        initial_configuration=initial_configuration_name,
        schema=schema,
    )


class TestConfigurationManager:
    def test_init(
        self, initial_configuration, test_configuration, schema, schema_violating_configuration
    ):
        # Initialize two configurations. Success expected.
        try:
            configuration_manager = ConfigurationManager(
                configurations=[initial_configuration, test_configuration],
                schema=schema,
                initial_configuration=initial_configuration["name"],
            )
        except:
            assert False

        # Test that the initial configuration is applied correctly. Success expected.
        expected_configuration_name = initial_configuration["name"]
        obtained_configuration_name = configuration_manager.active_configuration
        assert obtained_configuration_name == expected_configuration_name

        # Retrieve the stored settings after init. Success expected.
        expected_settings = initial_configuration["settings"]
        obtained_settings = configuration_manager.configurations[initial_configuration["name"]]
        assert obtained_settings == expected_settings

        expected_settings = test_configuration["settings"]
        obtained_settings = configuration_manager.configurations[test_configuration["name"]]
        assert obtained_settings == expected_settings

        # Initialize a manager with a config that does not follow the schema. Failure expected.
        with pytest.raises(SchemaViolation):
            ConfigurationManager(configurations=[schema_violating_configuration], schema=schema)

        # Pass an initial configuration to an empty configuration manager. Failure expected.
        with pytest.raises(UndefinedConfiguration):
            ConfigurationManager(initial_configuration=initial_configuration["name"])

    def test_from_json(
        self, initial_configuration, test_configuration, configurations_file, schema_file
    ):
        # Initialize a ConfigurationManager from a correct JSON file. Success expected.
        try:
            configuration_manager = ConfigurationManager.from_json(
                configurations_file_path=configurations_file, schema_file_path=schema_file,
            )
        except:
            assert False

    def test_validate_schema(self, initial_configuration, configuration_manager, schema):
        settings_to_validate = initial_configuration["settings"].copy()

        # Test validating settings with less arguments than the scheme. Failure expected.
        removed_key = "integer_setting"
        removed_value = settings_to_validate.pop(removed_key)
        with pytest.raises(SchemaViolation):
            configuration_manager.validate_schema(settings=settings_to_validate)
        # Add the removed key.
        settings_to_validate[removed_key] = removed_value

        # Test validating settings with more arguments than the scheme. Failure expected.
        new_key = "new_integer_setting"
        settings_to_validate[new_key] = 1
        with pytest.raises(SchemaViolation):
            configuration_manager.validate_schema(settings=settings_to_validate)
        # Remove the added key.
        settings_to_validate.pop(new_key)

        # Test validating settings with setting names different to the scheme.
        # Failure expected.
        old_key = "integer_setting"
        new_key = "new_integer_setting"
        # Replace the original setting key by a new key.
        settings_to_validate[new_key] = settings_to_validate.pop(old_key)
        with pytest.raises(SchemaViolation):
            configuration_manager.validate_schema(settings=settings_to_validate)
        # Undo the change of keys.
        settings_to_validate[old_key] = settings_to_validate.pop(new_key)

        # Test validating settings values with different types to the defined in the schema.
        # Failure expected
        key = "integer_setting"
        old_value = settings_to_validate[key]
        settings_to_validate[key] = "1"
        with pytest.raises(SchemaViolation):
            configuration_manager.validate_schema(settings=settings_to_validate)
        # Undo the change of values.
        settings_to_validate[key] = old_value

        # Test validating nested setting values with different types to the defined in the schema.
        # Failure expected
        original_value = settings_to_validate["dict_setting"]["nested_string_setting"]
        settings_to_validate["dict_setting"]["nested_string_setting"] = 1
        with pytest.raises(SchemaViolation):
            configuration_manager.validate_schema(settings=settings_to_validate)
        # Undo the change of values
        settings_to_validate["dict_setting"]["nested_string_setting"] = original_value

        # Test validating settings that follows the schema. Success expected.
        try:
            configuration_manager.validate_schema(settings=settings_to_validate)
        except:
            assert False

    def test_define_configuration(
        self, initial_configuration, test_configuration, schema, schema_violating_configuration
    ):
        configuration_manager = ConfigurationManager(schema=schema)

        # Test defining a configuration in an empty configuration manager. Success expected.
        try:
            configuration_manager.define_configuration(
                name=initial_configuration["name"], settings=initial_configuration["settings"]
            )
        except:
            assert False

        # Test the settings of the defined configuration are stored correctly. Success expected.
        expected_settings = initial_configuration["settings"]
        obtained_setting = configuration_manager.configurations[initial_configuration["name"]]
        assert obtained_setting == expected_settings

        # Override an existing configuration. Success expected.
        new_settings = initial_configuration["settings"].copy()
        new_settings["integer_setting"] = new_settings["integer_setting"] + 1
        configuration_manager.define_configuration(
            name=initial_configuration["name"], settings=new_settings, override=True,
        )
        obtained_setting = configuration_manager.configurations[initial_configuration["name"]]
        assert obtained_setting == new_settings

        # Define a configuration with settings that do not follow the schema. Failure expected.
        with pytest.raises(SchemaViolation):
            configuration_manager.define_configuration(
                name=schema_violating_configuration["name"],
                settings=schema_violating_configuration,
            )

        # Test defining an existent configuration with the override parameter not activated.
        # Failure expected.
        with pytest.raises(ConfigurationAlreadyDefined):
            configuration_manager.define_configuration(
                name=initial_configuration["name"],
                settings=initial_configuration["settings"],
                override=False,
            )

    def test_get_configuration(self, initial_configuration, configuration_manager):
        # Test retrieving a defined configuration. Success expected.
        expected_settings = initial_configuration["settings"]
        obtained_settings = configuration_manager.get_configuration(
            name=initial_configuration["name"]
        )
        assert obtained_settings == expected_settings

        # Test retrieving an undefined configuration. Failure expected.
        with pytest.raises(UndefinedConfiguration):
            configuration_manager.get_configuration(name="undefined_configuration")

    def test_apply_configuration(
        self, initial_configuration, test_configuration, configuration_manager
    ):
        # Test the current configuration is changed correctly. Success expected.
        configuration_manager.apply_configuration(name=test_configuration["name"])
        expected_settings = test_configuration["settings"]
        obtained_settings = configuration_manager.configurations[
            configuration_manager.active_configuration
        ]
        assert obtained_settings == expected_settings

        # Test setting an as initial an undefined configuration. Failure expected.
        with pytest.raises(UndefinedConfiguration):
            configuration_manager.apply_configuration(name="invalid_configuration")

    def test_get_active_configuration(self, initial_configuration, configuration_manager):
        # Test the current configuration is set correclty. Success expected.
        obtained_configuration = configuration_manager.get_active_configuration()
        expected_configuration = initial_configuration["settings"]
        assert obtained_configuration == expected_configuration

    def test_get_setting(self, initial_configuration, configuration_manager):
        # Test a setting value of the current configuration can be correctly retrieved.
        # Success expected.
        obtained_setting = configuration_manager.get_setting(key="integer_setting")
        expected_setting = initial_configuration["settings"]["integer_setting"]
        assert expected_setting == obtained_setting

        # Test retrieving an undefind setting. Failure expected.
        with pytest.raises(UndefinedSetting):
            configuration_manager.get_setting(key="undefined_setting")

        # Test a nested settings value of the current configuration can be correctly retrieved.
        # Success expected.
        obtained_setting = configuration_manager.get_setting(
            key=["dict_setting", "nested_boolean_setting"]
        )
        expected_setting = initial_configuration["settings"]["dict_setting"][
            "nested_boolean_setting"
        ]
        assert expected_setting == obtained_setting

        # Test retrieving an undefind nested setting. Failure expected.
        with pytest.raises(UndefinedSetting):
            configuration_manager.get_setting(key=("dict_setting", "nested_undefined_setting"))
