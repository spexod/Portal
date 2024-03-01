import os
from collections import namedtuple

import numpy as np
from autostar.table_read import num_format
from autostar.simbad_query import SimbadLib
from autostar.name_correction import verify_starname

from ref.ref import flux_cal_dir


SingleFluxCal = namedtuple('SingleFluxCal', 'um flux err ref')
per_spectrum_match_string = "star|spectrum"


class FluxCal:
    def __init__(self, simbad_lib=None, auto_load=True):
        self.full_paths = []
        for f in os.listdir(flux_cal_dir):
            test_file_name = os.path.join(flux_cal_dir, f)
            if os.path.isfile(test_file_name):
                self.full_paths.append(test_file_name)
        self.path_to_handle = {}
        for file in self.full_paths:
            basename = os.path.basename(file)
            handle, _extension = basename.rsplit(".", 1)
            self.path_to_handle[file] = handle
        self.flux_cal = None
        self.flux_cal_per_spectrum = None
        if simbad_lib is None:
            self.simbad_lib = SimbadLib()
        else:
            self.simbad_lib = simbad_lib
        if auto_load:
            self.load()

    def load(self):
        self.flux_cal = {}
        self.flux_cal_per_spectrum = {}
        for full_path in self.full_paths:
            with open(full_path, 'r') as f:
                raw_data = f.readlines()
            _, extension = full_path.rsplit(".", 1)
            if extension.lower() == "psv":
                delimiter = "|"
            else:
                delimiter = ","
            set_handle = self.path_to_handle[full_path]
            split_data = [[num_format(value) for value in raw_line.strip().split(delimiter)] for raw_line in raw_data
                          if raw_line != "" and raw_line[0] != "#"]
            header = [str(column_name) for column_name in split_data[0]]
            name_index = header.index("star")
            if per_spectrum_match_string == raw_data[0][:len(per_spectrum_match_string)]:
                if set_handle not in self.flux_cal_per_spectrum.keys():
                    self.flux_cal_per_spectrum[set_handle] = {}
                line_dicts = [{column_name: column_value
                               for column_name, column_value in list(zip(header, a_split_line))}
                              for a_split_line in split_data[1:]]
                for line_dict in line_dicts:
                    simbad_string_star_name = line_dict["star"]
                    object_name, hypatia_name = verify_starname(simbad_string_star_name)
                    spexodisks_handle, _star_names_dict = self.simbad_lib.get_star_dict(hypatia_name)
                    spectrum_base_handle = line_dict["spectrum"]
                    single_flux_cal = SingleFluxCal(um=line_dict["um"], flux=line_dict["flux"],
                                                    err=line_dict["err"], ref=line_dict["ref"])
                    if spexodisks_handle not in self.flux_cal_per_spectrum[set_handle].keys():
                        self.flux_cal_per_spectrum[set_handle][spexodisks_handle] = {}
                    self.flux_cal_per_spectrum[set_handle][spexodisks_handle][spectrum_base_handle] = single_flux_cal
            else:
                data_types = {}
                error_types = {}
                ref_types = {}
                for column_index, column_name in list(enumerate(header)):
                    if "_err" in column_name:
                        error_types[column_name.replace("_err", "")] = column_index
                    elif "_ref" in column_name:
                        ref_types[column_name.replace("_ref", "")] = column_index
                    elif column_name != "star":
                        data_types[column_name] = column_index
                for a_split_line in split_data[1:]:
                    line_data = []
                    object_name, hypatia_name = verify_starname(a_split_line[name_index])
                    spexodisks_handle, _star_names_dict = self.simbad_lib.get_star_dict(hypatia_name)
                    for data_type in data_types.keys():
                        value = a_split_line[data_types[data_type]]
                        if data_type in error_types.keys():
                            error = a_split_line[error_types[data_type]]
                        else:
                            error = None
                        if data_type in ref_types.keys():
                            ref = a_split_line[ref_types[data_type]]
                        else:
                            ref = None
                        line_data.append(SingleFluxCal(float(data_type), value, error, ref))

                    if set_handle not in self.flux_cal.keys():
                        self.flux_cal[set_handle] = {}
                    if spexodisks_handle in self.flux_cal[set_handle].keys():
                        self.flux_cal[set_handle][spexodisks_handle].extend(line_data)
                    else:
                        self.flux_cal[set_handle][spexodisks_handle] = line_data

    def get_relevant_calibrations(self, set_handle, spexodisks_handle, wave_length, spectrum_base_handle=None):
        relevant_calibrations = []
        set_handle = set_handle.lower()
        if set_handle in self.flux_cal.keys() and spexodisks_handle in self.flux_cal[set_handle].keys():
            available_calibrations = self.flux_cal[set_handle][spexodisks_handle]
            min_wave_length = wave_length[0]
            max_wave_length = wave_length[-1]
            for single_flux_cal in available_calibrations:
                if min_wave_length <= single_flux_cal.um <= max_wave_length:
                    relevant_calibrations.append(single_flux_cal)
        if spectrum_base_handle is not None and set_handle in self.flux_cal_per_spectrum.keys() and \
                spexodisks_handle in self.flux_cal_per_spectrum[set_handle].keys() and \
                spectrum_base_handle in self.flux_cal_per_spectrum[set_handle][spexodisks_handle].keys():
            single_flux_cal = self.flux_cal_per_spectrum[set_handle][spexodisks_handle][spectrum_base_handle]
            relevant_calibrations.append(single_flux_cal)
        return relevant_calibrations

    def calibrate(self, set_handle, spexodisks_handle, wave_length, flux, flux_error=None, spectrum_base_handle=None):
        calibrated = False
        cal_flux = None
        cal_flux_error = None
        cal_reference = None
        single_flux_cal = None
        # get the calibration
        if spexodisks_handle in self.flux_cal[set_handle].keys():
            relevant_calibrations = self.get_relevant_calibrations(set_handle, spexodisks_handle,
                                                                   wave_length, spectrum_base_handle)
            center_wave_length = (wave_length[-1] + wave_length[0]) / 2.0
            # in the case of multiple calibrations pick the one closest to the center frequency
            # is all the calibrations are at the same cal_um, this picks the first one.
            min_diff = float('inf')
            for single_flux_cal in relevant_calibrations:
                cal_um, flux_factor, flux_factor_err, cal_ref = single_flux_cal
                diff = np.abs(cal_um - center_wave_length)
                if diff < min_diff:
                    min_diff = diff
                    calibrated = True
                    cal_reference = cal_ref
                    cal_flux = flux * flux_factor
                    if flux_error is not None:
                        cal_flux_error = np.sqrt((flux_error / flux)**2 + np.abs(flux_factor_err / flux_factor)**2) \
                                         * np.abs(cal_flux)
        return calibrated, cal_flux, cal_flux_error, cal_reference, single_flux_cal


if __name__ == "__main__":
    fl = FluxCal()
    wl = np.arange(3.0, 8.01, 0.1)
    flux = np.random.rand(len(wl)) + 1.0
    flux_error = np.random.rand(len(wl)) / 10.0
    calibrated, cal_flux, cal_flux_error, cal_reference, single_flux_cal = \
        fl.calibrate('crires', "star_51_oph", wl, flux, flux_error)
