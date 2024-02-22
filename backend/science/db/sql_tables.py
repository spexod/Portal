# quickly change the lengths of some MySQL columns
max_star_name_size = 50
max_param_type_len = 20
max_len_str_param = 100
max_ref_len = 100
max_units_len = 10
max_notes_len = 100

max_spectral_handle_len = 100
max_output_filename_len = 225

# how the website updates the tables
update_schema_map = [('spexodisks', 'new_spexodisks'), ('spectra', 'new_spectra'),
                     ('stacked_line_spectra', 'new_stacked_line')]

name_specs = F"VARCHAR({max_star_name_size}) NOT NULL, "
param_name = F"VARCHAR({max_param_type_len}) NOT NULL, "
float_spec = f"FLOAT"
float_param = f"{float_spec} NOT NULL, "
float_param_error = f"{float_spec}, "
double_spec = f"DOUBLE"
double_param = f"{double_spec} NOT NULL, "
double_param_error = f"{double_spec}, "
str_param = F"VARCHAR({max_len_str_param}) NOT NULL, "
str_param_error = F"VARCHAR({max_len_str_param}), "
param_ref = F"VARCHAR({max_ref_len}), "
param_units = F"VARCHAR({max_units_len}), "
param_notes = F"VARCHAR({max_notes_len}), "
password_spec = F"VARCHAR(128) NOT NULL, "
bool_spec = F"TINYINT NOT NULL, "

spectrum_handle = F"VARCHAR({max_spectral_handle_len}) NOT NULL, "
stacked_line_handle = F"VARCHAR({max_spectral_handle_len + 30}) NOT NULL, "
output_filename = F"VARCHAR({max_output_filename_len}), "

co_table_header = "(`index_CO` int(11) NOT NULL AUTO_INCREMENT, " + \
                   "`wavelength_um` " + float_param + \
                   "`isotopologue` VARCHAR(20), " + \
                   "`upper_level` VARCHAR(30), " + \
                   "`lower_level` VARCHAR(30), " + \
                   "`transition` VARCHAR(30), " + \
                   "`einstein_A` " + float_param + \
                   "`upper_level_energy` " + float_param + \
                   "`lower_level_energy` " + float_param + \
                   "`g_statistical_weight_upper_level` " + float_param + \
                   "`g_statistical_weight_lower_level` " + float_param + \
                   "`upper_vibrational` INT(2), " + \
                   "`upper_rotational` INT(2), " + \
                   "`branch` VARCHAR(1), " + \
                   "`lower_vibrational` INT(2), " + \
                   "`lower_rotational` INT(2), " + \
                    "PRIMARY KEY (`index_CO`)" + \
                   ") ENGINE=InnoDB;"

h20_table_header = "(`index_H2O` int(11) NOT NULL AUTO_INCREMENT, " + \
                    "`wavelength_um` " + float_param + \
                    "`isotopologue` VARCHAR(20), " + \
                    "`upper_level` VARCHAR(30), " + \
                    "`lower_level` VARCHAR(30), " + \
                    "`transition` VARCHAR(65), " + \
                    "`einstein_A` " + float_param + \
                    "`upper_level_energy` " + float_param + \
                    "`lower_level_energy` " + float_param + \
                    "`g_statistical_weight_upper_level` " + float_param + \
                    "`g_statistical_weight_lower_level` " + float_param + \
                    "`upper_vibrational1` INT(2), " + \
                    "`upper_vibrational2` INT(2), " + \
                    "`upper_vibrational3` INT(2), " + \
                    "`upper_rotational` INT(2), " + \
                    "`upper_ka` INT(2), " + \
                    "`upper_kc` INT(2), " + \
                    "`lower_vibrational1` INT(2), " + \
                    "`lower_vibrational2` INT(2), " + \
                    "`lower_vibrational3` INT(2), " + \
                    "`lower_rotational` INT(2), " + \
                    "`lower_ka` INT(2), " + \
                    "`lower_kc` INT(2), " + \
                    "PRIMARY KEY (`index_H2O`)" + \
                    ") ENGINE=InnoDB;"


create_tables = {'object_name_aliases': "CREATE TABLE `object_name_aliases` (`alias` " + name_specs +
                                                                            "`spexodisks_handle` " + name_specs +
                                                                            "PRIMARY KEY (`alias`)" +
                                                                            ") " +
                                        "ENGINE=InnoDB;",
                 "object_params_str": "CREATE TABLE `object_params_str` "
                                        "(`str_index_params` int(11) NOT NULL AUTO_INCREMENT," +
                                         "`spexodisks_handle` " + name_specs +
                                         "`str_param_type` " + param_name +
                                         "`str_value` " + str_param +
                                         "`str_error` " + str_param_error +
                                         "`str_ref` " + param_ref +
                                         "`str_units` " + param_units +
                                         "`str_notes` " + param_notes +
                                         "PRIMARY KEY (`str_index_params`)" +
                                         ") " +
                                        "ENGINE=InnoDB;",
                 "object_params_float": "CREATE TABLE `object_params_float` "
                                                   "(`float_index_params` int(11) NOT NULL AUTO_INCREMENT," +
                                                    "`spexodisks_handle` " + name_specs +
                                                    "`float_param_type` " + param_name +
                                                    "`float_value` " + str_param +
                                                    "`float_error_low` " + str_param_error +
                                                    "`float_error_high` " + str_param_error +
                                                    "`float_ref` " + param_ref +
                                                    "`float_units` " + param_units +
                                                    "`float_notes` " + param_notes +
                                                    "PRIMARY KEY (`float_index_params`)" +
                                                    ") " +
                                                   "ENGINE=InnoDB;",
                 "spectra": "CREATE TABLE `spectra` (`spectrum_handle` " + spectrum_handle +
                                                    "`spectrum_display_name` " + name_specs +
                                                    "`spexodisks_handle` " + name_specs +
                                                    "`spectrum_set_type` VARCHAR(20), " +
                                                    "`spectrum_observation_date` DATETIME, " +
                                                    "`spectrum_pi` VARCHAR(50), " +
                                                    "`spectrum_reference` " + param_ref +
                                                    "`spectrum_downloadable` TINYINT, " +
                                                    "`spectrum_data_reduction_by` VARCHAR(50), " +
                                                    "`spectrum_aor_key` INT, " +
                                                    "`spectrum_flux_is_calibrated` TINYINT, " +
                                                    "`spectrum_ref_frame` VARCHAR(20), " +
                                                    "`spectrum_min_wavelength_um` DOUBLE, " +
                                                    "`spectrum_max_wavelength_um` DOUBLE," +
                                                    "`spectrum_resolution_um` DOUBLE, " +
                                                    "`spectrum_output_filename` " + output_filename +
                                                    "PRIMARY KEY (`spectrum_handle`)" +
                                                    ") " +
                                                   "ENGINE=InnoDB;",
                 "default_spectrum_info": "CREATE TABLE `default_spectrum_info` "
                                          "(`spectrum_handle` " + spectrum_handle +
                                           "`spectrum_display_name` " + name_specs +
                                           "`spexodisks_handle` " + name_specs +
                                           "`spectrum_set_type` VARCHAR(20), " +
                                           "`spectrum_observation_date` DATETIME, " +
                                           "`spectrum_pi` VARCHAR(50), " +
                                           "`spectrum_reference` " + param_ref +
                                           "`spectrum_downloadable` TINYINT, " +
                                           "`spectrum_data_reduction_by` VARCHAR(50), " +
                                           "`spectrum_aor_key` INT, " +
                                           "`spectrum_flux_is_calibrated` TINYINT, " +
                                           "`spectrum_ref_frame` VARCHAR(20), " +
                                           "`spectrum_min_wavelength_um` DOUBLE, " +
                                           "`spectrum_max_wavelength_um` DOUBLE," +
                                           "`spectrum_resolution_um` DOUBLE, " +
                                           "`spectrum_output_filename` " + output_filename +
                                           "PRIMARY KEY (`spectrum_handle`)" +
                                           ") " +
                                           "ENGINE=InnoDB;",
                 "flux_calibration": "CREATE TABLE `flux_calibration` " +
                                     "(`index_flux_cal` int(11) NOT NULL AUTO_INCREMENT, " +
                                     "`spectrum_handle` " + spectrum_handle +
                                     "`flux_cal` " + float_param +
                                     "`flux_cal_error` " + float_param_error +
                                     "`wavelength_um` " + float_param +
                                     "`ref` " + param_ref +
                                      "PRIMARY KEY (`index_flux_cal`)" +
                                      ") " +
                                     "ENGINE=InnoDB;",
                 "co": "CREATE TABLE `co` " + co_table_header,
                 "h2o": "CREATE TABLE `h2o` " + h20_table_header,
                 "line_fluxes_co": "CREATE TABLE `line_fluxes_co` " +
                                   "(`index_CO` int(11) NOT NULL AUTO_INCREMENT, " +
                                    "`flux` " + float_param +
                                    "`flux_error` " + float_param_error +
                                    "`match_wavelength_um` " + float_param +
                                    "`wavelength_um` " + float_param +
                                    "`spectrum_handle` " + spectrum_handle +
                                    "`isotopologue` VARCHAR(20), " +
                                    "`upper_level` VARCHAR(30), " +
                                    "`lower_level` VARCHAR(30), " +
                                    "`transition` VARCHAR(30), " +
                                    "`einstein_A` " + float_param +
                                    "`upper_level_energy` " + float_param +
                                    "`lower_level_energy` " + float_param +
                                    "`g_statistical_weight_upper_level` " + float_param +
                                    "`g_statistical_weight_lower_level` " + float_param +
                                    "`upper_vibrational` INT(2), " +
                                    "`upper_rotational` INT(2), " +
                                    "`branch` VARCHAR(1), " +
                                    "`lower_vibrational` INT(2), " +
                                    "`lower_rotational` INT(2), " +
                                     "PRIMARY KEY (`index_CO`)" +
                                    ") " +
                                  "ENGINE=InnoDB;",
                 "stacked_line_spectra": "CREATE TABLE `stacked_line_spectra` " +
                                         "(`stack_line_handle` " + stacked_line_handle +
                                          "`spectrum_handle` " + spectrum_handle +
                                          "`spexodisks_handle` " + name_specs +
                                          "`transition` VARCHAR(30) NOT NULL, " +
                                          "`isotopologue` VARCHAR(20) NOT NULL, " +
                                          "`molecule` VARCHAR(20) NOT NULL, " +
                                          "PRIMARY KEY (`stack_line_handle`)" +
                                          ") " +
                                         "ENGINE=InnoDB;",
                 "available_isotopologues": "CREATE TABLE `available_isotopologues` " +
                                            "(`name` VARCHAR(20) NOT NULL, " +
                                            "`label` VARCHAR(100) NOT NULL, " +
                                            "`molecule` VARCHAR(20) NOT NULL, " +
                                            "`mol_label` VARCHAR(100) NOT NULL, " +
                                            "`color` VARCHAR(20) NOT NULL, " +
                                            "`dash` VARCHAR(20) NOT NULL, " +
                                            "`min_wavelength_um` " + float_param +
                                            "`max_wavelength_um` " + float_param +
                                            "`total_lines` INT(6) NOT NULL, " +
                                            "PRIMARY KEY (`name`) ) ENGINE=InnoDB;",
                 "status": "CREATE TABLE `status` " +
                           "(`index_status` int(11) NOT NULL AUTO_INCREMENT, " + \
                           "`new_data_staged` TINYINT , " +
                           "`updated_mysql` TINYINT , " +
                           "PRIMARY KEY (`index_status`) ) ENGINE=InnoDB;",
                 "djangoAPI_useraccount": "CREATE TABLE `djangoAPI_useraccount` " +
                                          "(`id` int(11) NOT NULL AUTO_INCREMENT," +
                                          "`spexodisks_handle`" + name_specs +
                                          "`password` " + password_spec +
                                          "`last_login` DATETIME(6), " +
                                          "`is_superuser` " + bool_spec +
                                          "`email` " + stacked_line_handle +
                                          "`last_name` " + stacked_line_handle +
                                          "`first_name` " + stacked_line_handle +
                                          "`is_active` " + bool_spec +
                                          "`is_staff` " + bool_spec +
                                          "`institution` " + stacked_line_handle +
                                          "PRIMARY KEY (`id`)" +
                                          ") " +
                                          "ENGINE=InnoDB;",
                 "djangoAPI_useraccount_groups": "CREATE TABLE `djangoAPI_useraccount_groups` " +
                                                 "(`id` int(11) NOT NULL AUTO_INCREMENT, " +
                                                 "`useraccount_id` int(11) NOT NULL, " +
                                                 "`group_id` int(11) NOT NULL, " +
                                                 "PRIMARY KEY (`id`)" +
                                                 ") " +
                                                 "ENGINE=InnoDB;",
                 "djangoAPI_useraccount_user_permissions": "CREATE TABLE `djangoAPI_useraccount_user_permissions` " +
                                                            "(`id` int(11) NOT NULL AUTO_INCREMENT, " +
                                                            "`useraccount_id` int(11) NOT NULL, " +
                                                            "`permission_id` int(11) NOT NULL, " +
                                                            "PRIMARY KEY (`id`)" +
                                                            ") " +
                                                            "ENGINE=InnoDB;",
                 }

dynamically_named_tables = {"spectrum": "(`wavelength_um` " + double_param +
                                         "`flux` " + float_param_error +
                                         "`flux_error` " + float_param_error +
                                          "PRIMARY KEY (`wavelength_um`)" +
                                         ") " +
                                        "ENGINE=InnoDB;",
                            "stacked_spectrum": "(`velocity_kmps` " + float_param +
                                                 "`flux` " + float_param_error +
                                                 "`flux_error` " + float_param_error +
                                                 "PRIMARY KEY (`velocity_kmps`)" +
                                                 ") " +
                                                 "ENGINE=InnoDB;",
                            "co": co_table_header,
                            'h2o': h20_table_header}
