from typing import List, Tuple, Dict, Any


class UndefinedSetting(Exception):
    def __init__(self, key: str):
        super().__init__(f"Setting '{key}' undefined.")


class UndefinedConfiguration(Exception):
    def __init__(self, configuration: str):
        super().__init__(f"Configuration '{configuration}' undefined.")


class InvalidConfiguration(Exception):
    def __init__(self, message):
        super().__init__(message)


class ConfigurationAlreadyDefined(Exception):
    def __init__(self, configuration):
        super().__init__(
            f"Configuration '{configuration}' already exists. "
            "You can set the override option to True to redefine it. "
            "You can also use `edit_configuration()` instead to modify it."
        )


class ConfigurationManager:
    """
    The purpose of this abstract class is to centrally manage configuration parameters for an entire
    application.

    We define one of those parameters as a `setting`. A `setting` is a key-value pair, where the key
    is a string (its unique ID) and the value can be an object of any type. The following are all
    valid settings:

    "boolean_setting": True
    "numeric_setting": 42
    "text_setting": "A long time ago in a galaxy far, far away..."
    "object_setting": {
        "key1": True,
        "key2": 4,
        ...
    }

    A `configuration` is a named collection of settings, taking the form of a dictionary with the
    following structure:

    {
        "name": <configuration name (str, unique)>,
        "settings": {
            "setting1": <value1>,
            "setting2": <value2>,
            ...
        }
    }
    """

    _schema: Dict[str, Any]
    _settings: Dict[str, Any]
    _configurations: Dict[str, Dict[str, Any]]
    _active_configuration: str

    def __init__(
        self,
        schema: Dict[str, Any],
        predefined_configurations: List[Dict[str, Any]] = None,
        initial_configuration: str = None,
    ):
        """
        Initializes internal structures that store the configurations.

        A list of `predefined_configurations` can be passed to initialze the configuration manager,
        together with the name of the `initial_configuration`, if it's not given, no configuration
        is applied initially.

        Parameters
        ----------
        schema : Dict[str, Any]
            Structure of the settings with the corresponding types of each setting value.
        predefined_configurations : List[Dict[str, Any]], optional
            Collection of configurations with different combination of settings.
        initial_configuration: str, optional
            Name of the configuration in the `predefined_configurations` that will be set as the
            initial one.

        InvalidConfiguration
            If any configuration in the `predefined_configurations` does not contain the "name" or
            "settings" argument.

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

        self._schema = schema
        self._settings: Dict[str, Any] = {}
        self._configurations: Dict[str, Dict[str, Any]] = {}
        self._active_configuration = ""

        if predefined_configurations:

            for configuration in predefined_configurations:

                if "name" not in configuration or "settings" not in configuration:
                    raise InvalidConfiguration(
                        "'name' and 'settings' arguments must be contained in a configuration."
                    )

                self.define_configuration(
                    name=configuration["name"], configuration=configuration["settings"]
                )

            if initial_configuration:
                self.apply_configuration(name=initial_configuration)

    def _validate_configuration_schema(
        self, schema: Dict[str, Any], configuration: Dict[str, Any]
    ) -> bool:
        if isinstance(schema, dict) and isinstance(configuration, dict):
            # The structure is a dict of types or other dicts
            return len(schema) == len(configuration) and all(
                k in configuration
                and self._validate_configuration_schema(
                    schema=schema[k], configuration=configuration[k]
                )
                for k in schema
            )

        if isinstance(schema, list) and isinstance(configuration, list):
            # The structure is a list.
            return len(schema) == len(configuration) and all(
                self._validate_configuration_schema(schema=schema[0], configuration=config)
                for config in configuration
            )

        if isinstance(schema, tuple) and isinstance(configuration, tuple):
            # The structure is a tuple.
            return len(schema) == len(configuration) and all(
                self._validate_configuration_schema(schema=type_schema, configuration=config)
                for type_schema, config in zip(schema, configuration)
            )

        if isinstance(schema, type):
            # The structure is the type of indicated in schema
            return isinstance(configuration, schema)

        else:
            # The structure is neither a dict, nor list, nor tuple, nor type
            return False

    def get_setting(self, key: str) -> str:
        """
        Retrieves the value of a particular setting in the active configuration.

        Parameters
        ----------
        key : str
            Name of the setting.

        Returns
        -------
        str
            Value of the setting.

        Raises
        ------
        UndefinedSetting
            If a `key` that is not in the active configuration is given.

        """

        if key in self._settings:
            return self._settings[key]
        else:
            raise UndefinedSetting(key=key)

    def list_settings(self) -> List[Tuple[str, str]]:
        """
        Generates all key-value pairs settings in the active configuration.

        Returns
        -------
        List[Tuple[str, str]]
            List of pairs key-value settings.

        """
        return [(key, value) for key, value in self._settings.items()]

    def set_setting(self, key: str, value: Any) -> None:
        """
        Adds a key-value pair or replace the value of a setting in the active configuration.

        Parameters
        ----------
        key : str
            Name of the setting.
        value : str
            Value of the setting.

        """

        self._settings[key] = value

    def define_configuration(
        self, name: str, configuration: Dict[str, Any], override: bool = False
    ) -> None:
        """
        Adds a new configuration to the list of available configurations. If the configuration
        already exists an exception will be thrown unless `override` is set to True, in which case
        the configuration will be redefined with the provided settings dictionary. The given
        `configuration` must follow the schema defined previously.

        Parameters
        ----------
        name : str
            Name of the configuration.
        configuration : str
            Content of the configuration.
        override : bool, optional
            When the name of the given configuration is already defined, if set to True, the
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
            raise ConfigurationAlreadyDefined(configuration=name)

        if not self._validate_configuration_schema(
            schema=self._schema, configuration=configuration
        ):
            raise InvalidConfiguration(
                "The given configuration does not follow the predefined schema."
            )

        self._configurations[name] = configuration

        # If the modified config is the active one, reapply it,
        if name == self._active_configuration:
            self.apply_configuration(name=name)

    def get_configuration(self, name: str) -> Dict[str, Any]:
        """
        Retrieves the content of a configuration.

        Parameters
        ----------
        name : str
            Name of the configuration.

        Returns
        -------
        Dict[str, Any]
            Configuration content.

        Raises
        ------
        UndefinedConfiguration
            If the configuration was not defined previously.

        """

        try:
            return self._configurations[name]
        except KeyError:
            raise UndefinedConfiguration(configuration=name)

    def edit_configuration(self, name: str, configuration_override: Dict[str, Any]) -> None:
        """
        Applies a modification to a configuration. Modifying the active configuration also
        modifies the current settings.

        Parameters
        ----------
        name : str
            Name of the configuration.
        configuration_override : Dict[str, Any]
            Settings with the new values.

        Raises
        ------
        Exception
            If the configuration was not defined previously.

        InvalidConfiguration
            If the configuration does not follow the schema difined previously.

        """
        try:
            configuration = self.get_configuration(name=name)
        except UndefinedConfiguration:
            raise Exception(
                "Use `define_configuration` method instead to create a new configuration."
            )
        else:
            if not self._validate_configuration_schema(
                schema=self._schema, configuration=configuration_override
            ):
                raise InvalidConfiguration(
                    "The given configuration does not follow the predefined schema."
                )

            configuration.update(configuration_override)
            self._configurations[name] = configuration
            # If the modified config is the active one, reapply it.
            if self._active_configuration == name:
                self.apply_configuration(name=name)

    def get_active_configuration(self) -> str:
        """
        Obtains the name of the currently active configuration.

        Returns
        -------
        str
            The name of the active configuration.

        """

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

        try:
            self._settings = self._configurations[name]
        except KeyError:
            raise UndefinedConfiguration(configuration=name)
        self._active_configuration = name
