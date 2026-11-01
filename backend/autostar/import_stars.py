import os

from autostar.config.datapaths import ref_dir
from autostar.simbad_query import SimbadLib
from autostar.name_correction import verify_starname


class CheckStarNames:
    def __init__(self, string_name_list=None, file_name=None, delimiter=',', simbad_go_fast=False, verbose=True):
        self.simbad_lib = None
        self.simbad_go_fast = simbad_go_fast
        self.verbose = verbose
        self.list_of_star_names_dicts = None
        self.list_of_hypatia_handles = None

        self.raw_star_list = []
        if string_name_list:
            self.raw_star_list.extend(string_name_list)
        if file_name:
            self.stars_file = file_name
            with open(self.stars_file, 'r') as f:
                lines = f.readlines()
            for line in lines:
                self.raw_star_list.extend(line.strip().split(delimiter))
        self.verified_names = [verify_starname(string_name) for string_name in self.raw_star_list]
        self.hypatia_formatted_names = [hyp_name for str_name, hyp_name in self.verified_names]
        self.simbad_formatted_names = [str_name for str_name, hyp_name in self.verified_names]
        self.type_id_dict = {}
        self.available_star_name_types = set()
        for (name_type, star_id) in self.hypatia_formatted_names:
            if name_type in self.available_star_name_types:
                self.type_id_dict[name_type].add(star_id)
            else:
                self.type_id_dict[name_type] = {star_id}
                self.available_star_name_types.add(name_type)

    def update_simbad_ref(self):
        self.list_of_star_names_dicts = []
        self.list_of_hypatia_handles = []
        self.simbad_lib = SimbadLib(verbose=self.verbose, go_fast=self.simbad_go_fast)
        for hypatia_name in self.hypatia_formatted_names:
            hypatia_handle, star_names_dict = self.simbad_lib.get_star_dict(hypatia_name=hypatia_name)
            self.list_of_star_names_dicts.append(star_names_dict)
            self.list_of_hypatia_handles.append(hypatia_handle)


if __name__ == "__main__":
    csn = CheckStarNames(file_name=os.path.join(ref_dir, 'planets_2020.04.22_18.13.10.csv'))
    csn.update_simbad_ref()

