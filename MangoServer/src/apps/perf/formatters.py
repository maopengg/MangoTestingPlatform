from datetime import datetime

PERF_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def format_perf_datetime(value: datetime | None) -> str | None:
    return value.strftime(PERF_DATETIME_FORMAT) if value else None


def format_perf_row_datetimes(row: dict) -> dict:
    return {
        key: format_perf_datetime(value) if isinstance(value, datetime) else value
        for key, value in row.items()
    }
