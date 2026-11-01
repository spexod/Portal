"""
File locations and star-name settings for the autostar package.

autostar used to be a standalone package shared with HypatiaCatalog.com and read these settings
from a user.toml file that ref/ref.py wrote at import time. Now that it lives in the Portal backend
the settings come straight from the ref package: ref/ref.py for the directories and reference files,
ref/star_names.py for the star-name grammar (catalog types, parsing, formatting and the preference
order that decides each object's spexodisks handle).
"""
import os

from ref.star_names import (star_name_format, optimal_star_name, star_name_preference, StringStarName, StarName,
                            star_letters, asterisk_names, asterisk_name_types)
from ref.ref import (ref_dir, sb_bad_star_name_ignore, sb_main_ref_file_name, sb_ref_file_name, tic_ref_filename,
                     annoying_names_filename, popular_names_filename, sb_desired_names)

# the names the autostar modules import (kept from the user.toml keys)
sb_bad_star_name_ignore_filename = sb_bad_star_name_ignore
sb_main_ref_filename = sb_main_ref_file_name
sb_ref_filename = sb_ref_file_name

# data/reference_data is bind-mounted at run time (compose.yaml); the directory exists in the image too
os.makedirs(ref_dir, exist_ok=True)

__all__ = ['star_name_format', 'optimal_star_name', 'star_name_preference', 'StringStarName', 'StarName',
           'star_letters', 'asterisk_names', 'asterisk_name_types',
           'ref_dir', 'sb_bad_star_name_ignore_filename', 'sb_main_ref_filename', 'sb_ref_filename',
           'tic_ref_filename', 'annoying_names_filename', 'popular_names_filename', 'sb_desired_names']
