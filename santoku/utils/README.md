# Utils
This subpackage implements supporting methods and abstract classes that should be useful in a variety of projects.

## Configuration management 
The `configuration` module provides classes to store and manage configuration files at runtime. It provides a `Settings` class that stores configuration parameters allowing for hierarchical structures and a `ConfigurationManager` class that handles serving those values to an application, switching between different configurations and (optionally) validating the schema of a configuration.

Configurations can be loaded from Python dictionaries or serialized JSON files, like so:

```python
from santoku.utils.configuration import Settings, ConfigurationManager

configuration_manager = ConfigurationManager.(
    configurations=configs_list,
    initial_configuration="configuration_1",
    schema=schema_dict
)

# or

configuration_manager = ConfigurationManager.from_json(
    configurations_file_path="config.json",
    initial_configuration="configuration_1",
    schema_file_path="schema.json"
)
```

The value of each settings can be easily accessed:

```python
boolean_setting = configuration_manager.get_setting("boolean_setting")

# nested settings can be accessed by calling get_setting() on each level
nested_boolean_setting = configuration_manager.get_setting("object_setting")\
                                              .get_setting("nested_boolean_setting")

# alternatively, you can simply pass the list of keys in order
boolean_setting = configuration_manager.get_setting(
    ["object_setting", "nested_boolean_setting"]
)
```


### Schema validation
For schema validation of configuration files, we use our own definition of what a configuration looks like and also our own definition of what a schema should look like. In short, our schema is a narrow subset of [JSON Schema](https://json-schema.org/). We plan on fully adopting JSON Schema for our validation needs, but due to the lack of native Python tools and the effort of implementing our own parser we erred on the side of something simpler that allows for faster iteration.

```JSON
# config.json
[
    {
        "name": "configuration_1",
        "settings": {
            "boolean_setting": true,
            "numeric_setting": 42,
            "object_setting": {
                "nested_text_setting": "value",
                ...
            }
            ...
        }
    },
    {
        "name": "configuration_2",
        "settings": ...
    },
    ...
]
```

The settings in each configuration must take the form of a JSON object without the use of any array, i.e. a (possibly nested) dictionary. We define the following schema, which is (almost, it uses Python type names) a strict subset of JSON Schema:

```JSON
# schema.json
{
    "boolean_setting": {"type": "bool"},
    "int_setting": {"type": "int"},
    "float_setting": {"type": "float"},
    "string_setting": {"type": "string"},
    "object_setting": {
        "nested_boolean_setting": {"type": "bool"},
        ...
    },
    ...
}
```

### Recursive type hints
This module would greatly benefit from recursive type hints. We tried but discovered that currently mypy does not support this. To summarize, it is possible to define custom types using type aliasing, like so:

```python
from typing import List, Union

# a list of str and/or int
MyCustomType = List[Union[str, int]]
```

Recursive types can be created with the restriction that, to use a type inside its own definition, one must use a string literal instead of simply the type. This is called a [forward reference](https://www.python.org/dev/peps/pep-0484/#forward-references).

```python
from typing import Dict, List, Union

# use "JSON" instead of just JSON
JSON = Union[List["JSON"], Dict[str, Union[bool, int, float, str, "JSON"]]
```

Since this issue is currently [the most demanded from the mypy project](https://github.com/python/mypy/issues/731), it is expected that we will eventually have support for recursive type checking. However, even if mypy raises and error, the code above does compile. For now, we will have to make do with the less powerful (i.e. wrong) version:

```python
from typing import Dict, List, Union
JSON = Union[List[Any], Dict[str, Any]
```
    