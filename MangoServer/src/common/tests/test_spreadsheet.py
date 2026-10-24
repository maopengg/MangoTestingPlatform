from io import BytesIO

from django.test import SimpleTestCase
from openpyxl import Workbook

from src.common.utils.spreadsheet import read_excel_records


class SpreadsheetReaderTests(SimpleTestCase):
    @staticmethod
    def _workbook_bytes(rows) -> BytesIO:
        workbook = Workbook()
        worksheet = workbook.active
        for row in rows:
            worksheet.append(row)
        output = BytesIO()
        workbook.save(output)
        workbook.close()
        output.seek(0)
        return output

    def test_reads_first_sheet_with_first_row_as_headers(self):
        excel_file = self._workbook_bytes([
            ["名称", "请求方法", "备注"],
            ["查询接口", "GET", ""],
            ["保存接口", "POST", None],
        ])

        records = read_excel_records(excel_file)

        self.assertEqual([
            {"名称": "查询接口", "请求方法": "GET", "备注": None},
            {"名称": "保存接口", "请求方法": "POST", "备注": None},
        ], records)

    def test_reads_first_sheet_when_another_sheet_is_active(self):
        workbook = Workbook()
        first_sheet = workbook.active
        first_sheet.append(["名称"])
        first_sheet.append(["第一张表的数据"])
        active_sheet = workbook.create_sheet("当前活动页")
        active_sheet.append(["名称"])
        active_sheet.append(["不应读取的数据"])
        workbook.active = 1
        output = BytesIO()
        workbook.save(output)
        workbook.close()
        output.seek(0)

        self.assertEqual(
            [{"名称": "第一张表的数据"}],
            read_excel_records(output),
        )

    def test_ignores_empty_rows_and_unnamed_columns(self):
        excel_file = self._workbook_bytes([
            ["名称", None],
            [None, None],
            ["有效数据", "忽略值"],
        ])

        self.assertEqual([{"名称": "有效数据"}], read_excel_records(excel_file))

    def test_returns_empty_list_for_empty_workbook(self):
        self.assertEqual([], read_excel_records(self._workbook_bytes([])))
