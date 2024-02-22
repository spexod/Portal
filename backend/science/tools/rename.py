import os
from ref.ref import spectra_dir


def rename_files(path, string_to_replace, replace_with=""):
    for base_name in [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]:
        if string_to_replace in base_name:
            os.rename(os.path.join(path, base_name),
                      os.path.join(path, base_name.replace(string_to_replace, replace_with)))


if __name__ == "__main__":
    rename_files(path=os.path.join(spectra_dir, "NIRSPEC_data"), string_to_replace=".dat", replace_with=".txt")
