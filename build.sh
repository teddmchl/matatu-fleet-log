#!/usr/bin/env bash
# Build step for a host such as Render: install, collect static files, migrate.
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate
