import os

import numpy as np
import astroquery.mast

from autostar.table_read import num_format
from autostar.simbad_query import SimbadLib, StarDict
from autostar.object_params import ObjectParams, set_single_param
from autostar.config.datapaths import tic_ref_filename, star_name_format, StringStarName


class TicQuery:
    def __init__(self, simbad_lib=None, reference_file_name=None, verbose=True):
        self.verbose = verbose
        self.primary_values = {"Teff", "logg", "mass", "rad"}
        self.error_values = {"e_" + primary_value for primary_value in self.primary_values}
        self.error_to_primary_values = {"e_" + primary_value: primary_value for primary_value in self.primary_values}
        self.primary_values_to_error = {primary_value: "e_" + primary_value for primary_value in self.primary_values}
        self.tic_data_wanted = self.primary_values | self.error_values
        self.units_dict = {"Teff": "K", "logg": "cgs", "mass": "M_sun", "rad": "R_sun"}
        self.params_with_units = set(self.units_dict.keys())
        self.name_preference = ["gaia dr2", "2mass", "tyc", "hip"]
        self.allowed_names = {name_type for name_type in self.name_preference}
        self.new_tic_data = []
        self.header_star_name_types = set()
        self.tic_ref_data = None
        self.ref_data_hypatia_handle = None
        self.available_handles = None
        self.new_data_count = 0
        if simbad_lib is None:
            self.simbad_lib = SimbadLib()
        else:
            self.simbad_lib = simbad_lib
        if reference_file_name is None:
            self.reference_file_name = tic_ref_filename
        else:
            self.reference_file_name = reference_file_name

    def get_tic_data(self, requested_star_names_dict):
        """
        Get data from the online TIC catalog one item at a time.

        The desired values from the TIC are identified under tic_wanted_data, which must match the TIC headers. And
        because the TIC only has a certain number of limited names that are allowed, those are indicated under
        allowed_names_dict, which gives the names in hypatia and in the TIC, respectively.

        The TIC data is pulled using astroquery:
        https://astroquery.readthedocs.io/en/latest/mast/mast.html
        which provides the information as a masked table:
        https://docs.astropy.org/en/stable/table/masking.html
        """
        if self.verbose:
            print("Requesting Tess Input Catalog Data for a star with name(s):", requested_star_names_dict)
        # get information needed to preform the TIC database Query
        tic_query_names = self.select_name(requested_star_names_dict)
        available_names_in_preference_order = []
        available_name_types_this_star = set()
        string_name_dict = StarDict()
        for formatted_string_name in tic_query_names.keys():
            tic_name_type, hypatia_name_type, star_id = tic_query_names[formatted_string_name]
            available_name_types_this_star.add(hypatia_name_type)
            string_name_dict[hypatia_name_type] = formatted_string_name
        for hypatia_name_type in self.name_preference:
            if hypatia_name_type in available_name_types_this_star:
                for formatted_string_name in string_name_dict[hypatia_name_type]:
                    available_names_in_preference_order.append(formatted_string_name)
        # we can try all the available names in the to see it we get a match to the TIC data
        raw_tic_data = None
        desired_index = None
        for name_type in available_names_in_preference_order:
            # preform the TIC database Query
            try:
                raw_tic_data = astroquery.mast.Catalogs.query_object(name_type, catalog="TIC", radius=0.0001)
            except astroquery.exceptions.ResolverError:
                # this is the error that happens when the star is not found.
                pass
            # We only need to continue if data was retrieved
            if raw_tic_data is not None:
                # broadcast the table data into a dictionary
                raw_tic_dict = dict(raw_tic_data)
                # clean the dictionary to reveal only the data
                split_tic_dict = {key: str(raw_tic_dict[key]).split("\n")[2:] for key in raw_tic_dict.keys()}
                possible_found_tic_params = set(split_tic_dict.keys())
                # sometimes the query returns more then one result, find the index of the desired result
                for name_type_column_check in available_names_in_preference_order:
                    string_name, tic_name_type, star_id = tic_query_names[name_type_column_check]
                    for index, test_star_id in list(enumerate(split_tic_dict[string_name])):
                        if test_star_id == star_id:
                            desired_index = index
                            break
                    if desired_index is not None:
                        break
                if desired_index is not None:
                    break
        tic_params_dict = {}
        if desired_index is not None:
            # this is the flag that indicates everything that was needed was obtained.
            for over_lapping_param in self.tic_data_wanted & possible_found_tic_params:
                value = num_format(split_tic_dict[over_lapping_param][desired_index])
                # the data can still be all nans
                if not np.isnan(value):
                    tic_params_dict[over_lapping_param] = value
        if self.verbose:
            if tic_params_dict == {}:
                print("  Tess Input Catalog data not found for star_dict =!", requested_star_names_dict)
            else:
                print("  Tess Input Catalog data found!")
        # sometimes there is an error available but not the primary value (annoying), we delete those cases here
        tic_params_dict_keys = set(tic_params_dict.keys())
        for error_type in self.error_values & tic_params_dict_keys:
            value_type = self.error_to_primary_values[error_type]
            if value_type not in tic_params_dict_keys:
                del tic_params_dict[error_type]
        # we write out data when the tic_dict is empty. The empty tic_dict is an indication to not repeat this search
        self.new_tic_data.append((requested_star_names_dict, tic_params_dict))
        return tic_params_dict

    def select_name(self, star_names_dict):
        # string_name, name_type, star_num
        tic_query_names = {}
        for name_type in set(star_names_dict.keys()) & self.allowed_names:
            # Convert into an upper case string for the star, name using the Simbad formatter.
            for star_id in star_names_dict[name_type]:
                string_name = StringStarName(hypatia_name=(name_type, star_id)).string_name.upper()
                # The TIC name types are all in upper case
                tic_name_type = name_type.upper()
                # get only the number from the str star name
                star_id = string_name.replace(tic_name_type, "").strip()
                # deal with a few special cases
                if name_type == "2mass":
                    tic_name_type = "TWOMASS"
                    star_id = star_id.replace("J", "").strip()
                elif name_type == "gaia dr2":
                    tic_name_type = "GAIA"
                tic_query_names[string_name] = (tic_name_type, name_type, star_id)
        return tic_query_names

    def find_tic_dict(self, requested_star_names_dict):
        requested_tic_dict = None
        if self.tic_ref_data is None:
            self.load_ref()
        search_star_name_types = set(requested_star_names_dict.keys()) & self.allowed_names
        search_name_list = [name_type for name_type in self.name_preference if name_type in search_star_name_types]
        for name_type in search_name_list:
            for star_names_dict, tic_dict in self.tic_ref_data:
                if name_type in set(star_names_dict.keys()):
                    if star_names_dict[name_type] == requested_star_names_dict[name_type]:
                        requested_tic_dict = tic_dict
                        break
            if requested_tic_dict is not None:
                break
        return requested_tic_dict

    def new_data_update_loop(self, requested_star_names_dict, update_ref=True):
        """
        Check to see if a star is in the reference data. If not, do database a query. If data is found, write it out
        to the reference data.

        This is wasteful in terms of input-output writing and searching. Scales with the length of the
        reference file.

        :param requested_star_names_dict:
        :param update_ref: bool - True, update the references files with new data when found. Turn to False for
                           faster processing of new data by updating the reference after a batch from an out scope.
        :return: requested_tic_dict
        """
        if isinstance(requested_star_names_dict, (str, tuple)):
            hypatia_handle, requested_star_names_dict = self.simbad_lib.get_star_dict(requested_star_names_dict)
        hypatia_handle, requested_star_names_dict = self.simbad_lib.get_star_dict_with_star_dict(requested_star_names_dict)
        if self.ref_data_hypatia_handle is None:
            self.make_ref_data_look_up_dicts()
            # self.ref_data_hypatia_handle = None
        if set(requested_star_names_dict.keys()) & self.allowed_names != set():
            if hypatia_handle in self.available_handles:
                return self.ref_data_hypatia_handle[hypatia_handle]
            else:
                requested_tic_dict = self.get_tic_data(requested_star_names_dict=requested_star_names_dict)
                self.new_data_count += 1
                if update_ref:
                    self.update_ref()
                return requested_tic_dict
        return {}

    def update_ref(self):
        self.write_data(append_mode=True)
        self.load_ref()

    def get_object_params(self, requested_star_names_dict, update_ref=True):
        requested_dict = self.new_data_update_loop(requested_star_names_dict=requested_star_names_dict,
                                                   update_ref=update_ref)
        ref_str = "Tess Input Catalog"
        params_dicts = {}
        param_names = set()
        for param_key in requested_dict.keys():
            if "e_" == param_key[:2]:
                param_name = param_key.replace("e_", "")
                if param_name not in param_names:
                    params_dicts[param_name] = {}
                    param_names.add(param_name)
                params_dicts[param_name]['err'] = requested_dict[param_key]
            else:
                if param_key not in param_names:
                    params_dicts[param_key] = {}
                    param_names.add(param_key)
                params_dicts[param_key]['value'] = requested_dict[param_key]
                params_dicts[param_key]['ref'] = ref_str
                if param_key in self.params_with_units:
                    params_dicts[param_key]['units'] = self.units_dict[param_key]
        new_object_params = ObjectParams()
        for param_name in params_dicts.keys():
            new_object_params[param_name] = set_single_param(param_dict=params_dicts[param_name])
        return new_object_params

    def update_to_and_from_simbad_ref(self):
        self.simbad_lib.simbad_ref.load()
        self.simbad_lib.simbad_ref.make_lookup()
        for star_names_dict, tic_dic in self.tic_ref_data:
            simbad_star_dict = None
            for name_type in star_names_dict.keys():
                for star_id in star_names_dict[name_type]:
                    hypatia_name = (name_type, star_id)
                    _hypatia_handle, simbad_star_dict = self.simbad_lib.get_star_dict(hypatia_name=hypatia_name)
                    star_names_dict.update(simbad_star_dict)
                    break
                if simbad_star_dict is not None:
                    break
            else:
                self.simbad_lib.simbad_ref.add_star_dicts([star_names_dict])
                self.simbad_lib.simbad_ref.load()
                self.simbad_lib.simbad_ref.make_lookup()
        self.write_data()
        self.load_ref()
        for star_names_dict in self.simbad_lib.simbad_ref.star_dict_list:
            self.new_data_update_loop(star_names_dict)

    def make_ref_data_look_up_dicts(self):
        if self.tic_ref_data is None:
            self.load_ref()
        self.ref_data_hypatia_handle = {}
        self.available_handles = set()
        for star_names_dict, tic_dic in self.tic_ref_data:
            hypatia_handle, _star_name_dict = self.simbad_lib.get_star_dict_with_star_dict(star_names_dict)
            self.ref_data_hypatia_handle[hypatia_handle] = tic_dic
            self.available_handles.add(hypatia_handle)

    def write_data(self, append_mode=True):
        """
        Write the Tess Input Catalog data to a reference file, see self.reference_file_name for the file path.

        :param append_mode: bool - When True, existing reference data is loaded from self.reference_file_name.
                                   new reference data added by the method get_tic_data and stored in
                                   self.new_tic_data is added to the existing reference data and is written out.
                                   When False, only the new data is written to the reference file, overwritting
                                   existing data
        :return:
        """
        data_to_write = []
        # get the previously found reference data
        if os.path.isfile(self.reference_file_name) and append_mode:
            self.load_ref()
            data_to_write.extend(self.tic_ref_data)
        data_to_write.extend(self.new_tic_data)
        # get the column names for this data
        column_names = self.name_preference[:]
        for prime_value_name in sorted(self.primary_values):
            column_names.append(prime_value_name)
            error_value_name = self.primary_values_to_error[prime_value_name]
            column_names.append(error_value_name)
        # make the output's header
        header = ""
        for column_name in column_names:
            header += column_name + ","
        header = header[:-1]
        # make the output's body of data and star names
        body = []
        for star_dict, tic_dict in data_to_write:
            single_line = ""
            name_type_this_star = set(star_dict.keys()) & self.allowed_names
            data_types_this_star = set(tic_dict.keys())
            for column_name in column_names:
                if column_name in name_type_this_star:
                    name_list = sorted([StringStarName((column_name, star_id)).string_name
                                        for star_id in list(star_dict[column_name])])
                    single_line += name_list[-1] + ","
                elif column_name in data_types_this_star:
                    single_line += str(tic_dict[column_name]) + ","
                else:
                    single_line += ","
            body.append(single_line[:-1])
        # write the data to a file
        with open(self.reference_file_name, 'w') as f:
            f.write(header + "\n")
            for single_line in body:
                f.write(single_line + "\n")
        # do some clean up to reset this class to initial conditions
        self.tic_ref_data = None
        self.new_tic_data = []
        if self.verbose:
            print(self.new_data_count, " new TIC data requests this run.")
            print("Writing Tess Input Catalog data to reference file:", self.reference_file_name, "\n")

    def load_ref(self):
        self.tic_ref_data = []
        if os.path.isfile(self.reference_file_name):
            with open(self.reference_file_name, 'r') as f:
                raw_ref_data = f.readlines()
            column_names = raw_ref_data[0].strip().split(",")
            self.header_star_name_types |= set(column_names) - self.tic_data_wanted
            for data_line in raw_ref_data[1:]:
                star_names_dict = StarDict()
                tic_dict = {}
                values = data_line.strip().split(',')
                for index, value in list(enumerate(values)):
                    column_name = column_names[index]
                    if value != "":
                        if column_name in self.header_star_name_types:
                            _, star_id = star_name_format(value, key=column_name)
                            star_names_dict[column_name] = star_id
                        elif column_name in self.tic_data_wanted:
                            tic_dict[column_name] = num_format(value)
                if star_names_dict != {}:
                    self.tic_ref_data.append((star_names_dict, tic_dict))


if __name__ == "__main__":
    tq = TicQuery(simbad_lib=None, reference_file_name=None, verbose=True)
    one_star_tic_data = tq.new_data_update_loop("TYC 4767-00765-1")
