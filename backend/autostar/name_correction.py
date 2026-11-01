import os

from autostar.simbad_query import SimbadLib
from autostar.config.datapaths import annoying_names_filename, popular_names_filename, star_name_format, StringStarName


class AnnoyingNames:
    def __init__(self):
        self.path = annoying_names_filename
        self.annoying_names = set()
        self.sb_names = {}
        if os.path.exists(self.path):
            with open(self.path, 'r') as f:
                first_line = True
                for line in f.readlines():
                    if first_line:
                        first_line = False
                    else:
                        line = line.strip()
                        if line != "":
                            name, simbad_name = line.split(",")
                            self.annoying_names.add(name)
                            self.sb_names[name] = simbad_name
        else:
            with open(self.path, 'w') as f:
                f.write("name,simbad\n")

    def write(self):
        with open(self.path, 'w') as f:
            f.write("name,simbad\n")
            for name in sorted(self.sb_names.keys()):
                f.write(str(name).lower() + "," + str(self.sb_names[name]) + "\n")

    def append(self, name, simbad_name):
        if name in self.sb_names.keys():
            if simbad_name != self.sb_names[name]:
                self.sb_names[name] = simbad_name
                self.write()
        else:
            self.annoying_names.add(name)
            self.annoying_names.add(name)
            self.sb_names[name] = simbad_name
            with open(self.path, 'a') as f:
                f.write(str(name).lower() + "," + str(self.sb_names[name]) + "\n")


class PopNamesLib:
    def __init__(self, simbad_lib=None, simbad_go_fast=False):
        self.remove_from_pop_name = ['**', "V*", 'v*', "*"]

        if simbad_lib is None:
            simbad_lib = SimbadLib(go_fast=simbad_go_fast)
        self.simbad_lib = simbad_lib
        file_name = popular_names_filename
        with open(file_name, 'r') as f:
            pop_file_data = f.readlines()
        header = pop_file_data[0].strip().split(",")
        objects_list = [{column_name: column_value for column_name, column_value
                         in list(zip(header, one_line.strip().split(",")))}
                        for one_line in pop_file_data[1:]]
        self.handle_to_pop_name = {}
        for pop_name_dict in objects_list:
            pop_name_dict['hypatia_name'] = star_name_format(pop_name_dict['simbad_name'])
            pop_name_dict["spexodisks_handle"], pop_name_dict['star_names_dict'] \
                = self.simbad_lib.get_star_dict(pop_name_dict['hypatia_name'])
            self.handle_to_pop_name[pop_name_dict["spexodisks_handle"]] = pop_name_dict["popular_name"]
        self.pop_names_lower = {self.handle_to_pop_name[handle].lower(): handle
                                for handle in self.handle_to_pop_name.keys()}

    def get_or_generate(self, spexodisks_handle, simbad_preferred_name=None):
        if spexodisks_handle in self.handle_to_pop_name.keys():
            return self.handle_to_pop_name[spexodisks_handle]
        elif simbad_preferred_name is not None:
            self.add_pop_name(spexodisks_handle, simbad_preferred_name)
            return self.handle_to_pop_name[spexodisks_handle]
        else:
            raise KeyError("spexodisks_handle not in defined popular name and there is no simbad_preferred_name from " +
                           "which to create a popular name")

    def add_pop_name(self, spexodisks_handle, simbad_preferred_name):
        pop_name = simbad_preferred_name
        for thing_to_remove in self.remove_from_pop_name:
            if thing_to_remove in pop_name:
                pop_name = pop_name.replace(thing_to_remove, "").strip()
        self.handle_to_pop_name[spexodisks_handle] = pop_name

    def pop_name_to_handle(self, test_name):
        test_name_lower = test_name.lower()
        if test_name_lower in self.pop_names_lower.keys():
            return self.pop_names_lower[test_name_lower]
        return None


an = AnnoyingNames()


def verify_starname(test_object_name, other_info=None):
    object_name = None
    # This is catch for star names that are annoying that were previously found and recorded
    if test_object_name.lower() in an.annoying_names:
        test_object_name = an.sb_names[test_object_name.lower()]
    # try to format the name
    try:
        hypatia_name = star_name_format(test_object_name)
    except ValueError:
        if other_info is None:
            info_str = ""
        else:
            info_str = "\n" + str(other_info)
        object_name = input("Enter the Simbad name for: " + test_object_name + info_str)
        hypatia_name = star_name_format(object_name)
        an.append(test_object_name, object_name)
    if object_name is None:
        object_name = StringStarName(hypatia_name).string_name
    return object_name, hypatia_name
