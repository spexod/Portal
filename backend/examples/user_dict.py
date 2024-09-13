from collections import UserDict


class TableDict(UserDict):
    def __setitem__(self, key: str, value):
        # for setting key, value pairs as
        # a_table_dict[key] = value
        if not isinstance(key, str):
            # 1
            raise ValueError('TableDict ' +
                'only allows string keys, ' +
                f'got {key}, type {type(key)}')
        # 2
        key = key.lower()
        if self.__contains__(key):
            # 3
            raise KeyError(f'Key: {key}, ' +
                'already exists, repeated ' +
                'assignment is not allowed ' +
                'in TableDict')
        else:
            self.data[key] = value
            
            
if __name__ == '__main__':
    """
    Above is an example of a Python class with instances of data objects that do not allow duplicate keys. 
    This is part of a paper to be submitted in 2024.
    """
    a_table_dict = TableDict()
    a_table_dict['Name'] = 'Andrea'
    # examples of the exceptions raised
    # 1
    try:
        a_table_dict[1] = 'Natalie'
    except ValueError as e:
        print(e)  # TableDict only allows string keys, ref: 1
    # 2
    try:
        print(a_table_dict['Name'], 'cannot be found be because the key set to be lowercase')
    except KeyError as e:
        print(e)
        print(a_table_dict['name'], 'is found because the key is set to be lowercase')
    # 3
    try:
        a_table_dict['name'] = 'Caleb'
    except KeyError as e:
        print('KeyError:', e)  # KeyError: 'Key: name, already exists, repeated assignment is not allowed in TableDict'
    # the key can only be set once
    print(a_table_dict)  # {'name': 'Andrea'}
