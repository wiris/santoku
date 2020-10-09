import json

import jsonschema

from jsonschema import Draft7Validator
from jsonschema.exceptions import ValidationError, SchemaError
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union


"""
Note: This module is a temporary standalone solution, subject to change. Pending implementation of
either a third party solution or a fully featured version someday.
"""


class ConfigurationAlreadyDefined(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(f"Configuration '{name}' already exists. ")


class IllegalAccessPattern(Exception):
    def __init__(self) -> None:
        super().__init__(f"Acessing non-final nodes in the settings hierarchy is not allowed")


class InvalidConfiguration(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class NoActiveConfiguration(Exception):
    def __init__(self) -> None:
        super().__init__("No configuration has been activated.")


class UndefinedConfiguration(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(f"Configuration '{name}' undefined.")


class UndefinedSetting(Exception):
    def __init__(self, key: str, available: list) -> None:
        super().__init__(f"Setting '{key}' could not be found amongst {available}.")


class SchemaViolation(Exception):
    def __init__(self) -> None:
        super().__init__("The settings do not conform to the specified schema.")


class ConfigurationManager:
    """
    The purpose of this abstract class is to centrally manage configuration parameters for an
    entire application.

    We define one such parameters as a `setting`. A `setting` is a key-value pair. We organize
    settings in nested collections (essentially JSON objects, except arrays cannot contain objects).

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
        }
    }

    where the value of "settings" is an arbitrary JSON object (the collection of settings).

    Optionally, a schema can be provided, using the JSON Schema specification, to which.
    Here's how the schema for the above example would have to look like:

    {
        "type": "object",
        "properties": {
            "boolean_setting": {"type": "boolean"},
            "int_setting": {"type": "integer"},
            "object_setting": {
                "type": "object",
                "properties": {
                    "nested_float_setting": {"type": "number"},
                    "nested_string_setting": {"type": "string"}
                },
                "required": ["nested_float_setting", "nested_string_setting"],
                "additionalProperties": false
            }
        },
        "required": ["boolean_setting", "integer_setting", "object_setting"],
        "additionalProperties": false
    }

    The settings on each configuration must follow the schema if given.
    """

    JSON = Union[dict, list]  # naive, non-recursive type hint for parsed JSON objects
    configuration_list_schema: JSON = {
        "description": "A list of configurations to be parsed and managed by this class.",
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "name": {"description": "The name of the configuration.", "type": "string"},
                "settings": {
                    "description": "Arbitrary object with values for each setting. Must conform the schema if given",
                    "type": "object",
                },
            },
            "required": ["name", "settings"],
            "additionalProperties": False,
        },
    }

    def __init__(
        self,
        configurations: List[dict] = None,
        schema: JSON = None,
        initial_configuration: str = None,
    ):
        """
        A list of available `configurations` and a `schema` can be passed to be stored in the
        manager. The `initial_configuration` is an optional value. It must be the name of one of
        the `configurations`, which will become the active configuration. This is simply to save
        the user the initial call to `apply_configuration`.

        Parameters
        ----------
        configurations : List[Dict[str, Union[str, Dict[str, Any]]]], optional
            Collection of configurations with different combination of settings.
        schema : Dict[str, Any], optional
            Structure of the settings with the corresponding types of each setting value.
        initial_configuration: str, optional
            Name of the configuration in the `configurations` that will be set as the initial one.

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
        validate_schema
            Called to check whether each configuration follow the schema (if provided).
        define_configuration
            Called to add each configuration to the list of available configurations.
        apply_configuration
            Called to activate the `initial_configuration` (if provided).

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
            jsonschema.validate(instance=configurations, schema=self.configuration_list_schema)
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
        """
        Initialize the manager with the configurations stored in a JSON file.


        """
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

    def get_setting(self, *args) -> Any:
        """
        Retrieve the value of a particular setting in the active configuration. To access a nested
        value, pass all necessary keys needed to traverse the nesting (up to a leaf node) in order.

        Parameters
        ----------
        args
            Sequence of keys needed to traverse the configuration tree up to a leaf node.

        Returns
        -------
        Any
            Value of the setting.

        Raises
        ------
        UndefinedSetting
            If a key that is not in the active configuration is given.
        IllegalAccessPattern
            If the keys do not reach a leaf node in the configuration tree.
        
        Example
        -------
        Given the following settings:
        {
            "my_setting": 3,
            "nested_settings": {"foo": "bar", "stuff": ["this", "that"]}
        }
        You can access each of the individual settings, but only final values:
        >>> configuration_manager.get_setting("my_setting")
        3
        >>> configuration_manager.get_setting("nested_settings", "foo")
        'bar'
        >>> configuration_manager.get_setting("nested_settings", "stuff")
        ['this', 'that']
        >>> configuration_manager.get_setting("nested_settings")
        IllegalAccessPattern: Acessing non-final nodes in the settings hierarchy is not allowed
        """
        setting = self.get_active_configuration()
        for key in args:
            if key not in setting:
                raise UndefinedSetting(key=key, available=list(setting))
            setting = setting[key]

        # Accessing a non-leaf node in the settings hierarchy is disallowed
        if type(setting) == dict:
            raise IllegalAccessPattern

        return setting
