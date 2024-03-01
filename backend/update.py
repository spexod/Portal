from science.db.init import init_databases
from science.db.sql import update_mode
from science.analyze.prescriptions import sql_update

if __name__ == "__main__":
    print(f'Updating the the database with update_mode={update_mode}')
    init_databases()
    sql_update(upload_sql=True, write_plots=False, target_file=None,
               do_update_schemas=False, update_mode=update_mode)