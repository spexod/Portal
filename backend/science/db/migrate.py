"""
Move the staged new_* tables into the live schemas (see update_schema_map in sql_tables.py).

Runs at container start from docker-entrypoint.sh when DATA_MIGRATE_FROM_STAGED=true, and only when
an upload was staged (update.py) and committed (commit_data.py). A MySQL named lock makes sure two
containers starting at the same time do not both migrate.
"""
from science.analyze.prescriptions import update_schemas
from science.db.sql import LoadSQL, DATA_MIGRATE_FROM_STAGED
from science.db.data_status import set_data_status_mysql, get_data_status_mysql

MIGRATION_LOCK = 'spexodisks_migration'


def migration_is_due() -> bool:
    new_data_staged, new_data_commited, updated_mysql = get_data_status_mysql()
    return DATA_MIGRATE_FROM_STAGED and new_data_staged and new_data_commited


def do_migration() -> bool:
    """Migrate if due; returns True when this call did the migration."""
    with LoadSQL(auto_connect=True, verbose=False) as lock_sql:
        if not lock_sql.get_lock(MIGRATION_LOCK, timeout_seconds=0):
            print("Migration skipped: another process is migrating the staged tables.")
            return False
        try:
            # the status may have changed while waiting for the lock
            if not migration_is_due():
                return False
            # migrate the metadata and spectra tables.
            update_schemas(delete_spectra_tables=False)
            # update the states in the MySQL service
            set_data_status_mysql(new_data_staged_to_set=False, new_data_commited_to_set=False, updated_mysql_to_set=True)
            return True
        finally:
            lock_sql.release_lock(MIGRATION_LOCK)


if __name__ == '__main__':
    # do_migration checks whether a migration is due (under the lock) and returns False when it did nothing
    if do_migration():
        print("Staged data migrated to the live schemas.")
    else:
        print("No staged and committed data to migrate.")
