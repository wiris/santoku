import pytest

from santoku.utils.configuration_manager import (
    ConfigurationManager,
    UndefinedConfiguration,
    UndefinedSetting,
)


@pytest.fixture(scope="class")
def boolean_setting():
    return "BOOLEAN_SETTING"


@pytest.fixture(scope="class")
def string_setting():
    return "STRING_SETTING"


@pytest.fixture(scope="function")
def default_configuration(boolean_setting, string_setting):
    return {
        "NAME": "DEFAULT",
        "CONFIG": {boolean_setting: True, string_setting: "default_string_value"},
    }


@pytest.fixture(scope="function")
def test_configuration(boolean_setting, string_setting):
    return {"NAME": "TEST", "CONFIG": {boolean_setting: False, string_setting: "test_string_value"}}


@pytest.fixture(scope="function")
def configuration_manager(default_configuration, test_configuration):
    predefined_configurations = [default_configuration, test_configuration]
    return ConfigurationManager(
        predefined_configurations=predefined_configurations,
        default_configuration=default_configuration["NAME"],
    )


class TestConfigurationManager:
    def test_get_setting(
        self, boolean_setting, string_setting, default_configuration, configuration_manager
    ):
        # Get a setting from the current configuration. Success expected.
        expected_value = default_configuration["CONFIG"][boolean_setting]
        obtained_value = configuration_manager.get_setting(key=boolean_setting)
        assert obtained_value == expected_value

        expected_value = default_configuration["CONFIG"][string_setting]
        obtained_value = configuration_manager.get_setting(key=string_setting)
        assert obtained_value == expected_value

        # Get an undefined setting from the current configuration. Failure expected.
        undefined_setting_key = "undefined_setting"
        expected_message = f"Setting '{undefined_setting_key}' undefined."
        with pytest.raises(UndefinedSetting, match=expected_message) as e:
            configuration_manager.get_setting(key=undefined_setting_key)

    def test_list_settings(
        self, boolean_setting, string_setting, default_configuration, configuration_manager
    ):
        # List all settings defined in the current configuration. Success expected.
        expected_settings = [(boolean_setting, default_configuration["CONFIG"][boolean_setting])]
        expected_settings.append((string_setting, default_configuration["CONFIG"][string_setting]))
        obtained_settings = configuration_manager.list_settings()
        assert set(obtained_settings) == set(expected_settings)

    def test_set_setting(self, boolean_setting, default_configuration, configuration_manager):
        # Change the value of an already defined setting in the current configuration.
        # Success expected.
        expected_value = default_configuration["CONFIG"][boolean_setting]
        obtained_value = configuration_manager.get_setting(key=boolean_setting)
        assert obtained_value == expected_value

        expected_value = not expected_value
        configuration_manager.set_setting(key=boolean_setting, value=expected_value)
        obtained_value = configuration_manager.get_setting(key=boolean_setting)
        assert obtained_value == expected_value

    def test_define_configuration(self, boolean_setting, string_setting):
        # Add a configuration to an empty configuration manager and get its settings.
        # Success expected.
        configuration_manager = ConfigurationManager()
        new_configuration = {
            "NAME": "NEW_CONFIG",
            "CONFIG": {boolean_setting: False, string_setting: "new_config_string_value"},
        }
        configuration_manager.define_configuration(
            name=new_configuration["NAME"], configuration=new_configuration["CONFIG"]
        )

        expected_value = new_configuration["CONFIG"][boolean_setting]
        obtained_value = configuration_manager.get_setting(key=boolean_setting)
        assert obtained_value == expected_value

        expected_value = new_configuration["CONFIG"][string_setting]
        obtained_value = configuration_manager.get_setting(key=string_setting)
        assert obtained_value == expected_value

    def test_get_configuration(
        self, default_configuration, test_configuration, configuration_manager
    ):
        # Get the predefined configurations in the configuration manager. Success expected.
        config_name = default_configuration["NAME"]
        expected_configuration = default_configuration["CONFIG"]
        obtained_configuration = configuration_manager.get_configuration(name=config_name)
        assert obtained_configuration == expected_configuration

        config_name = test_configuration["NAME"]
        expected_configuration = test_configuration["CONFIG"]
        obtained_configuration = configuration_manager.get_configuration(name=config_name)
        assert obtained_configuration == expected_configuration

        # Get an undefined configurations. Failure expected.
        undefined_configuration_name = "undefined_configuration"
        expected_message = f"Configuration '{undefined_configuration_name}' undefined."
        with pytest.raises(UndefinedConfiguration, match=expected_message) as e:
            configuration_manager.get_configuration(name=undefined_configuration_name)

    def test_get_current_configuration(self, default_configuration, configuration_manager):
        # Get the current configuration. Success expected.
        expected_configuration = default_configuration["NAME"]
        obtained_configuration = configuration_manager.get_current_configuration()
        assert obtained_configuration == expected_configuration

    def test_list_configurations(
        self, default_configuration, test_configuration, configuration_manager
    ):
        # List all the configurations in the configuration manager. Success expected.
        expected_configurations = [default_configuration["NAME"], test_configuration["NAME"]]
        obtained_configurations = configuration_manager.list_configurations()
        assert set(expected_configurations) == set(obtained_configurations)

    def test_apply_configuration(self, boolean_setting, test_configuration, configuration_manager):
        # Change the default configuration of the configuration manager and get a setting.
        # Success expected.
        expected_configuration_name = test_configuration["NAME"]
        configuration_manager.apply_configuration(name=expected_configuration_name)
        obtained_configuration_name = configuration_manager.get_current_configuration()
        assert expected_configuration_name == obtained_configuration_name

        expected_setting_value = test_configuration["CONFIG"][boolean_setting]
        obtained_setting_value = configuration_manager.get_setting(key=boolean_setting)
        assert expected_setting_value == obtained_setting_value

        # Pass a default configuration to an empty configuration manager. Failure expected.
        undefined_configuration_name = "undefined_configuration"
        expected_message = f"Configuration '{undefined_configuration_name}' undefined."
        with pytest.raises(UndefinedConfiguration, match=expected_message) as e:
            ConfigurationManager(default_configuration=undefined_configuration_name,)
