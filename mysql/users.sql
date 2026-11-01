-- Two database accounts instead of root (run through mysql/create-users.sh, which fills in the
-- passwords from .env and executes this as root inside the mysqlDB container).
--
--   spexo_api       the API (Django, gunicorn): reads the catalogue schemas, reads and writes the
--                   users schema (accounts, sessions, refresh tokens, password-reset tokens).
--   spexo_pipeline  the data pipeline (update.py, commit_data.py) and the backend's start-up steps
--                   (schema init, Django migrations, moving staged tables live): owns the catalogue
--                   schemas, the staging new_* schemas, data_status and temp, and the users schema.
--
-- Neither account has global privileges: no access to the mysql system schema, no GRANT OPTION, no
-- FILE, PROCESS or SUPER. Both require TLS (the clients already use it, see science/db/sql.py).
-- The statements are idempotent: running the file again resets the passwords and the grants.

CREATE USER IF NOT EXISTS '__API_USER__'@'%' IDENTIFIED BY '__API_PASSWORD__' REQUIRE SSL;
ALTER USER '__API_USER__'@'%' IDENTIFIED BY '__API_PASSWORD__' REQUIRE SSL;
REVOKE ALL PRIVILEGES, GRANT OPTION FROM '__API_USER__'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON `users`.* TO '__API_USER__'@'%';
GRANT SELECT ON `spexodisks`.* TO '__API_USER__'@'%';
GRANT SELECT ON `spectra`.* TO '__API_USER__'@'%';
GRANT SELECT ON `stacked_line_spectra`.* TO '__API_USER__'@'%';
-- the staged tables, read by the API only when API_USE_NEW_TABLES=true (test and upload computers)
GRANT SELECT ON `new_spexodisks`.* TO '__API_USER__'@'%';
GRANT SELECT ON `new_spectra`.* TO '__API_USER__'@'%';
GRANT SELECT ON `new_stacked_line`.* TO '__API_USER__'@'%';

CREATE USER IF NOT EXISTS '__PIPELINE_USER__'@'%' IDENTIFIED BY '__PIPELINE_PASSWORD__' REQUIRE SSL;
ALTER USER '__PIPELINE_USER__'@'%' IDENTIFIED BY '__PIPELINE_PASSWORD__' REQUIRE SSL;
REVOKE ALL PRIVILEGES, GRANT OPTION FROM '__PIPELINE_USER__'@'%';
-- "ALL" at the schema level: CREATE (also creates the schema itself), DROP, ALTER, INDEX, REFERENCES,
-- SELECT, INSERT, UPDATE, DELETE, ... but nothing global and no GRANT OPTION
GRANT ALL PRIVILEGES ON `users`.* TO '__PIPELINE_USER__'@'%';
GRANT ALL PRIVILEGES ON `spexodisks`.* TO '__PIPELINE_USER__'@'%';
GRANT ALL PRIVILEGES ON `spectra`.* TO '__PIPELINE_USER__'@'%';
GRANT ALL PRIVILEGES ON `stacked_line_spectra`.* TO '__PIPELINE_USER__'@'%';
GRANT ALL PRIVILEGES ON `new_spexodisks`.* TO '__PIPELINE_USER__'@'%';
GRANT ALL PRIVILEGES ON `new_spectra`.* TO '__PIPELINE_USER__'@'%';
GRANT ALL PRIVILEGES ON `new_stacked_line`.* TO '__PIPELINE_USER__'@'%';
GRANT ALL PRIVILEGES ON `data_status`.* TO '__PIPELINE_USER__'@'%';
GRANT ALL PRIVILEGES ON `temp`.* TO '__PIPELINE_USER__'@'%';

SHOW GRANTS FOR '__API_USER__'@'%';
SHOW GRANTS FOR '__PIPELINE_USER__'@'%';

-- After every client uses the new accounts (the server's .env, the upload computer's .env), root can
-- be taken off the network. Root stays usable inside the container (mysql/upgrade.sh connects there):
--   DROP USER IF EXISTS 'root'@'%';
