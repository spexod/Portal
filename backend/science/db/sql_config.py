import os

import dotenv


repo_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))
dotenv.load_dotenv(os.path.join(repo_dir, '.env'))

sql_port = "3306"
sql_database = "spexodisks"
sql_host = os.environ.get("MYSQL_HOST", "spexodisks.com")
sql_user = os.environ.get("MYSQL_USER", "username")
sql_password = os.environ.get("MYSQL_PASSWORD", "password")

