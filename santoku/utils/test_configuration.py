import json

import pytest

from collections import namedtuple

from santoku.utils.configuration import (
    Settings,
    ConfigurationManager,
    UndefinedConfiguration,
    UndefinedSetting,
    ConfigurationAlreadyDefined,
    InvalidConfiguration,
)

# Setting = namedtuple("Setting", "name value")
# Configuration = namedtuple("Configuration", "name settings")


# @pytest.fixture(scope="class")
# def complex_schema():
#     return {
#         "integer_setting": int,
#         "boolean_setting": bool,
#         "string_setting": str,
#         "float_setting": float,
#         "dict_setting": {"list_setting": [str], "tuple_setting": (int, bool),},
#     }


# @pytest.fixture(scope="function")
# def complex_configuration():
#     return {
#         "integer_setting": 1,
#         "boolean_setting": True,
#         "string_setting": "string value",
#         "float_setting": 1.0,
#         "dict_setting": {"list_setting": ["string value in tuple"], "tuple_setting": (1, False),},
#     }


# @pytest.fixture(scope="class")
# def initial_boolean_setting():
#     return Setting("boolean_setting", True)


# @pytest.fixture(scope="class")
# def initial_string_setting():
#     return Setting("string_setting", "initial string value")


# @pytest.fixture(scope="class")
# def initial_schema(initial_boolean_setting, initial_string_setting):
#     return {
#         initial_boolean_setting.name: bool,
#         initial_string_setting.name: str,
#     }


# @pytest.fixture(scope="class")
# def initial_configuration(initial_boolean_setting, initial_string_setting):
#     settings = {
#         initial_boolean_setting.name: initial_boolean_setting.value,
#         initial_string_setting.name: initial_string_setting.value,
#     }
#     return Configuration("initial", settings)


# @pytest.fixture(scope="class")
# def initial_configuration_structured(
#     initial_boolean_setting, initial_string_setting, initial_configuration
# ):
#     return {
#         "name": initial_configuration.name,
#         "settings": {
#             initial_boolean_setting.name: initial_boolean_setting.value,
#             initial_string_setting.name: initial_string_setting.value,
#         },
#     }


# @pytest.fixture(scope="class")
# def test_boolean_setting():
#     return Setting("boolean_setting", False)


# @pytest.fixture(scope="class")
# def test_string_setting():
#     return Setting("string_setting", "test string value")


# @pytest.fixture(scope="class")
# def test_configuration(test_boolean_setting, test_string_setting):
#     settings = {
#         test_boolean_setting.name: test_boolean_setting.value,
#         test_string_setting.name: test_string_setting.value,
#     }
#     return Configuration("test", settings)


# @pytest.fixture(scope="class")
# def test_configuration_structured(test_boolean_setting, test_string_setting, test_configuration):
#     return {
#         "name": test_configuration.name,
#         "settings": {
#             test_boolean_setting.name: test_boolean_setting.value,
#             test_string_setting.name: test_string_setting.value,
#         },
#     }


# @pytest.fixture(scope="class")
# def configuration_manager(
#     initial_schema,
#     initial_configuration_structured,
#     test_configuration_structured,
#     initial_configuration,
# ):
#     # Initialize the configuration manager with two configurations.
#     predefined_configurations = [initial_configuration_structured, test_configuration_structured]
#     configuration_manager = ConfigurationManager(
#         schema=initial_schema,
#         predefined_configurations=predefined_configurations,
#         initial_configuration=initial_configuration.name,
#     )
#     configuration_manager.apply_configuration(name=initial_configuration.name)

#     return configuration_manager


# @pytest.fixture(scope="class")
# def new_boolean_setting():
#     return Setting("boolean_setting", True)


# @pytest.fixture(scope="class")
# def new_string_setting():
#     return Setting("string_setting", "new string value")


# @pytest.fixture(scope="class")
# def new_configuration(new_boolean_setting, new_string_setting):
#     settings = Settings(new_boolean_setting, new_string_setting)
#     return Configuration("new", settings)


# @pytest.fixture(scope="class")
# def new_named_configuration(new_configuration):
#     new_settings = new_configuration.settings
#     return [
#         {
#             "name": new_configuration.name,
#             "settings": {
#                 new_settings.setting1.name: new_settings.setting1.value,
#                 new_settings.setting2.name: new_settings.setting2.value,
#             },
#         }
#     ]


@pytest.fixture(scope="class")
def settings_sample():
    return {
        "integer_setting": 1,
        "boolean_setting": True,
        "string_setting": "string value",
        "float_setting": 1.0,
        "dict_setting": {
            "nested_string_setting": "dict string value",
            "nested_boolean_setting": False,
        },
    }


@pytest.fixture(scope="function")
def create_settings_file(settings_sample):
    def _create_settings_file(path):

        with open(path, "w") as f:
            json.dump(settings_sample, f)

    yield _create_settings_file


@pytest.fixture(scope="function")
def settings(settings_sample):
    return Settings(settings=settings_sample)


class TestSettings:
    def test_initialization(self, settings_sample):
        # Test initializing Settings stores settings values correctly and dicts are converted
        # into Settings objects. Success expected.
        settings = Settings(settings=settings_sample)
        created_settings = settings._settings

        expected_value = settings_sample["integer_setting"]
        obtained_value = created_settings["integer_setting"]
        assert obtained_value == expected_value

        expected_value = settings_sample["boolean_setting"]
        obtained_value = created_settings["boolean_setting"]
        assert obtained_value == expected_value

        expected_value = settings_sample["string_setting"]
        obtained_value = created_settings["string_setting"]
        assert obtained_value == expected_value

        expected_value = settings_sample["float_setting"]
        obtained_value = created_settings["float_setting"]
        assert obtained_value == expected_value

        expected_dict_setting = settings_sample["dict_setting"]
        created_dict_setting = created_settings["dict_setting"]
        assert type(created_dict_setting) == Settings

        expected_value = expected_dict_setting["nested_string_setting"]
        obtained_value = created_dict_setting._settings["nested_string_setting"]
        assert obtained_value == expected_value

        expected_value = expected_dict_setting["nested_boolean_setting"]
        obtained_value = created_dict_setting._settings["nested_boolean_setting"]
        assert obtained_value == expected_value

    def test_init_from_json(self, tmpdir, create_settings_file):
        # Test initializing a Settings reading from a JSON file. Success expected.
        file_path = tmpdir.join("settings.json")
        create_settings_file(path=file_path)
        try:
            settings = Settings.from_json(file_path=file_path)
        except:
            assert False
        else:
            assert True

    def test_to_dict(self, settings_sample, settings):
        # Test if the serialized settings object has the same form than the original dictionary.
        # Success expected.
        expected_dict = settings_sample
        obtained_dict = settings.to_dict()
        assert obtained_dict == expected_dict

    def test_to_json(self, tmpdir, settings_sample, settings):
        # Test if the JSON file generated by the Settigns class match the original dictionary that
        # created the Settings class. Success expected.
        file_path = tmpdir.join("settings.json")
        settings.to_json(file_path=file_path)
        expected_json = settings_sample
        with open(file_path, "r") as f:
            obtained_json = json.load(f)
        assert obtained_json == settings_sample

    def test_get_setting(self, settings_sample, settings):
        # Test settings values are stored correctly. Success expected.
        expected_value = settings_sample["integer_setting"]
        obtained_value = settings.get_setting(key="integer_setting")
        assert obtained_value == expected_value

        expected_value = settings_sample["boolean_setting"]
        obtained_value = settings.get_setting(key="boolean_setting")
        assert obtained_value == expected_value

        expected_value = settings_sample["string_setting"]
        obtained_value = settings.get_setting(key="string_setting")
        assert obtained_value == expected_value

        expected_value = settings_sample["float_setting"]
        obtained_value = settings.get_setting(key="float_setting")
        assert obtained_value == expected_value

        expected_dict_setting = settings_sample["dict_setting"]
        created_dict_setting = settings.get_setting(key="dict_setting")
        assert type(created_dict_setting) == Settings

        expected_value = expected_dict_setting["nested_string_setting"]
        obtained_value = created_dict_setting.get_setting(key="nested_string_setting")
        assert obtained_value == expected_value

        expected_value = expected_dict_setting["nested_boolean_setting"]
        obtained_value = created_dict_setting.get_setting(key="nested_boolean_setting")
        assert obtained_value == expected_value

    def test_set_setting(self, settings):
        # Test changing the value of a setting. Success expected.
        created_settings = settings._settings
        expected_value = created_settings["integer_setting"] + 1
        settings.set_setting(key="integer_setting", value=expected_value)
        obtained_value = created_settings["integer_setting"]
        assert obtained_value == expected_value

        # Test changing the value of a nested setting. Success expected.
        created_dict_setting = settings.get_setting(key="dict_setting")
        expected_value = not created_dict_setting._settings["nested_boolean_setting"]
        created_dict_setting.set_setting(key="nested_boolean_setting", value=expected_value)
        obtained_value = created_settings["dict_setting"]._settings["nested_boolean_setting"]
        assert obtained_value == expected_value


class TestConfigurationManager:
    def test_validate_configuration_schema(self, complex_schema, complex_configuration):
        # Test validating a configuration that follows the schema. Success expected.
        try:
            ConfigurationManager(
                schema=complex_schema,
                predefined_configurations=[{"name": "complex", "settings": complex_configuration}],
            )
        except InvalidConfiguration:
            assert False
        else:
            assert True

        # Test validating a configuration with less arguments than the scheme. Failure expected.
        removed_key = "integer_setting"
        removed_value = complex_configuration.pop(removed_key)
        expected_message = "The given configuration does not follow the predefined schema."
        with pytest.raises(InvalidConfiguration, match=expected_message):
            ConfigurationManager(
                schema=complex_schema,
                predefined_configurations=[{"name": "complex", "settings": complex_configuration}],
            )
        # Add the removed key.
        complex_configuration[removed_key] = removed_value

        # Test validating a configuration with more arguments than the scheme. Failure expected.
        new_key = "new_integer_setting"
        complex_configuration[new_key] = 1
        expected_message = "The given configuration does not follow the predefined schema."
        with pytest.raises(InvalidConfiguration, match=expected_message):
            ConfigurationManager(
                schema=complex_schema,
                predefined_configurations=[{"name": "complex", "settings": complex_configuration}],
            )
        # Remove the added key.
        complex_configuration.pop(new_key)

        # Test validating a configuration with setting names different to the scheme.
        # Failure expected.
        old_key = "integer_setting"
        new_key = "new_integer_setting"
        complex_configuration[new_key] = complex_configuration.pop(old_key)
        with pytest.raises(InvalidConfiguration, match=expected_message):
            ConfigurationManager(
                schema=complex_schema,
                predefined_configurations=[{"name": "complex", "settings": complex_configuration}],
            )
        # Undo the change of key.
        complex_configuration[old_key] = complex_configuration.pop(new_key)

        # Test validating a configuration with setting values different to the scheme.
        # Failure expected
        key = "integer_setting"
        old_value = complex_configuration[key]
        complex_configuration[key] = 1.0
        with pytest.raises(InvalidConfiguration, match=expected_message):
            ConfigurationManager(
                schema=complex_schema,
                predefined_configurations=[{"name": "complex", "settings": complex_configuration}],
            )
        complex_configuration[key] = old_value

        complex_configuration["dict_setting"]["tuple_setting"] = (1, "string value")
        with pytest.raises(InvalidConfiguration, match=expected_message):
            ConfigurationManager(
                schema=complex_schema,
                predefined_configurations=[{"name": "complex", "settings": complex_configuration}],
            )

    def test_get_setting(
        self, initial_boolean_setting, initial_string_setting, configuration_manager,
    ):
        # Get a setting from the active configuration. Success expected.
        expected_value = initial_boolean_setting.value
        obtained_value = configuration_manager.get_setting(key=initial_boolean_setting.name)
        assert obtained_value == expected_value

        expected_value = initial_string_setting.value
        obtained_value = configuration_manager.get_setting(key=initial_string_setting.name)
        assert obtained_value == expected_value

        # Get an undefined setting from the active configuration. Failure expected.
        undefined_setting_key = "undefined_setting"
        expected_message = f"Setting '{undefined_setting_key}' undefined."
        with pytest.raises(UndefinedSetting, match=expected_message):
            configuration_manager.get_setting(key=undefined_setting_key)

    def test_list_settings(
        self, initial_boolean_setting, initial_string_setting, configuration_manager
    ):
        # List all settings defined in the active configuration. Success expected.
        expected_settings = [
            (initial_boolean_setting.name, initial_boolean_setting.value),
            (initial_string_setting.name, initial_string_setting.value),
        ]
        obtained_settings = configuration_manager.list_settings()
        assert set(obtained_settings) == set(expected_settings)

    def test_set_setting(self, initial_boolean_setting, configuration_manager):
        # Change the value of an already defined setting in the active configuration.
        # Success expected.
        expected_value = not initial_boolean_setting.value
        configuration_manager.set_setting(key=initial_boolean_setting.name, value=expected_value)
        obtained_value = configuration_manager._settings[initial_boolean_setting.name]
        assert obtained_value == expected_value

    def test_define_configuration(
        self,
        initial_boolean_setting,
        initial_string_setting,
        initial_schema,
        initial_configuration,
    ):
        # Add a configuration to an empty configuration manager and get its settings.
        # Success expected.
        configuration_manager = ConfigurationManager(schema=initial_schema)
        configuration_manager.define_configuration(
            name=initial_configuration.name, configuration=initial_configuration.settings
        )
        # Apply configuration.
        configuration_manager._settings = initial_configuration.settings
        configuration_manager._active_configuration = initial_configuration.name

        expected_value = initial_boolean_setting.value
        obtained_value = configuration_manager._settings[initial_boolean_setting.name]
        assert obtained_value == expected_value

        expected_value = initial_string_setting.value
        obtained_value = configuration_manager._settings[initial_string_setting.name]
        assert obtained_value == expected_value

        # Override a configuration that already exists. Success expected.
        expected_value = not initial_boolean_setting.value
        new_configuration = initial_configuration.settings
        new_configuration[initial_boolean_setting.name] = expected_value

        configuration_manager.define_configuration(
            name=initial_configuration.name, configuration=new_configuration, override=True,
        )
        obtained_value = configuration_manager._settings[initial_boolean_setting.name]
        assert obtained_value == expected_value

        # Define a configuration that already exists without enabling override. Failure expected.
        expected_message = f"Configuration '{initial_configuration.name}' already exists."
        with pytest.raises(ConfigurationAlreadyDefined, match=expected_message):
            configuration_manager.define_configuration(
                name=initial_configuration.name, configuration=initial_configuration.settings
            )

    def test_get_configuration(
        self, initial_configuration, test_configuration, configuration_manager
    ):
        # Get the predefined configurations in the configuration manager. Success expected.
        expected_configuration = initial_configuration.settings
        obtained_configuration = configuration_manager.get_configuration(
            name=initial_configuration.name
        )
        assert obtained_configuration == expected_configuration

        expected_configuration = test_configuration.settings
        obtained_configuration = configuration_manager.get_configuration(
            name=test_configuration.name
        )
        assert obtained_configuration == expected_configuration

        # Get an undefined configurations. Failure expected.
        undefined_configuration_name = "undefined_configuration"
        expected_message = f"Configuration '{undefined_configuration_name}' undefined."
        with pytest.raises(UndefinedConfiguration, match=expected_message):
            configuration_manager.get_configuration(name=undefined_configuration_name)

    def test_edit_configuration(
        self, initial_boolean_setting, initial_configuration, configuration_manager
    ):
        # Get the edited configuration. Sucess expected.
        expected_value = not initial_boolean_setting.value
        expected_configuration = initial_configuration.settings
        expected_configuration[initial_boolean_setting.name] = expected_value
        configuration_manager.edit_configuration(
            name=initial_configuration.name, configuration_override=expected_configuration
        )

        obtained_configuration = configuration_manager._configurations[initial_configuration.name]
        assert obtained_configuration == expected_configuration

        obtained_value = configuration_manager._settings[initial_boolean_setting.name]
        assert obtained_value == expected_value

        # Edit an undefined configuration. Failure expected.
        undefined_configuration_name = "undefined_configuration"
        expected_message = (
            "Use `define_configuration` method instead to create a new configuration."
        )
        with pytest.raises(Exception, match=expected_message):
            configuration_manager.edit_configuration(
                name=undefined_configuration_name, configuration_override=[]
            )

        # Give a configuration that does not follow the scheme. Failure expected.
        expected_message = "The given configuration does not follow the predefined schema."
        expected_configuration[initial_boolean_setting.name] = "string value"
        with pytest.raises(Exception, match=expected_message):
            configuration_manager.edit_configuration(
                name=initial_configuration.name, configuration_override=expected_configuration
            )

    def test_get_active_configuration(self, initial_configuration, configuration_manager):
        # Get the active configuration. Success expected.
        expected_configuration = initial_configuration.name
        obtained_configuration = configuration_manager.get_active_configuration()
        assert obtained_configuration == expected_configuration

    def test_list_configurations(
        self, initial_configuration, test_configuration, configuration_manager
    ):
        # List all the configurations in the configuration manager. Success expected.
        expected_configurations = [initial_configuration.name, test_configuration.name]
        obtained_configurations = configuration_manager.list_configurations()
        assert set(expected_configurations) == set(obtained_configurations)

    def test_apply_configuration(
        self, test_boolean_setting, test_configuration, configuration_manager
    ):
        # Change the initial configuration of the configuration manager and get a setting.
        # Success expected.
        expected_configuration_name = test_configuration.name
        configuration_manager.apply_configuration(name=expected_configuration_name)
        obtained_configuration_name = configuration_manager._active_configuration
        assert expected_configuration_name == obtained_configuration_name

        expected_setting_value = test_boolean_setting.value
        obtained_setting_value = configuration_manager._settings[test_boolean_setting.name]
        assert expected_setting_value == obtained_setting_value

