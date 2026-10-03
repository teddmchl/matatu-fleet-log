#!/usr/bin/env python
# ==============================================================================
# DJANGO CLI ENTRY POINT (manage.py)
# ==============================================================================
# Role:
#   Command-line utility for administrative tasks across the project.
#   Created at repo root because we initialized with "django-admin startproject config ."
#
# Common Commands:
#   - python manage.py runserver     : Starts the local development server (localhost:8000)
#   - python manage.py migrate       : Applies database migrations (created 18 default tables)
#   - python manage.py makemigrations: Generates migration files when models change
#   - python manage.py createsuperuser: Creates an administrative user for /admin/
#   - python manage.py startapp <app>: Scaffolds a new application component
# ==============================================================================
import os
import sys


def main():
    """Run administrative tasks."""
    # Points Django to the project configuration settings package
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()

