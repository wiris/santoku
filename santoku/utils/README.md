# Utils
This subpackage implements supporting methods and abstract classes that should be useful in a variety of projects.

# Configuration
The `configuration` module provides classes to store and manage configuration files at runtime. For example, the `ConfigurationManager` class handles serving complex custom configuration files to an application, switching between different configurations and (optionally) strongly validating the schema of all configurations in a standard way, all at runtime.

Configurations can be loaded from Python dictionaries or serialized JSON files, like so:

```python
from santoku.utils import ConfigurationManager

# from Python data structures
configuration_manager = ConfigurationManager.(
    configurations=list_of_configurations,
    schema=schema_dict,
    initial_configuration="my_configuration"
)

# from JSON files
configuration_manager = ConfigurationManager.from_json(
    configurations_file_path="path/to/configurations.json",
    schema_file_path="path/to/schema.json",
    initial_configuration="my_configuration"
)
```

The value of each setting can be easily accessed:

```python
setting_value = configuration_manager.get_setting("my_setting")

# nested settings can be accessed by passing the list of keys, in order
nested_boolean_setting = configuration_manager.get_setting("object_setting", "nested_setting")
```


## Schema validation
For schema validation of configuration files, we use [JSON Schema](https://json-schema.org/) and the [jsonschema](https://pypi.org/project/jsonschema/) package. At the time of writing, we support drafts 4, 6 and 7 of the JSON Schema specification. `jsonschema` does not support the latest draft (2019-09, formerly knwon as draft 8), although it is [one of the most requested issues](https://github.com/Julian/jsonschema/issues/613) and the maintainer said that it will eventually be supported.

### Best Practices
When managing configurations with schemas, we recommend the following best practices:
- Add the `required` field to each object in the schema, such that if a setting is missing from the configuration a validation error will ensure that you do not execute with configurations. Irrelevant values (e.g. for hierarchical settings) can be made nullable and thus ignored (see below).
    ```json
    {
        "type": "object",
        "properties": {
            "first": {...},
            "second": {...},
        },
        "required": ["first", "second"]
    }
    ```
- Set `additionalProperties` to `false` on each object to indicate that nothing can be defined in addition to what the schema specifies. This will keep configuration files clean and to the point. This field defaults to `true`, but we recommend making that assertion explicit in your schemas if you ever need it.
    ```json
    {
        "type": "object",
        "properties": {...},
        "required": [...],
        "additionalProperties": false
    }
    ```
- To make a setting nullable, add `null` to the list of types for that particular field. In Python, a `null` value is parsed to `None`, which makes handling of unset settings easy.
    ```json
    {
    "setting": {
        "type": ["string", "null"]
        }
    }
    ```

## Example
Say you have the following schema for the settings your app needs:

```JSON
# schema.json
{
    "$schema": "http://json-schema.org/draft-07/schema#",
    "description": "Settings for my app",
    "type": "object",
    "properties": {
        "boolean_setting": {"type": "boolean"},
        "int_setting": {"type": "integer"},
        "object_setting": {
            "type": "object",
            "properties": {
                "nested_float_setting": {"type": "numeric"},
                "nested_string_setting": {"type": "string"},
            },
            "required": ["nested_float_setting", "nested_string_setting"],
            "additionalProperties": false
        }
    },
    "required": ["boolean_setting", "int_setting", "object_setting"],
    "additionalProperties": false
}
```

Your different configurations must then be provided in array form, with `name` being a unique identifier and the `settings` object conforming to the `schema.json` above:

```JSON
# configs.json
[
    {
        "name": "configuration_1",
        "settings": {
            "boolean_setting": true,
            "int_setting": 42,
            "object_setting": {
                "nested_float_setting": 3.14,
                "nested_string_setting": "Hello, Sailor!",
            }
        }
    },
    {
        "name": "configuration_2",
        "settings": ...
    },
    ...
]
```

## Note on recursive type hints
This module would greatly benefit from recursive type hints. We tried but discovered that currently mypy does not support this. To summarize, it is possible since Python 3.5 (when type hints where first implemented) to define custom types using type aliasing, like so:

```python
from typing import List, Union

# a custom type for a list of str and/or int
strings_and_ints = List[Union[str, int]]
```

Recursive types can be created with the restriction that, to use a type inside its own definition, one must use a string literal instead of simply the type. This is called a [forward reference](https://www.python.org/dev/peps/pep-0484/#forward-references).

```python
from typing import Dict, List, Union

# use "JSON" instead of just JSON
JSON = Union[bool, int, float, str, Dict[str, "JSON"], List["JSON"]]
```

Since this issue is currently [the most demanded from the mypy project](https://github.com/python/mypy/issues/731), it is expected that we will eventually have support for recursive type checking. However, even if mypy raises an error, the code above does compile. For now, we make do with a wrong but simple version that works for our purposes:

```python
from typing import Union
JSON = Union[list, dict]
```
    