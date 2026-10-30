"""
Unit tests that need no database:  cd backend && python3 -m unittest discover tests
"""
import unittest
from datetime import datetime, timezone, timedelta

from science.db.sql_values import quote_identifier, qualified_name, placeholders, sql_value


class IdentifierTests(unittest.TestCase):
    def test_valid_names_are_back_quoted(self):
        self.assertEqual(quote_identifier("spectra"), "`spectra`")
        self.assertEqual(quote_identifier("12c16o"), "`12c16o`")
        self.assertEqual(qualified_name("spectra", "new_spexodisks"), "`new_spexodisks`.`spectra`")

    def test_injection_attempts_are_rejected(self):
        for bad in ("spectra; DROP DATABASE x", "a`b", "a.b", "a b", "", "x" * 65, None):
            with self.assertRaises(ValueError, msg=repr(bad)):
                quote_identifier(bad)

    def test_placeholders(self):
        self.assertEqual(placeholders(1), "(%s)")
        self.assertEqual(placeholders(3), "(%s, %s, %s)")


class ValueTests(unittest.TestCase):
    def test_strings_are_passed_through_unchanged(self):
        # quoting is the client's job, the value is a parameter
        self.assertEqual(sql_value("O'Brien"), "O'Brien")
        self.assertEqual(sql_value("x'); DROP DATABASE spexodisks; --"), "x'); DROP DATABASE spexodisks; --")

    def test_numbers(self):
        self.assertEqual(sql_value(True), 1)
        self.assertEqual(sql_value(False), 0)
        self.assertEqual(sql_value(7), 7)
        self.assertEqual(sql_value(2.5), 2.5)
        self.assertIsNone(sql_value(float("nan")))
        self.assertIsNone(sql_value(float("inf")))
        self.assertIsNone(sql_value(None))

    def test_numpy_numbers_become_python_numbers(self):
        try:
            import numpy
        except ImportError:
            self.skipTest("numpy is not installed")
        self.assertEqual(sql_value(numpy.int64(3)), 3)
        self.assertIs(type(sql_value(numpy.int64(3))), int)
        self.assertEqual(sql_value(numpy.float32(1.5)), 1.5)
        self.assertIs(type(sql_value(numpy.float32(1.5))), float)
        self.assertIsNone(sql_value(numpy.float64("nan")))

    def test_aware_datetimes_become_naive_utc(self):
        aware = datetime(2024, 3, 1, 12, 0, tzinfo=timezone(timedelta(hours=-5)))
        self.assertEqual(sql_value(aware), datetime(2024, 3, 1, 17, 0))
        naive = datetime(2024, 3, 1, 12, 0)
        self.assertEqual(sql_value(naive), naive)

    def test_unknown_types_raise(self):
        with self.assertRaises(TypeError):
            sql_value([1, 2])


if __name__ == "__main__":
    unittest.main()
