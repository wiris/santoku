from typing import Any, Dict, List, Tuple

import mysql.connector
import pandas as pd

from santoku.aws.secretsmanager import SecretsManagerHandler


class MySQLConnector:
    """
    Manage MySQL interactions, the simplest of which is to query a particular table.
    This makes use of the official MySQL connector. More information at
    https://dev.mysql.com/doc/connector-python/en/

    """

    def __init__(self, user: str, password: str, host: str, database: str) -> None:
        """
        Base constructor. Use this to connect to the MySQL server.
        For alternative methods of authentication use the given class methods.

        Parameters
        ----------
        user : str
            The MySQL user name.
        password : str
            The password of the MySQL user.
        host : str
            Hostname or location of the MySQL server.
        database : str
            The database in the MySQL server to be connected to.

        Raises
        ------
        mysql.connector.errors.ProgrammingError
            Raised if credentials are not correctly specified or the database does not exsit.

        mysql.connector.errors.InterfaceError
            Raised if the connection to the MySQL server host cannot be done.

        Notes
        -----
        More information on MySQL connection: [1].

        References
        ----------
        [1] :
        https://dev.mysql.com/doc/connector-python/en/connector-python-example-connecting.html

        """
        self.db_connector = mysql.connector.connect(
            user=user, password=password, host=host, database=database
        )

    @classmethod
    def from_aws_secrets_manager(cls, secret_name: str, database: str) -> "MySQLConnector":
        """
        Retrieve the necessary information for the connection to MySQL from AWS Secrets Manager.
        Requires that AWS credentials with the appropriate permissions are located somewhere on the
        AWS credential chain in the local machine.

        Parameters
        ----------
        secret_name : str
            Name or ARN for the secret containing fields needed for MySQL authentication.
        database : str
            The database in the MySQL server to be connected to.

        See Also
        --------
        __init__ : this method calls the constructor.

        Notes
        -----
        The retrieved secret must have the following particular JSON structure:
        ```
        {
            "user": "<user>",
            "password": "<password>",
            "host": "<host>"
        }
        ```

        """
        secrets_manager = SecretsManagerHandler()
        credential_info = secrets_manager.get_secret_value(secret_name=secret_name)

        return cls(
            user=credential_info["user"],
            password=credential_info["password"],
            host=credential_info["host"],
            database=database,
        )

    def get_query_results(self, query: str) -> List[Tuple[Any]]:
        """
        Run an SQL query.

        Parameters
        ----------
        query : str
            SQL query to run against the database specified previously.

        Returns
        -------
        List[Tuple[Any]]
            The query result where each element in the list is a row in the table represented by a
            tuple, where each element in the tuple is a column.

        Notes
        -----
        More information on `MySQLCursor`: [1].
        More information on `MySQLCursor.execute()` method: [2]

        References
        ----------
        [1] :
        https://dev.mysql.com/doc/connector-python/en/connector-python-api-mysqlcursor-constructor.html
        [2] :
        https://dev.mysql.com/doc/connector-python/en/connector-python-api-mysqlcursor-execute.html

        """
        cursor = self.db_connector.cursor()
        cursor.execute(query)
        return cursor.fetchall()

    def read_sql_query_to_pandas_dataframe(
        self, query: str, **kwargs: Dict[str, Any]
    ) -> pd.DataFrame:
        """
        Run an SQL query and get the results in pandas dataframe form.

        Parameters
        ----------
        query : str
            SQL query to run against the database specified previously.

        kwargs : Dict[str, Any]
            Additional arguments for the `pd.read_sql()` method.

        Returns
        -------
        pd.DataFrame
            The query result in pandas dataframe form.

        Notes
        -----
        More information on `pd.read_sql()` method: [2]

        References
        ----------
        [1] :
        https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.read_sql.html

        """
        return pd.read_sql(sql=query, con=self.db_connector, **kwargs)
