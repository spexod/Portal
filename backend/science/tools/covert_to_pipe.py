def to_psv(old_name, new_name=None, current_delimiter=None):
    if new_name is None:
        base_name, suffix = old_name.rsplit(".", 1)
        if current_delimiter is None:
            if suffix == 'csv':
                current_delimiter = ','
            else:
                raise KeyError("Specify the current_delimiter")
        new_name = base_name + ".psv"
    with open(old_name, 'r') as f:
        raw_data = f.readlines()
    processed_data = []
    for raw_line in raw_data:
        stripped_line = raw_line.strip()
        if current_delimiter == " ":
            while "  " in stripped_line:
                stripped_line = stripped_line.replace("  ", " ")
        processed_data.append(stripped_line.replace(current_delimiter, "|") + '\n')
    with open(new_name, 'w') as f:
        for processed_line in processed_data:
            f.write(processed_line)
    print("\nThe file:", old_name)
    print("was converted to Pipe Separated Values '.psv' file and written to:")
    print(new_name)
    return new_name


if __name__ == "__main__":
    import os
    from ref.star_names import object_params_dir
    for file in ["main", 'rv', "incl"]:
        to_psv(os.path.join(object_params_dir, file + ".csv"))
