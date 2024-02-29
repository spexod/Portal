import os

import dotenv


repo_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))
env_path = os.path.join(repo_dir, '.env')
if os.path.exists(env_path):
    dotenv.load_dotenv(env_path)


def str_is_true(s: str) -> bool:
    return s.lower() in ["true", "yes", "1"]

sql_port = "3306"
sql_database = "spexodisks"
sql_host = os.environ.get("MYSQL_HOST", "spexodisks.com")
sql_user = os.environ.get("MYSQL_USER", "username")
sql_password = os.environ.get("MYSQL_PASSWORD", "password")
upload_dir = os.environ.get("UPLOAD_DIR", "/opt/bitnami/projects/backend/output")
update_mode = str_is_true(os.environ.get("DATA_NEW_UPLOADS_ONLY", "true"))
if str_is_true(os.environ.get("API_USE_NEW_TABLES", 'true')):
    schema_prefix = 'new_'
else:
    schema_prefix = ''

