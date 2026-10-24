from __future__ import annotations

from typing import BinaryIO

from openpyxl import load_workbook


def read_excel_records(file_object: BinaryIO) -> list[dict]:
    """Read the active worksheet into dictionaries without a dataframe dependency."""
    workbook = load_workbook(file_object, read_only=True, data_only=True)
    try:
        # pandas.read_excel() previously read the first worksheet by default.
        # Keep that behavior even when the workbook was saved with another
        # worksheet selected as active.
        rows = workbook.worksheets[0].iter_rows(values_only=True)
        headers = next(rows, None)
        if not headers:
            return []

        records = []
        for values in rows:
            record = {
                header: None if value == "" else value
                for header, value in zip(headers, values)
                if header is not None
            }
            if any(value is not None for value in record.values()):
                records.append(record)
        return records
    finally:
        workbook.close()


__all__ = ["read_excel_records"]
