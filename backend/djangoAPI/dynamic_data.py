import os

from science.db.sql import LoadSQL
from science.db.sandbox import Dispatch
from science.db.sql_config import schema_prefix


# # Find files that are available for users to download
# verbose prints things to the screen, gives you more information
dispatch = Dispatch(verbose=True, output_dir=None, uploads_dir=None)

def write_upload_zip(username: str, spectra_handles: list):
    zipfile_path, failed_requests = dispatch.zip_upload(username=username, spectra_handles=spectra_handles)
    return zipfile_path, failed_requests


def del_upload_zip(token: str):
    dispatch.zip_del(username=token)


schema_name = f'{schema_prefix}spexodisks'
table_name_iso = 'available_isotopologues'
table_name_spectra = 'spectra'
table_name_params = 'available_params_and_units'
# # The Query requests from MySQL Server
query_iso_str = f'SELECT molecule, name FROM {schema_name}.{table_name_iso}'
query_spectra_str = f'SELECT spectrum_handle FROM {schema_name}.{table_name_spectra}'
query_parameters_str = f'SELECT param_handle, units FROM {schema_name}.{table_name_params} WHERE for_display = 1'

# get the raw information needed to dynamically build model classes for tables.
with LoadSQL() as load_sql:
    # check if the schema exists
    load_sql.create_schema(schema_name=schema_name)
    # check if the tables exist
    if not load_sql.check_if_table_exists(database=schema_name, table_name=table_name_iso):
        load_sql.creat_table(database=schema_name, table_name=table_name_iso)
    available_isotopologues_raw = load_sql.query(sql_query_str=query_iso_str)
    if not load_sql.check_if_table_exists(database=schema_name, table_name=table_name_spectra):
        load_sql.creat_table(database=schema_name, table_name=table_name_spectra)
    available_spectra_raw = load_sql.query(sql_query_str=query_spectra_str)
    if not load_sql.check_if_table_exists(database=schema_name, table_name=table_name_params):
        load_sql.create_units_table(database=schema_name)
    available_params_raw = load_sql.query(sql_query_str=query_parameters_str)

# # Reshape and format the data for import in other parts of the project
# available_isotopologues
available_isotopologues = {}
for molecule, isotopologue in available_isotopologues_raw:
    if molecule not in available_isotopologues.keys():
        available_isotopologues[molecule] = set()
    available_isotopologues[molecule].add(isotopologue)

# spectra_handles
available_spectra_handles = {spectrum_data[0] for spectrum_data in available_spectra_raw}

# available_params
available_params_and_units = [(param_data[0], param_data[1]) for param_data in available_params_raw]
