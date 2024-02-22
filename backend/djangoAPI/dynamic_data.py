import os

from science.db.sql import OutputSQL
from science.db.sandbox import Dispatch
from science.analyze.spectrum import var_is_true


if var_is_true(os.environ.get("DJANGO_USE_NEW_TABLES", True)):
    schema_prefix = 'new_'
else:
    schema_prefix = ''

# # Find files that are available for users to download
# verbose prints things to the screen, gives you more information
dispatch = Dispatch(verbose=True, output_dir=None, uploads_dir=None)

def write_upload_zip(username: str, spectra_handles: list):
    zipfile_path, failed_requests = dispatch.zip_upload(username=username, spectra_handles=spectra_handles)
    return zipfile_path, failed_requests


def del_upload_zip(token: str):
    dispatch.zip_del(username=token)


# # The Query requests from MySQL Server
query_iso_str = f'SELECT molecule, name FROM {schema_prefix}spexodisks.available_isotopologues'
query_spectra_str = f'SELECT spectrum_handle FROM {schema_prefix}spexodisks.spectra'
query_parameters_str = f'SELECT param_handle, units FROM {schema_prefix}spexodisks.available_params_and_units WHERE for_display = 1'

# # get the raw Query information
with OutputSQL() as output_sql:
    available_isotopologues_raw = output_sql.query(sql_query_str=query_iso_str)
    available_spectra_raw = output_sql.query(sql_query_str=query_spectra_str)
    available_params_raw = output_sql.query(sql_query_str=query_parameters_str)

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
