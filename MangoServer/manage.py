#!/usr/bin/env python
import os
import sys
from src.tools import project_dir


def main():
    """Run administrative tasks."""
    print('如出现：You have 1 unapplied migration(s). Your project may not work properly until you apply the migrations for app(s): auto_api. 请执行：python manage.py migrate  进行迁移')
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
