import json

import jsonschema

from jsonschema import Draft7Validator
from jsonschema.exceptions import ValidationError, SchemaError
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union


"""
Note: This module is a temporary standalone solution, subject to change. Pending implementation of
either a third party solution or a fully featured version someday.
"""


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


class ConfigurationManager:
    """
    The purpose of this abstract class is to centrally manage configuration parameters for an entire
    application.

    We define one such parameters as a `setting`. A `setting` is a key-value pair. We organize
    settings in nested collections.

    A `configuration` is a named collection of settings. We represent a configuration by a JSON
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

    where the value of "settings" is an arbitrary JSON object.

    Optionally, a schema can be provided, using the JSON Schema specification.
    Here's how the schema of the above example would have to look like:

    {
        "name": {"type": "string"},
        "settings": {
            "type": "object",
            "properties": {
                "boolean_setting": {"type": "boolean"},
                "int_setting": {"type": "integer"},
                "object_setting": {
                    "type": "object",
                    "properties": {
                        "nested_float_setting": {"type": "number"},
                        "nested_string_setting": {"type": "string"}
                    }
                }
            }
        }
    }

    Configurations must follow the schema if given.
    """

    JSON = Union[dict, list]

    def __init__(
        self,
        configurations: List[dict] = None,
        schema: JSON = None,
        initial_configuration: str = None,
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
        The schema must conform to draft 7 of the JSON Schema specification [1].
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

        References
        ----------
        [1] :
        https://json-schema.org/specification-links.html#draft-7
        """
        if schema:
            Draft7Validator.check_schema(schema=schema)
        self.schema = schema

        self.configurations = {}
        if configurations:
            for config in configurations:
                settings = config["settings"]
                self.validate_schema(settings=settings)
                self.configurations[config["name"]] = settings

        self.active_configuration: Optional[str] = None
        if initial_configuration:
            self.apply_configuration(name=initial_configuration)

    @classmethod
    def from_json(
        cls,
        configurations_file_path: str,
        schema_file_path: str = None,
        initial_configuration: str = None,
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
            schema=schema,
            initial_configuration=initial_configuration,
        )

    def validate_schema(self, settings: JSON) -> None:
        """
        Throws an exception if a schema was specified and the settings do not comply with it.

        Parameters
        ----------
        settings : Union[dict, list]
            An arbitrary JSON object, parsed to use lists and dictionaries.

        Raises
        ------
        SchemaViolation
            If a schema exists and `settings` does not comply with it.
        """
        if self.schema:
            try:
                jsonschema.validate(instance=settings, schema=self.schema)
            except:
                raise SchemaViolation

    def define_configuration(self, name: str, settings: JSON, override: bool = False) -> None:
        """
        Adds a new configuration to the set of available configurations, which can be refrenced by
        name.

        If the configuration already exists, an exception will be thrown unless `override` is set to
        True.

        The given `configuration` must follow the given schema, if any.

        Parameters
        ----------
        name : str
            ID of the configuration.
        settings : Union[dict, list]
            An arbitrary JSON object, parsed to use dictionaries and lists.
        override : bool, optional
            If set to True, previous configurations with the same name will be overridden.

        Raises
        ------
        ConfigurationAlreadyDefined
            If `override` is set to False and a configuration with the same name already exists.

        InvalidConfiguration
            If the configuration does not follow the schema.
        """
        if not override and name in self.configurations:
            raise ConfigurationAlreadyDefined(name=name)

        self.validate_schema(settings=settings)
        self.configurations[name] = settings

        # If the modified config is the active one, reapply it
        if name == self.active_configuration:
            self.apply_configuration(name=name)

    def get_configuration(self, name: str) -> JSON:
        """
        Retrieves all the settings of an available configuration.

        Parameters
        ----------
        name : str
            Name of the configuration.

        Returns
        -------
        Union[dict, list]
            Arbitrary JSON-like object with the contents of the requested configuration.

        Raises
        ------
        UndefinedConfiguration
            If no configuration with that name exists.
        """
        try:
            return self.configurations[name]
        except KeyError:
            raise UndefinedConfiguration(name=name)

    def apply_configuration(self, name: str) -> None:
        """
        Sets a given configuration as the active configuration.

        Parameters
        ----------
        name: str
            ID of the configuration.

        Raises
        ------
        UndefinedConfiguration
            If no configuration with that name exists.
        """
        if name not in self.configurations:
            raise UndefinedConfiguration(name=name)
        self.active_configuration = name

    def get_active_configuration(self) -> JSON:
        """
        Retrieve all settings from the active configuration.

        Returns
        -------
        Union[dict, list]
            Arbitrary JSON-like object with the contents of the active configuration.

        Raises
        ------
        NoActiveConfiguration
            If no configuration is set to active
        UndefinedConfiguration
            If the active configuration is not available.
        """
        if not self.active_configuration:
            raise NoActiveConfiguration
        return self.get_configuration(name=self.active_configuration)

    def get_setting(self, key: Any) -> Any:
        """
        Retrieve the value of a particular setting in the active configuration. To access a nested
        value, pass the list of the necessary keys needed to traverse the nesting in order.

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
        active_configuration = self.get_active_configuration()
        if type(key) in (str, int):
            if key not in active_configuration:
                raise UndefinedSetting
            setting = active_configuration[key]
        elif type(key) in (list, tuple):
            setting = active_configuration
            for k in key:
                if k not in setting:
                    raise UndefinedSetting
                setting = setting[k]
        else:
            raise TypeError("'name' must be a key/index or a list/tuple of keys/indices")

        return setting
