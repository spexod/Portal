"""
SIMBAD server selection and a compatibility layer for the autostar package.

Importing this module (ref/ref.py does it) has two effects on astroquery's ``Simbad`` object, which
autostar uses for every live star-name lookup:

1. ``SIMBAD_SERVER`` (environment) selects the server. astroquery accepts ``simbad.cds.unistra.fr``
   (the CDS main site in Strasbourg, the default) and ``simbad.harvard.edu`` (the CfA mirror, the
   alternative while CDS is down).

2. The results are translated back to the format autostar expects. astroquery 0.4.8 moved from
   SIMBAD's retired sim-script interface to TAP: the columns are lower case now (``main_id``, ``ra``,
   ``id``) and the coordinates are degrees, while autostar (0.1.4, which predates that) reads
   ``MAIN_ID``, ``ID`` and sexagesimal ``RA``/``DEC`` strings. Without this translation every lookup of
   a star that is not in data/reference_data fails with ``KeyError: 'MAIN_ID'``. The old columns that
   TAP no longer provides (precisions, quality flag, script number) are filled with blanks, which the
   reference file already uses for unknown values.

This is a bridge until autostar is replaced (see the HySite-based plan); nothing here is used by the
website itself, only by the data pipeline (update.py).

Self test, no files are written:  python -m ref.simbad_compat "HD 189733"
"""
import os
import sys

from astropy import units as u
from astropy.coordinates import Angle
from astroquery.simbad import Simbad

SIMBAD_SERVER = os.environ.get('SIMBAD_SERVER', '').strip()
if SIMBAD_SERVER:
    # astroquery validates the name; an unknown server raises here, at import, with the allowed values
    Simbad.server = SIMBAD_SERVER

# TAP column -> the sim-script column autostar reads (anything else is upper-cased)
column_renames = {
    'main_id': 'MAIN_ID',
    'coo_err_maj': 'COO_ERR_MAJA',
    'coo_err_min': 'COO_ERR_MINA',
    'coo_err_angle': 'COO_ERR_ANGLE',
    'coo_wavelength': 'COO_WAVELENGTH',
    'coo_bibcode': 'COO_BIBCODE',
}
# autostar's SimbadMainRef writes these twelve columns to data/reference_data/simbad_main_ref_data.csv
main_ref_columns = ['MAIN_ID', 'RA', 'DEC', 'RA_PREC', 'DEC_PREC', 'COO_ERR_MAJA', 'COO_ERR_MINA',
                    'COO_ERR_ANGLE', 'COO_QUAL', 'COO_WAVELENGTH', 'COO_BIBCODE', 'SCRIPT_NUMBER_ID']


def ra_to_sexagesimal(ra_deg: float) -> str:
    """ 300.1821 -> '20 00 43.7129', the sim-script style autostar parses with SkyCoord(unit=hourangle). """
    return Angle(ra_deg, unit=u.deg).to_string(unit=u.hourangle, sep=' ', precision=4, pad=True)


def dec_to_sexagesimal(dec_deg: float) -> str:
    """ 22.7109 -> '+22 42 39.073' """
    return Angle(dec_deg, unit=u.deg).to_string(unit=u.deg, sep=' ', precision=3, pad=True, alwayssign=True)


def to_autostar_object_table(table):
    """ Rename and convert a query_object result in place; None when the object was not found. """
    if table is None or len(table) == 0:
        return None   # the old interface returned None, autostar prints "No Simbad Main Query data"
    for name in list(table.colnames):
        new_name = column_renames.get(name, name.upper())
        if new_name != name:
            table.rename_column(name, new_name)
    for coordinate, convert in (('RA', ra_to_sexagesimal), ('DEC', dec_to_sexagesimal)):
        if coordinate in table.colnames and table[coordinate].dtype.kind == 'f':
            table[coordinate] = [convert(value) if value == value else '' for value in table[coordinate]]
    for name in main_ref_columns:
        if name not in table.colnames:
            table[name] = [''] * len(table)
    return table


def to_autostar_ids_table(table):
    """ query_objectids: the identifiers moved from the 'ID' to the 'id' column. """
    if table is None:
        return None
    if 'id' in table.colnames and 'ID' not in table.colnames:
        table.rename_column('id', 'ID')
    return table


_query_object = Simbad.query_object
_query_objectids = Simbad.query_objectids


def query_object(*args, **kwargs):
    return to_autostar_object_table(_query_object(*args, **kwargs))


def query_objectids(*args, **kwargs):
    return to_autostar_ids_table(_query_objectids(*args, **kwargs))


if not getattr(Simbad, '_autostar_compat', False):
    Simbad.query_object = query_object
    Simbad.query_objectids = query_objectids
    Simbad._autostar_compat = True


if __name__ == '__main__':
    # a live lookup through autostar's own query functions, which do not write the reference files
    from autostar.simbad_query import get_query_object, get_single_name_data
    name = ' '.join(sys.argv[1:]) or 'HD 189733'
    print(f'SIMBAD server: {Simbad.server}')
    record = get_query_object(name)
    if record is None:
        print(f'{name}: not found')
        sys.exit(1)
    print(f'{name}: MAIN_ID={record["MAIN_ID"]} RA={record["RA"]} DEC={record["DEC"]} COO_BIBCODE={record["COO_BIBCODE"]}')
    names = get_single_name_data(name)
    print(f'{len(names)} name types: ' + ', '.join(f'{k}={sorted(v)}' for k, v in sorted(names.items())))
