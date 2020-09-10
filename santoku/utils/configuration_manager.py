from typing import List, Tuple, Dict, Any


class UndefinedSetting(Exception):
    def __init__(self, message):
        super().__init__(message)


class UndefinedConfiguration(Exception):
    def __init__(self, message):
        super().__init__(message)


class InvalidConfiguration(Exception):
    def __init__(self, message):
        super().__init__(message)


class ConfigurationManager:
    """
    Class to handle feature toggles (flags) in a project.

    Feature flags can be used to set values for some required parameters in the project or to enable
    or disable different parts of the source code that will be run in different executions. We
    define the concept of `setting` as each individual flag that controls certain feature, i.e.
    enabling/disabling the mock of an external service. A setting is a pair of key-value, being
    `key` the name of the setting, and `value` an object of any type. We also define the concept of
    `configuration` as a collection of multiple settings. In a project, each configuration should be
    formed by settings containing the same keys but different values. The purpose of this class is
    to handle the definition and retrieving of all the configuartion parameters so that the user can
    control the execution context of the code.

    """

    def __init__(
        self,
        predefined_configurations: List[Dict[str, Any]] = None,
        default_configuration: str = None,
    ):
        """
        Initialize internal structures that store the configurations.

        A list of `predefined_configurations` can be passed to initialze the configuration manager,
        together with the name of the `default_configuration`, if it's not given, he first
        configuration is set by default.

        Parameters
        ----------
        predefined_configurations : List[Dict[str, Any]], optional
            Collection of configurations with different combination of settings.
        default_configuration: str, optional
            Name of the configuration in the `predefined_configurations` that will be set as the
            default one.

        Raises
        ------
        UndefinedConfiguration
            If a `default_configuration` that is not in the `predefined_configurations` is given.

        InvalidConfiguration
            If any configuration in the `predefined_configurations` does not contain the "NAME" or
            "CONFIG" argument.

        See also
        --------
        apply_configuration: this method is called to set the default configuration.

        Notes
        -----
            The following structure is assumed for the list of predefined configurations:
            [
                {
                    "NAME": <name_of_the_configuration>,
                    "CONFIG": {
                        <key>: <value>,
                        ...
                    }
                },
                ...
            ]

        """

        self._settings: Dict[str, Any] = {}
        self._configurations: Dict[str, Dict[str, Any]] = {}
        self._current_configuration: str = ""

        if predefined_configurations:

            for configuration in predefined_configurations:

                if "NAME" not in configuration and "CONFIG" not in configuration:
                    raise InvalidConfiguration(
                        "'NAME' and 'CONFIG' arguments must be contained in a configuration."
                    )

                self.define_configuration(
                    name=configuration["NAME"], configuration=configuration["CONFIG"]
                )

            if default_configuration:
                self.apply_configuration(name=default_configuration)
            else:
                # Set the first configuratoin as default.
                self.apply_configuration(name=next(iter(self._configurations)))
        elif default_configuration:
            raise UndefinedConfiguration(f"Configuration '{default_configuration}' undefined.")

    def get_setting(self, key: str) -> str:
        """
        Obtain the value of a setting in the current configuration.

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
            If a `key` that is not in the current configuration is given.

        """

        if key in self._settings:
            return self._settings[key]
        else:
            raise UndefinedSetting(f"Setting '{key}' undefined.")

    def list_settings(self) -> List[Tuple[str, str]]:
        """
        Return all pairs of key-value settings in the current configuration.

        Returns
        -------
        List[Tuple[str, str]]
            List of pairs key-value settings.

        """
        return [(key, value) for key, value in self._settings.items()]

    def set_setting(self, key: str, value: Any) -> None:
        """
        Add a pair key-value or replace the value of a setting in the current configuration.

        Parameters
        ----------
        key : str
            Name of the setting.
        value : str
            Value of the setting.

        """

        self._settings[key] = value

    def define_configuration(self, name: str, configuration: Dict[str, Any]) -> None:
        """
        Add a configuration and set it as default if no configuration was defined previously.

        Parameters
        ----------
        name : str
            Name of the configuration.
        configuration : str
            Content of the configuration.

        See also
        ------
        apply_configuration: this method is called to set the default configuration.

        """

        self._configurations[name] = configuration
        if not self._current_configuration:
            self.apply_configuration(name=name)

    def get_configuration(self, name: str) -> Dict[str, Any]:
        """
        Retreive the content of a configuration.

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
            raise UndefinedConfiguration(f"Configuration '{name}' undefined.")

    def get_current_configuration(self) -> str:
        """
        Return the name of the current configuration.

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

        return self._current_configuration

    def list_configurations(self) -> List[str]:
        """
        Return the names all the defined configurations.

        Returns
        -------
        List[str]
            List of names of the configurations.

        """
        return [name for name, config in self._configurations.items()]

    def apply_configuration(self, name: str) -> None:
        """
        Set the current configuration.

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
            self._current_configuration = name
        except KeyError:
            raise UndefinedConfiguration(f"Configuration '{name}' undefined.")
