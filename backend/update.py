from science.analyze.prescriptions import web_update
from science.db.sql_config import update_mode

if __name__ == "__main__":
    print(f'Updating the the database with update_mode={update_mode}')
    web_update(update_mode=update_mode)