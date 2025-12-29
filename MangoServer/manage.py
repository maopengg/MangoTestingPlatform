#!/usr/bin/env python
import os
import sys
from django.core.management import call_command
from src.tools import project_dir

def set_env():
    for i, arg in enumerate(sys.argv):
        if '--env=' in arg:
            os.environ['DJANGO_ENV'] = arg.split('=')[1]
            del sys.argv[i]
            break


def migrate():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.settings')
    import django
    django.setup()
    call_command('migrate', '--noinput')


def main():
    """Run administrative tasks."""
    project_dir.init_folder()
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
    set_env()
    main()