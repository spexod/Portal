import os

from autostar.read_gaia import GaiaLib
from autostar.simbad_query import SimbadLib
from autostar.tic_query import TicQuery

from science.analyze.object_collection import ObjectCollection


def trash_auto_ref_files():
    simbad_lib = SimbadLib(verbose=True, go_fast=False, auto_load=False)
    if os.path.exists(simbad_lib.simbad_ref.ref_file_name):
        os.remove(simbad_lib.simbad_ref.ref_file_name)

    gaia_lib = GaiaLib(verbose=True)
    for dr_number in gaia_lib.dr_numbers:
        if os.path.exists(gaia_lib.__getattribute__("gaiadr" + str(dr_number) + "_ref").ref_file):
            os.remove(gaia_lib.__getattribute__("gaiadr" + str(dr_number) + "_ref").ref_file)

    tic_query = TicQuery(verbose=True)
    if os.path.exists(tic_query.reference_file_name):
        os.remove(tic_query.reference_file_name)


def full_reset_loop():
    trash_auto_ref_files()
    oc = ObjectCollection(verbose=True, simbad_go_fast=False)
    oc.standard_process()


if __name__ == "__main__":
    full_reset_loop()
