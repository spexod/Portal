import os

import numpy as np
from autostar.table_read import row_dict
from autostar.simbad_query import StarDict
from autostar.object_params import SingleParam

from ref.ref import ref_dir
unit_filepath = os.path.join(ref_dir, 'units.csv')


def read_units_file():
    param_data = row_dict(filename=unit_filepath, key='param_handle', delimiter=",",
                          null_value='NULL', inner_key_remove=True)
    return param_data


def params_value_format(value, decimals):
    try:
        formatted_value = float(np.round(value, decimals=decimals))
    except TypeError:
        formatted_value = value
    return formatted_value


def params_err_format(err, sig_figs):
    if sig_figs < 2:
        decimals = 1
    else:
        decimals = sig_figs - 1
    format_string = f'1.{decimals}e'
    return err.__format__(format_string)


class ParamsCheck:
    disallowed_params = {'rv', 'mass'}
    null_values = {'NULL'}

    def __init__(self):
        # read in the csv file data
        with open(unit_filepath, 'r') as f:
            raw_lines = [line.strip() for line in f.readlines()]
        self.header = [column_name.strip().lower() for column_name in raw_lines[0].split(',')]
        body = raw_lines[1:]
        self.params_data = {}
        self.max_lens = {column_name: 0 for column_name in self.header}
        self.params_order = []
        for param_line in body:
            str_values = [str_value.strip() for str_value in param_line.split(',')]
            row_data = {}
            for column_name, string_value in zip(self.header, str_values):
                # the key for each row in the table has extra formatting requirements
                if column_name == 'param_handle':
                    string_value = string_value.lower()
                # null values are expected in this format
                if string_value in self.null_values:
                    string_value = None
                row_data[column_name] = string_value
            params_handle = row_data['param_handle']
            # we will want to know when the max length per column for output SQL or another API
            for column_name in self.header:
                str_value = row_data[column_name]
                if str_value is not None:
                    len_this_str_value = len(str_value)
                    if len_this_str_value > self.max_lens[column_name]:
                        self.max_lens[column_name] = len_this_str_value
            # delete repeated data.
            del row_data['param_handle']
            self.params_data[params_handle] = row_data
            # record the parameter order
            self.params_order.append(params_handle)
        # get the set of allow parameters
        self.allowed_params = {param_handle for param_handle in self.params_data.keys()
                               if param_handle not in self.disallowed_params}
        # dictionary of allowed handles to expected units
        self.expected_units = {param_handle: units for param_handle, units
                               in self.expected_units_gen()}

    def expected_units_gen(self):
        # experimenting with generators to replace for loops
        for param_handle in self.allowed_params:
            data_this_param = self.params_data[param_handle]
            if 'units' in data_this_param.keys():
                yield param_handle, data_this_param['units']
            else:
                yield param_handle, None

    def single_params_check(self, param_handle):
        if param_handle in self.allowed_params:
            pass
        elif param_handle in self.disallowed_params:
            raise TypeError(F"Params Check Fail. param_handle:{param_handle} is one of the " +
                            F"disallowed parameter names: {self.disallowed_params}.")
        else:
            raise TypeError(f"Params Check Fail. param_handle:{param_handle} is one of the\n" +
                            f"allowed parameters: {self.allowed_params}")

    def single_param_units_check(self, param_handle, single_params):
        # see it values is an iterable or a singleton
        if isinstance(single_params, SingleParam):
            # convert the singleton to an iterable
            single_params = [single_params]
        else:
            single_params = list(single_params)
        for single_param in single_params:
            value_units = single_param.units
            if param_handle in self.allowed_params:
                expected_units = self.expected_units[param_handle]
                if expected_units == 'string':
                    if isinstance(single_param.value, str):
                        # checks passed
                        pass
                    else:
                        raise TypeError(F"When expected units are 'string' then SingleParam.value must by 'str' not " +
                                        F"{type(single_param.value)}")

                elif value_units == self.expected_units[param_handle]:
                    # checks passed
                    pass
                else:
                    raise TypeError(F"Unit Check Fail. param_handle:{param_handle}, {value_units} " +
                                    F"was passed when {expected_units} was expected.")
            else:
                if param_handle in self.disallowed_params:
                    raise TypeError(F"Unit Check Fail. param_handle:{param_handle} is one of the " +
                                    F"disallowed parameter names: {self.disallowed_params}.")
                else:
                    raise TypeError(F"Unit Check Fail. param_handle:{param_handle} not found in the file:\n" +
                                    F"{unit_filepath}\nwhich as the param_handles: {self.params_data.keys()}")
        # all checks passed
        return

    def value_format(self, param_handle, value):
        if value is None:
            return None
        if isinstance(value, int):
            value = float(value)
        if param_handle in self.allowed_params:
            expected_units = self.expected_units[param_handle]
            if expected_units == 'string':
                return value
            else:
                decimals = int(self.params_data[param_handle]['decimals'])
                if isinstance(value, tuple):
                    values_formatted = (params_value_format(a_val, decimals) for a_val in value)
                    return values_formatted
                else:
                    value_formatted = params_value_format(value, decimals)
                    return value_formatted
        else:
            raise TypeError(F"Value Format Fail. param_handle:{param_handle} is one of the " +
                            F"allowed parameter names: {self.allowed_params}.")

    def err_format(self, param_handle, err):
        if err is None:
            return None
        if isinstance(err, int):
            err = float(err)
        if param_handle in self.allowed_params:
            expected_units = self.expected_units[param_handle]
            if expected_units == 'string':
                return err
            else:
                decimals = int(self.params_data[param_handle]['decimals'])
                if isinstance(err, tuple):
                    values_formatted = tuple([params_value_format(a_val, decimals=decimals) for a_val in err])
                    return values_formatted
                else:
                    value_formatted = params_value_format(err, decimals=decimals)
                    return value_formatted
        else:
            raise TypeError(F"Value Format Fail. param_handle:{param_handle} is one of the " +
                            F"allowed parameter names: {self.allowed_params}.")


params_check = ParamsCheck()


class UnitsObjectParams(StarDict):
    def __setitem__(self, key, value):
        # all keys are required to be lower case and have no spaces
        key = key.lower().strip().replace(' ', '')
        # check to see that the units are the required standard
        params_check.single_params_check(param_handle=key)
        params_check.single_param_units_check(key, value)
        # record these/this values/value
        if self.__contains__(key):
            # key is already in this dictionary, so update the existing record(s)
            if isinstance(value, set):
                self.data[str(key)] |= value
            elif isinstance(value, SingleParam):
                self.data[str(key)].add(value)
            else:
                raise ValueError("SingleParam or set is required")
        else:
            # make a new data entry for this key
            if isinstance(value, set):
                self.data[str(key)] = value
            elif isinstance(value, SingleParam):
                self.data[str(key)] = {value}
            else:
                raise ValueError("SingleParam set is required")
