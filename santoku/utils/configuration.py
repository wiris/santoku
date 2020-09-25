import json

import jsonschema

from typing import Any, Dict, List, Optional, Tuple, Union


"""
Note: This module is a temporary standalone solution, subject to change. Pending implementation of
either a third party solution or a fully featured version someday.
"""


class InvalidSettingType(Exception):
    def __init__(self, key: str, type: type) -> None:
        super().__init__(f"Type {type} for setting '{key}' is not supported.")


class UndefinedSetting(Exception):
    def __init__(self, key: str) -> None:
        super().__init__(f"Setting '{key}' undefined.")


class UndefinedConfiguration(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(f"Configuration '{name}' undefined.")


class SchemaViolation(Exception):
    def __init__(self) -> None:
        super().__init__("The settings do not conform to the specified schema.")


class NoActiveConfiguration(Exception):
    def __init__(self) -> None:
        super().__init__("No configuration has been activated.")


class InvalidConfiguration(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class ConfigurationAlreadyDefined(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(f"Configuration '{name}' already exists. ")


class IlegalAccess(Exception):
    def __init__(self, key: List[str]) -> None:
        super().__init__(
            "Returning nested groups of settings is disallowed. "
            f"Key {key} is not suficient to reach a leaf node in the configuration tree."
        )


class Settings:
    """
    A settings object is a recursive structure. It consists of a collection of key-object pairs,
    where the key is a string (the name of the setting) and the object is either a bool, int, float,
    str or another settings object. This allows building complex (i.e. hierarchical) structures.
    
    It can be represented by a JSON object, with the only constraint that it cannot contain a list.
    For example:
    
    {
        "boolean_setting": true,
        "numeric_setting": 42,
        "text_setting": "A long time ago in a galaxy far, far away...",
        "object_setting": {
            "nested_setting_1": True,
            "nested_setting_2": 4,
            ...
        }
    }

    """

    def __init__(self, settings: dict) -> None:
        """
        Gets a potentially nested dictionary structure and recursively parses it.
        """
        self._settings: dict = {}

        for key, value in settings.items():
            if type(value) == dict:
                self._settings[key] = Settings(settings=value)
            elif (
                type(value) == bool
                or type(value) == int
                or type(value) == float
                or type(value) == str
            ):
                self._settings[key] = value
            else:
                raise InvalidSettingType(key=key, type=type(value))

    @classmethod
    def from_json(cls, file_path: str) -> "Settings":
        with open(file_path, "r") as f:
            parsed_json_as_dict = json.load(f)
        return cls(settings=parsed_json_as_dict)

    def to_dict(self) -> dict:
        """Recursively serialize the settings object into a nested dictionary."""
        settings_dict = {}
        for key, value in self._settings.items():
            if type(value) == Settings:
                settings_dict[key] = value.to_dict()
            else:
                settings_dict[key] = value
        return settings_dict

    def to_json(self, file_path: str) -> None:
        with open(file_path, "w") as f:
            json.dump(self.to_dict(), f, indent=4)

    def get_setting(self, key: str) -> Any:
        """
        Retrieves the value of a particular setting.

        Parameters
        ----------
        key : str
            Name of the setting.

        Returns
        -------
        Union[bool, int, float, str, Settings]
            Value of the setting. Either one of the allowed JSON types or another Settings object.

        Raises
        ------
        UndefinedSetting
            If `key` does not correspond to any setting.
        """
        if key not in self._settings:
            raise UndefinedSetting(key=key)

        return self._settings[key]

    def set_setting(self, key: str, value: Union[bool, int, float, str, "Settings"]) -> None:
        """
        Add a key-value pair or replace the value of a setting.

        Parameters
        ----------
        key : str
            Name of the setting.
        value : Union[bool, int, float, str, Settings]
            New value for the setting.
        """
        self._settings[key] = value

    def list_settings(self) -> List[Tuple[str, Any]]:
        """
        List all settings as key-value pairs. Nested settings are returned as settings objects.

        Returns
        -------
        List[Tuple[str, Any]]
            List of pairs key-value settings.
        """
        return [(key, value) for key, value in self._settings.items()]


class ConfigurationManager:
    """
    The purpose of this abstract class is to centrally manage configuration parameters for an entire
    application.

    We define one such parameters as a `setting`. A `setting` is a key-value pair. We organize
    settings in `settings` objects (see `Settings` class).
    
    A `configuration` is a named settings object. We represent a configuration by a JSON
    object following the structure of this example:

    {
        "name": "my_configuration_name",
        "settings": {
            "boolean_setting": true,
            "int_setting": 42,
            "object_setting": {
                "nested_float_setting": 3.14,
                "nested_string_setting": ""
            }
            ...
        }
    }

    where the value of "settings" must be compliant with the specification of a `settings` (see
    `Settings` class).

    Optionally, a schema can be provided, using our own specification, which is close to (but not
    quite, notice we use Python's type names) being a very restricted subset of JSON Schema. Here's
    how the schema of the above example would have to look like:

    {
        "name": {"type": "str"},
        "settings": {
            "type": "object",
            "properties": {
                "boolean_setting": {"type": "bool"},
                "int_setting": {"type": "int"},
                "object_setting": {
                    "type": "object",
                    "properties": {
                        "nested_float_setting": {"type": "float"},
                        "nested_string_setting": {"type": "str"}
                    }
                }
            }
        }
    }
    
    Configurations must follow the schema if given.
    """

    def __init__(
        self,
        configurations: List[Dict[str, Any]] = None,
        initial_configuration: str = None,
        schema: Optional[Dict[str, Any]] = None,
    ):
        """
        A list of `configurations` can be passed to be stored in the manager. If done, an
        `initial_configuration` can be passed to be applied. If not given, no initial configuration
        will be activated and this will be left to the user.

        Parameters
        ----------
        configurations : List[Dict[str, Union[str, Dict[str, Any]]]], optional
            Collection of configurations with different combination of settings.
        initial_configuration: str, optional
            Name of the configuration in the `configurations` that will be set as the initial one.
        schema : Dict[str, Any], optional
            Structure of the settings with the corresponding types of each setting value.

        InvalidConfiguration
            If one or more elements in `configurations` does not contain the "name" or "settings" keys.

        Notes
        -----
            The following structure is assumed for the schema:
            {
                <setting_key>: <type_of_the_setting_value>,
                ...
            }

            The following structure is assumed for the list of predefined configurations:
            [
                {
                    "name": <name_of_the_configuration>,
                    "settings": {
                        <key>: <value>,
                        ...
                    }
                },
                ...
            ]

        See also
        --------
        define_configuration
            This functions is called to add each configuration.
        """
        self._configurations: Dict[str, Settings] = {}
        self._active_configuration: Optional[str] = None
        self._schema: Optional[Dict[str, Any]] = schema

        if configurations:
            for configuration in configurations:
                if "name" not in configuration or "settings" not in configuration:
                    raise InvalidConfiguration(
                        "'name' and 'settings' keys must be included in each configuration dictionary."
                    )
                self.define_configuration(
                    name=configuration["name"], settings=configuration["settings"]
                )
            if initial_configuration:
                self.apply_configuration(name=initial_configuration)

    @classmethod
    def from_json(
        cls,
        configurations_file_path: str,
        initial_configuration: str = None,
        schema_file_path: str = None,
    ) -> "ConfigurationManager":
        with open(configurations_file_path, "r") as f:
            configurations = json.load(f)

        if schema_file_path:
            with open(schema_file_path, "r") as f:
                schema = json.load(f)
        else:
            schema = None

        return cls(
            configurations=configurations,
            initial_configuration=initial_configuration,
            schema=schema,
        )

    def validate_schema(self, schema: Dict[str, Any], settings: Settings) -> bool:
        """
        Returns true if the given Settings object complies with the given schema. Schema must follow
        the specification given in `validate_schema`. 
        """
        settings_list = settings.list_settings()

        if len(schema) != len(settings_list):
            return False

        for (key, value) in settings_list:
            if key not in schema:
                return False
            if type(value) == Settings:
                if not self.validate_schema(schema=schema[key], settings=value):
                    return False
            elif "type" in schema[key]:
                if not type(settings) is getattr(__builtins__, schema[key]["type"]):
                    return False

        return True

    def get_setting(self, key: Union[str, List[str]]) -> Union[bool, int, float, str]:
        """
        Retrieve the value of a particular setting in the active configuration. To access a nested
        setting, pass a list of the necessary keys needed to traverse the nesting in order.

        Parameters
        ----------
        key : Union[str, List[str]]
            Name of the setting or list of names needed to traverse the hierarchy in order to reach
            the setting.

        Returns
        -------
        Any
            Value of the setting.

        Raises
        ------
        UndefinedSetting
            If a `key` that is not in the active configuration is given.
        """
        if not isinstance(key, list):
            key = [key]

        setting_value = self.get_configuration(name=self.get_active_configuration())
        for k in key:
            setting_value = setting_value.get_setting(k)

        # It is disallowed to give the user non-lazy access to underlying objects since it would be
        # a potential source of silent bugs. Only static values (bool|int|float|str) can be returned
        if isinstance(setting_value, Settings):
            raise IlegalAccess(key=key)

        return setting_value

    def set_setting(self, key: Union[str, List[str]], value: Any) -> None:
        """
        Add a new setting or replace the value of an existing setting in the active configuration.

        Parameters
        ----------
        key : Union[str, List[str]]
            Name of the setting or list of names needed to traverse the hierarchy in order to reach
            the setting.
        value : Any
            New value of the setting or value of the new setting, if inexistent.
        """
        active_configuration = self.get_configuration(name=self.get_active_configuration())

        if type(value) == dict:
            value = Settings(settings=value)

        new_configuration = Settings(settings=active_configuration.to_dict())

        if not isinstance(key, list):
            key = [key]

        setting = new_configuration
        for k in key[:-1]:
            setting = setting.get_setting(key=k)

        new_configuration.set_setting(key=key[-1], value=value)

        self.define_configuration(name=self.get_active_configuration(), settings=new_configuration)

    def list_settings(self) -> List[Tuple[str, Union[bool, int, float, str, Settings]]]:
        """
        Generates all key-value pairs settings in the active configuration.

        Returns
        -------
        Union[bool, int, float, str, Settings]
            List of pairs key-value settings.
        """
        return self.get_configuration(name=self.get_active_configuration()).list_settings()

    def define_configuration(
        self, name: str, settings: Union[Dict[str, Any], Settings], override: bool = False
    ) -> None:
        """
        Adds a new configuration to the list of available configurations. Its settings can either be
        a Python dictionary or a `Settings` object.
        
        If the configuration already exists, an exception will be thrown unless `override` is set to
        True.
        
        The given `configuration` must follow the schema given to the manager, if any.

        Parameters
        ----------
        name : str
            Name of the configuration. Must be unique, unless the override option is set to true.
        settings : Union[Dict[str, Any], Settings]
            Content of the configuration. 
        override : bool, optional
            When the name of the given configuration is already defined, if this is set to True, the
            previous configuration will be overridden. Otherwise, an exception will be thrown.
            Not enabled by default.

        Raises
        ------
        ConfigurationAlreadyDefined
            If `override` is set to False and the configuration was defined previously.

        InvalidConfiguration
            If the configuration does not follow the schema difined previously.

        """
        if not override and name in self._configurations:
            raise ConfigurationAlreadyDefined(name=name)

        if not isinstance(settings, Settings):
            settings = Settings(settings=settings)

        if self._schema:
            if not self.validate_schema(schema=self._schema, settings=settings):
                raise SchemaViolation

        self._configurations[name] = settings

        # If the modified config is the active one, reapply it
        if name == self._active_configuration:
            self.apply_configuration(name=name)

    def get_configuration(self, name: str) -> Settings:
        """
        Retrieves the content of a configuration.

        Parameters
        ----------
        name : str
            Name of the configuration.

        Returns
        -------
        Settings
            Configuration content.

        Raises
        ------
        UndefinedConfiguration
            If the configuration was not defined previously.
        """
        try:
            return self._configurations[name]
        except KeyError:
            raise UndefinedConfiguration(name=name)

    def get_active_configuration(self) -> str:
        """
        Obtains the name of the currently active configuration.

        Returns
        -------
        str
            The name of the active configuration.
        """
        if not self._active_configuration:
            raise NoActiveConfiguration

        return self._active_configuration

    def list_configurations(self) -> List[str]:
        """
        Generates the names of all defined configurations.

        Returns
        -------
        List[str]
            List of names of the configurations.

        """
        return [name for name in self._configurations]

    def apply_configuration(self, name: str) -> None:
        """
        Sets the given configuration as the active one.

        Parameters
        ----------
        name : str
            Name of the configuration to be applied.

        Raises
        -------
        UndefinedConfiguration
            If the configuration was not defined previously.
        """
        if name not in self._configurations:
            raise UndefinedConfiguration(name=name)

        self._active_configuration = name
