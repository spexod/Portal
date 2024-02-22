import os
from warnings import warn
from datetime import date, datetime, time
from collections import namedtuple

import toml
import numpy as np
from scipy import stats
from matplotlib import pyplot as plt

from autostar.simbad_query import SimbadLib
from autostar.name_correction import verify_starname
from spexod.fits_read import get_fits, fits_headers_to_dict

from ref.ref import spectra_dir, ref_dir, flux_cal_dir, nirspec_flux_cal_ref, instrument_metadata
from science.load.flux_cal import SingleFluxCal


# expected values for instrument name
allowed_insts = {handle_and_name[0].lower() for handle_and_name in instrument_metadata}

# some custom setting for the original spexodisks spectral data (not well formatted data)
alt_format_ishell_data = {'51Oph_H2O.fits'}
new_format_crires = {"AATau_M_Helio.fits"}
new_format_spitzer = {"AATau_comb.fits"}

nirspec_month_abriv = {'jan': 1, 'feb': 2, 'mar': 3, "apr": 4, 'may': 5, "jun": 6,
                       'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}
suffixes = ['.txt', ".fits", ".dat"]
file_name_replace_strings = {"plus": "+", "minus": '-'}
acceptable_file_extensions = {"txt", "psv", 'csv', 'fits', 'toml'}

ExtraScienceProductPath = namedtuple("ExtraScienceProductPath", "isotopologue transition path")


class ExtraScienceProduct:
    def __init__(self, isotopologue, transition, spectrum):
        self.isotopologue = isotopologue
        if "v" == transition[0]:
            self.transition_type = "vibrational"
            upper_level, lower_level = transition[1:].split("-")
            self.upper_level = int(upper_level)
            self.lower_level = int(lower_level)
            self.description = "Stacked Rotational Line Spectrum " + self.isotopologue + \
                               " (v=" + str(self.upper_level) + "-" + str(self.lower_level) + ")"
        else:
            self.transition_type = self.upper_level = self.lower_level = self.description = None
        self.spectrum = spectrum


def flux_decal_from_median(um, flux):
    clean_um = um[~np.isnan(flux)]
    clean_flux = flux[~np.isnan(flux)]
    cal_um = np.mean(clean_um)
    cal_fux = np.median(clean_flux)
    relative_flux = flux / cal_fux
    cal_flux_error = stats.median_abs_deviation(clean_flux)
    single_flux_cal = SingleFluxCal(um=cal_um, flux=cal_fux, err=cal_flux_error, ref=nirspec_flux_cal_ref)
    return relative_flux, single_flux_cal


def default_spectrum(path):
    hdul = get_fits(path)
    header = fits_headers_to_dict(hdul[0].header)
    wavelength = hdul[1].data[0][0]
    flux = hdul[1].data[0][1]
    flux_error = hdul[1].data[0][2]
    return header, wavelength, flux, flux_error


set_parse_functions = {}


def parser(func):
    name_type = func.__name__
    set_parse_functions[name_type] = func
    return func


@parser
def stacked_lines(path):
    spec_data = {}
    spec_data['header'], spec_data['velocity_kmps'], spec_data['flux'], spec_data['flux_error'] = default_spectrum(path)
    return spec_data


@parser
def crires(path):
    spec_data = {}
    spec_data['header'], spec_data['wavelength_um'], spec_data['flux'], spec_data['flux_error'] = default_spectrum(path)
    date_time_str, _ = spec_data['header']["DATE"].split('.')
    spec_data['observation_date'] = datetime.fromisoformat(date_time_str)
    return spec_data


@parser
def igrins(path):
    hdul = get_fits(path)
    # the header in HDUL[0] is a simple auto generated header that is not useful
    header = fits_headers_to_dict(hdul[1].header)
    wavelength = hdul[1].data[0][0]
    flux = hdul[1].data[0][1]
    flux_error = hdul[1].data[0][2]
    # DATE-OBS has the fraction of a second in the format YYYY-MM-DDTHH:MM:SS.sss, different the CRIRES format
    try:
        observation_date = datetime.strptime(header["DATE-OBS"], "%Y-%m-%dT%H:%M:%S.%f")
    except ValueError:
        observation_date = datetime.strptime(header["DATE-OBS"], "%Y-%m-%d-%H:%M:%S.%f")
    return dict(wavelength_um=wavelength, flux=flux, flux_error=flux_error, header=header,
                observation_date=observation_date)


@parser
def ishell(path):
    hdul = get_fits(path)
    header = fits_headers_to_dict(hdul[0].header)
    data = hdul[0].data
    wavelength_um = data[0]
    flux = data[1]
    flux_error = data[2]
    if "AVE_DATE" in header.keys():
        date_str = header["AVE_DATE"]
        time_str = header['AVE_TIME']
        observation_date_iso = F"{date_str} {time_str}+00:00"
    elif "DATES" in header.keys():
        dates_str = header["DATES"]
        # get the start dates and unpack any additional dates into the list end_dates
        start_date, *end_dates = dates_str.split(",")
        # get the last entry in the end dates list.
        end_date = end_dates[-1]
        # without any time information we have to make our best guess at what the time was
        if start_date == end_date:
            # when the start and end date are the same we assume the time mean time for that date.
            observation_date_iso = F"{start_date} 12:00:00"
        else:
            # the start and end date can only different by one day, co-added observations in the same observing night
            observation_date_iso = F"{start_date} 23:59:59.999999"
    else:
        raise KeyError(F"Noe Data Found. The observation date-time information for the iShell spectra in the file:\n" +
                       F"   {path}")

    spec_data = {'header': header, 'wavelength_um': wavelength_um, 'flux': flux, 'flux_error': flux_error,
                 'observation_date': datetime.fromisoformat(observation_date_iso)}
    return spec_data


@parser
def miri(path):
    spec_data = toml.load(path)
    wavelength_um, flux = zip(*spec_data['wavelength_um_flux'])
    del spec_data['wavelength_um_flux']
    spec_data['header'] = dict(spec_data)
    spec_data['header']['observation_date'] = str(spec_data['observation_date'])
    spec_data['wavelength_um'] = np.array(wavelength_um)
    spec_data['flux'] = np.array(flux)
    return spec_data


@parser
def nirspec(path):
    spec_data = {}
    header_list = []
    wavelength = []
    flux = []
    with open(path, 'r') as f:
        trigger = False
        for line in f.readlines():
            line = line.strip().lower()
            while "  " in line:
                line = line.replace("  ", " ")
            if line != "":
                if trigger:
                    um, *jy = line.split(" ")
                    try:
                        formatted_um = float(um)
                        wavelength.append(formatted_um)
                        if jy[0] == "-nan":
                            flux.append(float("nan"))
                        else:
                            flux.append(float(jy[0]))
                    except ValueError:
                        header_list.append(line)

                else:
                    header_list.append(line)
                    if line == "wavelength flux":
                        trigger = True
    header_str = ''
    for line in header_list:
        header_str += line + " | "
    spec_data['header'] = {"HISTORY": header_str}
    date_line = header_list[1]
    _day_of_week, month, day, time_str, year = date_line.split(" ")
    time_object = time.fromisoformat(time_str)
    date_object = date(int(year), nirspec_month_abriv[month], int(day))
    spec_data['observation_date'] = datetime.combine(date_object, time_object)
    spec_data['wavelength_um'] = np.array(wavelength)
    spec_data['flux'], spec_data["single_flux_cal"] = flux_decal_from_median(spec_data['wavelength_um'], np.array(flux))
    spec_data['flux_calibrated'] = False
    return spec_data


@parser
def spex(path):
    hdul = get_fits(path)
    header = fits_headers_to_dict(hdul[0].header)
    data = hdul[0].data
    wavelength_um = data[0]
    flux = data[1]
    flux_error = data[2]
    date_str = header["DATE_OBS"]
    time_str = header['TIME_OBS']
    hour, min, sec = time_str.split(':')
    observation_date_iso = F"{date_str}T{hour:02}:{min:02}:{'%02.6f' % float(sec)}+00:00"
    observation_date = datetime.strptime(observation_date_iso, "%Y-%m-%dT%H:%M:%S.%f%z")
    spec_data = {'header': header, 'wavelength_um': wavelength_um, 'flux': flux, 'flux_error': flux_error,
                 'observation_date': observation_date}
    return spec_data


@parser
def spitzer(path):
    spec_data = {}
    hdul = get_fits(path)
    spec_data['header'] = fits_headers_to_dict(hdul[1].header)
    spec_data['wavelength_um'] = hdul[1].data[0][0]
    spec_data['flux'] = hdul[1].data[0][1]
    spec_data['flux_error'] = hdul[1].data[0][2]
    spec_data['pi'] = spec_data['header']["PI NAME"]
    try:
        spec_data["aor_key"] = int(spec_data['header']["AORKEY"])
    except (ValueError, KeyError):
        pass
    try:
        spec_data["data_reduction_by"] = spec_data["header"]["REDUCT"]
    except (ValueError, KeyError):
        pass
    year, month, day = spec_data["header"]["DATE"].split('-')
    spec_data['observation_date'] = datetime(year=int(year), month=int(month), day=int(day))
    return spec_data


@parser
def visir(path):
    spec_data = {}
    hdul = get_fits(path)
    spec_data['header'] = fits_headers_to_dict(hdul[0].header)
    date_time_str, _ = spec_data['header']["DATE"].split('.')
    spec_data['observation_date'] = datetime.fromisoformat(date_time_str)
    spec_data['wavelength_um'] = hdul[2].data[0][0]
    spec_data['flux'] = hdul[2].data[0][1]
    spec_data['flux_error'] = hdul[2].data[0][2]
    return spec_data


set_types = set(set_parse_functions.keys())


def clean_handle(handle):
    handle = handle.strip().replace(" ", "_").lower().replace(".fits", "").replace("F", "").replace('_data', "")
    handle = handle.replace("_settings_v1", "").replace("\\", "_").replace("/", "_")
    if handle.startswith("_"):
        handle = handle[1:]
    return handle


class SpecInfo:
    def __init__(self):
        self.file_name = os.path.join(ref_dir, 'spectra_infos.txt')
        self.delimiter = "|"
        self.allowed_scale_parameters = {"global", "set", "single"}
        self.spectra = None
        self.line_fluxes = None
        self.stacked_lines = None
        self.read()

    def read(self):
        with open(self.file_name, 'r', encoding="utf8") as f:
            raw_info = f.readlines()
        data_type = None
        scale = None
        header = None
        id_index = None
        header_trigger = False
        processed_info = {}
        for single_line in raw_info:
            stripped_line = single_line.strip()
            if stripped_line == "" or stripped_line[0] == "%":
                # we ignore empty lines or lines starting with the comment charter %
                pass
            else:
                if "%" in stripped_line:
                    # get rid of in-line comments
                    stripped_line, _ = stripped_line.split("%", 1)
                    stripped_line = stripped_line.rstrip()
                if stripped_line[0] == "#":
                    # the "#" denotes a data type, this data type is used until this line is triggered again
                    data_type = stripped_line[1:].lstrip().lower()
                elif "header" == stripped_line.lower():
                    # a trigger to read the header in the next line
                    header_trigger = True
                elif header_trigger:
                    header = [column_name.strip().lower() for column_name in stripped_line.split(self.delimiter)]
                    id_index = header.index('id')
                    header.pop(id_index)
                    header_trigger = False
                elif stripped_line[-1] == ":":
                    # the scale parameter is denoted by a line the ends in ":"
                    scale = stripped_line[:-1].rstrip().lower()
                    if scale not in self.allowed_scale_parameters:
                        raise KeyError(str(scale) + " is not an allowed, allowed values: "
                                       + str(self.allowed_scale_parameters))
                else:
                    column_values = [column_value.strip() for column_value in stripped_line.split(self.delimiter)]
                    if data_type not in processed_info.keys():
                        processed_info[data_type] = {}
                    if scale not in processed_info[data_type].keys():
                        processed_info[data_type][scale] = {}
                    value_id = column_values[id_index].lower().replace("/", "_")
                    column_values.pop(id_index)
                    if scale == 'global':
                        processed_info[data_type][scale] = {column_name: column_value
                                                            for column_name, column_value
                                                            in list(zip(header, column_values))}
                    else:
                        processed_info[data_type][scale][value_id] = {column_name: column_value
                                                                      for column_name, column_value
                                                                      in list(zip(header, column_values))}
        for key in processed_info.keys():
            self.__setattr__(key, processed_info[key])


class AllSpectra:
    def __init__(self, folders=None, simbad_go_fast=False, verbose=True, spectra_output_dir=None):
        self.verbose = verbose
        self.spectra_output_dir = spectra_output_dir
        self.set_types_to_decal = {"nirspec"}
        self.handle_list = []
        self.simbad_lib = SimbadLib(go_fast=simbad_go_fast, verbose=verbose)
        self.spec_info = SpecInfo()

        if folders is None:
            dir_paths = []
            spectral_set_handles = []
            for dirname, subdirs, files in os.walk(spectra_dir):
                if dirname != spectra_dir and files:
                    spectral_set_handle = clean_handle(dirname.replace(spectra_dir, ''))
                    inst_name = spectral_set_handle.split('_')[0]
                    if inst_name in allowed_insts:
                        dir_paths.append(dirname)
                        spectral_set_handles.append(spectral_set_handle)
                    else:
                        warn(f"{inst_name} is not an expected instrument: {allowed_insts}, skipping the folder {dirname}")
            # order by set_handle
            spectral_set_handles, dir_paths = list(zip(*sorted(zip(spectral_set_handles, dir_paths))))
        else:
            spectral_set_handles = [clean_handle(folder) for folder in folders]
            dir_paths = [os.path.join(spectra_dir, folder) for folder in folders]

        for spectral_set_handle, dir_path in zip(spectral_set_handles, dir_paths):
            self.handle_list.append(spectral_set_handle)
            self.__setattr__(spectral_set_handle, SpecSet(path=dir_path,
                                                          set_name=spectral_set_handle,
                                                          simbad_lib=self.simbad_lib, spec_info=self.spec_info,
                                                          verbose=self.verbose))
        self.write_flux_cal_files()

    def write_flux_cal_files(self):
        for set_type in self.set_types_to_decal:
            spectral_set_handles_this_type = [spectral_set_handle for spectral_set_handle in self.handle_list
                                              if set_type in spectral_set_handle]
            file_text = {}
            for spectral_set_handle in spectral_set_handles_this_type:
                single_set = self.__getattribute__(spectral_set_handle)
                for spectrum_handle in single_set.handle_list:
                    single_spectrum = single_set.__getattribute__(spectrum_handle)
                    object_string_name = single_spectrum.object_name
                    spectrum_base_handle = single_spectrum.base_handle
                    flux_cal = single_spectrum.single_flux_cal
                    if flux_cal is not None:
                        single_line = object_string_name + "|" + spectrum_base_handle + "|" + \
                                      str(flux_cal.um) + "|" + str(flux_cal.flux) + "|" + \
                                      str(flux_cal.err) + "|" + flux_cal.ref + "\n"
                        if object_string_name not in file_text.keys():
                            file_text[object_string_name] = {spectrum_base_handle: single_line}
                        else:
                            file_text[object_string_name][spectrum_base_handle] = single_line
            with open(os.path.join(flux_cal_dir, set_type.lower() + ".psv"), 'w') as f:
                f.write('star|spectrum|um|flux|err|ref\n')
                for object_string_name in list(sorted(file_text.keys())):
                    for spectrum_base_handle in list(sorted(file_text[object_string_name].keys())):
                        f.write(file_text[object_string_name][spectrum_base_handle])


class SpecSet:
    def __init__(self, path, set_name, simbad_lib, spec_info, verbose=False):
        self.verbose = verbose
        self.handle_list = []
        self.set_name = set_name
        self.ref_data_refresh_required = False
        self.unreferenced_stars = []
        self.simbad_lib = simbad_lib
        self.spec_info = spec_info
        # find the set_type to sent the spectra to the correct parser.
        if set_name in set_types:
            self.parse_type = set_name
        else:
            # try again if nothing was found
            for possible_set_type in set_types:
                # 'in' is a less strict comparator than ==, for the 2nd try
                if possible_set_type in set_name:
                    self.parse_type = possible_set_type
                    break
            else:
                # raise if self.set_type was never found
                raise KeyError("The set name: " + str(set_name) + "\n is with as one of the available " +
                               F"set types: {set_types}" +
                               "\nChange the set name or update parser functions in import_spectra.py")
        # find the observing instrument
        for possible_inst in allowed_insts:
            if possible_inst in set_name:
                self.inst_name = possible_inst
                break
        else:
            # raise if self.inst_name is not set
            raise KeyError("self.set_name: " + str(set_name) + "\n was unable to identify the associated " +
                           F"instrument, for the allowed instrument types: {allowed_insts}" +
                           "\nChange the set name, update parser functions, or update allow_insts in import_spectra.py")
        # loop over all the files in this folder
        self.files = {}
        for f in os.listdir(path):
            test_file_name = os.path.join(path, f)
            if os.path.isfile(test_file_name):
                base_name = os.path.basename(test_file_name)
                file_handle, extension = base_name.rsplit(".", 1)
                if extension in acceptable_file_extensions:
                    if "linefluxes" in file_handle or "stacked" in file_handle:
                        file_handle, isotopologue, transition, product_type = file_handle.rsplit("_", 3)
                        if file_handle not in self.files.keys():
                            self.files[file_handle] = {}
                        if product_type not in self.files[file_handle].keys():
                            self.files[file_handle][product_type] = set()
                        self.files[file_handle][product_type].add(
                            ExtraScienceProductPath(isotopologue, transition, test_file_name))
                    else:
                        if file_handle not in self.files.keys():
                            self.files[file_handle] = {}
                        self.files[file_handle]["path"] = test_file_name
        if self.verbose:
            print("Loading", self.set_name, "spectra,", len(self.files), "files found.")
        for file_handle in self.files.keys():
            spectra_handle = clean_handle(os.path.basename(file_handle))
            self.handle_list.append(spectra_handle)

            self.__setattr__(spectra_handle, ImportSpec(path=self.files[file_handle]["path"],
                                                        parse_type=self.parse_type,
                                                        inst_name=self.inst_name,
                                                        simbad_lib=self.simbad_lib, spec_info=self.spec_info,
                                                        verbose=self.verbose))
            single_spectrum = self.__getattribute__(spectra_handle)
            single_spectrum.open()
            single_spectrum.parse_object_name()
            for product_name in ["stacked", "linefluxes"]:
                if product_name in self.files[file_handle].keys():
                    for espp in self.files[file_handle][product_name]:
                        single_spectrum.__getattribute__('add_' + product_name)(espp)


class ImportSpec:
    def __init__(self, path, parse_type, inst_name, simbad_lib, spec_info, verbose=True):
        self.verbose = verbose
        self.parse_type = parse_type
        self.inst_name = inst_name
        self.file_path = path
        self.spec_info_match_handle = \
            self.file_path.replace(spectra_dir, "").replace("/", "_").replace('\\', "_")[1:].lower()
        self.basename = os.path.basename(self.file_path)
        self.base_handle, self.file_extension = self.basename.rsplit('.', 1)
        self.simbad_lib = simbad_lib
        self.spec_info = spec_info
        self.header = None
        self.observation_date = None
        self.data_reduction_by = None
        self.aor_key = None
        self.wavelength_um = None
        self.velocity_kmps = None
        self.flux = None
        self.flux_error = None
        self.flux_calibrated = None
        self.ref_frame = None
        self.pi = None
        self.reference = None
        self.downloadable = None
        self.object_name = None
        self.raw_original_object_name = None
        self.hypatia_name = None
        self.object_names_dict = None
        self.spexodisks_handle = None

        self.single_flux_cal = None

        self.stacked_lines = None
        self.line_fluxes = None

    def open(self):
        spec_data = set_parse_functions[self.parse_type](self.file_path)
        if self.spec_info.spectra is not None:
            info_dict = None
            if 'single' in self.spec_info.spectra.keys() \
                    and self.spec_info_match_handle in self.spec_info.spectra['single'].keys():
                info_dict = self.spec_info.spectra['single'][self.spec_info_match_handle]
            elif 'set' in self.spec_info.spectra.keys() and self.inst_name in self.spec_info.spectra['set'].keys():
                info_dict = self.spec_info.spectra['set'][self.inst_name]
            elif 'global' in self.spec_info.spectra.keys():
                info_dict = self.spec_info.spectra['global']
            if info_dict is not None:
                for data_type in info_dict.keys():
                    # will not overwrite values from set_parse_functions
                    if data_type not in spec_data.keys():
                        spec_data[data_type] = info_dict[data_type]

        for data_type in spec_data.keys():
            self.__setattr__(data_type, spec_data[data_type])
        if type(self.header) == dict:
            self.header = {key.lower(): self.header[key] for key in self.header.keys()}

    def add_stacked(self, extra_science_product_path):
        isotopologue, transition, path = extra_science_product_path
        if self.stacked_lines is None:
            self.stacked_lines = {}

        self.stacked_lines[extra_science_product_path] = ExtraScienceProduct(isotopologue, transition,
                                                                             ImportSpec(path=path,
                                                                                        parse_type='stacked_lines',
                                                                                        inst_name=self.inst_name,
                                                                                        simbad_lib=self.simbad_lib,
                                                                                        spec_info=self.spec_info,
                                                                                        verbose=self.verbose))
        self.stacked_lines[extra_science_product_path].spectrum.open()

    def add_linefluxes(self, extra_science_product_path):
        if self.line_fluxes is None:
            self.line_fluxes = set()
        self.line_fluxes.add(extra_science_product_path)

    def plot(self):
        if self.flux_error is None:
            plt.plot(self.wavelength_um, self.flux)
        else:
            plt.errorbar(self.wavelength_um, self.flux, self.flux_error)
        plt.show()

    def parse_object_name(self):
        header_name = None
        filename_parsed_name = None
        # parse the name from the file name
        try:
            filename_parsed_name, *_ = os.path.basename(self.file_path).split("_")
            for suffix in suffixes:
                if suffix in filename_parsed_name:
                    filename_parsed_name = filename_parsed_name.replace(suffix, "")
            for character_replace in file_name_replace_strings.keys():
                if character_replace in filename_parsed_name:
                    filename_parsed_name = filename_parsed_name.replace(character_replace,
                                                                        file_name_replace_strings[character_replace])
        except:
            pass
        # parse the name from the "object" parameter in the header
        if type(self.header) == dict and "object" in self.header.keys():
            header_name = self.header["object"].strip().replace("_", " ")
            if header_name.lower() == 'std':
                header_name = None
        # control the presence for using the parsed file name or the header name
        if header_name is None:
            self.raw_original_object_name = filename_parsed_name
        else:
            self.raw_original_object_name = header_name
        # verifies if the object name is a valid name
        if filename_parsed_name is None:
            other_info = None
        else:
            other_info = f"parsed name from filename: {filename_parsed_name}"
        self.object_name, self.hypatia_name = verify_starname(self.raw_original_object_name, other_info=other_info)
        if self.hypatia_name is None:
            raise NameError("A hypatia name is required to continue.")
        else:
            self.spexodisks_handle, self.object_names_dict = self.simbad_lib.get_star_dict(self.hypatia_name)


if __name__ == "__main__":
    # test_data = max_data
    # all_spec = AllSpectra(folders=test_data, simbad_go_fast=False, verbose=True)
    spec_info = SpecInfo()
