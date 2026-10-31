import os
import warnings
import numpy as np
from typing import Union, Tuple
from time import sleep
from collections import namedtuple, UserDict

from astropy import units as u
from astropy.coordinates import SkyCoord, Angle
from astroquery.simbad import Simbad
from astroquery.exceptions import TableParseError

from autostar.bad_stars import BadStars
from autostar.table_read import row_dict
from autostar.config.datapaths import sb_desired_names, star_name_format, star_name_preference, \
    StringStarName, StarName, sb_main_ref_filename, sb_ref_filename, optimal_star_name


Star_ID = namedtuple("Star_ID", "catalog type id")
simbad_count = 1

"""
SIMBAD server and result format

SIMBAD_SERVER (environment) selects the server astroquery talks to: simbad.cds.unistra.fr (the CDS main
site in Strasbourg, the default) or simbad.harvard.edu (the CfA mirror, the alternative while CDS is down).
astroquery rejects any other value here, at import time, naming the two it knows.

astroquery 0.4.8 moved from SIMBAD's retired sim-script interface to TAP: the columns are lower case now
(main_id, ra, id) and the coordinates are degrees. This module, the reference file
data/reference_data/simbad_main_ref_data.csv and the backend code that reads its records (RA, DEC, MAIN_ID,
COO_BIBCODE) use the sim-script names and sexagesimal strings, so every query result is translated back
by the two functions below. Columns TAP no longer provides (precisions, quality flag, script number) are
blank, as the reference file already uses for unknown values.
"""
SIMBAD_SERVER = os.environ.get('SIMBAD_SERVER', '').strip()
if SIMBAD_SERVER:
    Simbad.server = SIMBAD_SERVER

# TAP column -> the sim-script column this module reads (anything else is upper-cased)
column_renames = {
    'main_id': 'MAIN_ID',
    'coo_err_maj': 'COO_ERR_MAJA',
    'coo_err_min': 'COO_ERR_MINA',
    'coo_err_angle': 'COO_ERR_ANGLE',
    'coo_wavelength': 'COO_WAVELENGTH',
    'coo_bibcode': 'COO_BIBCODE',
}
# the columns SimbadMainRef writes to the reference file
main_ref_params = ['MAIN_ID', 'RA', 'DEC', 'RA_PREC', 'DEC_PREC', 'COO_ERR_MAJA', 'COO_ERR_MINA', 'COO_ERR_ANGLE',
                   'COO_QUAL', 'COO_WAVELENGTH', 'COO_BIBCODE', 'SCRIPT_NUMBER_ID']


def ra_to_sexagesimal(ra_deg: float) -> str:
    """ 300.1821 -> '20 00 43.7129', the sim-script style simbad_coord_to_deg parses as hour angles. """
    return Angle(ra_deg, unit=u.deg).to_string(unit=u.hourangle, sep=' ', precision=4, pad=True)


def dec_to_sexagesimal(dec_deg: float) -> str:
    """ 22.7109 -> '+22 42 39.073' """
    return Angle(dec_deg, unit=u.deg).to_string(unit=u.deg, sep=' ', precision=3, pad=True, alwayssign=True)


def query_object(formatted_name):
    """ Simbad.query_object in the sim-script format; None when the object is not found. """
    table = Simbad.query_object(formatted_name)
    if table is None or len(table) == 0:
        return None
    for name in list(table.colnames):
        new_name = column_renames.get(name, name.upper())
        if new_name != name:
            table.rename_column(name, new_name)
    for coordinate, convert in (('RA', ra_to_sexagesimal), ('DEC', dec_to_sexagesimal)):
        if coordinate in table.colnames and table[coordinate].dtype.kind == 'f':
            table[coordinate] = [convert(value) if value == value else '' for value in table[coordinate]]
    for name in main_ref_params:
        if name not in table.colnames:
            table[name] = [''] * len(table)
    return table


def query_objectids(formatted_name):
    """ Simbad.query_objectids with the identifiers in the 'ID' column, as sim-script named it. """
    table = Simbad.query_objectids(formatted_name)
    if table is not None and 'id' in table.colnames and 'ID' not in table.colnames:
        table.rename_column('id', 'ID')
    return table


def simbad_coord_to_deg(ra_string, dec_string):
    *_, hms = str(ra_string).split('\n')
    *_, dms = str(dec_string).split('\n')
    c = SkyCoord(hms + " " + dms, unit=(u.hourangle, u.deg))
    return c.ra.deg, c.dec.deg, c.to_string('hmsdms')


def get_single_name_data(formatted_name):
    found_names = StarDict()
    raw_results = query_objectids(formatted_name)
    if raw_results is not None:
        names_list = list(raw_results.columns["ID"])
        for test_name in names_list:
            try:
                name_type = optimal_star_name(star_name_lower=test_name.lower())
            except ValueError:
                pass
            else:
                if name_type in sb_desired_names:
                    new_hypatia_name = star_name_format(test_name)
                    found_names[name_type] = new_hypatia_name.id
    return found_names


def get_query_object(formatted_name):
    """
    This is the primary query type for Simbad, it gives the star's Main Simbad ID,
    and it's coordinates.

    :param formatted_name: str - a formatted string that will match a Simbad record.
    :return: list of dicts for multiple objects or a dictionary object with the query data
             for a single query.
    """
    try:
        results_table = query_object(formatted_name)
    except TableParseError:
        print(f'\nSimbad Query Exception for {formatted_name}\n')
        return None
    if results_table is None:
        return None
    results_dict = dict(results_table)

    data_len = len(np.array(results_dict['MAIN_ID']))
    if data_len != 1:
        results_per_object = []
        for object_index in range(data_len):
            data_this_object = {}
            for results_key in results_dict.keys():
                data_this_object[results_key] = np.array(results_dict[results_key])[object_index]
            results_per_object.append(data_this_object)
        return results_per_object
    else:
        data_this_object = {results_key: np.array(results_dict[results_key])[0]
                            for results_key in results_dict.keys()}
        return data_this_object


def simbad_to_handle(simbad_formatted_name):
    return simbad_formatted_name.replace(" ", "_").replace("*", "star").replace("+", "plus").replace("-", "minus")\
        .replace("2MASS", "TWOMASS").replace(".", "point").replace("[", "leftsqbracket").replace("]", "rightsqbracket")


def handle_to_simbad(handle):
    return handle.replace("star", "*").replace("_", " ").replace("plus", "+").replace("minus", "-")\
        .replace("TWOMASS", "2MASS").replace("point", ".").replace("leftsqbracket", "[").replace("rightsqbracket", "]")


def make_hypatia_handle(star_names_dict):
    star_type_keys_this_star = set(star_names_dict.keys())
    # select the name to reference this star's data within this class
    star_types_this_star = star_type_keys_this_star - {"star_name_index"}
    for preferred_name in star_name_preference:
        if preferred_name in star_types_this_star:
            possible_star_reference_names = sorted([StringStarName((preferred_name, star_id)).string_name
                                                    for star_id in star_names_dict[preferred_name]])
            star_reference_name = simbad_to_handle(possible_star_reference_names[0])
            break
    else:
        # self.star_name_preference includes all the allowed name types, this error should never be raised
        raise KeyError("This is no overlap between the star names and the star_name preferences.")
    return star_reference_name


class SimbadMainRef:
    """
    Simbad (simbad.fr) main query returns an object's primary (main_id) and coordinate data, and bibliographic code.
    This class handles the referencing of this data, also reads and writes new data.

    This class leverages the SimbadLib class to map the data to make the hypatia_handle the main tool for getting data.
    """

    main_ref_params = ['MAIN_ID', 'RA', 'DEC', 'RA_PREC', 'DEC_PREC', 'COO_ERR_MAJA', 'COO_ERR_MINA', 'COO_ERR_ANGLE',
                       'COO_QUAL', 'COO_WAVELENGTH', 'COO_BIBCODE', 'SCRIPT_NUMBER_ID']

    def __init__(self, ref_path=None, simbad_lib=None):
        if ref_path is None:
            self.ref_path = sb_main_ref_filename
        else:
            self.ref_path = ref_path
        if simbad_lib is None:
            self.simbad_lib = SimbadLib()
        else:
            self.simbad_lib = simbad_lib
        self.simbad_query = SimbadQuery()

        # data storage
        self.main_obj_by_handle = {}
        # operational Flags
        self.write_write_flag = False

        # get the reference data
        self.read()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.write_write_flag:
            self.write()
        return

    def str_to_handle(self, string_name):
        object_handle = make_hypatia_handle(self.simbad_lib.get_star_dict(string_name))
        return object_handle

    def add_star(self, string_name, object_handle=None):
        if object_handle is None:
            object_handle = self.str_to_handle(string_name=string_name)
        if object_handle in self.main_obj_by_handle.keys():
            return False
        else:
            simbad_string = handle_to_simbad(object_handle)
            object_dict = self.simbad_query.get_main_data(formatted_name=simbad_string)
            self.main_obj_by_handle[object_handle] = object_dict
            return True

    def get_object(self, string_name, object_handle=None):
        if object_handle is None:
            object_handle = self.str_to_handle(string_name=string_name)
        if self.add_star(string_name=string_name, object_handle=object_handle):
            self.write_write_flag = True
        return self.main_obj_by_handle[object_handle]

    def write(self):
        print(f'Writing the Simbad main query reference file at: {self.ref_path}')
        with open(self.ref_path, 'w') as f:
            header_line = f'handle'
            for simbad_column in self.main_ref_params:
                header_line += f',{simbad_column}'
            f.write(header_line + '\n')
            for object_handle in sorted(self.main_obj_by_handle.keys()):
                object_data = self.main_obj_by_handle[object_handle]
                line = f'{object_handle}'
                for simbad_column in self.main_ref_params:
                    if object_data is None:
                        line += f','
                    elif simbad_column not in object_data.keys():
                        line += f','
                    elif isinstance(object_data[simbad_column], str) and object_data[simbad_column] == '':
                        line += f','
                    elif isinstance(object_data[simbad_column], (float, int)) and np.isnan(object_data[simbad_column]):
                        line += f','
                    else:
                        line += f',{object_data[simbad_column]}'
                f.write(line + '\n')
        self.write_write_flag = False
        print(f'  ...writing complete')

    def read(self):
        print(f'Read the Simbad main query reference file at: {self.ref_path}')
        file_data = row_dict(filename=self.ref_path, key='handle', null_value='',
                             inner_key_remove=True)
        formatted_data = {}
        for handle in file_data.keys():
            file_record = file_data[handle]
            if file_record == {}:
                formatted_data[handle] = None
            else:
                formatted_data[handle] = file_record
        self.main_obj_by_handle.update(formatted_data)


class SimbadLib:
    def __init__(self, ref_file_name=None, verbose=True, go_fast=False, test_bad_stars=False, auto_load=True):
        self.test_bad_stars = test_bad_stars
        self.verbose = verbose
        self.go_fast = go_fast
        self.simbad_query = None
        self.ref_file_name = ref_file_name

        self.simbad_ref = SimbadRef(ref_file_name=self.ref_file_name)
        self.bad_stars = None

        self.reference_lookup = {}
        self.available_reference_ids = {}
        self.available_name_types = set()
        self.handle_to_output_name = None

        if auto_load:
            self.load()

    def load(self):
        self.simbad_ref.load()
        self.simbad_ref.make_lookup()
        self.bad_stars = BadStars()

    def update_lookup(self, star_names_dict):
        hypatia_handle = make_hypatia_handle(star_names_dict)
        for name_type in star_names_dict.keys():
            star_ids = star_names_dict[name_type]
            if name_type in self.available_name_types:
                self.available_reference_ids[name_type] |= star_ids
            else:
                self.available_name_types.add(name_type)
                self.available_reference_ids[name_type] = set()
                self.reference_lookup[name_type] = {}
            self.available_reference_ids[name_type] |= star_ids
            for star_id in star_names_dict[name_type]:
                self.reference_lookup[name_type][star_id] = hypatia_handle, star_names_dict

    def get_star_dict(self, hypatia_name: Union[str, Tuple]):
        """
        :param hypatia_name:
        :return: hypatia_handle, star_names_dict
        """
        if type(hypatia_name) == str:
            hypatia_name = star_name_format(hypatia_name)
        name_type, star_id = hypatia_name
        # check this class's reference_data to see if this has been requested before
        if name_type in self.available_name_types and star_id in self.available_reference_ids[name_type]:
            # Case 1, when we have looked up this reference data before
            return self.reference_lookup[name_type][star_id]
        else:
            # No ref data found yet
            # Check to see if the data can be found and made from the simbad reference csv file
            star_names_dict = self.simbad_ref.get_star_dict(hypatia_name)
            if star_names_dict is not None:
                # Case 2, a star_dict was found in the simbad ref csv file
                # update the lookup dicts for this class and the method will now exit at case 1
                self.update_lookup(star_names_dict)
                return self.get_star_dict(hypatia_name)
            else:
                # The data was not in the simbad reference csv file, we will try to get data from the Simbad website
                self.simbad_query = SimbadQuery(verbose=self.verbose, go_fast=self.go_fast)
                # a shortcut to Case 4 for some star know to no have Simbad information
                if self.test_bad_stars or hypatia_name not in self.bad_stars.hypatia_names:
                    self.simbad_query.get_name_data(simbad_name_list=[StringStarName(hypatia_name).string_name])
                if self.simbad_query.stars_found:
                    # Case 3 we got new simbad data from the website.
                    # we need to save it and update the reference file
                    self.simbad_ref.add_star_dicts(star_dict_list=self.simbad_query.stars_found)
                    if self.verbose:
                        print("New reference data found for " + StringStarName(hypatia_name).string_name + ".")
                    # with the reference data updated, this should now exit Case 2
                    return self.get_star_dict(hypatia_name)
                else:
                    # Case 4 getting reference data from Simbad has failed.
                    # is this a star we know about?
                    if hypatia_name in self.bad_stars.hypatia_names:
                        if self.verbose:
                            print("\nKnown Issue: The star " + StringStarName(hypatia_name).string_name + "\n" +
                                  "  is a reported 'bad star name', reason:",
                                  self.bad_stars.hyp_name_to_reason_dict[hypatia_name], "\n")
                    else:
                        warnings.warn("\nThe star name '" + StringStarName(hypatia_name).string_name +
                                      " was not found in the reference data!\n")
                    star_names_dict = StarDict()
                    star_names_dict[name_type] = star_id
                    # update the lookup dicts for this class, and the method will now exit at case 1
                    self.update_lookup(star_names_dict)
                    return self.get_star_dict(hypatia_name)

    def get_star_dict_with_star_dict(self, input_star_names_dict):
        name_types_found = []
        found_hypatia_names = []
        new_hypatia_names = []
        hypatia_name = None
        for name_type in input_star_names_dict.keys():
            for star_id in list(input_star_names_dict[name_type]):
                hypatia_name = StarName(name_type, star_id)
                requested_star_names_dict = self.simbad_ref.get_star_dict(hypatia_name)
                if requested_star_names_dict is None:
                    name_types_found.append(False)
                    new_hypatia_names.append(hypatia_name)
                else:
                    name_types_found.append(True)
                    found_hypatia_names.append(hypatia_name)
        if all(name_types_found):
            # if all the names are found, any name will work.
            return self.get_star_dict(hypatia_name)
        elif hypatia_name is not None:
            # this is just a clever way to make sure we are not acting on an empty dictionary
            # and that at least one hypatia_name is in the list new_hypatia_names
            max_names_dict = StarDict()
            # names from the input dictionary
            for name_type in input_star_names_dict.keys():
                for star_id in input_star_names_dict[name_type]:
                    max_names_dict[name_type] = star_id
            # names from the reference data
            if found_hypatia_names:
                _hypatia_handle, existing_names_dict = self.get_star_dict(found_hypatia_names[0])
                for name_type in existing_names_dict:
                    for star_id in existing_names_dict[name_type]:
                        max_names_dict[name_type] = star_id
            # names of the name types that were not found
            for new_hypatia_name in new_hypatia_names:
                hypatia_handle, simbad_search_star_names_dict = self.get_star_dict(new_hypatia_name)
                for name_type in simbad_search_star_names_dict:
                    for star_id in simbad_search_star_names_dict[name_type]:
                        max_names_dict[name_type] = star_id
            self.simbad_ref.add_star_dicts([max_names_dict])
            return self.get_star_dict_with_star_dict(input_star_names_dict)
        else:
            raise KeyError("input_star_names_dict was None or empty.")


class SimbadQuery:
    def __init__(self, verbose=True, go_fast=False, desired_name_types=None):
        self.verbose = verbose
        if desired_name_types is None:
            self.desired_name_types = sb_desired_names
        else:
            self.desired_name_types = desired_name_types
        self.stars_found = []
        self.stars_not_found = []

        self.count = None

        self.count_per_big_sleep = 50
        if go_fast:
            self.big_sleep_time = 0
            self.small_sleep_time = 0
        else:
            self.big_sleep_time = 30
            self.small_sleep_time = 0.30
        self.coord_star_info = None

    def get_name_data(self, simbad_name_list=None):
        global simbad_count
        for index, sb_name_string in list(enumerate(simbad_name_list)):
            simbad_count += 1
            if self.verbose:
                print("Getting name info for star:", "%30s" % sb_name_string, " ", "%5s" % (index + 1), "of",
                      "%5s" % len(simbad_name_list))
            star_dict = get_single_name_data(sb_name_string)
            if star_dict != StarDict():
                try:
                    name_type, name_id = star_name_format(sb_name_string)
                except ValueError:
                    pass
                else:
                    star_dict[name_type] = name_id
                self.stars_found.append(star_dict)
            else:
                self.stars_not_found.append(sb_name_string)
            if 0 == simbad_count % self.count_per_big_sleep:
                if self.verbose:
                    print("\nBig Simbad Sleep:", self.big_sleep_time, 'seconds.\n')
                sleep(self.big_sleep_time)
            else:
                sleep(self.small_sleep_time)
        self.count = simbad_count

    def get_coord_data(self, simbad_name_list=None):
        self.coord_star_info = {}
        len_names_list = len(simbad_name_list)
        global simbad_count
        for index, name_string in list(enumerate(simbad_name_list)):
            if 0 == simbad_count % self.count_per_big_sleep:
                if self.verbose:
                    print("\nBig Simbad Sleep:", self.big_sleep_time, 'seconds.\n')
                sleep(self.big_sleep_time)
            else:
                sleep(self.small_sleep_time)
            if self.verbose:
                print("Getting data for star:", "%30s" % name_string, " ", "%5s" % (index + 1), "of",
                      "%5s" % len_names_list)
            result_table = query_object(name_string)
            simbad_count += 1
            if result_table is not None:
                try:
                    ra_deg, dec_deg, hmsdms = simbad_coord_to_deg(result_table.columns["RA"],
                                                                       result_table.columns["DEC"])
                    result_dict = {'ra': ra_deg, 'dec': dec_deg, 'hmsdms': hmsdms,
                                   'star_names': get_single_name_data(name_string)}
                    hypatia_name = star_name_format(name_string)
                    self.coord_star_info[hypatia_name] = result_dict
                except ValueError:
                    pass
        self.count = simbad_count

    def get_main_data(self, formatted_name):
        """ This is the primary query type for Simbad, it gives the star's Main Simbad ID,
            and it's coordinates.

        :param formatted_name: str - a formatted string that will match a Simbad record.
        :return: dict - A dictionary object with the query data for a single query.
        """
        global simbad_count
        if 0 == simbad_count % self.count_per_big_sleep:
            if self.verbose:
                print("\nBig Simbad Sleep:", self.big_sleep_time, 'seconds.\n')
            sleep(self.big_sleep_time)
        else:
            sleep(self.small_sleep_time)
        object_dict = get_query_object(formatted_name=formatted_name)
        simbad_count += 1
        if isinstance(object_dict, list):
            raise TypeError(f"only single object queries are allows, this query resulted in {len(object_dict)} " +
                            "objects returned.")
        if object_dict is None:
            print(f"No Simbad Main Query data for {formatted_name}.")
        else:
            print(f'Found data from Main Simbad Query. Query:{formatted_name}  ' +
                  f"Main_ID:{object_dict['MAIN_ID']}")
        return object_dict


class SimbadRef:
    def __init__(self, ref_file_name=None):
        if ref_file_name is None:
            self.ref_file_name = sb_ref_filename
        else:
            self.ref_file_name = ref_file_name
        self.star_dict_list = None
        self.available_name_types = None
        self.lookup_dicts = None
        self.found_ids = None

    def load(self):
        self.available_name_types = set()
        self.star_dict_list = []
        if os.path.exists(self.ref_file_name):
            with open(self.ref_file_name, 'r') as f:
                for line in f.readlines():
                    star_dict = StarDict()
                    ref_line_list = line.strip().split("|")
                    for string_name in ref_line_list:
                        name_type, star_id = star_name_format(string_name)
                        star_dict[name_type] = star_id
                    self.star_dict_list.append(star_dict)

    def load_csv(self):
        self.available_name_types = set()
        if os.path.exists(self.ref_file_name):
            ref_list = row_dict(self.ref_file_name, null_value="")
        else:
            ref_list = []
        self.star_dict_list = []
        for ref_dict in list(ref_list):
            star_dict = StarDict()
            for name_type in ref_dict.keys():
                if "_other" in name_type:
                    base_name_type, _other_number = name_type.split('_other')
                else:
                    base_name_type = name_type
                self.available_name_types.add(base_name_type)
                _name_type, star_id = star_name_format(ref_dict[name_type])
                star_dict[base_name_type] = star_id
            self.star_dict_list.append(star_dict)

    def make_lookup(self):
        """
        Makes look up dictionaries for reference name finding. the dictionaries are stored in self.lookup_dicts.
        up to find the index of the star_dict in the variable self.star_dict_list.

        Example:
        name_type, star_id = hypatia_name
        star_dict = self.star_dict_list[self.lookup_dicts[name_type][star_id]]

        This method will combine star dictionaries in self.star_dict_list and remove one of the copies after
        combination of dictionaries that wer found to have overlapping data for the same object.

        :return:
        """
        if self.star_dict_list is None:
            self.load()
        self.lookup_dicts = {name_type: {} for name_type in self.available_name_types}
        self.found_ids = {name_type: set() for name_type in self.available_name_types}
        for index, star_dict in list(enumerate(self.star_dict_list)):
            found_index = None
            name_types_this_star = set(star_dict.keys())
            for name_type in name_types_this_star:
                for star_id in star_dict[name_type]:
                    if name_type in self.available_name_types:
                        if star_id in self.found_ids[name_type]:
                            found_index = self.lookup_dicts[name_type][star_id]
                            break
                        else:
                            self.lookup_dicts[name_type][star_id] = index
                            self.found_ids[name_type].add(star_id)
                    else:
                        self.available_name_types.add(name_type)
                        self.lookup_dicts[name_type] = {star_id: index}
                        self.found_ids[name_type] = {star_id}
            if found_index is not None:
                # only add new types, do not overwrite
                print("Duplicate_data data found, updating and restarting the Simbad reference file tool: make_lookup")
                for name_type in name_types_this_star:
                    self.star_dict_list[found_index][name_type] = star_dict[name_type]
                    self.available_name_types.add(name_type)
                self.star_dict_list.pop(index)
                # run this again with a duplicate entry removed.
                self.make_lookup()
                break

    def get_star_dict(self, hypatia_name):
        if type(hypatia_name) == str:
            hypatia_name = star_name_format(hypatia_name)
        name_type, star_id = hypatia_name
        if self.lookup_dicts is None:
            self.make_lookup()
        star_dict = None
        if name_type in self.available_name_types and star_id in self.found_ids[name_type]:
            star_dict = self.star_dict_list[self.lookup_dicts[name_type][star_id]]
        return star_dict

    def add_star_dicts(self, star_dict_list):
        if self.star_dict_list is None:
            self.load()
        self.star_dict_list.extend(star_dict_list)
        self.make_lookup()
        self.write()
        self.load()
        self.make_lookup()

    def write(self, write_name=None):
        if write_name is None:
            write_name = self.ref_file_name
        body = []
        # write the star_name reference data
        for star_dict in self.star_dict_list:
            a_line = ""
            for name_type in sorted(star_dict.keys()):
                names_list_this_type = sorted([StringStarName((name_type, star_id)).string_name
                                               for star_id in star_dict[name_type]], reverse=True)
                for string_name in names_list_this_type:
                    a_line += string_name + "|"

            body.append(a_line[:-1] + "\n")
        # The file writing code
        with open(write_name, 'w') as f:
            for a_line in body:
                f.write(a_line)

    def write_csv(self, write_name=None):
        if write_name is None:
            write_name = self.ref_file_name
        # write the header
        header = ""
        name_type_list = sorted(list(self.available_name_types))
        # Find how many "_other#" columns will be needed
        columns_per_name_type = {name_type: 0 for name_type in name_type_list}
        for star_dict in self.star_dict_list:
            for name_type in star_dict.keys():
                columns_per_name_type[name_type] = max(columns_per_name_type[name_type], len(star_dict[name_type]))
        #
        for name_type in name_type_list:
            header += str(name_type) + ','
            for index in range(1, columns_per_name_type[name_type]):
                header += str(name_type) + "_other" + str(index) + ","
        header = header[:-1] + "\n"
        body = []
        # write the star_name reference data
        for star_dict in self.star_dict_list:
            a_line = ""
            for name_type in name_type_list:
                if name_type in star_dict.keys():
                    name_list = sorted([StringStarName((name_type, star_id)).string_name
                                        for star_id in star_dict[name_type]])
                    name_list.reverse()
                    for index in range(columns_per_name_type[name_type]):
                        if len(name_list) > index:
                            a_line += name_list[index] + ","
                        else:
                            a_line += ","
                else:
                    for index in range(columns_per_name_type[name_type]):
                        a_line += ","
            body.append(a_line[:-1] + "\n")
        # The file writing code
        with open(write_name, 'w') as f:
            f.write(header)
            for a_line in body:
                f.write(a_line)


class StarDict(UserDict):
    def __missing__(self, key):
        if isinstance(key, str):
            raise KeyError
        return self[str(key)]

    def __contains__(self, key):
        return str(key) in self.data

    def __setitem__(self, key, value):
        if not self.__contains__(key):
            if isinstance(value, set):
                self.data[str(key)] = value
            else:
                self.data[str(key)] = {value}
        if isinstance(value, set):
            self.data[str(key)] |= value
        else:
            self.data[str(key)].add(value)


if __name__ == "__main__":
    # a live lookup that writes no reference files:  python -m autostar.simbad_query "HD 189733"
    import sys
    name = ' '.join(sys.argv[1:]) or 'HD 189733'
    print(f'SIMBAD server: {Simbad.server}')
    record = get_query_object(name)
    if record is None:
        print(f'{name}: not found')
        sys.exit(1)
    print(f'{name}: MAIN_ID={record["MAIN_ID"]} RA={record["RA"]} DEC={record["DEC"]} '
          f'COO_BIBCODE={record["COO_BIBCODE"]}')
    names = get_single_name_data(name)
    print(f'{len(names)} name types: ' + ', '.join(f'{k}={sorted(v)}' for k, v in sorted(names.items())))
