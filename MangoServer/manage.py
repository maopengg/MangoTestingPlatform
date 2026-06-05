#!/usr/bin/env python
import os
import sys


def set_env_from_argv():
    for i, arg in enumerate(list(sys.argv)):
        if arg.startswith('--env='):
            os.environ['DJANGO_ENV'] = arg.split('=', 1)[1]
            del sys.argv[i]
            break


def main():
    """Run administrative tasks."""
    set_env_from_argv()
    from src.common.tools import project_dir

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
    main()
