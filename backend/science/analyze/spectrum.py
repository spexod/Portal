import os
import gc
import warnings
from operator import attrgetter
from itertools import zip_longest
from typing import NamedTuple, Optional

import unidecode
import numpy as np
from astropy.io import fits
from astropy import units as u
from astropy.coordinates import SkyCoord, FK5
from astropy.utils.exceptions import AstropyUserWarning
import matplotlib.pyplot as plt
import matplotlib.lines as mlines

from ref.ref import plot_dir, spexodisks_ref, caleb_ref, k_c, instrument_metadata,  output_dir
from ref.star_names import StringStarName
from science.tools.julian import get_julian_datetime
from science.load.hitran import hitran_line_header, make_hl_dict
from science.load.line_flux import line_flux_header
from science.load.hitran import Hitran, isotopologue_to_color, isotopologue_to_molecule


instrument_handle_to_name = {}
instrument_handle_to_short_name = {}
handle_to_inst_dict = {}
for inst_handle, inst_name, inst_name_short, show_by_default in instrument_metadata:
    instrument_handle_to_name[inst_handle] = inst_name
    instrument_handle_to_short_name[inst_handle] = inst_name_short
    handle_to_inst_dict[inst_handle] = {'inst_handle': inst_handle, 'inst_name': inst_name,
                                        'inst_name_short': inst_name_short, 'show_by_default': show_by_default}

spectra_output_dir_default = output_dir
true_set = {True, 'true', "True", 'TRUE', 'T', 't', 'y', 'Y', 'Yes', 'yes', 'YES', '1', 1, 'on', 'On', 'ON'}

default_ls = ['solid', 'dotted', 'dashed', 'dashdot']
warnings.filterwarnings('ignore', category=AstropyUserWarning, append=True)


def um_to_vel(wavelength_um, zero_velocity_wavelength_um):
    del_wavelength_um = wavelength_um - zero_velocity_wavelength_um
    velocity_mps = (del_wavelength_um / zero_velocity_wavelength_um) * k_c
    velocity_kmps = velocity_mps / 1000.0
    return velocity_kmps


def vel_to_um(velocity_kmps, zero_velocity_wavelength_um):
    velocity_mps = velocity_kmps * 1000.0
    del_wavelength_um = (velocity_mps / k_c) * zero_velocity_wavelength_um
    wavelength_um = del_wavelength_um + zero_velocity_wavelength_um
    return wavelength_um


def get_more_ticks(xmin, xmax, x_ticks_min_number, ax):
    x_diff = xmax - xmin
    default_ticks = ax.get_xticks()
    first_tick = float(default_ticks[0])
    default_tick_step = float(default_ticks[1]) - first_tick
    tick_step = default_tick_step
    while x_ticks_min_number > x_diff / tick_step:
        tick_step = tick_step / 2.0
    tick_list = [first_tick]
    while tick_list[0] > xmin:
        tick_list.insert(0, tick_list[0] - tick_step)
    while tick_list[-1] < xmax:
        tick_list.append(tick_list[-1] + tick_step)
    return tick_list


def get_spectrum_output_dir(spectra_output_dir: str, object_pop_name: str) -> str:
    # only single spaces
    while "  " in object_pop_name:
        object_pop_name = object_pop_name.replace("  ", " ")
    # remove leading and trailing spaces
    object_pop_name = object_pop_name.strip()
    # underscores for spaces, all lower case
    return os.path.join(spectra_output_dir, object_pop_name.replace(" ", "_").lower())


hitran_line_split_by = ["molecule", "isotopologue"]


def hitran_line_split(hitran_lines):
    split_dict = {}
    for hitran_line in hitran_lines:
        key = tuple([hitran_line.__getattribute__(attr) for attr in hitran_line_split_by])
        if key not in split_dict.keys():
            split_dict[key] = []
        split_dict[key].append(hitran_line)
    return split_dict


def fluxcal_statement(flux_is_calibrated, has_stacked_lines, has_line_fluxes):
    cal_statement = ''
    if has_stacked_lines and has_line_fluxes:
        cal_statement += "The Primary Spectrum, Stack Line Spectra, and Measured Line Fluxes "
        are_is = 'are '
    elif has_stacked_lines:
        cal_statement += "The Primary Spectrum and Stack Line Spectra "
        are_is = 'are '
    elif has_line_fluxes:
        cal_statement += "The Primary Spectrum and Measured Line Fluxes "
        are_is = 'are '
    else:
        cal_statement += "The Primary Spectrum "
        are_is = 'is '
    if flux_is_calibrated:
        cal_statement += are_is + 'Flux Calibrated using the following'
    else:
        cal_statement += 'can be calibrated to (Jansky) using the following'
    return cal_statement


def lineflux_name(isotopologue, upper_level, lower_level):
    return isotopologue + " (v=" + str(upper_level) + "-" + str(lower_level) + ")"


def flux_cal_to_dict(flux_cal):
    return {"flux_cal": flux_cal.flux, "flux_cal_error": flux_cal.err,
            "wavelength_um": flux_cal.um, 'ref': flux_cal.ref}


def make_spectrum_hdu(x_column, flux, flux_error, name="Primary Spectrum", velocity_mode=False):
    if velocity_mode:
        x_label = 'velocity_kmps'
    else:
        x_label = 'wavelength_um'
    x_column = fits.Column(name=x_label, format='D', array=x_column)
    column_flux = fits.Column(name='flux', format='D', array=flux)
    column_flux_error = fits.Column(name='flux_error', format='D', array=flux_error)
    columns = fits.ColDefs([x_column, column_flux, column_flux_error])
    hdu_spectrum = fits.BinTableHDU.from_columns(columns, name=name)
    return hdu_spectrum


class Spectrum:
    stellar_params_for_fits = {'dist', 'teff'}
    stellar_params_to_fits_name = {'dist': 'DIST', 'teff': 'TEFF'}
    allowed_hitran_molecules = {'co', 'h2o'}

    co_dtypes = {"wavelength_um": '<f8',
                 "isotopologue": '<U20',
                 "upper_level": '<U30',
                 "lower_level": '<U30',
                 "transition": '<U30',
                 "einstein_A": '<f8',
                 "upper_level_energy": '<f8',
                 "lower_level_energy": '<f8',
                 "g_statistical_weight_upper_level": '<f8',
                 "g_statistical_weight_lower_level": '<f8',
                 "upper_vibrational": '<i2',
                 "upper_rotational": '<i2',
                 "branch": '<U1',
                 "lower_vibrational": '<i2',
                 "lower_rotational": '<i2'}

    h2o_dtypes = {"wavelength_um": '<f8',
                  "isotopologue": '<U20',
                  "upper_level": '<U30',
                  "lower_level": '<U30',
                  "transition": '<U65',
                  "einstein_A": '<f8',
                  "upper_level_energy": '<f8',
                  "lower_level_energy": '<f8',
                  "g_statistical_weight_upper_level": '<f8',
                  "g_statistical_weight_lower_level": '<f8',
                  "upper_vibrational1": '<i2',
                  "upper_vibrational2": '<i2',
                  "upper_vibrational3": '<i2',
                  "upper_rotational": '<i2',
                  "upper_ka": '<i2',
                  "upper_kc": '<i2',
                  "lower_vibrational1": '<i2',
                  "lower_vibrational2": '<i2',
                  "lower_vibrational3": '<i2',
                  "lower_rotational": '<i2',
                  "lower_ka": '<i2',
                  "lower_kc": '<i2'}

    fluxcal_dtypes = {"flux_cal": '<f8',
                      "flux_cal_error": "<f8",
                      "wavelength_um": "<f8",
                      "ref": "<U40"}

    lineflux_dtypes = {"flux": '<f8',
                       "err": '<f8',
                       "match_wavelength_um": '<f8'}

    header_keys_to_remove = {'#######'}

    def __init__(self, pop_name, spectrum_object, spectra_output_dir=None):
        self.object_pop_name = pop_name
        if spectra_output_dir is None:
            self.spectra_output_dir = spectra_output_dir_default
        else:
            self.spectra_output_dir = spectra_output_dir

        self.file_path = spectrum_object.file_path
        self.basename = spectrum_object.basename
        self.base_handle = spectrum_object.base_handle
        self.file_extension = spectrum_object.file_extension

        self.set_type = spectrum_object.inst_name
        self.inst_handle = self.set_type
        self.inst_name = instrument_handle_to_name[self.set_type]

        self.observation_date = spectrum_object.observation_date
        self.raw_original_object_name = spectrum_object.raw_original_object_name
        self.object_string_name = spectrum_object.object_name
        self.object_hypatia_name = spectrum_object.hypatia_name

        self.pi = spectrum_object.pi
        self.reference = spectrum_object.reference

        self.header_original = spectrum_object.header

        if spectrum_object.downloadable in true_set:
            self.downloadable = True
        else:
            self.downloadable = False

        self.spectrum_header = spectrum_object.header

        self.flux = spectrum_object.flux
        self.flux_error = spectrum_object.flux_error
        self.wavelength_um = spectrum_object.wavelength_um
        self.velocity_kmps = spectrum_object.velocity_kmps

        # Spitzer stuff
        self.data_reduction_by = spectrum_object.data_reduction_by
        self.aor_key = spectrum_object.aor_key

        if spectrum_object.flux_calibrated in true_set:
            self.flux_is_calibrated = True
        else:
            self.flux_is_calibrated = False
        self.ref_frame = spectrum_object.ref_frame
        self.output_dir_this_object = get_spectrum_output_dir(self.spectra_output_dir, self.object_pop_name)

        # extra data products
        self.stacked_lines = spectrum_object.stacked_lines
        self.line_fluxes = None
        self.line_fluxes_paths = spectrum_object.line_fluxes

        # Calculations
        self.min_wavelength_um = None
        self.max_wavelength_um = None
        self.resolution_um = None
        self.range_str = None
        self.spectrum_display_name = None

        # file name and directory determination
        self.output_filename = None
        self.output_txt_filename = None
        self.output_fits_filename = None
        self.calculations()

        # parameters that are set elsewhere, such as in the methods of this class or ObjectCollection
        self.flux_cals = None
        self.hitran_lines = None
        self.spectrum_summary = None
        self.zero_velocity_wavelength_um = None
        if self.velocity_kmps is None:
            self.make_velocity_axis()

    def calculations(self):
        # Calculations
        self.min_wavelength_um = float(np.nanmin(self.wavelength_um))
        self.max_wavelength_um = float(np.nanmax(self.wavelength_um))
        self.resolution_um = (self.max_wavelength_um - self.min_wavelength_um) / len(self.wavelength_um)
        min_wl_for_handle = str('%04i' % int(np.round(self.min_wavelength_um * 1000.0))) + "nm"
        max_wl_for_handle = str('%04i' % int(np.round(self.max_wavelength_um * 1000.0))) + "nm"
        self.range_str = min_wl_for_handle + "_" + max_wl_for_handle
        # self.spectrum_display_name = f'{self.inst_name} {self.observation_date.date()} ' + \
        #                              f'({min_wl_for_handle}-{max_wl_for_handle})'
        self.spectrum_display_name = f'{self.observation_date.date()} ({min_wl_for_handle}-{max_wl_for_handle})'

        # file name and directory determination
        if not os.path.isdir(self.output_dir_this_object):
            os.mkdir(self.output_dir_this_object)
        self.output_filename = os.path.join(self.output_dir_this_object, self.set_type + "_" + self.range_str)
        self.output_txt_filename = self.output_filename + ".txt"
        self.output_fits_filename = self.output_filename + ".fits"
        # Things that should not be allowed for proper data representation.
        if len(self.wavelength_um) != len(self.flux):
            error_msg = f'Flux array length {len(self.flux)} does not match wavelength array length ' + \
                             f'{len(self.wavelength_um)}.\n' + \
                             f'Check the raw data at: {self.file_path}'
            # print(error_msg, '\n')
            raise IndexError(error_msg)
        if self.flux_error is not None:
            if len(self.flux) != len(self.flux_error):
                error_msg = f'Flux array length {len(self.flux)} does not match the flux_error array length ' + \
                                 f'{len(self.flux_error)}.\n' + \
                                 f'Check the raw data at: {self.file_path}'
                print(error_msg)
                # raise IndexError(error_msg)
                print('Setting flux error to None!\n')
                self.flux_error = None

    def make_velocity_axis(self, zero_velocity_wavelength_um=None):
        if zero_velocity_wavelength_um is None:
            self.zero_velocity_wavelength_um = self.min_wavelength_um
        else:
            self.zero_velocity_wavelength_um = zero_velocity_wavelength_um
        self.velocity_kmps = um_to_vel(self.wavelength_um, self.zero_velocity_wavelength_um)

    def make_spectrum_summary(self):
        self.spectrum_summary = SpectraSummary(file=self.output_filename,
                                               um_min=self.min_wavelength_um,
                                               um_max=self.max_wavelength_um,
                                               set_type=self.set_type,
                                               raw_name=self.raw_original_object_name)
        return self.spectrum_summary

    def plot(self, save=True, show=False, show_error_bars=False, show_hitran_lines=False,
             color="firebrick", zero_velocity_wavelength_um=None, transition_text=False,
             min_wavelength_um=None, max_wavelength_um=None, plot_file_name=None, do_pdf=False,
             x_fig_size=30.0, y_fig_size=8.0, text_rotation=20, x_ticks_min_number=20, verbose=True,
             primary_line_width=3, fmt=None, markersize=5, alpha=1.0, error_liw=0.25, error_maker='|',
             error_cap_size=4, error_ls='None', legend_loc=0, legend_num_points=3,
             legend_handle_length=5, legend_fontsize='small', text_fontsize=7, frame_on=True):

        # where the main axis is in figure coordinates
        left = 0.03
        bottom = 0.07
        right = 0.99
        top = 0.87

        title = f"{self.object_pop_name} {self.inst_name}"
        x_label = r'Wavelength ($\mu$m)'

        x_axis_all = []
        y_axis_all = []
        ls_all = []

        # calculations and data organization
        if min_wavelength_um is not None or max_wavelength_um is not None:
            if min_wavelength_um is None:
                mask_min_wavelength_um = float("-inf")
            else:
                mask_min_wavelength_um = min_wavelength_um
            if max_wavelength_um is None:
                mask_max_wavelength_um = float("inf")
            else:
                mask_max_wavelength_um = max_wavelength_um

            wavelength_mask = (mask_min_wavelength_um <= self.wavelength_um) & \
                              (self.wavelength_um <= mask_max_wavelength_um)
            wavelength_um = self.wavelength_um[wavelength_mask]
            flux = self.flux[wavelength_mask]
            if self.flux_error is None:
                flux_error = None
            else:
                flux_error = self.flux_error[wavelength_mask]
        else:
            wavelength_um = self.wavelength_um
            flux = self.flux
            flux_error = self.flux_error
        # Calculations
        min_wavelength_um = float(np.nanmin(wavelength_um))
        max_wavelength_um = float(np.nanmax(wavelength_um))
        resolution_um = (max_wavelength_um - min_wavelength_um) / len(wavelength_um)
        min_wl_for_handle = str(int(np.round(min_wavelength_um * 1000.0))) + "nm"
        max_wl_for_handle = str(int(np.round(max_wavelength_um * 1000.0))) + "nm"
        range_str = min_wl_for_handle + "_" + max_wl_for_handle

        # file name and directory determination
        if not os.path.isdir(plot_dir):
            os.mkdir(plot_dir)
        if plot_file_name is None:
            plot_file_name = os.path.join(plot_dir, self.object_pop_name + "_" + self.set_type + "_" + range_str)
        # hitran lines
        if show_hitran_lines:
            hitran_this_plot = Hitran(auto_load=False)
            hitran_this_plot.receive(data=self.hitran_lines)
            hitran_lines = hitran_this_plot.get_lines(min_wavelength_um=min_wavelength_um,
                                                      max_wavelength_um=max_wavelength_um).ordered_data
        else:
            hitran_lines = []

        # y-label that is dependant on a spectrum's options
        if self.flux_is_calibrated:
            y_label = r"Flux (erg $s^{-1} cm^{-2}$)"
        else:
            y_label = "Flux (unitless)"

        # plot boundaries
        flux_max = np.nanmax(flux[flux != float("inf")])
        flux_min = np.nanmin(flux[flux != float("-inf")])
        if flux_min == float('nan') or flux_max == float('nan'):
            raise ValueError("No real values in the flux for spectrum at: " + str(self.file_path))
        elif flux_max == flux_min:
            raise ValueError("Only a single real value, " + str(flux_max) +
                             ", in the flux for spectrum at: " + str(self.file_path))
        diff = flux_max - flux_min
        top_margin = 0.05
        bot_margin = 0.05
        ymax = flux_max + (diff * top_margin)
        ymin = flux_min - (diff * bot_margin)

        # data and data display options
        x_axis_all.append(wavelength_um)
        y_axis_all.append(flux)
        ls_all.append("-")
        line_widths_all = [primary_line_width]
        if show_error_bars and flux_error is not None:
            y_errors_all = [flux_error]
        else:
            y_errors_all = [None]
        colors_all = [color]
        legend_lines = [mlines.Line2D([], [], color=colors_all[0], ls=ls_all[0],
                                      lw=primary_line_width, marker=fmt, markersize=markersize,
                                      markerfacecolor=colors_all[0], alpha=alpha,
                                      label='Primary Spectrum')]
        # Hitran lines
        hitran_line_width = 0.5
        text_xy = []
        texts = []
        texts_colors = []
        if show_hitran_lines:
            hitran_available_ls = default_ls[1:]
            split_dict = hitran_line_split(hitran_lines)
            for index, key in enumerate(sorted(split_dict.keys())):
                molecule, isotopologue = key
                hitran_color = isotopologue_to_color[isotopologue]
                hitran_ls = hitran_available_ls[index % len(hitran_available_ls)]
                legend_lines.append(mlines.Line2D([], [], color=hitran_color, ls=hitran_ls,
                                                  linewidth=hitran_line_width, marker=fmt, markersize=markersize,
                                                  markerfacecolor=hitran_color, alpha=alpha,
                                                  label=str(isotopologue)))
                text_y = flux_max - (diff * (float(index) / float(len(split_dict))))
                for hitran_line in split_dict[key]:
                    wl = hitran_line.wavelength_um
                    x_axis_all.append((wl, wl))
                    y_axis_all.append((ymax, ymin))
                    ls_all.append(hitran_ls)
                    colors_all.append(hitran_color)
                    line_widths_all.append(hitran_line_width)
                    text_xy.append((wl, text_y))
                    texts.append(hitran_line.transition)
                    texts_colors.append(hitran_color)

        # top velocity axis for the plots
        if zero_velocity_wavelength_um is None:
            self.make_velocity_axis(zero_velocity_wavelength_um=min_wavelength_um)
        else:
            self.make_velocity_axis(zero_velocity_wavelength_um=zero_velocity_wavelength_um)
        top_x_axis_label = "Velocity (km/s) relative to " + str(self.zero_velocity_wavelength_um) + r" $\mu$m"

        # These functions make the double x-axis tick labels simpler
        def to_vel(wavelength_um):
            return um_to_vel(wavelength_um=wavelength_um, zero_velocity_wavelength_um=self.zero_velocity_wavelength_um)

        def to_um(velocity_kmps):
            return vel_to_um(velocity_kmps=velocity_kmps, zero_velocity_wavelength_um=self.zero_velocity_wavelength_um)
        top_x_funcs = (to_vel, to_um)
        #  starting to plot things
        if verbose:
            print('Starting the SpExoDisks Spectra plotter...')
        fig = plt.figure(figsize=(x_fig_size, y_fig_size))
        ax = fig.add_axes((left, bottom,  right - left, top - bottom), frameon=frame_on)
        # plot the lists of data, spectra and Hitran lines
        for x_data, y_data, color, ls, y_error, line_width \
                in zip_longest(x_axis_all, y_axis_all, colors_all, ls_all, y_errors_all, line_widths_all):
            if y_error is None:
                ax.plot(x_data, y_data, linestyle=ls, color=color,
                        linewidth=line_width, marker=fmt, markersize=markersize,
                        markerfacecolor=color, alpha=alpha)
            else:
                ax.errorbar(x_data, y_data, yerr=y_error,
                            marker=error_maker, color=color, capsize=error_cap_size,
                            linestyle=error_ls, elinewidth=error_liw)
        # now we will add the title and x and y axis labels
        ax.set_title(title)
        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)
        # now we will make the legend (do_legend is True)
        # call the legend command
        ax.legend(handles=legend_lines, loc=legend_loc,
                  numpoints=legend_num_points, handlelength=legend_handle_length,
                  fontsize=legend_fontsize)
        # now we adjust the x and y limits of the plot
        ax.set_xlim((min_wavelength_um, max_wavelength_um))
        ax.set_ylim((ymin, ymax))
        # tick marks
        if x_ticks_min_number is not None:
            tick_list = get_more_ticks(min_wavelength_um, max_wavelength_um, x_ticks_min_number, ax)
            ax.set_xticks(ticks=tick_list[1:-1])
        # add a second x-axis on the top of the graph.
        bx = ax.secondary_xaxis('top', functions=top_x_funcs)
        if top_x_axis_label is not None:
            bx.set_xlabel(top_x_axis_label)
        # text added to the plot for the Hitran lines
        if transition_text:
            for xy, text_color, text, in zip(text_xy, texts_colors, texts):
                x, y = xy
                ax.text(x, y, text, fontsize=text_fontsize, color=text_color, rotation=text_rotation)
        # here the plot can be saved
        if save:
            if do_pdf:
                plot_file_name += '.pdf'
            else:
                plot_file_name += '.png'
            if verbose:
                print('  saving the plot:', plot_file_name)
            plt.savefig(plot_file_name)
        # here the plot can be shown
        if show:
            if verbose:
                print('  showing the plot in a pop up window')
            plt.show()
        # close the figure and free up the memory
        plt.close(fig=fig)
        # this is needed to stop a memory leak in large loops. (possibly from the 2nd axis)
        gc.collect()
        if verbose:
            print("  ...figure closed.")

    def write_txt(self, single_object, spectrum_handle=None):
        if spectrum_handle is not None:
            self.output_txt_filename = os.path.join(os.path.dirname(self.output_filename),
                                                    f'{spectrum_handle.lower()}.txt')
        section_separation = "\n% "
        # Section: Object Names and Observation Date
        file_text = [section_separation[-2:] + "Object Names and Observation Date", "Popular Object Name: " +
                     single_object.pop_name]
        star_names_line = "Simbad Object Name(s): "
        object_names_dict = single_object.object_names_dict
        for star_name_type in sorted(object_names_dict.keys()):
            for string_name in sorted([StringStarName((star_name_type, star_id)).string_name
                                       for star_id in object_names_dict[star_name_type]]):
                star_names_line += string_name + "|"
        file_text.append(star_names_line[:-1])
        if self.observation_date is None:
            file_text.append("Observation Date: Not available")
            file_text.append("Julian Observation Date: Not available")
        else:
            file_text.append("Observation Date: " + str(self.observation_date))
            file_text.append("Julian Observation Date: " + str(get_julian_datetime(self.observation_date)))
        object_params = single_object.object_params
        available_params = set(object_params.keys())
        if 'ra_epochJ2000' in available_params and 'dec_epochJ2000' in available_params:
            ra_epochJ2000_deg = None
            dec_epochJ2000_deg = None
            for preference in ['Gaia Data Release 2', 'Gaia Data Release 1']:
                if ra_epochJ2000_deg is None:
                    for single_param in object_params['ra_epochJ2000']:
                        if single_param.ref == preference:
                            ra_epochJ2000_deg = single_param.value
                            break
                if dec_epochJ2000_deg is None:
                    for single_param in object_params['dec_epochJ2000']:
                        if single_param.ref == preference:
                            dec_epochJ2000_deg = single_param.value
                            break
            if ra_epochJ2000_deg is not None and dec_epochJ2000_deg is not None:
                c = SkyCoord(ra=ra_epochJ2000_deg * u.deg, dec=dec_epochJ2000_deg,
                             frame=FK5(equinox='J2000'), unit="deg")
                file_text.append("J2000 Right Ascension and Declination (hms dms): " + c.to_string('hmsdms'))

        # Section: Reference and Citation
        file_text.append(section_separation + "Reference and Citation")
        file_text.append("Principal Investigator for Primary Spectrum: " + self.pi)
        file_text.append("Reference for Primary Spectrum: " + self.reference)
        file_text.append("Spectrograph: " + self.set_type.upper())
        if self.data_reduction_by is not None:
            file_text.append("Primary spectrum Data Reduction by: " + self.data_reduction_by)
        if self.aor_key is not None:
            file_text.append("Spitzer AOR Key: " + str(self.aor_key))
        if self.hitran_lines is not None:
            file_text.append("Reference for Spectroscopic Line Data: Hitran2016 molecular spectroscopic database " +
                             "(Gordon et al. 2017) at hitran.org")
        if self.line_fluxes is not None:
            file_text.append("Reference for Line-Fluxes Measurements: " + spexodisks_ref)
        if self.stacked_lines is not None:
            file_text.append("Reference for Stacked-Line Profiles: " + spexodisks_ref)
        file_text.append("Data Prepared and Organized by: " + spexodisks_ref)
        file_text.append("SpExoDisks Backend written by: " + caleb_ref)

        # Section: Online Database

        file_text.append(section_separation + "Online Database")
        file_text.append("Downloadable: " + str(self.downloadable))

        # Section: Spectrum Context
        file_text.append(section_separation + "Spectrum Context")
        if self.flux_is_calibrated:
            file_text.append("Spectral Flux: Calibrated (Jansky)")
        else:
            file_text.append("Spectral Flux: Not Calibrated (unitless)")
        file_text.append("Spectral Wavelength/Velocity Reference Frame: " + str(self.ref_frame).upper())
        file_text.append("Wavelength Units: um=10^-6 meters")
        file_text.append("Wavelength Range: (" + str(self.min_wavelength_um) + " um, " +
                         str(self.max_wavelength_um) + " um)")

        # Section: Flux Calibration
        if self.flux_cals:
            file_text.append(section_separation + "Flux Calibration")
            if self.stacked_lines is not None and self.line_fluxes is not None:
                calibrated_items = "# The Primary Spectrum, Stack Line Spectra, and Measured Line Fluxes "
                are_is = 'are '
            elif self.stacked_lines is not None:
                calibrated_items = "# The Primary Spectrum and Stack Line Spectra "
                are_is = 'are '
            elif self.line_fluxes is not None:
                calibrated_items = "# The Primary Spectrum and Measured Line Fluxes "
                are_is = 'are '
            else:
                calibrated_items = "# The Primary Spectrum "
                are_is = 'is '
            if self.flux_is_calibrated:
                file_text.append(calibrated_items + are_is + 'Flux Calibrated using the following')
            else:
                file_text.append(calibrated_items + 'can be calibrated to (Jansky) using the following')
            flux_cal_header = "flux_cal,flux_cal_error,wavelength_um,ref"
            flux_cal_body = [str(flux_cal.flux) + "," + str(flux_cal.err) + "," +
                             str(flux_cal.um) + "," + str(flux_cal.ref) for flux_cal in self.flux_cals]
            file_text.append(flux_cal_header)
            file_text.extend(flux_cal_body)

        # Section: Spectroscopic Line Data
        if self.hitran_lines:
            file_text.append(section_separation + "Spectroscopic Line Data")
            file_text.append(hitran_line_header)
            file_text.extend([str(hitran_line) for hitran_line in self.hitran_lines])

        # Section: Primary Spectrum
        file_text.append(section_separation + "Primary Spectrum")
        if self.flux_error is None:
            prime_header = 'wavelength,velocity_kmps,flux'
            prime_body = [str(single_wavelength) + ',' + str(single_vel) + "," + str(single_flux)
                          for single_wavelength, single_vel, single_flux
                          in zip(self.wavelength_um, self.velocity_kmps, self.flux)]

        else:
            prime_header = 'wavelength,velocity_kmps,flux,flux_error'
            prime_body = [str(single_wavelength) + ',' + str(single_vel) + ","
                          + str(single_flux) + "," + str(single_flux_error)
                          for single_wavelength, single_vel, single_flux, single_flux_error
                          in zip(self.wavelength_um, self.velocity_kmps, self.flux, self.flux_error)]
        file_text.append(prime_header)
        file_text.extend(prime_body)

        # Section: Measured Line Fluxes
        if self.line_fluxes is not None:
            file_text.append(section_separation + "Measured Line Fluxes")
            total_sets_of_line_fluxes = len(self.line_fluxes)
            ordered_sets_of_flux_lines = sorted([self.line_fluxes[set_key] for set_key in self.line_fluxes.keys()],
                                               key=attrgetter("upper_level", "lower_level"))
            for index, line_flux_set in enumerate(ordered_sets_of_flux_lines):

                file_text.append("@ Measured Line Fluxes for " + line_flux_set.isotopologue +
                                 " (v=" + str(line_flux_set.upper_level) + "-" + str(line_flux_set.lower_level) + ")")
                file_text.append(line_flux_header)
                file_text.extend([str(measured_flux_line) for measured_flux_line in line_flux_set.flux_data])
                if index + 1 != total_sets_of_line_fluxes:
                    file_text.append("")

        # Section: Stacked Line Spectra
        if self.stacked_lines is not None:
            file_text.append(section_separation + "Stacked Line Spectra")
            total_sets_of_stacked_lines = len(self.stacked_lines)
            ordered_sets_of_stacked_lines = sorted([self.stacked_lines[set_key]
                                                   for set_key in self.stacked_lines.keys()],
                                                   key=attrgetter("upper_level", "lower_level"))
            for index, stacked_line_set in enumerate(ordered_sets_of_stacked_lines):
                file_text.append("@ " + stacked_line_set.description)
                spectrum = stacked_line_set.spectrum
                if spectrum.flux_error is None:
                    stack_header = 'velocity_kmps,flux'
                    stack_body = [str(single_wavelength) + ',' + str(single_flux)
                                  for single_wavelength, single_flux in zip(spectrum.velocity_kmps, spectrum.flux)]

                else:
                    stack_header = 'velocity_kmps,flux,flux_error'
                    stack_body = [str(single_wavelength) + ',' + str(single_flux) + "," + str(single_flux_error)
                                  for single_wavelength, single_flux, single_flux_error
                                  in zip(spectrum.velocity_kmps, spectrum.flux, spectrum.flux_error)]
                file_text.append(stack_header)
                file_text.extend(stack_body)
                if index + 1 != total_sets_of_stacked_lines:
                    file_text.append("")

        # Write the output data
        with open(self.output_txt_filename, 'w') as f:
            for text_line in file_text:
                f.write(text_line + "\n")
        print(f'Wrote Spectrum TXT output file at: {self.output_txt_filename}')

    def write_fits(self, single_object, spectrum_handle=None):
        hdu_list = []
        if spectrum_handle is not None:
            self.output_fits_filename = os.path.join(os.path.dirname(self.output_filename),
                                                     f'{spectrum_handle.lower()}.fits')
        """
        Static HDU Extensions
        """
        # # The SpExoDisks Header, hdul[0]
        spexod_header = fits.Header()
        # add all the star names to the header
        spexod_header['POPNAME'] = single_object.pop_name
        spexod_header['SIMBAD'] = single_object.main_simbad_name
        object_names_dict = single_object.object_names_dict
        for star_name_type in sorted(object_names_dict.keys()):
            name_counter = 1
            for string_name in sorted([StringStarName((star_name_type, star_id)).string_name
                                       for star_id in object_names_dict[star_name_type]]):
                spexod_header[f'{star_name_type.upper()}{name_counter}'] = string_name
                name_counter += 1
        # Add other SIMBAD data
        spexod_header['SIMBLINK'] = single_object.simbad_link
        spexod_header['SIMBBIB'] = single_object.main_simbad_bibcode
        # add selected stellar parameters
        object_params = single_object.object_params
        available_params = set(object_params.keys())
        if 'ra_epochJ2000' in available_params and 'dec_epochJ2000' in available_params:
            ra_epochJ2000_deg = None
            dec_epochJ2000_deg = None
            ra_ref = None
            dec_ref = None
            for preference in ['Gaia Data Release 2', 'Gaia Data Release 1']:
                if ra_epochJ2000_deg is None:
                    for single_param in object_params['ra_epochJ2000']:
                        if single_param.ref == preference:
                            ra_ref = single_param.ref
                            ra_epochJ2000_deg = single_param.value
                            break
                if dec_epochJ2000_deg is None:
                    for single_param in object_params['dec_epochJ2000']:
                        if single_param.ref == preference:
                            dec_ref = single_param.ref
                            dec_epochJ2000_deg = single_param.value
                            break
            if ra_epochJ2000_deg is not None and dec_epochJ2000_deg is not None:
                c = SkyCoord(ra=ra_epochJ2000_deg * u.deg, dec=dec_epochJ2000_deg,
                             frame=FK5(equinox='J2000'), unit="deg")
                spexod_header['SKYCOORD'] = "J2000 Right Ascension and Declination (hms dms): " + c.to_string('hmsdms')
                spexod_header['RAJ2000'] = ra_epochJ2000_deg
                spexod_header['RAREF'] = ra_ref
                spexod_header['RAUNITS'] = 'degrees'
                spexod_header['DECJ2000'] = dec_epochJ2000_deg
                spexod_header['DECREF'] = dec_ref
                spexod_header['DECUNITS'] = 'degrees'
        # automatically add the rest of the stellar parameters
        for param_name in sorted(self.stellar_params_for_fits.intersection(set(object_params.keys()))):
            param_count = 1
            param_header_str = self.stellar_params_to_fits_name[param_name]
            for single_param in sorted(object_params[param_name],  key=attrgetter('value')):
                spexod_header[f'{param_header_str}{param_count}'] = single_param.value
                if single_param.err is not None:
                    spexod_header[f'{param_header_str}ERR{param_count}'] = single_param.err
                if single_param.ref is not None:
                    spexod_header[f'{param_header_str}REF{param_count}'] = single_param.ref
                if single_param.units is not None:
                    spexod_header[f'{param_header_str}UNI{param_count}'] = single_param.units
                param_count += 1
        # Add the spectrum data
        spexod_header['INSTNAME'] = self.inst_name
        spexod_header['WAVEMIN'] = self.min_wavelength_um
        spexod_header['WAVEMAX'] = self.max_wavelength_um
        spexod_header['WAVESTEP'] = self.resolution_um
        spexod_header['WAVEUNIT'] = "Wavelength Units: um=10^-6 meters"
        spexod_header['OBSDATE'] = str(self.observation_date)
        spexod_header['OBSJUL'] = "Julian Observation Date: " + str(get_julian_datetime(self.observation_date))
        spexod_header['REFFRAME'] = "Spectral Wavelength/Velocity Reference Frame: " + str(self.ref_frame).upper()
        spexod_header['SPECREF'] = "Reference for Primary Spectrum: " + unidecode.unidecode(self.reference)
        spexod_header['DATAREF'] = "Data Prepared and Curated by: " + spexodisks_ref
        spexod_header['DATASCI'] = "The SpExoDisks Data Scientist and Database Architect is " + caleb_ref
        cal_statement = fluxcal_statement(flux_is_calibrated=self.flux_is_calibrated,
                                          has_stacked_lines=self.stacked_lines is not None,
                                          has_line_fluxes=self.line_fluxes is not None)
        spexod_header['CALSTATE'] = cal_statement
        if self.flux_is_calibrated:
            spexod_header['FLUXCAL'] = "Spectral Flux: Calibrated (Jansky)"
        else:
            spexod_header['FLUXCAL'] = "Spectral Flux: Not Calibrated (unitless)"
        if self.data_reduction_by is not None:
            spexod_header['REDUCREF'] = "Primary spectrum Data Reduction by: " + self.data_reduction_by
        if self.line_fluxes is not None:
            spexod_header['HITRANRF'] = "Reference for Spectroscopic Line Data: Hitran2016 molecular spectroscopic " + \
                                        "database (Gordon et al. 2017) at hitran.org"
        if self.line_fluxes is not None:
            spexod_header['LINEFLUX'] = "Reference for Line-Fluxes Measurements: " + spexodisks_ref
        if self.stacked_lines is not None:
            spexod_header['STACKLIN'] = "Reference for Stacked-Line Profiles: " + spexodisks_ref
        if self.pi is not None:
            spexod_header['PI'] = unidecode.unidecode(self.pi)
        if self.aor_key is not None:
            spexod_header['AORKEY'] = "Spitzer AOR Key: " + str(self.aor_key)

        # make a header-only primary HDU
        hdu_primary = fits.PrimaryHDU(header=spexod_header)
        hdu_list.append(hdu_primary)

        # # The spectrum table, hudl[1]
        hdu_spectrum = make_spectrum_hdu(x_column=self.wavelength_um,
                                         flux=self.flux, flux_error=self.flux_error, name="Primary Spectrum")
        hdu_list.append(hdu_spectrum)

        # # The original header, hudl[2]
        original_header = fits.Header(self.header_original)
        hdu_original_header = fits.ImageHDU(name='observation header')
        for key in list(original_header):
            if key in self.header_keys_to_remove:
                original_header.remove(key)
        hdu_original_header.header.extend(original_header)
        hdu_list.append(hdu_original_header)
        """
        Dynamic HDU Extensions
        """
        # # Hitran Line - dynamics extensions - one HDU extension per Molecule
        if self.hitran_lines:
            # sort the Hitran by molecule and determine the lines available for this spectrum
            hitran_lines_for_fits = {}
            for h_line in self.hitran_lines:
                this_molecule = h_line.molecule.lower()
                if this_molecule in self.allowed_hitran_molecules:
                    if this_molecule not in hitran_lines_for_fits.keys():
                        hitran_lines_for_fits[this_molecule] = []
                    hitran_lines_for_fits[this_molecule].append(h_line)
            # add per-molecule table fits extensions
            for molecule in sorted(hitran_lines_for_fits.keys()):
                line_list = hitran_lines_for_fits[molecule]
                table_values = []
                dtypes_for_table = self.__getattribute__(f'{molecule}_dtypes')
                table_header = list(dtypes_for_table.keys())
                for h_line in line_list:
                    h_line_dict = make_hl_dict(hitran_line=h_line)
                    h_line_values = tuple([h_line_dict[column_name] for column_name in table_header])
                    table_values.append(h_line_values)
                molecule_array = np.array(table_values, dtype=[(column_name, dtypes_for_table[column_name])
                                                               for column_name in table_header])
                # make the HDU for this molecule
                hdu_this_molecule = fits.BinTableHDU(data=molecule_array, name=f'{molecule.upper()} Hitran Line')
                # header additions
                hdu_this_molecule.header['HITRANRF'] = "Reference for Spectroscopic Line Data: Hitran2016 " + \
                                                       "molecular spectroscopic database (Gordon et al. 2017) " + \
                                                       "at hitran.org"
                hdu_this_molecule.header['MOLETYPE'] = f"{molecule.upper()}"
                hdu_this_molecule.header['DYNMTYPE'] = f"hitran"
                hdu_list.append(hdu_this_molecule)
        # # flux calibrations
        if self.flux_cals:
            fluxcal_header = list(self.fluxcal_dtypes.keys())
            fluxcal_values = []
            for flux_cal in self.flux_cals:
                this_fluxcal_dict = flux_cal_to_dict(flux_cal)
                this_flux_values = tuple([this_fluxcal_dict[fluxcal_column] for fluxcal_column in fluxcal_header])
                fluxcal_values.append(this_flux_values)
            fluxcal_array = np.array(fluxcal_values, dtype=[(column_name, self.fluxcal_dtypes[column_name])
                                                            for column_name in fluxcal_header])
            hdu_fluxcal = fits.BinTableHDU(data=fluxcal_array, name=f'Flux Calibrations')
            # header additions
            hdu_fluxcal.header['DYNMTYPE'] = 'fluxcal'
            if self.flux_is_calibrated:
                hdu_fluxcal.header['FLUXCAL'] = "Spectral Flux: Calibrated (Jansky)"
            else:
                hdu_fluxcal.header['FLUXCAL'] = "Spectral Flux: Not Calibrated (unitless)"
            hdu_fluxcal.header['CALSTATE'] = cal_statement
            hdu_list.append(hdu_fluxcal)

        # # Measured Line Fluxes
        if self.line_fluxes:
            ordered_sets_of_flux_lines = sorted([self.line_fluxes[set_key] for set_key in self.line_fluxes.keys()],
                                                key=attrgetter("upper_level", "lower_level"))
            for line_flux_set in ordered_sets_of_flux_lines:
                isotopologue = line_flux_set.isotopologue
                molecule = isotopologue_to_molecule[isotopologue]
                upper_level = line_flux_set.upper_level
                lower_level = line_flux_set.lower_level
                hitran_dtypes = self.__getattribute__(f'{molecule.lower()}_dtypes')
                header_list_line_flux = list(self.lineflux_dtypes.keys())
                header_list_line_flux_hitran = list(hitran_dtypes.keys())
                dtypes_for_line_flux = {}
                dtypes_for_line_flux.update(self.lineflux_dtypes)
                dtypes_for_line_flux.update(hitran_dtypes)
                full_header_list = header_list_line_flux + header_list_line_flux_hitran
                line_flux_values = []
                for line_flux in line_flux_set.flux_data:
                    line_flux_dict = {lineflux_column: line_flux.__getattribute__(lineflux_column)
                                      for lineflux_column in header_list_line_flux}
                    line_flux_dict.update(make_hl_dict(hitran_line=line_flux.hitran_line))
                    h_line_values = tuple([line_flux_dict[column_name] for column_name in full_header_list])
                    line_flux_values.append(h_line_values)
                line_flux_array = np.array(line_flux_values, dtype=[(column_name, dtypes_for_line_flux[column_name])
                                                                    for column_name in full_header_list])
                lineflux_label = lineflux_name(isotopologue, upper_level, lower_level)
                hdu_lineflux = fits.BinTableHDU(data=line_flux_array, name=f'Line fluxes for {lineflux_label}')
                # header additions
                hdu_lineflux.header['DYNMTYPE'] = 'lineflux'
                hdu_lineflux.header['MOLECULE'] = molecule
                hdu_lineflux.header['ISOTOPOL'] = isotopologue
                hdu_lineflux.header['UPPERLVL'] = upper_level
                hdu_lineflux.header['LOWERLVL'] = lower_level
                hdu_lineflux.header['FLXTRANS'] = lineflux_label
                hdu_list.append(hdu_lineflux)

        # # Stacked Line Spectra
        if self.stacked_lines:
            ordered_sets_of_stacked_lines = sorted([self.stacked_lines[set_key]
                                                    for set_key in self.stacked_lines.keys()],
                                                   key=attrgetter("upper_level", "lower_level"))
            for stacked_line_set in ordered_sets_of_stacked_lines:
                stackedlines_statement = stacked_line_set.description
                spectrum = stacked_line_set.spectrum
                hdu_spectrum_stacked = make_spectrum_hdu(x_column=spectrum.velocity_kmps,
                                                         flux=spectrum.flux, flux_error=spectrum.flux_error,
                                                         name=stackedlines_statement,
                                                         velocity_mode=True)
                # header additions
                isotopologue = stacked_line_set.isotopologue
                molecule = isotopologue_to_molecule[isotopologue]
                upper_level = stacked_line_set.upper_level
                lower_level = stacked_line_set.lower_level
                hdu_spectrum_stacked.header['DYNMTYPE'] = 'stackedline'
                hdu_spectrum_stacked.header['MOLECULE'] = molecule
                hdu_spectrum_stacked.header['ISOTOPOL'] = isotopologue
                hdu_spectrum_stacked.header['UPPERLVL'] = upper_level
                hdu_spectrum_stacked.header['LOWERLVL'] = lower_level
                hdu_spectrum_stacked.header['STKTRANS'] = lineflux_name(isotopologue, upper_level, lower_level)
                hdu_list.append(hdu_spectrum_stacked)

        # # write the assembled fits file
        hdul = fits.HDUList(hdu_list)
        hdul.writeto(self.output_fits_filename, overwrite=True, output_verify='fix')
        print(f'Wrote Spectrum FITS output file at: {self.output_fits_filename}')


def set_single_output_spectra(param_dict):
    keys = set(param_dict.keys())
    file, um_min, um_max, set_type, ref, raw_name = None, None, None, None, None, None
    if "file" in keys:
        file = param_dict['file']
        if 'um_min' in keys:
            um_min = param_dict['um_min']
        if 'um_max' in keys:
            um_max = param_dict['um_max']
        if 'set_type' in keys:
            set_type = param_dict['set_type']
        if 'ref' in keys:
            ref = param_dict['ref']
        if 'raw_name' in keys:
            raw_name = param_dict['raw_name']
        return SpectraSummary(file=file, um_min=um_min, um_max=um_max, set_type=set_type, ref=ref, raw_name=raw_name)
    else:
        raise ValueError("A key named 'file' is needed to set a parameter")


class SpectraSummary(NamedTuple):
    """ Represents all the data that goes in to the out file for a single spectrum"""
    file: str
    um_min: Optional[float] = None
    um_max: Optional[float] = None
    set_type: Optional[str] = None
    ref: Optional[str] = None
    raw_name: Optional[str] = None
