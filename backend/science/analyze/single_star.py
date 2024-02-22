from operator import itemgetter

from autostar.simbad_query import StarDict, handle_to_simbad
from autostar.object_params import SingleParam

from ref.ref import instrument_metadata
from ref.star_names import star_name_format
from science.load.units import UnitsObjectParams
from science.analyze.spectrum import Spectrum

class SingleObject:
    def __init__(self, spexodisks_handle, pop_names_lib, verbose=True, spectra_output_dir=None):
        self.verbose = verbose
        self.spectra_output_dir = spectra_output_dir
        self.spexodisks_handle = spexodisks_handle
        self.preferred_simbad_name = handle_to_simbad(spexodisks_handle)
        self.pop_name = pop_names_lib.get_or_generate(spexodisks_handle=spexodisks_handle,
                                                      simbad_preferred_name=self.preferred_simbad_name)
        self.main_simbad_record = None
        self.main_simbad_name = None
        self.simbad_link = None
        self.main_simbad_bibcode = None
        self.preferred_hypatia_name = star_name_format(self.preferred_simbad_name)
        self.object_names_dict = StarDict()
        self.available_spectral_handles = set()
        self.spectra_by_set_type = {}
        self.object_params = UnitsObjectParams()
        self.inst_sum_str = None
        self.is_target = False
        self.esa_sky = None

    def add_spectrum(self, spectrum_object):
        self.object_names_dict.update(spectrum_object.object_names_dict)
        single_spectrum = Spectrum(self.pop_name, spectrum_object, self.spectra_output_dir)
        spectral_handle = single_spectrum.set_type + "_" + single_spectrum.range_str + "_" + self.spexodisks_handle
        if spectral_handle in self.available_spectral_handles:
            count = 0
            while spectral_handle in self.available_spectral_handles:
                if count == 0:
                    spectral_handle += "___"
                count += 1
                spectral_handle = spectral_handle[:-2] + str("%02i" % count)
        single_spectrum.__setattr__('spectrum_handle', spectral_handle)
        single_spectrum.__setattr__('spexodisks_handle', self.spexodisks_handle)
        self.available_spectral_handles.add(spectral_handle)
        self.__setattr__(spectral_handle, single_spectrum)
        # for counting and self statistics
        set_type = single_spectrum.set_type
        if set_type not in self.spectra_by_set_type.keys():
            self.spectra_by_set_type[set_type] = set()
        self.spectra_by_set_type[set_type].add(spectral_handle)

    def add_simbad_main_record(self, main_record):
        if main_record is not None:
            self.main_simbad_record = main_record
            formatted_main_name = self.main_simbad_record['MAIN_ID']
            while '  ' in formatted_main_name:
                formatted_main_name = formatted_main_name.replace('  ', ' ')
            self.main_simbad_name = formatted_main_name
            link_name = self.main_simbad_name.replace('+', '%2B').replace(' ', '+')
            self.simbad_link = f'https://simbad.u-strasbg.fr/simbad/sim-basic?Ident={link_name}&submit=SIMBAD+search'

            if 'COO_BIBCODE' in self.main_simbad_record.keys():
                self.main_simbad_bibcode = self.main_simbad_record['COO_BIBCODE']

    def add_param(self, param_str, value, err=None, units=None, ref=None, notes=None):
        self.object_params[param_str] = SingleParam(value=value, err=err, units=units, ref=ref, notes=notes)

    def remove_param(self, param_str, value, err=None, units=None, ref=None, notes=None):
        param_to_remove = SingleParam(value=value, err=err, units=units, ref=ref, notes=notes)
        if param_to_remove in self.object_params[param_str]:
            self.object_params[param_str].remove(param_to_remove)
            if self.object_params[param_str] == set():
                # delete the entry is the parameter is now an empty set
                del self.object_params[param_str]
        else:
            raise KeyError("Parameter not found for removal")

    def summary(self, all_instruments):
        """
        Create, store and return and instrument summary string.

        :param all_instruments: iter of strings representing the instruments names
                                associated with this object's spectra.

        :return: str - this has all the instrument summary details in a simple to parse string
        """
        summary = ""

        inst_set = set(all_instruments)
        for inst_handle, inst_name, inst_name_short, show_by_default in instrument_metadata:
            if inst_handle in inst_set:
                summary += f'{inst_handle}:'
                if inst_handle in self.spectra_by_set_type.keys():
                    summary += f'{len(self.spectra_by_set_type[inst_handle])}'
                    # sort by display name here
                    display_name_and_handle = []
                    for spectrum_handle in sorted(self.spectra_by_set_type[inst_handle]):
                        single_spectrum = self.__getattribute__(spectrum_handle)
                        display_name = single_spectrum.spectrum_display_name
                        display_name_and_handle.append((display_name, spectrum_handle))
                    display_name_and_handle_sorted = sorted(display_name_and_handle,
                                                            key=itemgetter(0), reverse=True)
                    for display_name, spectrum_handle in display_name_and_handle_sorted:
                        # summary += f';{spectrum_handle}'
                        summary += f';{spectrum_handle}:{display_name}'
                else:
                    summary += '0'
                summary += '|'
        self.inst_sum_str = summary[:-1]
        return self.inst_sum_str

