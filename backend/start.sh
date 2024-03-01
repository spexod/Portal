#!/bin/bash
# initialize the databases, if not already initialized
python science/db/init.py
# migrate the Django database and tables
python manage.py makemigrations djangoAPI
python manage.py migrate
# collect the static files
python manage.py collectstatic --clear --noinput
# add the cron jobs to the Django management, but only after the data is upload to mysql
python manage.py crontab add
# start the cron service
service cron start
# migrate the database to the production tables if the database is staged and triggered
python science/db/migrate.py
# start the gunicorn server
gunicorn core.wsgi --bind 0.0.0.0:8000