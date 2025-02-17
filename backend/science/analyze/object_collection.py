import os
import copy
import shutil

import numpy as np
from datetime import datetime
from operator import attrgetter
from itertools import zip_longest

from astropy import units as u
from astropy.coordinates import SkyCoord, FK5

from ref.star_names import star_name_format, StringStarName
from ref.ref import (object_params_dir, spectra_schema, spexo_schema, stacked_line_schema,
    references_per_parameter_path, instrument_metadata, sql_spectrum_types,
    bandwidth_fraction_for_null, simbad_reference, web_default_spectrum, output_dir)

from autostar.read_gaia import GaiaLib
from autostar.tic_query import TicQuery
from autostar.table_read import num_format
from autostar.object_params import SingleParam, set_single_param
from autostar.name_correction import verify_starname, PopNamesLib
from autostar.simbad_query import StarDict, SimbadLib, handle_to_simbad, SimbadMainRef, simbad_coord_to_deg
from science.db.sql import LoadSQL
from science.load.flux_cal import FluxCal
from science.db.file_sync import rsync_output
from science.load.line_flux import LineFluxes
from science.load.import_spectra import AllSpectra
from science.analyze.single_star import SingleObject
from science.db.alchemy import UploadSQL, is_good_num
from science.db.data_status import set_data_status_mysql
from science.load.ref_rank import rank_ref, rank_per_column
from science.load.units import UnitsObjectParams, params_check
from science.analyze.spectrum import (SpectraSummary, set_single_output_spectra, spectra_output_dir_default,
                                      handle_to_inst_dict, get_spectrum_output_dir)
from science.load.hitran import (HitranRef, isotopologue_to_molecule, isotopologue_to_color, plotly_dash_value,
                                 molecule_to_label, isotopologue_to_label, make_hl_dict,
                                 columns_CO, columns_H2O, columns_OH)


def set_website_values(ra_epoch_j2000_deg, dec_epoch_j2000_deg):
    esa_sky = f'https://sky.esa.int/?target={ra_epoch_j2000_deg}%20{dec_epoch_j2000_deg}&' + \
              f'hips=DSS2+color&fov=0.24832948784432046&cooframe=J2000&sci=true&lang=en'
    ra_dec_str_for_web = ra_dec_web_format(ra_epoch_j2000_deg=ra_epoch_j2000_deg,
                                           dec_epoch_j2000_deg=dec_epoch_j2000_deg)
    ra, dec = ra_dec_str_for_web.split(',')
    return ra, dec, esa_sky, ra_dec_str_for_web


def fair_rounding(ones_int, decimal_int):
    ones_int = int(ones_int)
    decimal_int = int(decimal_int)
    if decimal_int < 5:
        return ones_int
    elif decimal_int > 5:
        return ones_int + 1
    else:  # when decimal_int == 5
        # when 5 round down for even ones_int and up for odd
        if ones_int % 2 == 0:
            return ones_int
        else:
            return ones_int + 1


def format_after_decimal(hmsstr):
    try:
        hms_front, s_decimal = hmsstr.split('.')
    except ValueError:
        return hmsstr
    hms_formatted = f'{hms_front}.'
    if len(s_decimal) < 1:
        hms_formatted += '0'
    elif len(s_decimal) == 1:
        hms_formatted += s_decimal
    else:
        hms_formatted += f'{fair_rounding(ones_int=s_decimal[0], decimal_int=s_decimal[1])}'
    return hms_formatted


def ra_dec_web_format(ra_epoch_j2000_deg, dec_epoch_j2000_deg):
    coord = SkyCoord(ra=ra_epoch_j2000_deg * u.deg, dec=dec_epoch_j2000_deg * u.deg,
                     frame=FK5(equinox='J2000'), unit="deg")
    rahmsstr = coord.ra.to_string(u.hour).replace('s', '').replace('m', ' ').replace('h', ' ')
    decdmsstr = coord.dec.to_string(u.degree, alwayssign=True).replace('s', '').replace('m', ' ').replace('d', ' ')
    web_string = f'{format_after_decimal(hmsstr=rahmsstr)},{format_after_decimal(hmsstr=decdmsstr)}'
    return web_string


def get_stacked_line_handle(isotopologue: str, transition: str, spectrum_handle: str) -> str:
    return str(isotopologue + "_" + transition.replace("-", "to") +
               "_" + spectrum_handle).lower()


def spectrum_sql_upload_old(output_sql, single_spectrum, database=spectra_schema, table_name=None):
    spectrum_handle = single_spectrum.spectrum_handle
    if table_name is None:
        table_name = spectrum_handle
    output_sql.creat_table(table_name=table_name, database=database,
                           dynamic_type="spectrum", run_silent=True)
    output_sql.buffer_insert_init(table_name=table_name,
                                  columns=["wavelength_um", "velocity_kmps", "flux", "flux_error"],
                                  database=database, run_silent=True)
    if single_spectrum.flux_error is None:
        for wavelength_um, velocity_kmps, flux \
                in zip(single_spectrum.wavelength_um, single_spectrum.velocity_kmps, single_spectrum.flux):
            if is_good_num(flux):
                output_sql.buffer_insert_value(values=[wavelength_um, velocity_kmps, flux, None])
            else:
                output_sql.buffer_insert_value(values=[wavelength_um, velocity_kmps, None, None])
    else:
        for wavelength_um, velocity_kmps, flux, flux_error \
                in zip(single_spectrum.wavelength_um, single_spectrum.velocity_kmps,
                       single_spectrum.flux, single_spectrum.flux_error):
            single_row_values = [wavelength_um, velocity_kmps]
            if is_good_num(flux):
                single_row_values.append(flux)
            else:
                single_row_values.append(None)
            if is_good_num(flux_error):
                single_row_values.append(flux_error)
            else:
                single_row_values.append(None)
            output_sql.buffer_insert_value(values=single_row_values)
    output_sql.buffer_insert_execute(run_silent=True)
    return


def spectrum_data_for_sql(single_spectrum):
    spectrum_data = {"spectrum_handle": single_spectrum.spectrum_handle.lower(),
                     "spexodisks_handle": single_spectrum.spexodisks_handle,
                     "spectrum_display_name": single_spectrum.spectrum_display_name}
    for an_attr in sql_spectrum_types:
        if an_attr == 'output_filename':
            value = single_spectrum.sql_file_path
        else:
            value = single_spectrum.__getattribute__(an_attr)
        if value is not None:
            if isinstance(value, bool):
                value = int(value)
            spectrum_data["spectrum_" + an_attr] = value
    return spectrum_data


class ObjectCollection:
    def __init__(self, verbose=True, simbad_go_fast=False, spectra_output_dir=spectra_output_dir_default,
                 update_mode: bool = False):
        self.verbose = verbose
        if self.verbose:
            print("Initializing SpExoDisks Database")
        self.simbad_go_fast = simbad_go_fast
        self.spectra_output_dir = spectra_output_dir
        self.update_mode = update_mode
        if not os.path.isdir(self.spectra_output_dir):
            os.mkdir(self.spectra_output_dir)
        self.params_output_dir = os.path.join(self.spectra_output_dir, '!params')
        if not os.path.isdir(self.params_output_dir):
            os.mkdir(self.params_output_dir)
        self.all_spectra = None
        self.available_spexodisks_handles = set()
        self.available_spectrum_handles = set()
        self.spectrum_handles_to_spexodisks_handles = {}
        self.available_spexodisks_instruments = None
        self.inst_spectra_count = None
        self.max_char_count_for_summary = 0

        # for behavior in the write_sql() method
        self.default_spectrum = web_default_spectrum

        if self.verbose:
            print("  Loading Simbad reference data")
        self.simbad_lib = SimbadLib(go_fast=self.simbad_go_fast, verbose=self.verbose)
        self.simbad_main_ref = SimbadMainRef(ref_path=None, simbad_lib=self.simbad_lib)
        if self.verbose:
            print("  Loading Popular Names library")
        self.pop_names_lib = PopNamesLib(simbad_lib=self.simbad_lib)
        if self.verbose:
            print("  Loading Flux Calibration reference")
        self.flux_cal = FluxCal(simbad_lib=self.simbad_lib, auto_load=True)
        if self.verbose:
            print("  Loading Hitran spectral lines lists")
        self.hitran_ref = HitranRef(verbose=self.verbose)
        self.gaia_lib = None
        self.tic_query = None
        self.main_disk = None
        self.summary = None
        file_name = "AllParamsOutput.csv"
        self.output_file = os.path.join(self.params_output_dir, file_name)

        # used by the OutputObjectCollection subclass
        self.target_file = None
        self.targets_requested = None
        self.targets_found = None
        self.targets_not_found = None
        self.targets_found_at_least_one_spectrum = None
        self.targets_found_no_spectra = None

        # finishing up
        if self.verbose:
            print("SpExoDisk database initialized.")

    def get_stats(self):
        all_inst_str = ''
        all_inst_handle_and_names_str = ''
        totals = {'total_stars': len(self.available_spexodisks_handles),
                  'total_spectra': len(self.available_spectrum_handles)}
        instruments = {}
        for inst_handle, inst_name, inst_name_short, show_by_default in instrument_metadata:
            if inst_handle in self.available_spexodisks_instruments:
                all_inst_str += f'{inst_handle}|'
                all_inst_handle_and_names_str += f'{inst_handle}:{inst_name}|'

        for inst_handle in sorted(self.available_spexodisks_instruments):
            instruments[inst_handle] = handle_to_inst_dict[inst_handle] | {
                'spectra_count': self.inst_spectra_count[inst_handle]}
        return totals, instruments

    def __len__(self):
        return len(self.available_spexodisks_handles)

    def standard_output(self, upload_sql=False, write_plots=False):
        """
        An amalgamated tool for outputting ObjectCollection Data

        :param upload_sql:
        :param write_plots:
        :return:
        """
        if upload_sql:
            self.write_sql()
        if write_plots:
            self.plot_all()

    def standard_process(self, per_isotopologues_filter=None,
                         upload_sql=False, write_plots=False):
        self.import_spectra()
        self.update_params()
        self.get_flux_cals()
        self.get_hitran_lines(per_isotopologues_filter=per_isotopologues_filter)
        self.link_line_fluxes()
        self.do_stats()
        self.add_simbad_main_names()
        self.standard_output(upload_sql=upload_sql, write_plots=write_plots)

    def get_single_star(self, hypatia_name, not_found_exception=False):
        if isinstance(hypatia_name, str):
            test_handle = self.pop_names_lib.pop_name_to_handle(hypatia_name)
            if test_handle is None and test_handle in self.available_spexodisks_handles:
                return self.__getattribute__(test_handle)
            _object_name, hypatia_name = verify_starname(hypatia_name)
        spexodisks_handle, _star_names_dict = self.simbad_lib.get_star_dict(hypatia_name)
        if spexodisks_handle in self.available_spexodisks_handles:
            return self.__getattribute__(spexodisks_handle)
        elif not_found_exception:
            raise KeyError("Star name: " + str(hypatia_name) + ' not found.')
        return None

    def get_star_from_spectrum_handle(self, spectrum_handle):
        if spectrum_handle in self.available_spectrum_handles:
            spexodisks_handle = self.spectrum_handles_to_spexodisks_handles[spectrum_handle]
            return self.__getattribute__(spexodisks_handle)
        else:
            raise KeyError(f'spectrum_handle {spectrum_handle}  was not found.')

    def import_spectra(self):
        if self.verbose:
            print("\n Importing Spectra")
        self.all_spectra = AllSpectra(folders=None, simbad_go_fast=self.simbad_go_fast, verbose=self.verbose,
                                      spectra_output_dir=self.spectra_output_dir)
        if self.simbad_lib is None:
            self.simbad_lib = self.all_spectra.simbad_lib
        if self.verbose:
            print("  Importing Spectra and connecting to the database to register handles for new spectra")
        with LoadSQL(verbose=self.verbose) as load_qsl:
            for spec_set_handle in self.all_spectra.handle_list:
                spectral_set = self.all_spectra.__getattribute__(spec_set_handle)
                for object_handle in spectral_set.handle_list:
                    spectrum_object = spectral_set.__getattribute__(object_handle)
                    spexodisks_handle = spectrum_object.spexodisks_handle
                    if spexodisks_handle not in self.available_spexodisks_handles:
                        self.available_spexodisks_handles.add(spexodisks_handle)
                        self.__setattr__(spexodisks_handle, SingleObject(spexodisks_handle, self.pop_names_lib,
                                                                         verbose=self.verbose,
                                                                         spectra_output_dir=self.spectra_output_dir))
                    self.__getattribute__(spexodisks_handle).add_spectrum(output_sql=load_qsl,
                                                                          spectrum_object=spectrum_object)

        # do some database wide stats
        self.inst_spectra_count = {}
        for spexodisks_handle in self.available_spexodisks_handles:
            single_object = self.__getattribute__(spexodisks_handle)
            for spectrum_handle in single_object.available_spectral_handles:
                single_spectrum = single_object.__getattribute__(spectrum_handle)
                inst_name = single_spectrum.set_type
                if inst_name not in self.inst_spectra_count.keys():
                    self.inst_spectra_count[inst_name] = 0
                self.inst_spectra_count[inst_name] += 1
        self.available_spexodisks_instruments = set(self.inst_spectra_count.keys())
        if self.verbose:
            print(" Spectra Imported")

    def do_stats(self):
        # get some per-object stats
        for spexodisks_handle in self.available_spexodisks_handles:
            single_object = self.__getattribute__(spexodisks_handle)
            char_count = len(single_object.summary(all_instruments=self.available_spexodisks_instruments))
            self.max_char_count_for_summary = max(char_count, self.max_char_count_for_summary)
            self.available_spectrum_handles.update(single_object.available_spectral_handles)
            for spectrum_handle in single_object.available_spectral_handles:
                self.spectrum_handles_to_spexodisks_handles[spectrum_handle] = spexodisks_handle

    def add_simbad_main_names(self):
        with SimbadMainRef(ref_path=None, simbad_lib=self.simbad_lib) as simbad_main_ref:
            for spexodisks_handle in sorted(self.available_spexodisks_handles):
                single_object = self.__getattribute__(spexodisks_handle)
                main_record = simbad_main_ref.get_object(string_name=single_object.preferred_simbad_name,
                                                         object_handle=spexodisks_handle)
                single_object.add_simbad_main_record(main_record)

    def update_params(self, update_main_file=True, update_gaia=True, update_tic=True):
        if self.verbose:
            print("\n Updating per object parameters")
        if self.simbad_lib is None:
            self.simbad_lib = SimbadLib(verbose=self.verbose, go_fast=self.simbad_go_fast)
        if update_main_file:
            self.update_main_file()
        if update_gaia:
            self.update_gaia()
        if update_tic:
            self.update_tic()
        if self.verbose:
            print(" Object parameters updated")

    def update_main_file(self, file_names=None):
        if file_names is None:
            file_names = []
            for f in os.listdir(object_params_dir):
                test_file_name = os.path.join(object_params_dir, f)
                if os.path.isfile(test_file_name):
                    _prefix, extension = test_file_name.rsplit(".", 1)
                    if extension in {"psv", "csv"}:
                        file_names.append(test_file_name)
        for file_name in file_names:
            found_data = self.read(file_name)
            spexodisks_handles, _found_name_data, object_names_dicts, _spectral_data, object_data = found_data
            for spexodisks_handle in spexodisks_handles:
                params_this_object = object_data[spexodisks_handle]
                if spexodisks_handle not in self.available_spexodisks_handles:
                    object_names_dict = object_names_dicts[spexodisks_handle]
                    self.available_spexodisks_handles.add(spexodisks_handle)
                    self.__setattr__(spexodisks_handle, SingleObject(spexodisks_handle, self.pop_names_lib,
                                                                     verbose=self.verbose))
                    self.__getattribute__(spexodisks_handle).object_names_dict.update(object_names_dict)
                self.__getattribute__(spexodisks_handle).object_params.update(params_this_object)
            if self.verbose:
                print("Updated object parameters from user file:", file_name)

    def update_gaia(self):
        if self.gaia_lib is None:
            self.gaia_lib = GaiaLib(simbad_lib=self.simbad_lib, simbad_go_fast=self.simbad_go_fast,
                                    verbose=self.verbose)
        for spexodisks_handle in self.available_spexodisks_handles:
            single_object = self.__getattribute__(spexodisks_handle)
            object_names_dict = single_object.object_names_dict
            _spexodisks_handle, gaia_object_params = self.gaia_lib.get_object_params(object_names_dict)
            # spexodisks does not need the dist_parallax parameter, if will only add confusion with the 'dist'
            if "dist_parallax" in gaia_object_params.keys():
                if 'dist' not in gaia_object_params.keys():
                    gaia_object_params['dist'] = gaia_object_params["dist_parallax"]
                del gaia_object_params["dist_parallax"]
            # spexodisks only allows specific parameters to be updated.
            gaia_object_params_spexodisks = {}
            for key in gaia_object_params.keys():
                if key in params_check.allowed_params:
                    gaia_object_params_spexodisks[key] = gaia_object_params[key]
            # update the parameters
            self.__getattribute__(spexodisks_handle).object_params.update(gaia_object_params_spexodisks)
        if self.verbose:
            print("Updated object parameters from Gaia for all SpExoDisks objects.")

    def update_tic(self):
        if self.tic_query is None:
            self.tic_query = TicQuery(simbad_lib=self.simbad_lib, verbose=self.verbose)
        for spexodisks_handle in self.available_spexodisks_handles:
            single_object = self.__getattribute__(spexodisks_handle)
            object_names_dict = single_object.object_names_dict
            tic_object_params = self.tic_query.get_object_params(object_names_dict)
            if 'mass' in tic_object_params.keys():
                tic_object_params['m_star'] = tic_object_params['mass']
                del tic_object_params['mass']
            single_object.object_params.update(tic_object_params)
        if self.verbose:
            print("Updated object parameters from Tess Input Catalog for all SpExoDisks objects.")

    def get_flux_cals(self):
        for spexodisks_handle in self.available_spexodisks_handles:
            single_object = self.__getattribute__(spexodisks_handle)
            for spectrum_handle in single_object.available_spectral_handles:
                single_spectrum = single_object.__getattribute__(spectrum_handle)
                wl = single_spectrum.wavelength_um
                cals = self.flux_cal.get_relevant_calibrations(set_handle=single_spectrum.set_type,
                                                               spexodisks_handle=spexodisks_handle,
                                                               wave_length=wl[~np.isnan(wl)],
                                                               spectrum_base_handle=single_spectrum.base_handle)
                single_spectrum.__setattr__("flux_cals", cals)

    def get_hitran_lines(self, per_isotopologues_filter=None):
        if per_isotopologues_filter is None:
            hitran_object = self.hitran_ref
        else:
            line_set = set()
            for isotopologue in per_isotopologues_filter.keys():
                line_set.update(self.hitran_ref.ref_iso(isotopologue=isotopologue,
                                                        filter_dict=per_isotopologues_filter[isotopologue]).data)
            hitran_object = HitranRef(data=line_set)
        for spexodisks_handle in self.available_spexodisks_handles:
            single_object = self.__getattribute__(spexodisks_handle)
            for spectrum_handle in single_object.available_spectral_handles:
                single_spectrum = single_object.__getattribute__(spectrum_handle)
                hitran_lines = hitran_object.get_lines(max_wavelength_um=single_spectrum.max_wavelength_um,
                                                       min_wavelength_um=single_spectrum.min_wavelength_um)

                single_spectrum.__setattr__("hitran_lines", hitran_lines.ordered_data)

    def link_line_fluxes(self):
        for spexodisks_handle in self.available_spexodisks_handles:
            single_object = self.__getattribute__(spexodisks_handle)
            for spectrum_handle in single_object.available_spectral_handles:
                single_spectrum = single_object.__getattribute__(spectrum_handle)
                if single_spectrum.line_fluxes_paths is not None:
                    single_spectrum.line_fluxes = {}
                    for extra_science_product_path in single_spectrum.line_fluxes_paths:
                        line_flux_set = LineFluxes(extra_science_product_path=extra_science_product_path,
                                                   hitran_ref=self.hitran_ref)
                        single_spectrum.line_fluxes[extra_science_product_path] = line_flux_set

    def plot_all(self):
        for spexodisks_handle in self.available_spexodisks_handles:
            single_object = self.__getattribute__(spexodisks_handle)
            for spectrum_handle in single_object.available_spectral_handles:
                single_spectrum = single_object.__getattribute__(spectrum_handle)
                single_spectrum.plot()

    def add_param(self, hypatia_name, param_str, value, err=None, units=None, ref=None, notes=None):
        single_object = self.get_single_star(hypatia_name=hypatia_name, not_found_exception=True)
        single_object.add_param(param_str=param_str, value=value, err=err, units=units, ref=ref, notes=notes)

    def remove_param(self, hypatia_name, param_str, value, err=None, units=None, ref=None, notes=None):
        single_object = self.get_single_star(hypatia_name=hypatia_name, not_found_exception=True)
        single_object.remove_param(param_str=param_str, value=value, err=err, units=units, ref=ref, notes=notes)

    def assemble_output_data(self):
        output_stars_dict = {}
        object_params_for_header = {}
        params_found = set()
        for spexodisks_handle in self.available_spexodisks_handles:
            # initialize the output dictionary
            rows_required = 0
            output_stars_dict[spexodisks_handle] = StarDict()
            single_object = self.__getattribute__(spexodisks_handle)

            # get the object parameter data
            object_params_this_star = single_object.object_params
            # update the output dict with the stellar parameters
            output_stars_dict[spexodisks_handle].update(object_params_this_star)
            # This is a bunch of stuff needed to correctly write the header of the output file.
            object_param_names_this_star = object_params_this_star.keys()
            for param_name in object_param_names_this_star:
                # keeps a running list of all the parameters that wer found
                params_found.add(param_name)
                # Detect if this other data types related to the parameter's main value are available
                if param_name not in object_params_for_header.keys():
                    object_params_for_header[param_name] = {"err": False, 'units': False, 'ref': False, "notes": False}
                set_of_params = object_params_this_star[param_name]
                rows_required = max(rows_required, len(set_of_params))
                for _value, err, ref, units, notes in set_of_params:
                    if not object_params_for_header[param_name]['err'] and err is not None:
                        object_params_for_header[param_name]['err'] = True
                    if not object_params_for_header[param_name]['units'] and units is not None:
                        object_params_for_header[param_name]['units'] = True
                    if not object_params_for_header[param_name]['ref'] and ref is not None:
                        object_params_for_header[param_name]['ref'] = True
                    if not object_params_for_header[param_name]['notes'] and notes is not None:
                        object_params_for_header[param_name]['notes'] = True
            # get the data for spectra
            available_spectral_handles = single_object.available_spectral_handles
            rows_required = max(rows_required, len(available_spectral_handles))
            for spectra_handle in available_spectral_handles:
                single_spectrum = single_object.__getattribute__(spectra_handle)
                output_stars_dict[spexodisks_handle]['spectra'] = single_spectrum.make_spectrum_summary()

            # get the name data
            output_stars_dict[spexodisks_handle]["name"] = single_object.preferred_simbad_name
            # the standard name to go up front
            object_names_dict = single_object.object_names_dict
            # get a ton of other names to be helpful
            other_names_for_object = ""
            for star_name_type in sorted(object_names_dict.keys()):
                for star_id in object_names_dict[star_name_type]:
                    other_names_for_object += StringStarName((star_name_type, star_id)).string_name + "|"
            output_stars_dict[spexodisks_handle]["other_names"] = other_names_for_object[:-1]

            # how many rows will be needed for all the data available for this object?
            output_stars_dict[spexodisks_handle]['rows_required'] = rows_required
        # now we make a per parameter centric output
        output_params_dict = {}
        sorted_spex_handle_list = sorted(output_stars_dict.keys())
        for found_param in sorted(params_found):
            output_params_dict[found_param] = {}
            for spexodisks_handle in sorted_spex_handle_list:
                if found_param in output_stars_dict[spexodisks_handle].keys():
                    values_this_param_this_star = output_stars_dict[spexodisks_handle][found_param]
                    output_params_dict[found_param][spexodisks_handle] = values_this_param_this_star
        return output_stars_dict, object_params_for_header, output_params_dict

    def write_all_params(self, file_name=None):
        if file_name is None:
            file_name = self.output_file
        _, extension = file_name.rsplit(".")
        if extension.lower() == "psv":
            delimiter = "|"
            secondary_delimiter = ","
        else:
            delimiter = ","
            secondary_delimiter = "|"
        dirname = os.path.dirname(file_name)
        if not os.path.isdir(dirname):
            os.mkdir(dirname)
        output_dict, object_params_for_header, output_params_dict = self.assemble_output_data()
        primary_object_params = set(object_params_for_header.keys())
        header_key_list = ['pop_name', 'name']
        for param_name in sorted(primary_object_params):
            header_key_list.append(param_name)
            for attribute_type in ['err', "ref", 'units', "notes"]:
                if object_params_for_header[param_name][attribute_type]:
                    header_key_list.append(param_name + "_" + attribute_type)
        example_output_spectrum = SpectraSummary(file='')
        header_key_list.extend(["spectrum_" + output_spectra_type
                                for output_spectra_type in list(example_output_spectrum._fields)])
        header_key_list.append('other_names')
        header = ''
        for header_key in header_key_list:
            string_header_key = str(header_key)
            if delimiter in header_key:
                string_header_key.replace(delimiter, secondary_delimiter)
            header += string_header_key + delimiter
        header = header[:-1] + '\n'

        body = []
        for spexodisks_handle in sorted(self.available_spexodisks_handles):
            output_data_this_star = output_dict[spexodisks_handle]
            primary_params_this_object = set(output_data_this_star.keys())
            output_list_data = {param_name: list(output_data_this_star[param_name])
                                for param_name in primary_params_this_object}
            rows_required = np.max(output_list_data['rows_required'])
            for index in range(rows_required):
                row_dict = {"name": output_list_data["name"][0],
                            "pop_name": self.__getattribute__(spexodisks_handle).pop_name,
                            "other_names": output_list_data["other_names"][0]}
                for primary_object_param in primary_object_params & primary_params_this_object:
                    if index < len(output_list_data[primary_object_param]):
                        single_param = output_list_data[primary_object_param][index]
                        row_dict[primary_object_param] = single_param.value
                        for attribute_type in ['err', "ref", 'units', "notes"]:
                            attr_value = single_param.__getattribute__(attribute_type)
                            if attr_value is not None:
                                row_dict[primary_object_param + "_" + attribute_type] = attr_value
                if 'spectra' in primary_params_this_object:
                    if index < len(output_list_data['spectra']):
                        output_spectra = output_list_data['spectra'][index]
                        for output_spectra_type in list(example_output_spectrum._fields):
                            attr_value = output_spectra.__getattribute__(output_spectra_type)
                            if attr_value is not None:
                                row_dict["spectrum_" + output_spectra_type] = attr_value
                string_row = ""
                header_keys_this_dict = set(row_dict.keys())
                for header_key in header_key_list:
                    if header_key in header_keys_this_dict:
                        string_value = str(row_dict[header_key])
                        if delimiter in string_value:
                            string_value = string_value.replace(delimiter, secondary_delimiter)
                        string_row += string_value + delimiter
                    else:
                        string_row += delimiter
                body.append(string_row[:-1] + "\n")
        # write open the file for writing and write all the data
        with open(file_name, 'w') as f:
            f.write(header)
            for row in body:
                f.write(row)
        if self.verbose:
            print("\n Output SpExoDisks all-parameters file written to:", file_name, "\n")

    def write_spectral_output(self, write_txt=True, write_fits=True):
        if not write_txt and not write_fits:
            output_types = 'None selected'
        else:
            output_types = ' '
            if write_txt:
                output_types += 'txt '
            if write_fits:
                output_types += 'fits '
        if self.verbose:
            print(f"\nWriting spectral output ({output_types}) files for {len(self)} stars...")
        for spexodisks_handle in sorted(self.available_spexodisks_handles):
            single_object = self.__getattribute__(spexodisks_handle)
            for spectrum_handle in sorted(single_object.available_spectral_handles):
                single_spectrum = single_object.__getattribute__(spectrum_handle)
                if write_txt:
                    single_spectrum.write_txt(single_object=single_object, spectrum_handle=spectrum_handle)
                if write_fits:
                    single_spectrum.write_fits(single_object=single_object, spectrum_handle=spectrum_handle)
        if self.verbose:
            print("  Spectral output files written.")

    def write_individual_params(self, params_to_write=None):
        output_dict, object_params_for_header, output_params_dict = self.assemble_output_data()
        if params_to_write is None:
            params_to_write = sorted(output_params_dict.keys())
        else:
            params_to_write = sorted(set(params_to_write) | set(output_params_dict.keys()))

        for param in params_to_write:
            # these values are reset for every parameter
            filename = f'{param}.csv'
            stars_this_param = output_params_dict[param]
            # Determine the number of columns needed to represent this parameter across all stars
            parameter_columns_needed = 0
            secondary_parameter_data_types_needed = set()
            for spexodisks_handle in stars_this_param.keys():
                single_params_this_star = stars_this_param[spexodisks_handle]
                parameter_columns_needed = max((parameter_columns_needed, len(single_params_this_star)))
                # Detect if this other data types related to the parameter's main value are available
                for single_param in single_params_this_star:
                    value, err, ref, units, notes = single_param
                    ref_is_none_flag = False
                    if err is not None:
                        secondary_parameter_data_types_needed.add('err')
                    if units is not None:
                        secondary_parameter_data_types_needed.add('units')
                    if ref is None:
                        ref_is_none_flag = True
                    else:
                        secondary_parameter_data_types_needed.add('ref')
                    if notes is not None:
                        secondary_parameter_data_types_needed.add('notes')
                    if ref_is_none_flag:
                        # we need to make the ref an empty string for a comparison from a sorting function later on
                        new_single_param = SingleParam(value, err, '', units, notes)
                        single_params_this_star.remove(single_param)
                        single_params_this_star.add(new_single_param)

            # make and ordered list of the secondary data types that relate to each parameters primary value
            secondary_types = [secondary_type for secondary_type in ['err', 'units', 'ref', 'notes']
                               if secondary_type in secondary_parameter_data_types_needed]
            # write the header for this output file
            header = 'pop_name,simbad'
            for param_count in range(1, parameter_columns_needed + 1):
                base_param_name = f'{param}{param_count}'
                header += f',{base_param_name}'
                for secondary_type in secondary_types:
                    header += f',{base_param_name}_{secondary_type}'
            # now that we know the shape of the file we can start writing
            full_file_path = os.path.join(self.params_output_dir, filename)
            with open(full_file_path, 'w') as f:
                f.write(f'{header}\n')
                for spexodisks_handle in stars_this_param.keys():
                    single_params_this_star = stars_this_param[spexodisks_handle]
                    # sort the parameters in order of reference
                    sorted_single_params = sorted(single_params_this_star, key=attrgetter('ref'))
                    simbad_name = handle_to_simbad(spexodisks_handle)
                    pop_name = self.pop_names_lib.get_or_generate(spexodisks_handle=spexodisks_handle)
                    write_line = f'{pop_name},{simbad_name}'
                    for param_count, single_param in zip_longest(range(1, parameter_columns_needed + 1),
                                                                 sorted_single_params):
                        if single_param is None:
                            # this is the case where there are more parameter columns then paramaters for this star
                            write_line += ','
                            for secondary_type in secondary_types:
                                write_line += ','
                        else:
                            # there is available parameter data to put in this column
                            write_line += f",{str(single_param.value).replace(',', '|')}"
                            for secondary_type in secondary_types:
                                secondary_type_value = str(single_param.__getattribute__(secondary_type)).replace(',',
                                                                                                                  '|')
                                if secondary_type_value is None:
                                    write_line += ','
                                else:
                                    write_line += f',{secondary_type_value}'
                    f.write(f'{write_line}\n')
            if self.verbose:
                print(f"  Output SpExoDisks per-parameter data for {param} file written to: {full_file_path}")
        if self.verbose:
            print(f"All per-parameter data written\n")

    def read(self, file_name):
        _, extension = file_name.rsplit(".", 1)
        if extension.lower() == "psv":
            delimiter = "|"
            secondary_delimiter = ","
        else:
            delimiter = ","
            secondary_delimiter = "|"
        if self.simbad_lib is None:
            self.simbad_lib = SimbadLib(go_fast=self.simbad_go_fast, verbose=self.verbose)
        # Read the data from file
        rows_of_data = []
        if os.path.exists(file_name):
            with open(file_name, 'r') as f:
                rows_of_data = f.readlines()
        # Do a first pass to organize and format the data into int, floats, strings
        single_param_keys = list(SingleParam._fields)
        if rows_of_data:
            # check for a flag that indicates an alternative file format that uses standard units and has
            # a single reference per file.
            if rows_of_data[0].strip()[0] == "%":
                file_reference = rows_of_data[0].replace("%", "").strip().split(delimiter)[0]
                rows_of_data = rows_of_data[1:]
            else:
                file_reference = None
            # the first line of rows_of_data is expected to be the header
            header_keys = [header_key.strip().lower() for header_key in rows_of_data[0].strip().split(delimiter)]
            row_dicts = []
            for row_string in rows_of_data[1:]:
                row_dict = {}
                row_string_values = [value_string.strip() for value_string in row_string.strip().split(delimiter)]
                for column_index, header_key in list(enumerate(header_keys)):
                    value_string = row_string_values[column_index]
                    if value_string != "":
                        row_dict[header_key] = num_format(value_string)
                if row_dict != {}:
                    row_dicts.append(row_dict)
            # Split the data into different classes, add data to the correct data container for each class
            found_name_data = {}
            internal_name_data = {}
            spectral_data = {}
            object_data = {}
            spexodisks_handles = set()
            for row_dict in row_dicts:
                row_dict_keys = set(row_dict.keys())
                _string_name, hypatia_name = verify_starname(row_dict['name'])
                if "pop_name" in row_dict.keys():
                    del row_dict["pop_name"]
                    row_dict_keys.remove("pop_name")
                spexodisks_handle, star_names_dict = self.simbad_lib.get_star_dict(hypatia_name)
                if spexodisks_handle not in spexodisks_handles:
                    spexodisks_handles.add(spexodisks_handle)
                    found_name_data[spexodisks_handle] = StarDict()
                    internal_name_data[spexodisks_handle] = star_names_dict
                    spectral_data[spexodisks_handle] = set()
                    object_data[spexodisks_handle] = UnitsObjectParams()
                # star name data
                if "other_names" in row_dict_keys:
                    string_star_names = [value_string
                                         for value_string in row_dict["other_names"].strip().split(delimiter)]
                    hypatia_names = {star_name_format(string_name) for string_name in string_star_names}
                    for star_name_type, star_id in hypatia_names:
                        found_name_data[spexodisks_handle][star_name_type] = star_id
                # spectral data
                spectrum_dict = {}
                spectrum_header_keys = {header_key for header_key in header_keys if "spectrum_" in header_key}
                for spectrum_header_key in spectrum_header_keys & row_dict_keys:
                    spectrum_key = spectrum_header_key.replace("spectrum_", "")
                    spectrum_dict[spectrum_key] = row_dict[spectrum_header_key]
                if spectrum_dict != {}:
                    spectral_data[spexodisks_handle].add(set_single_output_spectra(spectrum_dict))
                # object parameters
                row_params_dict = {}
                params_this_row = set()
                for object_header_key in row_dict_keys - ({"other_names", "name"} | spectrum_header_keys):
                    for single_param_data_type in single_param_keys:
                        if single_param_data_type in object_header_key:
                            data_type = single_param_data_type
                            object_key = object_header_key.replace("_" + single_param_data_type, "")
                            break
                    else:
                        data_type = "value"
                        object_key = object_header_key
                    if object_key not in params_this_row:
                        params_this_row.add(object_key)
                        row_params_dict[object_key] = {}
                    row_params_dict[object_key][data_type] = row_dict[object_header_key]
                for param_type in row_params_dict.keys():
                    param_dict = row_params_dict[param_type]
                    if param_dict != {}:
                        if 'err' in param_dict.keys() and isinstance(param_dict['err'], str) \
                                and "(" in param_dict['err']:
                            err_tuple = param_dict['err'].replace("(", "").replace(")", "")
                            param_dict['err'] = tuple([num_format(num_str) for num_str in
                                                       err_tuple.split(secondary_delimiter)])
                        if file_reference is not None:
                            param_dict['ref'] = file_reference
                            if param_type in params_check.expected_units.keys():
                                param_dict['units'] = params_check.expected_units[param_type]
                        object_data[spexodisks_handle][param_type] = set_single_param(param_dict)
            return spexodisks_handles, found_name_data, internal_name_data, spectral_data, object_data
        return None

    def write_metadata(self, upload_all_params: bool = False):
        max_star_name_size = 0
        references_per_parameter = {}
        star_params = {}
        star_params_curated = {}
        if self.verbose:
            print("\nWriting SpExoDisks Data to MySQL Server")
        with LoadSQL(auto_connect=True, verbose=self.verbose) as load_sql:
            # faster upload of data to MySQL server, only implemented for spectral data
            uploader = UploadSQL()
            # create the statistics tables
            load_sql.create_stats_total_table(database=spexo_schema)
            load_sql.create_stats_inst_table(database=spexo_schema)
            # create the stellar names and parameters tables
            load_sql.creat_table(table_name='object_name_aliases', database=spexo_schema)
            if upload_all_params:
                load_sql.creat_table(table_name="object_params_float", database=spexo_schema)
                load_sql.creat_table(table_name="object_params_str", database=spexo_schema)
            # create the per spectra data tables
            load_sql.creat_table(table_name="flux_calibration", database=spexo_schema)
            load_sql.creat_table(table_name="line_fluxes_co", database=spexo_schema)
            load_sql.creat_table(table_name="spectra", database=spexo_schema)
            load_sql.creat_table(table_name="stacked_line_spectra", database=spexo_schema)

            # stellar params and units table
            load_sql.create_units_table(database=spexo_schema)
            known_string_param = []
            known_float_params = []
            for param in params_check.params_order:
                param_dict = params_check.params_data[param]
                param_dict['param_handle'] = param
                if param_dict['units'] == 'string':
                    known_string_param.append(param)
                else:
                    known_float_params.append(param)
                load_sql.insert_into_table(table_name='available_params_and_units',
                                             data=param_dict, database=spexo_schema)
            # load a default spectrum and spectrum info for an initial display on the website's ExploreData page
            default_object = self.get_star_from_spectrum_handle(self.default_spectrum)
            default_spectrum = default_object.__getattribute__(self.default_spectrum)
            uploader.upload_spectra(table_name='default_spectrum',
                                    wavelength_um=default_spectrum.wavelength_um,
                                    flux=default_spectrum.flux,
                                    flux_error=default_spectrum.flux_error,
                                    bandwidth_fraction_for_null=bandwidth_fraction_for_null,
                                    schema=spexo_schema)
            load_sql.creat_table(table_name='default_spectrum_info', database=spexo_schema)
            spectrum_data = spectrum_data_for_sql(single_spectrum=default_spectrum)
            load_sql.insert_into_table(table_name='default_spectrum_info', data=spectrum_data, database=spexo_schema)

            # add a single entry for the overall database stats table
            totals, instruments = self.get_stats()
            load_sql.insert_into_table(table_name='stats_total', database=spexo_schema,
                                         data=totals)
            # add one entry to an instrument stats (stats_instrument) table for each instrument found
            inst_handles_in_order = []
            for inst_handle, inst_name, inst_name_short, show_by_default in instrument_metadata:
                if inst_handle in self.available_spexodisks_instruments:
                    inst_handles_in_order.append(inst_handle)
            for inst_handle in inst_handles_in_order:
                load_sql.insert_into_table(table_name='stats_instrument', database=spexo_schema,
                                             data=instruments[inst_handle])

            # put data in the MySQL tables, per-star and per-spectra data
            # # object_params_float, object_params_str
            if upload_all_params:
                load_sql.buffer_insert_init(table_name="object_params_str",
                                              columns=["spexodisks_handle", "str_param_type", "str_value",
                                                       "str_error", 'str_ref', 'str_units', 'str_notes'],
                                              database=spexo_schema, run_silent=True, buffer_num=1)
                load_sql.buffer_insert_init(table_name="object_params_float",
                                              columns=["spexodisks_handle", "float_param_type", "float_value",
                                                       "float_error_low", 'float_error_high', 'float_ref',
                                                       'float_units', 'float_notes'],
                                              database=spexo_schema, run_silent=True, buffer_num=2)
            print_faction = int(np.round(len(self.available_spexodisks_handles) / 100))
            percent_divider = len(self.available_spexodisks_handles) / 100.0
            for star_count, spexodisks_handle in list(enumerate(self.available_spexodisks_handles)):
                if self.verbose and star_count % print_faction == 0:
                    raw_percentage = star_count / percent_divider
                    print(f"    {('%05.2f' % raw_percentage)}%" +
                          f" of SQL table data written for per-star and per-spectra metadata at {datetime.now()}")
                single_object = self.__getattribute__(spexodisks_handle)
                # The object_name_aliases table
                max_star_name_size = max(max_star_name_size, len(spexodisks_handle))
                object_names_dict = single_object.object_names_dict
                for name_type in object_names_dict.keys():
                    id_set = object_names_dict[name_type]
                    for id in list(id_set):
                        simbad_name = StringStarName((name_type, id)).string_name
                        max_star_name_size = max(max_star_name_size, len(simbad_name))
                        load_sql.insert_into_table(table_name='object_name_aliases', database=spexo_schema,
                                                     data={"alias": simbad_name,
                                                           "spexodisks_handle": spexodisks_handle})
                object_params = single_object.object_params
                for param_type in object_params.keys():
                    star_param_id = (spexodisks_handle, param_type)
                    if star_param_id not in star_params.keys():
                        star_params[star_param_id] = object_params[param_type]
                    if param_type not in references_per_parameter.keys():
                        references_per_parameter[param_type] = set()
                    for single_param in list(object_params[param_type]):
                        value, err, ref, units, notes = single_param.value, single_param.err, single_param.ref, \
                            single_param.units, single_param.notes
                        # truncate the value to the correct number of decimals specified in the units.csv files
                        value = params_check.value_format(param_type, value)
                        err = params_check.err_format(param_type, err)
                        data = {"param_type": param_type,
                                "value": value}
                        if err is not None:
                            data["error"] = err
                        if ref is not None:
                            data['ref'] = ref
                            references_per_parameter[param_type].add(ref)
                            if param_type in rank_per_column.keys():
                                ref_rank = rank_ref(param=param_type, ref=ref)
                            else:
                                ref_rank = -1.0
                        else:
                            ref_rank = float('-inf')
                        if units is not None:
                            data['units'] = units
                        if notes is not None:
                            data['notes'] = notes
                        if isinstance(value, str):
                            str_data = {"str_" + key: data[key] for key in data.keys()}
                            str_data["spexodisks_handle"] = spexodisks_handle
                            if upload_all_params:
                                load_sql.buffer_insert_value(values=[spexodisks_handle, param_type, value,
                                                                       err, ref, units, notes], buffer_num=1)
                            output_data = {key.replace('str_', ''): str_data[key] for key in str_data.keys()}
                        elif isinstance(value, float):
                            if isinstance(err, tuple):
                                del data['error']
                                error_low, error_high = err
                            elif isinstance(err, float):
                                del data['error']
                                error_high = err
                                error_low = err * -1.0
                            else:
                                error_high = error_low = None

                            data["error_low"], data["error_high"] = error_low, error_high
                            float_data = {"float_" + key: data[key] for key in data.keys()}
                            float_data["spexodisks_handle"] = spexodisks_handle
                            if upload_all_params:
                                load_sql.buffer_insert_value(values=[spexodisks_handle, param_type, value,
                                                                       error_low, error_high, ref, units, notes],
                                                               buffer_num=2)
                            output_data = {key.replace('float_', ''): float_data[key] for key in float_data.keys()}
                        else:
                            raise TypeError
                        if star_param_id in star_params_curated.keys():
                            previous_ref_rank, previous_output_data = star_params_curated[star_param_id]
                            if ref_rank > previous_ref_rank:
                                star_params_curated[star_param_id] = (ref_rank, output_data)
                        else:
                            star_params_curated[star_param_id] = (ref_rank, output_data)
                # per-spectra data tables
                for spectrum_handle in single_object.available_spectral_handles:
                    # Spectrum table
                    single_spectrum = single_object.__getattribute__(spectrum_handle)
                    spectrum_data = spectrum_data_for_sql(single_spectrum=single_spectrum)
                    load_sql.insert_into_table(table_name="spectra", database=spexo_schema, data=spectrum_data)
                    # Flux Calibration
                    if single_spectrum.flux_cals is not None:
                        for flux_cal in single_spectrum.flux_cals:
                            flux_cal_data = {"spectrum_handle": spectrum_handle.lower(),
                                             "flux_cal": flux_cal.flux,
                                             "wavelength_um": flux_cal.um}
                            if flux_cal.ref is not None:
                                flux_cal_data["ref"] = flux_cal.ref
                            if flux_cal.err is not None:
                                flux_cal_data["flux_cal_error"] = flux_cal.err
                            load_sql.insert_into_table(table_name="flux_calibration", database=spexo_schema,
                                                         data=flux_cal_data)
                    # Line Fluxes CO
                    if single_spectrum.line_fluxes is not None:
                        for extra_science_product_path in single_spectrum.line_fluxes.keys():
                            isotopologue, transition, _path = extra_science_product_path
                            flux_data = single_spectrum.line_fluxes[extra_science_product_path].flux_data
                            for flux, flux_error, match_wavelength, hitran_line in flux_data:
                                single_measured_flux_data = {"flux": flux,
                                                             "flux_error": flux_error,
                                                             "match_wavelength_um": match_wavelength,
                                                             "wavelength_um": hitran_line.wavelength_um,
                                                             "spectrum_handle": spectrum_handle.lower(),
                                                             "isotopologue": isotopologue.lower(),
                                                             "upper_level": str(hitran_line.upper_level),
                                                             "lower_level": str(hitran_line.lower_level),
                                                             "transition": hitran_line.transition,
                                                             "einstein_A": hitran_line.einstein_A,
                                                             "upper_level_energy": hitran_line.upper_level_energy,
                                                             "lower_level_energy": hitran_line.lower_level_energy,
                                                             "g_statistical_weight_upper_level": hitran_line.g_statistical_weight_upper_level,
                                                             "g_statistical_weight_lower_level": hitran_line.g_statistical_weight_lower_level,
                                                             "upper_vibrational": hitran_line.upper_level.vibrational,
                                                             "upper_rotational": hitran_line.upper_level.rotational,
                                                             "branch": hitran_line.upper_level.branch,
                                                             "lower_vibrational": hitran_line.lower_level.vibrational,
                                                             "lower_rotational": hitran_line.lower_level.rotational}
                                load_sql.insert_into_table(table_name="line_fluxes_co", database=spexo_schema,
                                                             data=single_measured_flux_data)
                    # Stacked Line Spectra
                    if single_spectrum.stacked_lines is not None:
                        for extra_science_product_path in single_spectrum.stacked_lines.keys():
                            isotopologue, transition, _path = extra_science_product_path
                            stack_line_handle = get_stacked_line_handle(isotopologue=isotopologue,
                                                                        transition=transition,
                                                                        spectrum_handle=spectrum_handle)
                            stacked_line_id_data = {"stack_line_handle": stack_line_handle,
                                                    "spectrum_handle": spectrum_handle.lower(),
                                                    "spexodisks_handle": spexodisks_handle,
                                                    "transition": transition,
                                                    "isotopologue": isotopologue,
                                                    "molecule": isotopologue_to_molecule[isotopologue]}
                            load_sql.insert_into_table(table_name="stacked_line_spectra", data=stacked_line_id_data,
                                                         database=spexo_schema)
            else:
                # below is last thing the loop does if no 'break' statement is encountered.
                if upload_all_params:
                    load_sql.buffer_insert_execute(run_silent=True, buffer_num=1)
                    load_sql.buffer_insert_execute(run_silent=True, buffer_num=2)
                if self.verbose:
                    print(" Completed writing SQL tables for per-star and per-spectra metadata")
            # Make the curated table and other tables that recast the data to per star and per spectrum data
            if upload_all_params:
                load_sql.params_tables(database=spexo_schema)
                # make the curated table of data
                str_params = sorted([item[0] for item in
                                     load_sql.query(
                                         sql_query_str=F"SELECT str_params "
                                                       F"FROM {spexo_schema}.available_str_params")])

                float_params = sorted([item[0] for item in
                                       load_sql.query(
                                           sql_query_str=F"SELECT float_params "
                                                         F"FROM {spexo_schema}.available_float_params")])
            else:
                float_params = known_float_params
                str_params = known_string_param
            all_column_names = load_sql.create_curated_table(float_params=float_params, str_params=str_params,
                                                               database=spexo_schema)
            # Curated data: rearrange the data to be by star, then by parameter
            star_params_curated_by_star = {}
            for this_handle, this_column in star_params_curated.keys():
                this_param_data = star_params_curated[(this_handle, this_column)]
                if this_handle not in star_params_curated_by_star.keys():
                    star_params_curated_by_star[this_handle] = {}
                star_params_curated_by_star[this_handle][this_column] = this_param_data
            # the stars table (which uses the curated table)
            print_faction = int(np.round(len(self.available_spexodisks_handles) / 30.0))
            percent_divider = len(self.available_spexodisks_handles) / 100.0
            # loop over the data and write a record for each spexodisks_handle
            for star_count, spexodisks_handle in list(enumerate(self.available_spexodisks_handles)):
                if self.verbose:
                    if star_count % print_faction == 0:
                        raw_percentage = star_count / percent_divider
                        print(F"    {('%05.2f' % raw_percentage)}%" +
                              " of SQL table data written for the 'curated' table")
                single_object = self.__getattribute__(spexodisks_handle)
                if single_object.available_spectral_handles:
                    has_spectra = 1
                else:
                    has_spectra = 0

                if spexodisks_handle in star_params_curated_by_star.keys():
                    params_data = star_params_curated_by_star[spexodisks_handle]
                else:
                    params_data = {}

                # The 'curated' table, the primary table of SpExoDisks per-star data
                if single_object.main_simbad_name is None:
                    website_simbad_name = single_object.preferred_simbad_name
                else:
                    website_simbad_name = single_object.main_simbad_name
                # the esa sky website
                if 'ra_epochj2000' in params_data.keys() and 'dec_epochj2000' in params_data.keys():
                    # make and esa sky link
                    ra_target_location_deg = params_data['ra_epochj2000'][1]['value']
                    dec_target_location_deg = params_data['dec_epochj2000'][1]['value']
                    ra, dec, esa_sky, ra_dec_str_for_web \
                        = set_website_values(ra_epoch_j2000_deg=ra_target_location_deg,
                                             dec_epoch_j2000_deg=dec_target_location_deg)
                else:
                    main_simbad_record = self.__getattribute__(spexodisks_handle).main_simbad_record
                    if main_simbad_record is None:
                        esa_sky = None
                        ra_dec_str_for_web = None
                        ra = None
                        dec = None
                    else:
                        ra_string = main_simbad_record["RA"]
                        dec_string = main_simbad_record["DEC"]
                        ra_deg, dec_deg, hmsdms = simbad_coord_to_deg(ra_string=ra_string, dec_string=dec_string)
                        ra, dec, esa_sky, ra_dec_str_for_web \
                            = set_website_values(ra_epoch_j2000_deg=ra_deg,
                                                 dec_epoch_j2000_deg=dec_deg)
                        params_data['ra_epochj2000'] = (1, dict(value=ra_deg, units='deg', ref=simbad_reference))
                        params_data['dec_epochj2000'] = (1, dict(value=dec_deg, units='deg', ref=simbad_reference))

                single_object = self.__getattribute__(spexodisks_handle)

                curated_record = {'spexodisks_handle': spexodisks_handle, 'pop_name': single_object.pop_name,
                                  'preferred_simbad_name': website_simbad_name,
                                  "simbad_link": single_object.simbad_link,
                                  'ra_dec': ra_dec_str_for_web,
                                  'ra': ra,
                                  'dec': dec,
                                  "esa_sky": esa_sky,
                                  'has_spectra': has_spectra}
                # loop over all the parameters found for this star and add to the curated record.
                for column_name in sorted(params_data.keys()):
                    _ref_rank, output_data = params_data[column_name]
                    curated_record[F"{column_name}_value"] = output_data['value']
                    if 'error_high' in output_data.keys():
                        curated_record[F"{column_name}_err_high"] = output_data['error_high']
                    if 'error_low' in output_data.keys():
                        curated_record[F"{column_name}_err_low"] = output_data['error_low']
                    if 'ref' in output_data.keys():
                        curated_record[F"{column_name}_ref"] = output_data['ref']
                # export the curated data to the MySQL server table.
                load_sql.insert_into_table(table_name='curated', database=spexo_schema, data=curated_record)

        # Finishing up (outside the 'with' statement)
        if self.verbose:
            print("Data output written to MySQL server.\n")
        # write the parameters to files
        self.write_all_params()
        self.write_individual_params()
        # output a file to see what references are used by what parameters.
        with open(references_per_parameter_path, 'w') as f:
            for column_name in sorted(references_per_parameter.keys()):
                ref_values = ''
                for ref in sorted(references_per_parameter[column_name], reverse=True):
                    ref_values += F"{ref}|"
                f.write(F"{column_name}:{ref_values[:-1]}\n")

    def write_spectra(self,  do_sync: bool = True):
        with LoadSQL(auto_connect=True, verbose=self.verbose) as load_sql:
            if self.update_mode and load_sql.check_if_table_exists(table_name="spectra", database='spexodisks'):
                handles_to_skip = {row[0] for row in load_sql.query(
                    sql_query_str="""SELECT spectrum_handle FROM spexodisks.spectra""")}
            else:
                handles_to_skip = set()
            # faster upload of data to MySQL server, only implemented for spectral data
            uploader = UploadSQL()
            percent_divider = len(self.available_spectrum_handles) / 100.0
            spectrum_count = 0
            for spexodisks_handle in sorted(self.available_spexodisks_handles):
                single_star = self.__getattribute__(spexodisks_handle)
                star_dir_to_sync = get_spectrum_output_dir(spectra_output_dir=self.spectra_output_dir,
                                                           object_pop_name=single_star.pop_name)
                if not os.path.exists(star_dir_to_sync):
                    os.mkdir(star_dir_to_sync)
                needs_update = False
                for spectrum_handle in sorted(single_star.available_spectral_handles):
                    if spectrum_handle.lower() in handles_to_skip:
                        if self.verbose:
                            print(F"Skipping {spectrum_handle} as it already exists in the database.")
                        continue
                    if self.verbose:
                        raw_percentage = spectrum_count / percent_divider
                        print(f"    {('%05.2f' % raw_percentage)}%" +
                              f" data uploaded for spectra at {datetime.now()}, next spectra: {spectrum_handle}")
                    single_spectrum = single_star.__getattribute__(spectrum_handle)
                    # The Primary Spectrum
                    uploader.upload_spectra(table_name=spectrum_handle.lower(),
                                            wavelength_um=single_spectrum.wavelength_um,
                                            flux=single_spectrum.flux,
                                            flux_error=single_spectrum.flux_error,
                                            bandwidth_fraction_for_null=bandwidth_fraction_for_null,
                                            schema=spectra_schema)
                    single_spectrum.write_txt(single_object=single_star, spectrum_handle=spectrum_handle)
                    single_spectrum.write_fits(single_object=single_star, spectrum_handle=spectrum_handle)
                    # Stacked Line Spectra
                    if single_spectrum.stacked_lines is not None:
                        for extra_science_product_path in single_spectrum.stacked_lines.keys():
                            isotopologue, transition, _path = extra_science_product_path
                            stack_line_handle = get_stacked_line_handle(isotopologue=isotopologue, transition=transition,
                                                                        spectrum_handle=spectrum_handle)
                            stack_line_spectrum = single_spectrum.stacked_lines[extra_science_product_path].spectrum
                            load_sql.creat_table(table_name=stack_line_handle, database=stacked_line_schema,
                                                 dynamic_type="stacked_spectrum", run_silent=True)
                            load_sql.buffer_insert_init(table_name=stack_line_handle,
                                                        columns=["velocity_kmps", "flux", "flux_error"],
                                                        database=stacked_line_schema,
                                                        run_silent=True)
                            for velocity_kmps, flux, flux_error in zip(stack_line_spectrum.velocity_kmps,
                                                                       stack_line_spectrum.flux,
                                                                       stack_line_spectrum.flux_error):
                                single_row_values = [velocity_kmps]
                                if is_good_num(flux):
                                    single_row_values.append(flux)
                                else:
                                    single_row_values.append(None)
                                if is_good_num(flux_error):
                                    single_row_values.append(flux_error)
                                else:
                                    single_row_values.append(None)
                                load_sql.buffer_insert_value(values=single_row_values)
                    # end of the spectrum loop
                    spectrum_count += 1
                    needs_update = True
                # per star data this syncs the whole star's spectra directory
                if do_sync and needs_update:
                    rsync_output(dir_or_file=star_dir_to_sync, verbose=self.verbose)
        if self.verbose:
            print(" Completed writing SQL tables for spectra")

    def write_hitran(self):
        values_CO = []
        values_H2O = []
        values_OH = []
        values_isos = {}
        one_tenth = int(np.round(len(self.hitran_ref.data) / 10.0))
        percent_divider = len(self.hitran_ref.data) / 100.0
        with LoadSQL(auto_connect=True, verbose=self.verbose) as load_sql:
            if self.update_mode and load_sql.check_if_table_exists(table_name="available_isotopologues", database='spexodisks'):
                handles_to_skip = {row[0] for row in load_sql.query(
                    sql_query_str="""SELECT name FROM spexodisks.available_isotopologues""")}
            else:
                handles_to_skip = set()
            for line_count, hitran_line in list(enumerate(self.hitran_ref.data)):
                if self.verbose:
                    if line_count % one_tenth == 0:
                        raw_percentage = line_count / percent_divider
                        print(F"    {'%05.2f' % raw_percentage}%" +
                              " of data sorted for Hitran molecular data")
                hl_data = make_hl_dict(hitran_line=hitran_line)
                if hitran_line.molecule == 'CO':
                    values_CO.append(hl_data)
                elif hitran_line.molecule == 'H2O':
                    values_H2O.append(hl_data)
                elif hitran_line.molecule == 'OH':
                    values_OH.append(hl_data)
            # sort data to isotopologue data tables.
            for isotopologue in self.hitran_ref.ref_dic_isotopologue.keys():
                isotopologue_hitran = self.hitran_ref.ref_dic_isotopologue[isotopologue]
                if isotopologue not in values_isos.keys():
                    values_isos[isotopologue] = [make_hl_dict(hitran_line=hitran_line)
                                                 for hitran_line in isotopologue_hitran.ordered_data]

            # the isotopologue tables
            load_sql.creat_table(table_name='available_isotopologues', database=spexo_schema, drop_if_exists=True)
            for isotopologue in values_isos.keys():
                molecule = isotopologue_to_molecule[isotopologue].lower()
                if molecule == 'h2o':
                    columns = columns_H2O
                elif molecule == 'co':
                    columns = columns_CO
                elif molecule == 'oh':
                    columns = columns_OH
                else:
                    raise KeyError(f"The SpExoDisks database does have the molecule {molecule}, " +
                                   f"for MySQL isotopologue tables.")
                # make and insert isotopologue summary data
                isotopologue_ordered_data = self.hitran_ref.ref_dic_isotopologue[isotopologue].ordered_data
                min_wavelength_um = isotopologue_ordered_data[0].wavelength_um
                max_wavelength_um = isotopologue_ordered_data[-1].wavelength_um
                isotopologue_summary_data = {'name': isotopologue.lower(),
                                             'label': f'{isotopologue_to_label[isotopologue]}',
                                             'molecule': molecule,
                                             'mol_label': f'{molecule_to_label[molecule.upper()]}',
                                             'color': isotopologue_to_color[isotopologue],
                                             'dash': plotly_dash_value[isotopologue],
                                             'min_wavelength_um': min_wavelength_um,
                                             'max_wavelength_um': max_wavelength_um,
                                             'total_lines': len(isotopologue_ordered_data)}
                load_sql.insert_into_table(table_name='available_isotopologues', data=isotopologue_summary_data,
                                           database=spexo_schema)
                if isotopologue.lower() in handles_to_skip:
                    if self.verbose:
                        print(F"Skipping {isotopologue} as it already exists in the database.")
                    continue
                # insert the per isotopologue Hitran line data
                table_name = f'isotopologue_{isotopologue.lower()}'
                load_sql.creat_table(table_name=table_name, database=spexo_schema, dynamic_type=molecule)
                load_sql.buffer_insert_init(table_name=table_name, columns=columns,
                                            database=spexo_schema, run_silent=False)
                values_hitran = values_isos[isotopologue]
                fraction = int(np.round(len(values_hitran) / 30.0))
                percent_divider = len(values_hitran) / 100.0
                for line_count, single_line_values_dict in list(enumerate(values_hitran)):
                    if line_count % fraction == 1:
                        load_sql.buffer_insert_execute(run_silent=True)
                        load_sql.buffer_insert_init(table_name=table_name, columns=columns,
                                                    database=spexo_schema, run_silent=True)
                        raw_percentage = line_count / percent_divider
                        print(F"    {'%05.2f' % raw_percentage}%" +
                              f" of {isotopologue} isotopologue table data written")
                    load_sql.buffer_insert_value(values=[single_line_values_dict[column_name]
                                                         for column_name in columns])
                else:
                    load_sql.buffer_insert_execute(run_silent=False)
        if self.verbose:
            print(" Completed writing SQL tables for Hitran molecular data")

    def write_sql(self, upload_all_params: bool = False):
        set_data_status_mysql(new_data_staged_to_set=False, new_data_commited_to_set=False, updated_mysql_to_set=False)
        with LoadSQL(auto_connect=True, verbose=self.verbose) as load_sql:
            load_sql.create_schema(schema_name=spexo_schema)
            load_sql.clear_database(database=spexo_schema)
            load_sql.create_schema(schema_name=stacked_line_schema)
            load_sql.clear_database(database=spectra_schema)
            load_sql.create_schema(schema_name=spectra_schema)
            load_sql.clear_database(database=stacked_line_schema)
        # delete all the files and folders in the output directory
        for root, dirs, files in os.walk(output_dir):
            for f in files:
                os.unlink(os.path.join(root, f))
            for d in dirs:
                shutil.rmtree(os.path.join(root, d))
        self.write_metadata(upload_all_params=upload_all_params)
        self.write_spectra()
        self.write_hitran()
        set_data_status_mysql(new_data_staged_to_set=True, new_data_commited_to_set=False, updated_mysql_to_set=False)

    def calculate_summary(self):
        self.summary = Summary()
        for spexodisks_handle in self.available_spexodisks_handles:
            self.summary.add_object(self.__getattribute__(spexodisks_handle))


def count_dictionary(count_dict, keys):
    for key in keys:
        add_to_count_dictionary(count_dict, key)


def add_to_count_dictionary(count_dict, key):
    if key in count_dict.keys():
        count_dict[key] += 1
    else:
        count_dict[key] = 1


class Summary:
    def __init__(self):
        self.desired_spec_params = {"hitran_lines", "line_fluxes", "flux_cals", "stacked_line",
                                    "max_wavelength_um", "min_wavelength_um"}
        # Stores of Summary Data
        self.object_count = 0
        self.object_names = {}
        self.object_params = {}

        self.spectra_count = 0
        self.spectra_per_star = {}
        self.instruments = {}

        self.line_flux_count = 0
        self.flux_cal_count = 0
        self.stacked_line_count = 0

        self.wavelength_coverages = []
        self.obsevationdates = []
        self.star_with_spec_param = {}
        self.spectra_with_spec_param = {}

    def add_object(self, single_object):
        self.object_count += 1
        count_dictionary(count_dict=self.object_names, keys=single_object.object_names_dict.keys())
        count_dictionary(count_dict=self.object_params, keys=single_object.object_params.keys())

        self.spectra_per_star[single_object.spexodisks_handle] = 0
        for spectral_handle in single_object.available_spectral_handles:
            self.spectra_per_star[single_object.spexodisks_handle] += 1
            self.add_spectrum(single_spectrum=single_object.__getattribute__(spectral_handle))

    def add_spectrum(self, single_spectrum):
        self.spectra_count += 1
        add_to_count_dictionary(count_dict=self.instruments, key=single_spectrum.set_type)


class OutputCollection(ObjectCollection):
    def receive_data(self, **kwargs):
        kwargs_dict = {key: value for key, value in kwargs.items()}
        if "object_dict" in kwargs_dict.keys():
            object_dict = kwargs_dict["object_dict"]
            for spexodisks_handle in object_dict.keys():
                self.available_spexodisks_handles.add(spexodisks_handle)
                self.__setattr__(spexodisks_handle, copy.deepcopy(object_dict[spexodisks_handle]))
