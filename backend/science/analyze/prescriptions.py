import os
from getpass import getuser

from ref.ref import working_dir, target_file_default
from science.db.sql import LoadSQL
from science.load.hitran import isotopologue_key
from science.analyze.spectrum import spectra_output_dir_default
from science.analyze.object_collection import ObjectCollection
from science.analyze.output_collection import OutputObjectCollection


def standard(upload_sql=False, write_plots=False, target_file=None,
             spectra_output_dir=None, update_mode: bool = False):
    if spectra_output_dir is None:
        spectra_output_dir = spectra_output_dir_default
    isotopologues_filter = {}
    for h2o_iso in ['H216O', 'H217O', 'H218O']:
        isotopologues_filter[h2o_iso] = {"upper_vibrational_quanta_h20": {(0, 0, 0), (0, 0, 1), (0, 1, 0), (1, 0, 0)},
                                         "upper_rotational_h2o": None,
                                         "upper_ka_h2o": None,
                                         "upper_kc_h2o": None,
                                         "lower_vibrational_quanta_h20": {(0, 0, 0)},
                                         "lower_rotational_h2o": None,
                                         "lower_ka_h2o": None,
                                         "lower_kc_h2o": None}
    for co_iso_key in isotopologue_key['CO'].keys():
        co_iso = isotopologue_key['CO'][co_iso_key]
        isotopologues_filter[co_iso] = {"upper_vibrational_levels_co": None,
                                        "branch_co": None,
                                        "upper_rotational_levels_co": None,
                                        "lower_vibrational_levels_co": None,
                                        "lower_rotational_levels_co": None}
    # get the data from this instance of OutputStarData
    output_collection = OutputObjectCollection(verbose=True, simbad_go_fast=False,
                                               spectra_output_dir=spectra_output_dir, update_mode=update_mode)
    # a copy of this instance
    output_collection.standard_process(per_isotopologues_filter=isotopologues_filter, upload_sql=False,
                                       write_plots=False)
    # if the target file is not None, then we will return only a subset of the data that has
    # the requested targets.
    if target_file is not None:
        output_collection.read_target_list(target_file=target_file)
        output_collection.remove_non_targets()

    output_collection.standard_output(upload_sql=upload_sql, write_plots=write_plots)
    return output_collection


def update_schemas(delete_spectra_tables: bool = False):
    with LoadSQL() as output_sql:
        if delete_spectra_tables:
            output_sql.delete_spectra()
        output_sql.update_schemas()


def sql_update(upload_sql=True, write_plots=True, target_file=None,
               update_mode: bool = False):
    output_collection = standard(upload_sql=upload_sql, write_plots=write_plots,
                                 target_file=target_file, update_mode=update_mode)
    return output_collection


def max_data(upload_sql=False, write_plots=False):
    object_collection = ObjectCollection(verbose=True, simbad_go_fast=False)
    object_collection.standard_process(per_isotopologues_filter=None,
                                       upload_sql=upload_sql,
                                       write_plots=write_plots)
    return object_collection


def get_single_object(object_collection, object_name, do_plot=True,
                      show_error_bars=True,
                      min_wavelength_um=None,
                      max_wavelength_um=None,
                      zero_velocity_wavelength_um=None,
                      show_hitran_lines=True,
                      transition_text=True,
                      x_fig_size=30, y_fig_size=8.0,
                      text_rotation=30, x_ticks_min_number=20):
    single_object = object_collection.get_single_star(object_name)
    if do_plot:
        for spectral_handle in single_object.available_spectral_handles:
            single_spectrum = single_object.__getattribute__(spectral_handle)
            single_spectrum.plot(show_error_bars=show_error_bars,
                                 min_wavelength_um=min_wavelength_um,
                                 max_wavelength_um=max_wavelength_um,
                                 zero_velocity_wavelength_um=zero_velocity_wavelength_um,
                                 show_hitran_lines=show_hitran_lines,
                                 transition_text=transition_text,
                                 x_fig_size=x_fig_size, y_fig_size=y_fig_size,
                                 text_rotation=text_rotation, x_ticks_min_number=x_ticks_min_number)
    return single_object


if __name__ == "__main__":
    example_target_file1 = target_file_default
    example_target_file2 = os.path.join('SpExoDisks', 'spexodisks', "load", 'target_list.csv')
    example_target_file3 = ['V* RU LUP', 'IRAS 04303+2240', 'HD139614']  # this can also be a list of star names
    dsharp_targets_file = os.path.join(working_dir, "load", 'reference_data', 'star_lists', 'dsharp_targets.csv')
    jwst_targets_file = os.path.join(working_dir, "load", 'reference_data', 'star_lists', 'jwst_targets.csv')

    username = getuser()
    if username == "chw3k5" or getuser() == "cwheeler":  # Caleb's computers
        # what runs on Caleb's computers
        # with LoadSQL() as output_sql:
        #     output_sql.update_schemas()
        oc = standard(upload_sql=True, write_plots=False, target_file=None, update_mode=True)
        # oc = sql_update(write_txt=False, write_fits=False, upload_sql=True,
        #                 write_plots=False, target_file=None, return_oc=True, update_mode=True)
    elif getuser() == "a_b1140":  # Andrea's computers
        # what runs on your computers (copy this statement and then edit the username above)
        oc = standard(upload_sql=True, update_mode=True, write_plots=False, target_file=None)
        # with LoadSQL() as output_sql:
        #    output_sql.update_schemas()
        # oc = sql_update(upload_sql=True, update_mode=True, write_plots=False, target_file=None)
        # single_object = get_single_object(object_collection=oc, object_name='HD190073', do_plot=True,
        #                                  show_error_bars=True,
        #                                  min_wavelength_um=4.802,
        #                                  max_wavelength_um=None,
        #                                  zero_velocity_wavelength_um=4.80302,
        #                                  show_hitran_lines=True,
        #                                  transition_text=True,
        #                                  x_fig_size=30, y_fig_size=8.0,
        #                                  text_rotation=30, x_ticks_min_number=20)
        dsharp = standard(upload_sql=False, update_mode=True, write_plots=False, target_file=dsharp_targets_file)
        jwst = standard(upload_sql=False, update_mode=True, write_plots=False, target_file=jwst_targets_file)
    else:
        # default statement
        print("Your username is:", getuser())
        print("consider adding your own elif statement, and not editing the default space.")
        # oc = standard(write_txt=True, write_fits=True, upload_sql=False, write_plots=True, target_file=None)
        # single_object = get_single_object(object_collection=oc, object_name='rulup', do_plot=True)
