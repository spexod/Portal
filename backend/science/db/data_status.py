from science.db.sql import LoadSQL

from mysql.connector.errors import ProgrammingError


database = 'data_status'
table_name = 'status'
query_str = f'SELECT new_data_staged, updated_mysql FROM {database}.{table_name}'


def set_data_status_mysql(new_data_staged_to_set: bool = False, updated_mysql_to_set: bool = False):
    # upload the data status to the MySQL database
    with LoadSQL(auto_connect=True, verbose=True) as output_sql:
        output_sql.clear_database(database=database)
        output_sql.creat_table(table_name=table_name, database=database)
        output_sql.insert_into_table(table_name=table_name, database=database,
                                     data={"new_data_staged": new_data_staged_to_set,
                                           "updated_mysql": updated_mysql_to_set})


def get_data_status_mysql():
    # read the status variables from the MySQL server
    with LoadSQL() as output_sql:
        try:
            data_status_mysql = output_sql.query(sql_query_str=query_str)
        except ProgrammingError:
            # initialize the data status table
            set_data_status_mysql(new_data_staged_to_set=False, updated_mysql_to_set=False)
            data_status_mysql = output_sql.query(sql_query_str=query_str)
        # map the most resent data status to the variables
        new_data_staged_int, updated_mysql_int = data_status_mysql[-1]
        # convert to the boolean values
        new_data_staged = bool(new_data_staged_int)
        updated_mysql = bool(updated_mysql_int)
    return new_data_staged, updated_mysql
