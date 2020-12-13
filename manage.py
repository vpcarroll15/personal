#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

import dotenv


ENVIRONMENT_FILE_PATH = os.path.expanduser("~/environment.env")


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "website.settings")
    # Load these environment variables if they exist. We need them to make Django work
    # in the cloud.
    if os.path.exists(ENVIRONMENT_FILE_PATH):
        dotenv.load_dotenv(ENVIRONMENT_FILE_PATH, override=True)
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
