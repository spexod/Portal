import os
import subprocess

from science.db.sql import UPLOAD_DIR
from ref.ref import rsync_key_file


def rsync_output(dir_or_file: str, verbose: bool = False):
    if os.path.exists(rsync_key_file):
        # an argument list, not a shell string: the path comes from the data directory names
        subprocess.run(["rsync", "-avz", "-e", f"ssh -i {rsync_key_file}",
                        dir_or_file, f"ubuntu@spexodisks.com:{UPLOAD_DIR}"], check=True)
        if verbose:
            print(f"rsynced {dir_or_file} to spexodisks.com")
    else:
        pass
