import os
import pathlib
import shutil
import zipfile
import datetime
from typing import NamedTuple, Union

import mysql.connector
from spexod.filepaths import fitsfile_py_path, fitsfile_md_path

from science.db.sql import django_tables, LoadSQL
from ref.ref import uploads_dir, data_pro_dir, today_str
from science.analyze.prescriptions import standard, sql_update


class OutputDatum(NamedTuple):
    spectrum_handle: str
    starname: str
    output_path: str


class Dispatch:
    output_dir_default = os.path.join(os.getcwd(), 'output')
    uploads_dir_default = os.path.join(os.getcwd(), 'uploads')
    allowed_extensions = {'txt', 'fits'}

    def __init__(self, verbose=False, output_dir=None, uploads_dir=None):
        self.verbose = verbose
        if output_dir is None:
            self.output_dir = self.output_dir_default
        else:
            self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.mkdir(self.output_dir)
        if uploads_dir is None:
            self.uploads_dir = self.uploads_dir_default
        else:
            self.uploads_dir = uploads_dir
        if not os.path.exists(self.uploads_dir):
            os.mkdir(self.uploads_dir)
        self.output_datum_by_spectrum_handle = None
        self.refresh()
        if verbose:
            if self.output_datum_by_spectrum_handle is None:
                print('No output data found.')
            else:
                print(f'Dispatch initialized with {len(self.output_datum_by_spectrum_handle)} spectra.')
            print(f'Output directory: {self.output_dir}')
            print(f'Uploads directory: {self.uploads_dir}')

    def refresh(self):
        self.output_datum_by_spectrum_handle = {}
        print(f'output_dir: {self.output_dir}')
        for file_or_dir in os.listdir(self.output_dir):
            starname_dir = os.path.join(self.output_dir, file_or_dir)
            if file_or_dir[0] != '!' and os.path.isdir(starname_dir):
                starname = file_or_dir
                for output_file in os.listdir(starname_dir):
                    print('file_or_dir', file_or_dir)
                    print('starname', starname_dir)
                    print('output_file', output_file)
                    spectrum_handle, extension = output_file.rsplit('.', 1)
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
    def write_sql(do_update_schemas=False):
        sql_update(upload_sql=True, write_plots=False, target_file=None, do_update_schemas=do_update_schemas)

    def get_zipfile_path(self, username):
        username = username.replace(' ', '_')
        return os.path.join(self.uploads_dir, f'{username}.zip')

    def zip_upload(self, username: str, spectra_handles: list):
        failed_requests = []
        zipfile_path = self.get_zipfile_path(username)
        file_count = 0
        with zipfile.ZipFile(zipfile_path, 'w') as zip_ref:
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
        if self.verbose:
            print(f'Zip file made at: {zipfile_path}')
            print(f'   with {file_count} files returned out of {len(spectra_handles)} requests.')

        return zipfile_path, failed_requests

    def zip_del(self, username: str):
        zipfile_path = self.get_zipfile_path(username)
        if os.path.exists(zipfile_path):
            os.remove(zipfile_path)
            if self.verbose:
                print(f'Zip file deleted at: {zipfile_path}')


def write_upload_files():
    dispatch = Dispatch(verbose=True, output_dir=None, uploads_dir=None)
    dispatch.write_upload_files()


def write_sql(do_update_schemas=False):
    dispatch = Dispatch(verbose=True, output_dir=None, uploads_dir=None)
    dispatch.write_sql(do_update_schemas=do_update_schemas)


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


def zip_test(spectrum_handles=None, date_str=None):
    if spectrum_handles is None:
        spectrum_handles = ['spitzer_9886nm_37157nm_hd_036112',
                            'nirspec_2902nm_3698nm_hd_256013',
                            'crires_2906nm_2990nm_vstar_an_sex']
    if date_str is None:
        date_str = today_str
    dispatch = Dispatch(verbose=True, output_dir=os.path.join(data_pro_dir, date_str),
                        uploads_dir=uploads_dir)
    dispatch.zip_upload('test', spectrum_handles)


def is_expired(path, delta_time):
    timestamp = os.path.getmtime(str(path))
    last_modified = datetime.datetime.fromtimestamp(timestamp)
    delta_time_this_file = datetime.datetime.now() - last_modified
    return delta_time_this_file > delta_time


def zip_delete_old(delete_time_min: float = 15.0, uploads_dir: Union[str, pathlib.Path] = None):
    if uploads_dir is None:
        uploads_dir = Dispatch.uploads_dir_default
    delta_time_for_delete = datetime.timedelta(minutes=delete_time_min)
    only_files = [os.path.join(uploads_dir, f) for f in os.listdir(uploads_dir)
                  if os.path.isfile(os.path.join(uploads_dir, f))]
    for file in only_files:
        if is_expired(path=file, delta_time=delta_time_for_delete):
            os.remove(file)
            print(f'Zip file deleted at: {file}')


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
    parser.add_argument('--zip-test', dest='zip_test', action='store_true',
                        help="Creates test zip file.")
    parser.add_argument('--no-zip-test', dest='zip_test', action='store_false', default=True,
                        help="Default - Does NOT preform the test zip file creation.")
    parser.add_argument('--test-run', dest='test_run', action='store_true',
                        help='Only upload to the MySQL test database, but does not upload to the ' +
                             'production database.')
    parser.add_argument('--no-test-run', dest='test_run', action='store_false', default=True,
                        help='Default - Upload to the MySQL production database after a successful writing to the ' +
                             'test database.')
    parser.add_argument('--zip-delete-old', dest='zip_delete_old', action='store_true',
                        help='Deletes old zip files from the uploads directory.')
    parser.add_argument('--no-zip-delete-old', dest='zip_delete_old', action='store_false', default=True,
                        help='Default - Does NOT delete old zip files from the uploads directory.')

    # parse the arguments
    args = parser.parse_args()

    # do the work
    if args.write_upload:
        write_upload_files()
    elif args.write_sql:
        write_sql(do_update_schemas=not args.test_run)
    if args.zip_test:
        zip_test()
    if args.zip_delete_old:
        zip_delete_old()

    print(f'Done with the script in {os.path.basename(__file__)}, args: {args}')
