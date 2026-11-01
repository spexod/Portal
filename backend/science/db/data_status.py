"""
Three flags in MySQL (data_status.status) that track an upload through staging, commit and migration:
update.py sets new_data_staged, commit_data.py sets new_data_commited, migrate.py sets updated_mysql.

The table is created once and updated in place. It used to be dropped and recreated on every write,
and a reader that hit the gap reset all flags to False, which silently cancelled a pending migration.
"""
from MySQLdb import ProgrammingError, OperationalError

from science.db.sql import LoadSQL
from science.db.sql_tables import create_tables
from science.db.sql_values import quote_identifier, qualified_name

database = 'data_status'
table_name = 'status'
query_str = f'SELECT new_data_staged, new_data_commited, updated_mysql FROM {qualified_name(table_name, database)} ' \
            f'ORDER BY index_status DESC LIMIT 1'
# MySQL error codes: unknown database, unknown table
ERROR_NO_DATABASE, ERROR_NO_TABLE = 1049, 1146


def create_status_table(output_sql: LoadSQL):
    output_sql.cursor.execute(f"CREATE DATABASE IF NOT EXISTS {quote_identifier(database)};")
    create_str = create_tables[table_name].replace(f"CREATE TABLE `{table_name}`",
                                                   f"CREATE TABLE IF NOT EXISTS {qualified_name(table_name, database)}", 1)
    output_sql.cursor.execute(create_str)
    output_sql.connection.commit()


def set_data_status_mysql(new_data_staged_to_set: bool = False,
                          new_data_commited_to_set: bool = False,
                          updated_mysql_to_set: bool = False):
    # upload the data status to the MySQL database
    with LoadSQL(auto_connect=True, verbose=True) as output_sql:
        create_status_table(output_sql)
        # delete and insert in one transaction, a concurrent reader sees the old row or the new one
        output_sql.cursor.execute(f"DELETE FROM {qualified_name(table_name, database)};")
        output_sql.insert_into_table(table_name=table_name, database=database,
                                     data={'new_data_staged': new_data_staged_to_set,
                                           'new_data_commited': new_data_commited_to_set,
                                           'updated_mysql': updated_mysql_to_set})


def get_data_status_mysql() -> tuple[bool, bool, bool]:
    # read the status variables from the MySQL server
    with LoadSQL() as output_sql:
        try:
            rows = output_sql.query(sql_query_str=query_str)
        except (ProgrammingError, OperationalError) as err:
            if err.args[0] not in (ERROR_NO_DATABASE, ERROR_NO_TABLE):
                raise
            # first use: make the (empty) table, which means "nothing staged"
            create_status_table(output_sql)
            rows = []
    if not rows:
        return False, False, False
    new_data_staged_int, new_data_commited_int, updated_mysql_int = rows[0]
    return bool(new_data_staged_int), bool(new_data_commited_int), bool(updated_mysql_int)
