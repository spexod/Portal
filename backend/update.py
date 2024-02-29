from science.analyze.prescriptions import sql_update
from science.db.sql_config import update_mode

if __name__ == "__main__":
    print(f'Updating the the database with update_mode={update_mode}')
    sql_update(upload_sql=True, write_plots=False, target_file=None,
               do_update_schemas=False)