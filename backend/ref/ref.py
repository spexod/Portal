import os
import toml
from warnings import warn
from datetime import datetime

# References used in the SpExoDisks Catalog
now = datetime.now()
today_str = F"{'%04i' % now.year}_{'%02i' % now.month}_{'%02i' % now.day}"
spexodisks_ref = 'A Banzatti, C Wheeler, SpExoDisks (' + str(now.month) + "-" + str(now.year) + ")"
andrea_ref = "A Banzatti"
caleb_ref = "Dr Caleb Wheeler (chw3k5@gmail.com), Underground Instruments"
nirspec_flux_cal_ref = "Same as Primary Spectrum"
# Instrument metadata

instrument_metadata = [
    # 'handle',    'long_name',   'short', 'display'
    ( 'crires',   'VLT-CRIRES',  "CRIRES",  True),
    ( 'ishell',  'IRTF-iSHELL',  "iSHELL",  True),
    ('nirspec', 'Keck-NIRSPEC', "NIRSPEC",  True),
    ('spitzer',  'Spitzer-IRS',     "IRS",  True),
    (   'miri',    'JWST-MIRI',    "MIRI",  True),
    (  'visir',    'VLT-VISIR',   "VISIR", False),
    ( 'igrins',       'IGRINS',  "IGRINS",  True),
    (   'spex',    'IRTF-SpeX',    "SpeX", False)
]
web_default_spectrum = 'ishell_4517nm_5240nm_Vstar_V1003_OPH'

# directory tree used by SpExoDisks Database, including folder creation for things in .gitignore
base_dir = os.path.dirname(os.path.realpath(__file__))
star_names_dir = base_dir
try:
    backend_dir = os.path.dirname(base_dir)
except ValueError:
    warn(f'Could not find the SpExoDisks DataScience package directory')
    backend_dir = '/django'
working_dir = os.path.join(backend_dir, "science")
input_data_dir = os.path.join(backend_dir, "data")
uploads_dir = os.path.join(backend_dir, "uploads")
output_dir = os.path.join(backend_dir, "output")
ref_dir = os.path.join(input_data_dir, "reference_data")
spectra_dir = os.path.join(input_data_dir, "spectral_data")
data_pro_dir = os.path.join(input_data_dir, "data_products")
object_params_dir = os.path.join(ref_dir, 'object_params')
flux_cal_dir = os.path.join(ref_dir, "flux_cal")
hitran_dir = os.path.join(ref_dir, "hitran")
plot_dir = os.path.join(data_pro_dir, "plots")
if not os.path.exists(data_pro_dir):
    os.mkdir(data_pro_dir)
if not os.path.exists(plot_dir):
    os.mkdir(plot_dir)

# reference ranking
references_per_parameter_path = os.path.join(ref_dir, 'references_per_parameter.txt')
reference_preference_path = os.path.join(ref_dir, 'reference_preference.txt')

# target files for selecting a subset of stars
target_file_default = os.path.join(working_dir, "load", 'target_list.csv')


# for the simbad Query Class
sb_save_file_name = os.path.join(ref_dir, "simbad_query_data.pkl")
sb_save_coord_file_name = os.path.join(ref_dir, "simbad_coord_data.pkl")
sb_ref_file_name = os.path.join(ref_dir, "simbad_ref_data.psv")
sb_main_ref_file_name = os.path.join(ref_dir, "simbad_main_ref_data.csv")
sb_desired_names = {"2mass", 'gaia dr3', "gaia dr2", "gaia dr1", "hd", "cd", "tyc", "hip", "gj", "hr", "bd", "ids", "tres", "gv",
                    "cs", "ngc", "bps", "ogle", "xo", "v*", "*", "**", 'iras', "hh", 'hbc', "[c91] irs", "[s87b] irs",
                    "[lln92] {irs}", 'wise', 'wds', "chlt", 'wray', "rox", 'wds', "tha"}
sb_bad_star_name_ignore = os.path.join(ref_dir, "bad_starname_ignore.csv")
simbad_reference = "Simbad Database (simbad.u-strasbg.fr/simbad)"
# simbad_reference = "2000,A&AS,143,9 "The SIMBAD astronomical database", Wenger et al."

# for the Tess Input Catalog
tic_ref_filename = os.path.join(ref_dir, "tic_ref.csv")

# key file for syncing data
rsync_key_file = os.path.join(backend_dir, "spexod-us-est-1.pem")

# for the name correction files
annoying_names_filename = os.path.join(ref_dir, "annoying_names.csv")
popular_names_filename = os.path.join(ref_dir, "popular_names.csv")

# Constants used in the SpExoDisks Database
k_h = 6.6260755E-34  # Js
k_c = 299792458.0  # m/s
k_k = 1.380658E-23  # J/K
conv = 1.0e7 / k_c
conv_cmk = k_h * k_c / k_k * 100.0

# for the spectra, when upload to mysql, if gaps in the data are larger, then this fraction of the
# total spectrum bandwidth, then the spectrum will be split into chunks, delineated by a null value
bandwidth_fraction_for_null = 0.002

# Schema Names for the MySQL data output
spexo_schema = 'new_spexodisks'
spectra_schema = 'new_spectra'
stacked_line_schema = 'new_stacked_line'
temp_schema = 'temp'
update_schema_map = [('spexodisks', 'new_spexodisks'), ('spectra', 'new_spectra'),
                     ('stacked_line_spectra', 'new_stacked_line')]  # (to be updated, source)

# SQL metadata types for spectra
sql_spectrum_types = ['set_type', "observation_date", 'pi', 'reference', 'downloadable', 'data_reduction_by', "aor_key",
                      'flux_is_calibrated', "ref_frame", "min_wavelength_um", "max_wavelength_um", "resolution_um",
                      "output_filename"]

# write the user toml for the autostar package
autostar_toml = {'reference_data_dir': ref_dir,
                 'sb_bad_star_name_ignore_filename': sb_bad_star_name_ignore,
                 'sb_main_ref_filename': sb_main_ref_file_name,
                 'sb_save_filename': sb_save_file_name,
                 'sb_save_coord_filename': sb_save_coord_file_name,
                 'sb_ref_filename': sb_ref_file_name,
                 'tic_ref_filename': tic_ref_filename,
                 'annoying_names_filename': annoying_names_filename,
                 'popular_names_filename': popular_names_filename,
                 'sb_desired_names': sb_desired_names}

ref_module_dir = os.path.dirname(os.path.realpath(__file__))
with open(os.path.join(ref_module_dir, "user.toml"), 'w') as f:
    toml.dump(autostar_toml, f)
