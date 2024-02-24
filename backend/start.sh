#!/bin/bash
# collect the static files
RUN python manage.py collectstatic --clear --noinput
# add the cron jobs to the Django management, but only after the data is upload to mysql
RUN python manage.py crontab add
# start the cron service
service cron start
# migrate the database to the production tables
python science/db/migrate.py
# start the gunicorn server
gunicorn core.wsgi --bind 0.0.0.0:8000