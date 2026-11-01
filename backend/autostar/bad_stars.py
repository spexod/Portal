import os

from autostar.config.datapaths import ref_dir, star_name_format, StringStarName, sb_bad_star_name_ignore_filename
from autostar.table_read import row_dict


class BadStars:
    def __init__(self):
        self.file_name = sb_bad_star_name_ignore_filename
        if os.path.exists(self.file_name):
            self.name_data = row_dict(filename=self.file_name, key="star", delimiter=",", null_value="",
                                      inner_key_remove=True)
        else:
            self.name_data = {}
        self.hypatia_names = set()
        self.simbad_names = set()
        self.reason_lists = {}
        self.hyp_name_to_reason_dict = {}
        for star_name in self.name_data.keys():
            hypatia_name = star_name_format(star_name)
            reason = self.name_data[star_name]["reason"]
            self.hyp_name_to_reason_dict[hypatia_name] = reason
            self.hypatia_names.add(hypatia_name)
            self.simbad_names.add(StringStarName(hypatia_name=hypatia_name).string_name)
            if reason in self.reason_lists.keys():
                self.reason_lists[reason].append(hypatia_name)
            else:
                self.reason_lists[reason] = [hypatia_name]


if __name__ == "__main__":
    bs = BadStars()
