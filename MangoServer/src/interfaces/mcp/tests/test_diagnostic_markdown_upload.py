from asgiref.sync import async_to_sync
from django.test import SimpleTestCase
from fastmcp import FastMCP

from src.interfaces.mcp.tools.report.test_report import register_test_report_tools
from src.interfaces.mcp.tools.scheduled_task.task import register_scheduled_task_tools


class DiagnosticMarkdownUploadToolTests(SimpleTestCase):
    def test_upload_tools_only_accept_markdown_file_names(self):
        mcp = FastMCP('diagnostic-markdown-upload-test')
        register_test_report_tools(mcp)
        register_scheduled_task_tools(mcp)

        tools = {
            tool.name: tool
            for tool in async_to_sync(mcp.list_tools)(run_middleware=False)
        }

        for tool_name in (
                'upload_test_report_diagnostic_markdown',
                'upload_scheduled_task_diagnostic_markdown',
        ):
            with self.subTest(tool_name=tool_name):
                file_name_schema = tools[tool_name].parameters['properties']['file_name']
                self.assertEqual(file_name_schema['pattern'], r'.*\.[mM][dD]$')
                self.assertIn('必须以 .md 结尾', file_name_schema['description'])
