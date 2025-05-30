from science.analyze.prescriptions import update_schemas
from science.db.data_status import set_data_status_mysql


def do_migration():
    # migrate the metadata and spectra tables.
    update_schemas(delete_spectra_tables=False)
    # update the states in the MySQL service
    set_data_status_mysql(new_data_staged_to_set=False, new_data_commited_to_set=False, updated_mysql_to_set=True)


if __name__ == '__main__':
    from science.db.sql import DATA_MIGRATE_FROM_STAGED
    from science.db.data_status import get_data_status_mysql
    # read the status variables from the MySQL server
    new_data_staged, new_data_commited, updated_mysql = get_data_status_mysql()
    if DATA_MIGRATE_FROM_STAGED and new_data_staged and new_data_commited:
        do_migration()
