from typing import NamedTuple, Optional

from autostar.table_read import row_dict
from science.load.hitran import HitranRef, Hitran, HitranLine, hitran_line_header, \
    isotopologue_to_molecule


class LineFlux(NamedTuple):
    """ Represents all the data that goes in to the out file for a single spectrum"""
    flux: float
    err: Optional[float] = None
    match_wavelength_um: Optional[float] = None
    hitran_line: Optional[HitranLine] = None

    def __str__(self):
        return str(self.flux) + "," + str(self.err) + "," + str(self.match_wavelength_um) + "," + str(self.hitran_line)


line_flux_header = "flux,flux_err,match_wavelength_um," + hitran_line_header


class LineFluxes:
    def __init__(self, extra_science_product_path, hitran_ref=None, auto_load=True):
        self.path = extra_science_product_path.path
        self.isotopologue = extra_science_product_path.isotopologue
        molecule = isotopologue_to_molecule[self.isotopologue]
        if hitran_ref is None:
            hitran_ref = HitranRef()
        iso_data = hitran_ref.ref_iso(self.isotopologue)
        if "v" == extra_science_product_path.transition[0] and molecule in {"CO", "H2O"}:
            self.transition_type = "vibrational"
            upper_level, lower_level = extra_science_product_path.transition[1:].split("-")
            self.upper_level = int(upper_level)
            self.lower_level = int(lower_level)
            if molecule == "CO":
                self.hitran = iso_data.get_lines(upper_vibrational_levels_co={self.upper_level},
                                                 lower_vibrational_levels_co={self.lower_level})
            elif molecule == "H2O":
                self.hitran = iso_data.get_lines(upper_vibrational_quanta_h20={self.upper_level},
                                                 lower_vibrational_quanta_h20={self.lower_level})

        else:
            self.transition_type = self.upper_level = self.lower_level = None
            hitran_lines = hitran_ref.data
            self.hitran = Hitran(auto_load=False)
            self.hitran.receive(data=hitran_lines)

        self.flux_data = None
        if auto_load:
            self.load()

    def load(self):
        raw_data = row_dict(filename=self.path, key='wavelength_um', delimiter=',',
                            null_value=None, inner_key_remove=True)
        if "comments" in raw_data.keys():
            del raw_data["comments"]
        self.flux_data = []
        for target_wavelength_um in sorted(raw_data.keys()):
            closest_line = self.hitran.find_closest(target_wavelength=target_wavelength_um, n=1)
            data_this_line = raw_data[target_wavelength_um]
            flux = data_this_line["flux"]
            if 'flux_err' in data_this_line.keys():
                err = data_this_line['flux_err']
            else:
                err = None
            self.flux_data.append(LineFlux(flux=flux, err=err, match_wavelength_um=target_wavelength_um,
                                           hitran_line=closest_line[0]))


if __name__ == "__main__":
    import os
    from collections import namedtuple
    from SpExoDisks.star_names import spectra_dir
    ExtraScienceProductPath = namedtuple("ExtraScienceProduct", "isotopologue transition path")
    file = os.path.join(spectra_dir, "CRIRES", "RULup_M_APR07_12C16O_v1-0_linefluxes.csv")
    expp = ExtraScienceProductPath(isotopologue='12C16O',
                                   transition="v1-0",
                                   path=file)

    lf = LineFluxes(extra_science_product_path=expp)
