import os
import pathlib
import shutil
import zipfile
import datetime
from io import BytesIO
from typing import NamedTuple, Union

import mysql.connector
from spexod.filepaths import fitsfile_py_path, fitsfile_md_path

from science.db.sql import django_tables, LoadSQL
from ref.ref import data_pro_dir, today_str
from science.analyze.prescriptions import standard, sql_update


class OutputDatum(NamedTuple):
    spectrum_handle: str
    starname: str
    output_path: str


class Dispatch:
    output_dir_default = os.path.join(os.getcwd(), 'output')
    allowed_extensions = {'txt', 'fits'}

    def __init__(self, verbose=False, output_dir=None):
        self.verbose = verbose
        if output_dir is None:
            self.output_dir = self.output_dir_default
        else:
            self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.mkdir(self.output_dir)
        self.output_datum_by_spectrum_handle = None
        self.refresh()
        if verbose:
            if self.output_datum_by_spectrum_handle is None:
                print('No output data found.')
            else:
                print(f'Dispatch initialized with {len(self.output_datum_by_spectrum_handle)} spectra.')
            print(f'Output directory: {self.output_dir}')

    def refresh(self):
        self.output_datum_by_spectrum_handle = {}
        for file_or_dir in os.listdir(self.output_dir):
            starname_dir = os.path.join(self.output_dir, file_or_dir)
            if file_or_dir[0] != '!' and os.path.isdir(starname_dir):
                starname = file_or_dir
                for output_file in os.listdir(starname_dir):
                    try:
                        spectrum_handle, extension = output_file.rsplit('.', 1)
                    except ValueError:
                        continue
                    if extension.lower() in self.allowed_extensions:
                        output_path = os.path.join(starname_dir, output_file)
                        if os.path.isfile(output_path):
                            output_datum = OutputDatum(spectrum_handle=spectrum_handle, starname=starname,
                                                       output_path=output_path)
                            if spectrum_handle not in self.output_datum_by_spectrum_handle.keys():
                                self.output_datum_by_spectrum_handle[spectrum_handle] = []
                            self.output_datum_by_spectrum_handle[spectrum_handle].append(output_datum)

    def write_upload_files(self):
        if os.path.exists(self.output_dir):
            for file_or_dir in os.listdir(self.output_dir):
                file_or_starname_dir = os.path.join(self.output_dir, file_or_dir)
                shutil.rmtree(file_or_starname_dir)
        standard(upload_sql=False, write_plots=False, target_file=None, spectra_output_dir=self.output_dir)

    @staticmethod
    def write_sql():
        sql_update(upload_sql=True, write_plots=False, target_file=None)

    def zip_upload(self, spectra_handles: list) -> bytes:
        failed_requests = []
        file_count = 0
        mem_zip = BytesIO()
        with zipfile.ZipFile(mem_zip, mode="w",) as zip_ref:
            # This python file is packaged with the FITS files so that users have a hope of reading them
            zip_ref.write(fitsfile_py_path, arcname=os.path.basename(fitsfile_py_path))
            # The markdown file is packaged with the FITS files so that users have a hope of reading them
            zip_ref.write(fitsfile_md_path, arcname=os.path.basename(fitsfile_md_path))
            for spectra_handle in spectra_handles:
                if spectra_handle in self.output_datum_by_spectrum_handle.keys():
                    spectrum_data = self.output_datum_by_spectrum_handle[spectra_handle]
                    for spectrum_datum in spectrum_data:
                        arcname = os.path.join(f'{spectrum_datum.starname}',
                                               os.path.basename(spectrum_datum.output_path))
                        zip_ref.write(spectrum_datum.output_path, arcname=arcname)
                        file_count += 1
                else:
                    failed_requests.append(spectra_handle)
        return mem_zip.getvalue()


def write_upload_files():
    dispatch = Dispatch(verbose=True, output_dir=None)
    dispatch.write_upload_files()


def write_sql():
    dispatch = Dispatch(verbose=True, output_dir=None)
    dispatch.write_sql()


def move_django_tables():
    with LoadSQL(auto_connect=True, verbose=True) as load_sql:
        load_sql.create_schema(schema_name='users')
        for table_name in django_tables:
            command_str = f"""ALTER TABLE spectra.{table_name} rename users.{table_name}"""
            try:
                load_sql.cursor.execute(command_str)
                load_sql.connection.commit()
            except mysql.connector.errors.ProgrammingError:
                print(f'Could not move table {table_name} to users schema.')


if __name__ == '__main__':
    """
    Command line interfacing to preload Docker images with processed results, do command line testing.
    and can also upload data to a MySQL database.
    """

    import argparse
    # set up the parser for this Script
    parser = argparse.ArgumentParser(description='Parser for play.py, a Wordle Emulator.')
    parser.add_argument('--write-upload', dest='write_upload', action='store_true',
                        help="White the upload files available for users to download via the API.")
    parser.add_argument('--no-write-upload', dest='write_upload', action='store_false', default=True,
                        help="Default - Does NOT white the upload files available for users to download via the API.")
    parser.add_argument('--write-sql', dest='write_sql', action='store_true',
                        help="White the SQL tables the website uses to via the API.")
    parser.add_argument('--no-write-sql', dest='write_sql', action='store_false', default=True,
                        help="Default - Does NOT white the SQL tables the website uses to via the API.")
    parser.add_argument('--test-run', dest='test_run', action='store_true',
                        help='Only upload to the MySQL test database, but does not upload to the ' +
                             'production database.')
    parser.add_argument('--no-test-run', dest='test_run', action='store_false', default=True,
                        help='Default - Upload to the MySQL production database after a successful writing to the ' +
                             'test database.')

    # parse the arguments
    args = parser.parse_args()

    # do the work
    if args.write_upload:
        write_upload_files()
    elif args.write_sql:
        write_sql()

    print(f'Done with the script in {os.path.basename(__file__)}, args: {args}')
