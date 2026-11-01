"""
Prepare a spectrum for the per-spectrum SQL tables: drop bad values and isolated points, and insert a
null point into every large wavelength gap, so the plot shows separate segments instead of a line
across the gap.

Only numpy, no database: tests/test_spectrum_format.py runs this without MySQL.
"""
from typing import List, Optional

import numpy as np

null_val = np.nan
# a gap larger than this fraction of the spectrum's bandwidth separates two segments
bandwidth_fraction_for_null_default = 0.01


def is_good_num(a_float):
    if any((np.isnan(a_float), np.isinf(a_float))):
        return False
    return True


def remove_bad_nums(wavelength_um: List[float], flux: List[float], flux_error: Optional[List[float]] = None):
    if flux_error is None:
        flux_error = [null_val] * len(flux)
    for wavelength_um, flux, flux_error in zip(wavelength_um, flux, flux_error):
        if is_good_num(flux):
            if not is_good_num(flux_error):
                flux_error = null_val
            yield wavelength_um, flux, flux_error


def singleton_mask(wavelength_um: np.array,
                   bandwidth_for_null_um: float = bandwidth_fraction_for_null_default):
    wavelength_um_step = np.array(wavelength_um[1:] - wavelength_um[:-1])
    # the first and last points have no neighbor on one side: an infinite step there
    left_side_steps = np.concatenate((np.array([np.inf]), wavelength_um_step), axis=0)
    right_side_steps = np.concatenate((wavelength_um_step, np.array([np.inf])), axis=0)
    # keep a point when at least one neighbor is close ("&" dropped the real data points on both
    # sides of every gap as well, not only isolated points)
    return (left_side_steps < bandwidth_for_null_um) | (right_side_steps < bandwidth_for_null_um)


def format_spectrum(wavelength_um: List[float], flux: List[float], flux_error: Optional[List[float]] = None,
                    bandwidth_fraction_for_null: float = bandwidth_fraction_for_null_default):
    # replacement here to save memory in the function call
    good_points = list(remove_bad_nums(wavelength_um, flux, flux_error))
    if not good_points:
        raise ValueError("the spectrum has no finite flux values")
    wavelength_um, flux, flux_error = zip(*good_points)
    wavelength_um = np.array(wavelength_um)
    spectrum_bandwidth_um = max(wavelength_um) - min(wavelength_um)
    bandwidth_for_null_um = spectrum_bandwidth_um * bandwidth_fraction_for_null
    # remove singletons, points isolated in wavelength from both neighbors by more than bandwidth_for_null_um
    true_is_non_singleton = singleton_mask(wavelength_um, bandwidth_for_null_um)
    wavelength_um = wavelength_um[true_is_non_singleton]
    flux = np.array(flux)[true_is_non_singleton]
    flux_error = np.array(flux_error)[true_is_non_singleton]
    # For large steps in wavelength, (re)insert a null value to break up the spectrum into segments of
    # contiguous data. All gaps are found on the unmodified array and inserted in one call: inserting one
    # at a time while reading positions from the growing array put the nulls at the wrong wavelengths.
    wavelength_um_step = wavelength_um[1:] - wavelength_um[:-1]
    gap_indices = np.flatnonzero(wavelength_um_step > bandwidth_for_null_um)   # gap between i and i + 1
    wavelength_um_null = wavelength_um[gap_indices] + (wavelength_um_step[gap_indices] / 2.0)
    wavelength_um = np.insert(wavelength_um, gap_indices + 1, wavelength_um_null)
    flux = np.insert(flux, gap_indices + 1, null_val)
    flux_error = np.insert(flux_error, gap_indices + 1, null_val)
    return np.array(list(zip(wavelength_um, flux, flux_error)),
                    dtype=[('wavelength_um', np.float64), ('flux', np.float32), ('flux_error', np.float32)])
