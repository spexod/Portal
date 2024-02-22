def space_to_csv(old_name, new_name=None):
    if new_name is None:
        base_name, _suffix = old_name.rsplit(".", 1)
        new_name = base_name + ".csv"
    with open(old_name, 'r') as f:
        raw_data = f.readlines()
    processed_data = []
    for raw_line in raw_data:
        stripped_line = raw_line.strip()
        while "  " in stripped_line:
            stripped_line = stripped_line.replace("  ", " ")
        processed_data.append(stripped_line.replace(' ', ",") + "\n")
    with open(new_name, 'w') as f:
        for processed_line in processed_data:
            f.write(processed_line)
    print("The file:", old_name)
    print("was converted to CSV file and written to:")
    print(new_name)
    return new_name
