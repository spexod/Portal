import pandas as pd

curated = [
    "spexodisks_handle",
    "pop_name",
    "preferred_simbad_name",
    "simbad_link",
    "ra_dec",
    "ra",
    "dec",
    "esa_sky",
    "has_spectra",
    "f0point88mm_value",
    "f0point88mm_err_low",
    "f0point88mm_err_high",
    "f0point88mm_ref",
    "f1point3mm_value",
    "f1point3mm_err_low",
    "f1point3mm_err_high",
    "f1point3mm_ref",
    "dec_epochj2000_value",
    "dec_epochj2000_err_low",
    "dec_epochj2000_err_high",
    "dec_epochj2000_ref",
    "dist_value",
    "dist_err_low",
    "dist_err_high",
    "dist_ref",
    "l_star_value",
    "l_star_err_low",
    "l_star_err_high",
    "l_star_ref",
    "logl_acc_value",
    "logl_acc_err_low",
    "logl_acc_err_high",
    "logl_acc_ref",
    "logm_acc_value",
    "logm_acc_err_low",
    "logm_acc_err_high",
    "logm_acc_ref",
    "m_star_value",
    "m_star_err_low",
    "m_star_err_high",
    "m_star_ref",
    "ra_epochj2000_value",
    "ra_epochj2000_err_low",
    "ra_epochj2000_err_high",
    "ra_epochj2000_ref",
    "radial_velocity_value",
    "radial_velocity_err_low",
    "radial_velocity_err_high",
    "radial_velocity_ref",
    "spt_value",
    "spt_err_low",
    "spt_err_high",
    "spt_ref",
    "teff_value",
    "teff_err_low",
    "teff_err_high",
    "teff_ref",
    "is_jwst_target_value",
    "is_jwst_target_err_low",
    "is_jwst_target_err_high",
    "is_jwst_target_ref",
    "is_dsharp_target_value",
    "is_dsharp_target_err_low",
    "is_dsharp_target_err_high",
    "is_dsharp_target_ref",
]

curated_types = [
    "string",
    "string",
    "string",
    "string",
    "string",
    "string",
    "string",
    "string",
    "bool",
    "float",
    "float",
    "float",
    "string",
    "float",
    "float",
    "float",
    "string",
    "float",
    "float",
    "float",
    "string",
    "float",
    "float",
    "float",
    "string",
    "float",
    "float",
    "float",
    "string",
    "float",
    "float",
    "float",
    "string",
    "float",
    "float",
    "float",
    "string",
    "float",
    "float",
    "float",
    "string",
    "float",
    "float",
    "float",
    "string",
    "float",
    "float",
    "float",
    "string",
    "float",
    "float",
    "float",
    "string",
    "float",
    "float",
    "float",
    "string",
    "float",
    "float",
    "float",
    "string",
    "float",
    "float",
    "float",
    "string",
]

# Create a CSV file, curated will be the column names, curated_types will be the data types
curated_csv = pd.DataFrame({"Curated Labels": curated, "Curated Types": curated_types})
curated_csv.to_csv(
    "/Volumes/Isaac Portable SSD/Isaac Backup/Google Drive/School/Texas State/SpExoDisks/SpExoDisks_Container/SpExServer/Sphinx/curated.csv",
    index=False)

spectra = [
    "spectrum_handle",
    "spectrum_display_name",
    "spexodisks_handle",
    "spectrum_set_type",
    "spectrum_observation_date",
    "spectrum_pi",
    "spectrum_reference",
    "spectrum_downloadable",
    "spectrum_data_reduction_by",
    "spectrum_aor_key",
    "spectrum_flux_is_calibrated",
    "spectrum_ref_frame",
    "spectrum_min_wavelength_um",
    "spectrum_max_wavelength_um",
    "spectrum_resolution_um",
    "spectrum_output_filename",
]

spectra_types = [
    "string",
    "string",
    "string",
    "string",
    "datetime",
    "string",
    "string",
    "bool",
    "string",
    "int",
    "bool",
    "string",
    "double",
    "double",
    "double",
    "string",
]

spectra_csv = pd.DataFrame({"Spectra Labels": spectra, "Spectra Types": spectra_types})
spectra_csv.to_csv(
    "/Volumes/Isaac Portable SSD/Isaac Backup/Google Drive/School/Texas State/SpExoDisks/SpExoDisks_Container/SpExServer/Sphinx/spectra.csv",
    index=False)

objectnamealiases = [
    "alias",
    "spexodisks_handle"
]

objectnamealiases_types = [
    "string",
    "string"
]

objectnamealiases_csv = pd.DataFrame(
    {"Object Name Aliases Labels": objectnamealiases, "Object Name Aliases Types": objectnamealiases_types})
objectnamealiases_csv.to_csv(
    "/Volumes/Isaac Portable SSD/Isaac Backup/Google Drive/School/Texas State/SpExoDisks/SpExoDisks_Container/SpExServer/Sphinx/objectnamealiases.csv",
    index=False)

availableiso = [
    "name",
    "label",
    "molecule",
    "mol_label",
    "color",
    "dash",
    "min_wavelength_um",
    "max_wavelength_um",
    "total_lines",
]

availableiso_types = [
    "string",
    "string",
    "string",
    "string",
    "string",
    "string",
    "float",
    "float",
    "int",
]

availableiso_csv = pd.DataFrame(
    {"Available Isotopologues Labels": availableiso, "Available Isotopologues Types": availableiso_types})
availableiso_csv.to_csv(
    "/Volumes/Isaac Portable SSD/Isaac Backup/Google Drive/School/Texas State/SpExoDisks/SpExoDisks_Container/SpExServer/Sphinx/availableiso.csv",
    index=False)

params_units = [
    "param_handle",
    "order_index",
    "units",
    "short_label",
    "plot_axis_label",
    "for_display",
    "decimals",
]

params_units_types = [
    "int",
    "string",
    "string",
    "string",
    "string",
    "bool",
    "bool",
]

params_units_csv = pd.DataFrame(
    {"Avaiable Parameters and Units Labels": params_units, "Parameters and Units Types": params_units_types})
params_units_csv.to_csv(
    "/Volumes/Isaac Portable SSD/Isaac Backup/Google Drive/School/Texas State/SpExoDisks/SpExoDisks_Container/SpExServer/Sphinx/params_units.csv",
    index=False)

isotopologues = [
    "index_co",
    "wavelength_um",
    "isotopologue",
    "upper_level",
    "lower_level",
    "transition",
    "einstein_a",
    "upper_level_energy",
    "lower_level_energy",
    "g_statistical_weight_upper_level",
    "g_statistical_weight_lower_level",
    "upper_vibrational",
    "upper_rotational",
    "branch",
    "lower_vibrational",
    "lower_rotational",
]

isotopologues_types = [
    "int",
    "float",
    "string",
    "string",
    "string",
    "string",
    "float",
    "float",
    "float",
    "float",
    "float",
    "int",
    "int",
    "string",
    "int",
    "int",
]

isotopologues_csv = pd.DataFrame({"Isotopologues Labels": isotopologues, "Isotopologues Types": isotopologues_types})
isotopologues_csv.to_csv(
    "/Volumes/Isaac Portable SSD/Isaac Backup/Google Drive/School/Texas State/SpExoDisks/SpExoDisks_Container/SpExServer/Sphinx/isotopologues.csv",
    index=False)

specrum_handle = [
    "wavelength_um",
    "flux",
    "flux_error",
]

specrum_handle_types = [
    "double",
    "float",
    "float",
]

specrum_handle_csv = pd.DataFrame(
    {"Spectrum Handle Labels": specrum_handle, "Spectrum Handle Types": specrum_handle_types})
specrum_handle_csv.to_csv(
    "/Volumes/Isaac Portable SSD/Isaac Backup/Google Drive/School/Texas State/SpExoDisks/SpExoDisks_Container/SpExServer/Sphinx/spectrum_handle.csv",
    index=False)
