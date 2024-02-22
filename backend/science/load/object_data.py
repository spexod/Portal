import os

from autostar.table_read import num_format
from autostar.simbad_query import SimbadLib
from autostar.object_params import set_single_param
from autostar.name_correction import verify_starname

from ref.ref import ref_dir
from science.load.units import UnitsObjectParams


class MainDisk:
    def __init__(self, file_name, simbad_go_fast=False, verbose=True):
        self.file_name = file_name
        self.verbose = verbose
        self.column_data_dict = None
        self.object_data = None
        self.object_names_dicts = None
        self.spexodisks_handles = None
        self.simbad_lib = None
        self.simbad_go_fast = simbad_go_fast

    def read_ref(self):
        with open(self.file_name, "r") as f:
            main_disk_lines = f.readlines()
        main_disk_lines = [main_disk_lines[row_index].strip().split(",") for row_index in range(len(main_disk_lines))]
        # Getting header, column notes, data units
        self.column_data_dict = {}
        line = main_disk_lines[0]
        row_index = 0
        while line[0] != "":
            self.column_data_dict[line[0]] = line[1:]
            row_index += 1
            line = main_disk_lines[row_index]
        # Parsing line with data names.
        column_dict = {}
        column_names = set()
        type_to_index = {}
        reference_column_indexes = {}
        error_column_indexes = {}
        for column_index, data_type in list(enumerate(self.column_data_dict['data_name'])):
            if '_ref' in data_type:
                reference_column_indexes[data_type.replace('_ref', "")] = column_index
            elif "_err" in data_type:
                error_column_indexes[data_type.replace('_err', "")] = column_index
            elif data_type == "":
                pass
            else:
                column_names.add(data_type)
                type_to_index[data_type] = column_index
                column_dict[data_type] = {}
        # Parsing other data name types.
        for other_column_data in set(self.column_data_dict.keys()) - {"data_name"}:
            for data_type in column_names:
                column_dict[data_type][other_column_data]\
                    = self.column_data_dict[other_column_data][type_to_index[data_type]]
        # Process the rest of the data into a object -> param_name -> list -> param_card -> value/ref/err/ect.
        data_types_with_ref = set(reference_column_indexes.keys())
        data_types_with_err = set(error_column_indexes.keys())
        self.object_data = {}
        self.object_names_dicts = {}
        self.spexodisks_handles = set()
        if self.simbad_lib is None:
            self.simbad_lib = SimbadLib(go_fast=self.simbad_go_fast, verbose=self.verbose)
        for _, *row_of_data in main_disk_lines[row_index:]:
            raw_star_name = row_of_data[type_to_index['object_name']]
            object_name, hypatia_name = verify_starname(raw_star_name)
            spexodisks_handle, object_names_dict = self.simbad_lib.get_star_dict(hypatia_name)
            if spexodisks_handle not in self.spexodisks_handles:
                self.object_data[spexodisks_handle] = UnitsObjectParams()
                self.object_names_dicts[spexodisks_handle] = object_names_dict
                self.spexodisks_handles.add(spexodisks_handle)
            for data_type in column_names - {"object_name"}:
                value = row_of_data[type_to_index[data_type]]
                if value != "":
                    column_dict[data_type]['value'] = num_format(value)
                    if data_type in data_types_with_err:
                        column_dict[data_type]['err'] = num_format(row_of_data[error_column_indexes[data_type]])
                    if data_type in data_types_with_ref:
                        column_dict[data_type]['ref'] = row_of_data[reference_column_indexes[data_type]]
                    self.object_data[spexodisks_handle][data_type] = set_single_param(column_dict[data_type])


if __name__ == "__main__":
    md = MainDisk(file_name=os.path.join(ref_dir, "object_params", "MAIN_disk_sample.csv"), verbose=True)
    md.read_ref()
