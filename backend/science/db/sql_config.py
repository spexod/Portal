import os

import dotenv


repo_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))
env_path = os.path.join(repo_dir, '.env')
if os.path.exists(env_path):
    dotenv.load_dotenv(env_path)

sql_port = "3306"
sql_database = "spexodisks"
sql_host = os.environ.get("MYSQL_HOST", "spexodisks.com")
sql_user = os.environ.get("MYSQL_USER", "username")
sql_password = os.environ.get("MYSQL_PASSWORD", "password")
target_dir = os.environ.get("TARGET_DIR", "/home/ubuntu/spexodisks")

