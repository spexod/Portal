#!/bin/bash
# migrate the database to the production tables if the database is staged and triggered
python science/db/migrate.py
# start the gunicorn server
gunicorn core.wsgi --bind 0.0.0.0:8000