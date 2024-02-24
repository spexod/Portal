import os

from mysql.connector import ProgrammingError

from science.analyze.spectrum import var_is_true
from science.db.data_status import set_data_status_mysql, get_data_status_mysql
from science.db.sandbox import write_sql, write_upload_files, copy_django_tables, init_django_tables


DATA_RESET_UPLOAD = var_is_true(os.environ.get("DATA_RESET_UPLOAD", False))
# read the status variables from the MySQL server
new_data_staged, updated_mysql = get_data_status_mysql()


def upload_data():
    if DATA_RESET_UPLOAD or not new_data_staged:
        set_data_status_mysql(new_data_staged_to_set=False, updated_mysql_to_set=False)
        # try to test with the user database tables by copying them.
        try:
            copy_django_tables()
        except ProgrammingError:
            init_django_tables(new_schema=True)
        # no new data is staged and the database schemas and the parameter MySQL database do not have up-to-date status
        write_sql(do_update_schemas=False)
        # update the states in the MySQL service
        set_data_status_mysql(new_data_staged_to_set=True, updated_mysql_to_set=False)
    # File Upload: these are spectra files that only exist in the docker image and must be remade at build-time
    write_upload_files()


if __name__ == "__main__":
    upload_data()