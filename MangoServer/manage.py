#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os

import sys

from src.tools import project_dir


def main():
    """Run administrative tasks."""
    project_dir.init_folder()
    django_env = None
    for i, arg in enumerate(sys.argv):
        if '--env=' in arg:
            django_env = arg.split('=')[1]
            del sys.argv[i]
            break
    os.environ.setdefault('DJANGO_ENV', django_env or 'master')
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.settings')
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
