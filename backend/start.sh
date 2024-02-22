#!/bin/bash
service cron start
python science/db/migrate.py
gunicorn core.wsgi --bind 0.0.0.0:8000