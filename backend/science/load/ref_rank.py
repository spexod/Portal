from ref.ref import reference_preference_path

with open(reference_preference_path, 'r') as f:
    raw_lines = f.readlines()

rank_per_column = {}
for raw_line in raw_lines:
    params_column_name, ref_pref = raw_line.split(":")
    rank_per_column[params_column_name.strip()] = {raw_ref.strip(): rank_index for rank_index, raw_ref
                                                   in list(enumerate(reversed(ref_pref.split('|'))))}


def rank_ref(param, ref):
    rank_dict = rank_per_column[param]
    if ref in rank_dict.keys():
        return rank_dict[ref]
    else:
        # unknown references get the best rank
        return len(rank_dict) + 1

# print("rank_ref(param='dist', ref='Bailer-Jones et al. (2018)'):",
#       rank_ref(param='dist', ref='Bailer-Jones et al. (2018)'))
