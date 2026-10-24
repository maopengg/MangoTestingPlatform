import os


def access_log_enabled() -> bool:
    return os.getenv('DJANGO_ENV', 'master') == 'dev'
