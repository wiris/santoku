# Wiris AWS Python library

This repository contains a Python package with a set of tools to be
used in AWS services like Amazon's ETL: AWS Glue.

In order to use this library in a AWS Glue job of type _Python Shell_
we first need to bundle the library to a Python Wheels object. To do
so, run the following command inside _src_ folder:

```
python3 setup.py bdist_wheel
```

and the library can be found at

```
src/dist/wiris-*.whl
```

This file must be uploaded to S3 and included in the list of Python
library path for certain job, where several libraries can be used by
provided a comma-separated list.

Finally, in a Python Shell job we can import the modules. For
instance, this is an example to read files from a S3 bucket folder.

```
from wiris.aws import s3tools

s3tools = s3tools()

s3_bucket = 'wiris-bucket'
s3_prefix = 'input_folder'
for file_key in s3tools.get_keys_as_generator(s3_bucket, s3_prefix):
    print('Read file "{}"'.format(file_key))
    file_content = s3tools.get_file_content(s3_bucket, file_key)
    
    # do something with content    
```
