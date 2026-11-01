import os
import time
import importlib

import numpy as np
from astropy import units as u
from astropy.time import Time
from astropy.coordinates import SkyCoord, Distance

from autostar.table_read import row_dict
from autostar.simbad_query import SimbadLib, StarDict
from autostar.object_params import ObjectParams, set_single_param
from autostar.config.datapaths import ref_dir, star_name_format, StarName, StringStarName


deg_per_mas = 1.0 / (1000.0 * 60.0 * 60.0)
gaia_dr3_ref = "Gaia DR3 Gaia Collaboration et al. (2016b) and Gaia Collaboration et al. (2022k)"


def simple_job_text(dr_num, sub_list):
    job_text = "SELECT * FROM gaiadr" + str(dr_num) + ".gaia_source WHERE source_id=" + str(sub_list[0])
    if len(sub_list) > 1:
        for list_index in range(1, len(sub_list)):
            job_text += " OR source_id=" + str(sub_list[list_index])
    return job_text


class GaiaLib:
    gaia_dr3_ref = gaia_dr3_ref

    def __init__(self, simbad_lib=None, simbad_go_fast=False, verbose=True):
        self.verbose = verbose
        self.simbad_go_fast = simbad_go_fast
        self.max_dr_number = 3
        self.dr_numbers = list(range(1, self.max_dr_number + 1))
        self.gaia_name_types = set()
        for dr_number in self.dr_numbers:
            self.gaia_name_types.add("gaia dr" + str(dr_number))
            self.__setattr__('gaiadr' + str(dr_number) + "_ref",
                             GaiaRef(verbose=self.verbose, dr_number=dr_number))
        if simbad_lib is None:
            self.simbad_lib = SimbadLib(go_fast=self.simbad_go_fast, verbose=self.verbose)
        else:
            self.simbad_lib = simbad_lib

        self.gaia_query = GaiaQuery(verbose=self.verbose)

        self.object_params_to_trim = {"ra", "ra_error", 'dec', "dec_error", 'ref_epoch', "duplicated_source",
                                      "source_id"}

        self.special_case_params = {"r_est", "r_lo", 'r_hi',
                                    "teff_val", "teff_percentile_upper", 'teff_percentile_lower'}

    def batch_update(self, dr_number, simbad_formatted_names_list):
        dr_number = int(dr_number)
        gaia_ref = self.__getattribute__('gaiadr' + str(dr_number) + "_ref")
        self.gaia_query.astroquery_source(simbad_formatted_name_list=simbad_formatted_names_list, dr_num=dr_number)
        gaia_star_ids = set(self.gaia_query.star_dict.keys())
        for gaia_star_id in gaia_star_ids:
            gaia_ref.add_ref({gaia_star_id}, self.gaia_query.star_dict[gaia_star_id])
        if gaia_star_ids != set():
            gaia_ref.save()

    def get_gaia_names_dict(self, hypatia_name):
        if isinstance(hypatia_name, dict) or isinstance(hypatia_name, StarDict):
            hypatia_handle, star_names_dict = self.simbad_lib.get_star_dict_with_star_dict(hypatia_name)
        else:
            hypatia_handle, star_names_dict = self.simbad_lib.get_star_dict(hypatia_name=hypatia_name)
        gaia_star_names_dict = {star_type: star_names_dict[star_type] for star_type in star_names_dict.keys()
                                if star_type in self.gaia_name_types}
        return hypatia_handle, gaia_star_names_dict

    def get_single_dr_number_data(self, gaia_hypatia_name):
        gaia_name_type, gaia_star_id = gaia_hypatia_name
        dr_number = int(gaia_name_type.replace("gaia dr", "").strip())
        gaia_ref = self.__getattribute__('gaiadr' + str(dr_number) + "_ref")
        test_output = gaia_ref.find(gaia_star_id=gaia_star_id)
        if test_output is not None:
            # This is the primary case, data is available in the reference file, and is returned
            return test_output
        else:
            # is data available on the ESA website?
            dr_number = int(gaia_name_type.lower().replace("gaia dr", "").strip())
            self.gaia_query.astroquery_source([StringStarName(StarName(gaia_name_type, gaia_star_id)).string_name],
                                              dr_num=dr_number)
            if gaia_star_id in self.gaia_query.star_dict.keys():
                # We found the data and can update the reference data so that it is found first next time
                gaia_params_dict = self.gaia_query.star_dict[gaia_star_id]
            else:
                # no data was found, we record this so that next time a search is not needed.
                gaia_params_dict = {}
            gaia_ref.add_ref({gaia_star_id}, gaia_params_dict)
            gaia_ref.save()
            gaia_ref.load()
            gaia_ref.make_lookup()
            return self.get_single_dr_number_data(gaia_hypatia_name)

    def get(self, hypatia_name):
        hypatia_handle, gaia_star_names_dict = self.get_gaia_names_dict(hypatia_name)
        gaia_hypatia_names = []
        for gaia_name_type in gaia_star_names_dict.keys():
            for star_id in gaia_star_names_dict[gaia_name_type]:
                gaia_hypatia_names.append(StarName(gaia_name_type, star_id))
        return hypatia_handle, {gaia_hypatia_name: self.get_single_dr_number_data(gaia_hypatia_name)
                                for gaia_hypatia_name in gaia_hypatia_names}

    def convert_to_object_params(self, gaia_params_dicts):
        new_object_params = ObjectParams()
        for gaia_hypatia_name in gaia_params_dicts.keys():
            gaia_name_type, _gaia_star_id = gaia_hypatia_name
            dr_number = int(gaia_name_type.replace("gaia dr", "").strip())
            _gaia_ids, gaia_params_dict = gaia_params_dicts[gaia_hypatia_name]
            gaia_params_dict_keys = set(gaia_params_dict.keys())
            if dr_number == 3:
                ref_str = self.gaia_dr3_ref
            else:
                ref_str = "Gaia Data Release " + str(dr_number)
            params_dicts = {}
            param_names_found = set()
            # handling for the distance from the Bailer-Jones Catalog
            if "r_est" in gaia_params_dict_keys:
                params_dicts['dist'] = {}
                param_names_found.add('dist')
                params_dicts['dist']['value'] = gaia_params_dict["r_est"]
                params_dicts['dist']['ref'] = "Bailer-Jones et al. (2018)"
                params_dicts['dist']['units'] = self.gaia_query.param_to_units["r_est"]
                if "r_hi" in gaia_params_dict_keys:
                    upper_error = gaia_params_dict["r_hi"] - gaia_params_dict["r_est"]
                else:
                    upper_error = None
                if "r_lo" in gaia_params_dict_keys:
                    lower_error = gaia_params_dict["r_lo"] - gaia_params_dict["r_est"]
                else:
                    lower_error = None
                if lower_error is not None or upper_error is not None:
                    params_dicts['dist']['err'] = (lower_error, upper_error)
            elif "distance_gspphot" in gaia_params_dict_keys:
                params_dicts['dist'] = {}
                param_names_found.add('dist')
                params_dicts['dist']['value'] = gaia_params_dict["distance_gspphot"]
                params_dicts['dist']['ref'] = self.gaia_dr3_ref
                params_dicts['dist']['units'] = self.gaia_query.param_to_units["distance_gspphot"]
                if "distance_gspphot_upper" in gaia_params_dict_keys:
                    upper_error = gaia_params_dict["distance_gspphot_upper"] - gaia_params_dict["distance_gspphot"]
                else:
                    upper_error = None
                if "distance_gspphot_lower" in gaia_params_dict_keys:
                    lower_error = gaia_params_dict["distance_gspphot_lower"] - gaia_params_dict["distance_gspphot"]
                else:
                    lower_error = None
                if lower_error is not None or upper_error is not None:
                    params_dicts['dist']['err'] = (lower_error, upper_error)

            if "teff_val" in gaia_params_dict_keys:
                params_dicts['teff'] = {}
                param_names_found.add('teff')
                params_dicts['teff']['value'] = gaia_params_dict["teff_val"]
                params_dicts['teff']['ref'] = ref_str
                params_dicts['teff']['units'] = self.gaia_query.param_to_units["teff_val"]
                if "teff_percentile_upper" in gaia_params_dict_keys:
                    upper_error = gaia_params_dict["teff_percentile_upper"] - gaia_params_dict["teff_val"]
                else:
                    upper_error = None
                if "teff_percentile_lower" in gaia_params_dict_keys:
                    lower_error = gaia_params_dict["teff_percentile_lower"] - gaia_params_dict["teff_val"]
                else:
                    lower_error = None
                if lower_error is not None or upper_error is not None:
                    params_dicts['teff']['err'] = (lower_error, upper_error)
            elif "teff_gspphot" in gaia_params_dict_keys:
                params_dicts['teff'] = {}
                param_names_found.add('teff')
                params_dicts['teff']['value'] = gaia_params_dict["teff_gspphot"]
                params_dicts['teff']['ref'] = ref_str
                params_dicts['teff']['units'] = self.gaia_query.param_to_units["teff_gspphot"]
                if "teff_gspphot_upper" in gaia_params_dict_keys:
                    upper_error = gaia_params_dict["teff_gspphot_upper"] - gaia_params_dict["teff_gspphot"]
                else:
                    upper_error = None
                if "teff_gspphot_lower" in gaia_params_dict_keys:
                    lower_error = gaia_params_dict["teff_gspphot_lower"] - gaia_params_dict["teff_gspphot"]
                else:
                    lower_error = None
                if lower_error is not None or upper_error is not None:
                    params_dicts['teff']['err'] = (lower_error, upper_error)
            for param_key in gaia_params_dict_keys - self.special_case_params:
                if "_error" in param_key:
                    param_name = param_key.replace("_error", "")
                    if param_name not in param_names_found:
                        params_dicts[param_name] = {}
                        param_names_found.add(param_name)
                    params_dicts[param_name]['err'] = gaia_params_dict[param_key]
                else:
                    if param_key not in param_names_found:
                        params_dicts[param_key] = {}
                        param_names_found.add(param_key)
                    params_dicts[param_key]['value'] = gaia_params_dict[param_key]
                    params_dicts[param_key]['ref'] = ref_str
                    if param_key in self.gaia_query.params_with_units:
                        params_dicts[param_key]['units'] = self.gaia_query.param_to_units[param_key]
            param_names = set(params_dicts.keys()) - self.object_params_to_trim
            for param_name in param_names:
                this_param_single_param = set_single_param(param_dict=params_dicts[param_name])
                new_object_params[param_name] = this_param_single_param
        return new_object_params

    def get_object_params(self, hypatia_name):
        hypatia_handle, gaia_params_dicts = self.get(hypatia_name)
        return hypatia_handle, self.convert_to_object_params(gaia_params_dicts=gaia_params_dicts)


class GaiaRef:
    def __init__(self, dr_number=2, verbose=False):
        self.dr_number = dr_number
        self.verbose = verbose
        self.ref_data = None
        self.gaia_name_type = "gaia dr" + str(self.dr_number)
        self.ref_file = os.path.join(ref_dir, "GaiaDR" + str(self.dr_number) + "_ref.csv")
        self.lookup = None
        self.available_ids = None

    def load(self):
        self.ref_data = []
        if os.path.exists(self.ref_file):
            read_ref = row_dict(filename=self.ref_file, key="name", delimiter=",", null_value="", inner_key_remove=True)
            for saved_names in read_ref.keys():
                star_ids = set()
                for simbad_formatted_gaia_name in saved_names.split("|"):
                    gaia_name_type, gaia_star_id = star_name_format(simbad_formatted_gaia_name)
                    star_ids.add(gaia_star_id)
                    if not gaia_name_type == self.gaia_name_type:
                        raise KeyError("Gaia Data Release," + str(self.gaia_name_type) + ", received:" +
                                       str(gaia_name_type))
                self.ref_data.append((star_ids, read_ref[saved_names]))

    def save(self):
        self.make_lookup()
        header_params = set()
        name_string_to_params = {}
        for star_ids, params in self.ref_data:
            header_params |= set(params.keys())
            star_names_string = ""
            for star_id in star_ids:
                hypatia_name = StarName(self.gaia_name_type, star_id)
                simbad_formatted_name = StringStarName(hypatia_name=hypatia_name).string_name
                star_names_string += simbad_formatted_name + "|"
            name_string_to_params[star_names_string[:-1]] = params
        header = "name,"
        sorted_header_params = sorted(header_params)
        for gaia_param in sorted_header_params:
            header += gaia_param + ","
        header = header[:-1] + "\n"
        body = []
        for output_string_name in sorted(name_string_to_params.keys()):
            params = name_string_to_params[output_string_name]
            row_data = output_string_name + ","
            params_this_row = set(params.keys())
            for param_name in sorted_header_params:
                if param_name in params_this_row:
                    row_data += str(params[param_name]) + ","
                else:
                    row_data += ","
            body.append(row_data[:-1] + "\n")
        with open(self.ref_file, 'w') as f:
            f.write(header)
            [f.write(row_data) for row_data in body]

    def add_ref(self, gaia_star_ids, params):
        if self.ref_data is None:
            self.load()
        self.ref_data.append((gaia_star_ids, params))

    def find(self, gaia_star_id):
        if self.lookup is None:
            self.make_lookup()
        if gaia_star_id in self.available_ids:
            return self.ref_data[self.lookup[gaia_star_id]]
        return None

    def make_lookup(self):
        if self.ref_data is None:
            self.load()
        self.lookup = {}
        self.available_ids = set()
        found_index = None
        for ref_index, (star_ids, params) in list(enumerate(self.ref_data)):
            for gaia_star_id in star_ids:
                if gaia_star_id not in self.available_ids:
                    self.available_ids.add(gaia_star_id)
                    self.lookup[gaia_star_id] = ref_index
                else:
                    found_index = self.lookup[gaia_star_id]
                    break
            if found_index is not None:
                # only add new types, do not overwrite
                print("Duplicate_data data found, removing duplicate and restarting the Gaia reference file tool:" +
                      " make_lookup")
                self.ref_data.pop(ref_index)
                # run this again with a duplicate entry removed.
                self.make_lookup()
                break


class GaiaQuery:
    def __init__(self, verbose=False):
        # import this package at 'runtime' not 'import time' to avoid an unnecessary connection to the Gaia SQL server
        self.astro_query_gaia = importlib.import_module("astroquery.gaia")
        self.Gaia = self.astro_query_gaia.Gaia
        self.verbose = verbose
        self.gaia_dr1_data = None
        self.gaia_dr2_data = None
        self.gaia_dr3_data = None

        self.astro_query_dr1_params = {"ra", "ra_error", "dec", "dec_error", "ref_epoch", "source_id", "parallax",
                                       "parallax_error",
                                       "pmra", "pmra_error", "pmdec", "pmdec_error", "duplicated_source",
                                       "phot_g_mean_flux", "phot_g_mean_flux_error", "phot_g_mean_mag"}
        self.astro_query_dr2_params = {"ra", "ra_error", "dec", "dec_error", "ref_epoch", "source_id",
                                       "parallax", "parallax_error",
                                       "pmra", "pmra_error", "pmdec", "pmdec_error", "duplicated_source",
                                       "phot_g_mean_flux", "phot_g_mean_flux_error",
                                       "phot_g_mean_mag",
                                       "radial_velocity", "radial_velocity_error",
                                       "teff_val", "teff_percentile_lower", "teff_percentile_upper",
                                       "r_est", "r_lo", "r_hi"}
        self.astro_query_dr3_params = {"ra", "ra_error", "dec", "dec_error", "ref_epoch", "source_id",
                                       "parallax", "parallax_error",
                                       "pmra", "pmra_error", "pmdec", "pmdec_error", "duplicated_source",
                                       "phot_g_mean_flux", "phot_g_mean_flux_error",
                                       "phot_g_mean_mag",
                                       "radial_velocity", "radial_velocity_error",
                                       "teff_gspphot", "teff_gspphot_lower", "teff_gspphot_upper",
                                       "distance_gspphot", "distance_gspphot_lower", "distance_gspphot_upper"}
        self.param_to_units = {"ra_epochJ2000": "deg", "ra_error": "deg", 'dec_epochJ2000': 'deg', "dec_error": 'deg',
                               "ref_epoch": 'Julian Years', 'parallax': 'mas', "parallax_error": "mas",
                               "pmra": 'mas/year', "pmra_error": "mas/year",
                               "pmdec": 'mas/year', "pmdec_error": "mas/year",
                               "phot_g_mean_flux": "e-/s", "phot_g_mean_mag": 'mag',
                               "radial_velocity": "km/s",
                               "teff_val": "K", "teff_percentile_lower": "K", "teff_percentile_upper": "K",
                               "teff_gspphot": "K", "teff_gspphot_lower": "K", "teff_gspphot_upper": "K",
                               "dist_parallax": "[pc]",
                               "r_est": "[pc]", "r_lo": "[pc]", "r_hi": "[pc]", 'dist': '[pc]',
                               "distance_gspphot": "[pc]", "distance_gspphot_lower": "[pc]", "distance_gspphot_upper": "[pc]"}
        self.params_with_units = set(self.param_to_units.keys())

    def astroquery_get_job(self, job, dr_num=2):
        while job._phase != "COMPLETED":
            time.sleep(1)
        raw_results = job.get_results()
        sources_dict = {}

        if dr_num == 1:
            query_params = self.astro_query_dr1_params
        elif dr_num == 2:
            query_params = self.astro_query_dr2_params
        elif dr_num == 3:
            query_params = self.astro_query_dr3_params
        else:
            raise KeyError("The given Gaia Data Release number " + str(dr_num) + " is not of the format.")

        for index in range(len(raw_results.columns["source_id"])):
            available_params = set(raw_results.columns)
            params_dict = {param: raw_results.columns[param][index] for param in available_params & query_params
                           if not np.ma.is_masked(raw_results.columns[param][index])}
            found_params = set(params_dict.keys())
            if {'ra', 'dec', 'pmra', 'pmdec', "ref_epoch"} - found_params == set():
                # if parallax is available, do a more precise calculation using the distance.
                if np.ma.is_masked(params_dict['parallax']) or params_dict['parallax'] < 0.0:
                    icrs = SkyCoord(ra=params_dict['ra'] * u.deg, dec=params_dict['dec'] * u.deg,
                                    pm_ra_cosdec=params_dict['pmra'] * u.mas / u.yr,
                                    pm_dec=params_dict['pmdec'] * u.mas / u.yr,
                                    obstime=Time(params_dict['ref_epoch'], format='decimalyear'))
                else:
                    icrs = SkyCoord(ra=params_dict['ra'] * u.deg, dec=params_dict['dec'] * u.deg,
                                    distance=Distance(parallax=params_dict['parallax'] * u.mas, allow_negative=False),
                                    pm_ra_cosdec=params_dict['pmra'] * u.mas / u.yr,
                                    pm_dec=params_dict['pmdec'] * u.mas / u.yr,
                                    obstime=Time(params_dict['ref_epoch'], format='decimalyear'))
                J2000 = icrs.apply_space_motion(Time(2000.0, format='decimalyear'))
                params_dict["ra_epochJ2000"] = J2000.ra.degree
                params_dict["dec_epochJ2000"] = J2000.dec.degree
                params_dict["ra_epochJ2000_error"] = params_dict["ra_error"] * deg_per_mas
                params_dict["dec_epochJ2000_error"] = params_dict["dec_error"] * deg_per_mas
                # distance
                if 'parallax' in found_params:
                    parallax_arcsec = float(params_dict['parallax']) * 0.001
                    params_dict['dist_parallax'] = 1.0 / parallax_arcsec
                    # if "parallax_error" in found_params:
                    #     parallax_error_arcsec = float(params_dict['parallax_error']) * 0.001
                    #     params_dict['dist_parallax_error'] = 1.0 / (parallax_arcsec - (2.0 * parallax_error_arcsec))
            sources_dict[params_dict['source_id']] = {param: params_dict[param] for param in params_dict.keys()
                                                      if params_dict[param] != '--'}
        return sources_dict

    def astroquery_source(self, simbad_formatted_name_list, dr_num=2):
        list_of_sub_lists = []
        sub_list = []
        cut_index = len("Gaia DR# ")
        cut_name_list = [gaia_name[cut_index:] for gaia_name in simbad_formatted_name_list]
        for source_id in cut_name_list:
            if len(sub_list) == 500:
                list_of_sub_lists.append(sub_list)
                sub_list = [source_id]
            else:
                sub_list.append(source_id)
        list_of_sub_lists.append(sub_list)
        self.star_dict = {}
        for sub_list in list_of_sub_lists:
            if dr_num == 2:
                job_text = "SELECT * FROM gaiadr" + str(dr_num) + ".gaia_source AS g, " + \
                           "external.gaiadr2_geometric_distance AS d " + \
                           "WHERE (g.source_id=" + str(sub_list[0]) + " AND d.source_id = g.source_id)"
                if len(sub_list) > 1:
                    for list_index in range(1, len(sub_list)):
                        job_text += " OR (g.source_id=" + str(sub_list[list_index]) + " AND d.source_id = g.source_id)"
            else:
                job_text = simple_job_text(dr_num, sub_list)
            job = self.Gaia.launch_job_async(job_text)
            sources_dict = self.astroquery_get_job(job, dr_num=dr_num)
            redo_ids = [source_id for source_id in
                        {int(source_id_str) for source_id_str in sub_list} - set(sources_dict.keys())]
            if redo_ids:
                job_text = simple_job_text(dr_num, redo_ids)
                job = self.Gaia.launch_job_async(job_text)
                sources_dict.update(self.astroquery_get_job(job, dr_num=dr_num))
            self.star_dict.update({(gaia_id_int,): sources_dict[gaia_id_int] for gaia_id_int in sources_dict.keys()})

    def astroquery_cone(self, ra_icrs, dec_icrs, radius_deg=1.0):
        # gaia_coord = convert_to_gaia_dr2_coord(ra_icrs, dec_icrs)

        job_text = "SELECT * FROM gaiadr2.gaia_source WHERE " + \
                   "CONTAINS(POINT('ICRS',gaiadr2.gaia_source.ra,gaiadr2.gaia_source.dec)," + \
                   "CIRCLE('ICRS'," + str(ra_icrs) + "," + str(dec_icrs) + "," + str(radius_deg) + "))=1;"

        job = self.Gaia.launch_job_async(job_text)
        sources_dict = self.astroquery_get_job(job)
        return sources_dict


if __name__ == "__main__":
    gl = GaiaLib(verbose=True)
    hypatia_handle, gaia_params = gl.get(hypatia_name="HD 1234")
    # gl.gaia_query.astroquery_source(simbad_formatted_name_list=["Gaia DR2 1016674048078637568",
    #                                                               "Gaia DR2 1076515002779544960"], dr_num=2)
