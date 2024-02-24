import os

from science.db.sql_config import target_dir
from ref.ref import rsync_key_file


def rsync_output(dir_or_file: str):
    command_str = 'rsync -avz -e --delete' + \
                  f'"ssh -i {rsync_key_file}" ' + \
                  f'./output/{dir_or_file} ubuntu@xpqlt.com:{target_dir}'
    os.system(command_str)