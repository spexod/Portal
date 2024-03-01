from science.db.sql import LoadSQL


def schema_with_new(schema_name:str,  use_new: bool) -> str:
    if use_new:
        return 'new_' + schema_name
    else:
        return schema_name


def init_spectra_table(load_sql: LoadSQL, database: str):
    if not load_sql.check_if_table_exists(database=database, table_name='spectra'):
        load_sql.creat_table(database=database, table_name='spectra')


def init_iso_table(load_sql: LoadSQL, database: str):
    # initialize the isotopologue table if it does not exist
    if not load_sql.check_if_table_exists(database=database, table_name='available_isotopologues'):
        load_sql.creat_table(database=database, table_name='available_isotopologues')


def init_units_table(load_sql: LoadSQL, database: str):
    # initialize the parameter table if it does not exist
    if not load_sql.check_if_table_exists(database=database, table_name='available_params_and_units'):
        load_sql.create_units_table(database=database)


def init_databases():
    with LoadSQL(verbose=False) as load_sql:
        # create the schema if it does not exist
        load_sql.create_schema(schema_name='users')
        for is_new in [False, True]:
            for schema_name in ['spexodisks', 'spectra']:
                # create the schema if it does not exist
                database = schema_with_new(schema_name, use_new=is_new)
                load_sql.create_schema(schema_name=database)
                if schema_name == 'spexodisks':
                    # initialize the tables if they do not exist
                    init_iso_table(load_sql, database=database)
                    init_units_table(load_sql, database=database)
                    init_spectra_table(load_sql, database=database)


if __name__ == "__main__":
    init_databases()
