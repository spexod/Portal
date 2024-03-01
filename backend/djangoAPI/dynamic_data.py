from science.db.sql import LoadSQL
from science.db.sandbox import Dispatch
from science.db.sql import API_USE_NEW_TABLES

# # Find files that are available for users to download
# verbose prints things to the screen, gives you more information
dispatch = Dispatch(verbose=True, output_dir=None, uploads_dir=None)


def write_upload_zip(username: str, spectra_handles: list):
    zipfile_path, failed_requests = dispatch.zip_upload(username=username, spectra_handles=spectra_handles)
    return zipfile_path, failed_requests


def package_iso_data(iso_data: list) -> dict:
    iso_dict = {}
    for a_molecule, a_isotopologue in iso_data:
        if a_molecule not in iso_dict.keys():
            iso_dict[a_molecule] = set()
        iso_dict[a_molecule].add(a_isotopologue)
    return iso_dict


# get the raw information needed to dynamically build model classes for tables.
if API_USE_NEW_TABLES:
    schema_prefix = 'new_'
else:
    schema_prefix = ''
schema_name = f'{schema_prefix}spexodisks'
# get the raw information needed to dynamically build model classes for tables.
with LoadSQL() as load_sql:
    available_isotopologues_raw = load_sql.query(
        sql_query_str=f'SELECT molecule, name FROM {schema_name}.available_isotopologues')
    available_isotopologues = package_iso_data(iso_data=available_isotopologues_raw)
    available_spectra_raw = load_sql.query(
        sql_query_str=f'SELECT spectrum_handle FROM {schema_name}.spectra')
    available_spectra_handles = {spectrum_data[0] for spectrum_data in available_spectra_raw}
    available_params_raw = load_sql.query(
        sql_query_str=f'SELECT param_handle, units FROM {schema_name}.available_params_and_units WHERE for_display = 1')
    available_params_and_units = [(param_data[0], param_data[1]) for param_data in available_params_raw]

# # map the handles to the correct database
# live data
if API_USE_NEW_TABLES:
    with LoadSQL() as load_sql:
        # find all the spectra handles that are not in the new table
        available_new_spectra_tables = set(load_sql.get_all_tables(database='new_spectra'))
        available_new_spexodisks_tables = set(load_sql.get_all_tables(database='new_spexodisks'))
else:
    available_new_spectra_tables = set()
    available_new_spexodisks_tables = set()
# new data
available_live_spectra_handles = set(load_sql.get_all_tables(database='spectra'))
available_live_iso_handles = {table_name for table_name in load_sql.get_all_tables(database='spexodisks')
                              if table_name.startswith('isotopologue')}
# mapping for spectra
available_spectra_to_database = {}
for available_spectra_handle in available_spectra_handles:
    if available_spectra_handle in available_new_spectra_tables:
        available_spectra_to_database[available_spectra_handle] = 'new_spectra'
    elif available_spectra_handle in available_live_spectra_handles:
        available_spectra_to_database[available_spectra_handle] = 'spectra'
    else:
        raise KeyError(f'Could not find the database for the spectrum handle: {available_spectra_handle}')
# mapping for isotopologues
available_isotopologues_to_database = {molecule: {} for molecule in available_isotopologues.keys()}
for molecule in available_isotopologues.keys():
    for isotopologue in available_isotopologues[molecule]:
        if f'isotopologue_{isotopologue}' in available_new_spexodisks_tables:
            available_isotopologues_to_database[molecule][isotopologue] = 'new_spexodisks'
        elif f'isotopologue_{isotopologue}' in available_live_iso_handles:
            available_isotopologues_to_database[molecule][isotopologue] = 'spexodisks'
        else:
            raise KeyError(f'Could not find the database for the isotopologue: {isotopologue}')
