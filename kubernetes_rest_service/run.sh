#!/bin/sh
set -u -e

echo "Running migrations ..."
python app/manage.py migrate

echo "Starting Gunicorn ..."
gunicorn \
  --workers 4 \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  app.config.wsgi
