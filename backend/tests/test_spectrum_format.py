"""
Unit tests for science/analyze/spectrum_format.py (needs numpy, no database):
    cd backend && python3 -m unittest discover tests
"""
import unittest

import numpy as np

from science.analyze.spectrum_format import format_spectrum, singleton_mask


class FormatSpectrumTests(unittest.TestCase):
    def test_contiguous_spectrum_is_unchanged(self):
        # steps of 0.1% of the bandwidth, well under the 1% gap rule (an 11-point spectrum would be all gaps)
        wavelength = np.linspace(1.0, 2.0, 1001)
        flux = np.ones(1001)
        out = format_spectrum(wavelength, flux)
        np.testing.assert_allclose(out['wavelength_um'], wavelength)
        self.assertFalse(np.isnan(out['flux']).any())

    def test_null_is_inserted_in_the_middle_of_every_gap(self):
        # three segments: 1.0-1.1, 2.0-2.1, 3.0-3.1 (bandwidth 2.1, gaps of 0.9 >> 1% of the bandwidth)
        segments = [np.linspace(1.0, 1.1, 11), np.linspace(2.0, 2.1, 11), np.linspace(3.0, 3.1, 11)]
        wavelength = np.concatenate(segments)
        flux = np.ones(len(wavelength))
        out = format_spectrum(wavelength, flux)
        self.assertEqual(len(out), len(wavelength) + 2)
        nulls = out[np.isnan(out['flux'])]
        # before the fix the second null landed at the wrong wavelength, below its left neighbour
        np.testing.assert_allclose(nulls['wavelength_um'], [1.55, 2.55])
        self.assertTrue((np.diff(out['wavelength_um']) > 0).all(), "wavelengths stay strictly increasing")

    def test_bad_flux_values_and_singletons_are_dropped(self):
        wavelength = np.array([1.0, 1.01, 1.02, 1.03, 1.04, 1.05, 1.06, 1.07, 1.08, 1.09, 1.10, 5.0])
        flux = np.array([1.0, np.nan, 1.0, np.inf, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0])
        out = format_spectrum(wavelength, flux)
        # 2 bad values and the isolated point at 5.0 are gone, no gap remains
        self.assertEqual(len(out), 9)
        self.assertFalse(np.isnan(out['flux']).any())

    def test_all_bad_values_raise_a_clear_error(self):
        with self.assertRaises(ValueError):
            format_spectrum([1.0, 2.0], [np.nan, np.nan])

    def test_singleton_mask(self):
        mask = singleton_mask(np.array([1.0, 1.1, 1.2, 5.0]), bandwidth_for_null_um=0.5)
        self.assertEqual(mask.tolist(), [True, True, True, False])


if __name__ == "__main__":
    unittest.main()
