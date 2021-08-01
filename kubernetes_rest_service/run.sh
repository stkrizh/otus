#!/bin/sh
set -u -e

echo "Running migrations ..."
python app/manage.py migrate

echo "Starting Gunicorn ..."
gunicorn \
  --worker-class gthread \
  --threads 8 \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  app.config.wsgi
