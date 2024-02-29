import os

from science.db.sql_config import upload_dir
from ref.ref import rsync_key_file


def rsync_output(dir_or_file: str, verbose: bool = False):
    if os.path.exists(rsync_key_file):
        command_str = 'rsync -avz -e ' + \
                      f'"ssh -i {rsync_key_file}" ' + \
                      f'"{dir_or_file}" bitnami@spexodisks.com:"{upload_dir}"'
        os.system(command_str)
        if verbose:
            print(f"rsynced {dir_or_file} to spexodisks.com")
    else:
        pass
