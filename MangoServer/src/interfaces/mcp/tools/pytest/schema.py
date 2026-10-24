from __future__ import annotations

from mangotools.enums import TaskEnum

from src.apps.auto_pytest.enums import PytestAssetStatusEnum, PytestCasePublicationStatusEnum
from src.apps.test_center.enums import CaseLevelEnum
from src.apps.test_center.enums.environment import EnvironmentEnum
from src.interfaces.mcp.common import ok
from .helpers import (
    FileStatusEnum,
    PytestSourceStatusEnum,
)
from .helpers import _enum_options


def register_schema_tools(mcp):
    @mcp.tool()
    def get_pytest_automation_schema() -> dict:
        """返回 Pytest MCP 字段、枚举、文件读写、同步和危险操作说明。"""
        return ok(
            {
                "enums": {
                    "file_status": _enum_options(FileStatusEnum),
                    "source_status": _enum_options(PytestSourceStatusEnum),
                    "asset_status": _enum_options(PytestAssetStatusEnum),
                    "publication_status": _enum_options(PytestCasePublicationStatusEnum),
                    "case_level": _enum_options(CaseLevelEnum),
                    "task_status": _enum_options(TaskEnum),
                    "environment": _enum_options(EnvironmentEnum),
                },
                "pytest_product_fields": {
                    "project_product_id": "Mango 项目产品 ID，保存到 PytestProduct.project_product。",
                    "repository_id": "PytestRepository.id，用于指定代码仓库。",
                    "name": "Pytest 项目展示名。",
                    "file_name": "项目目录相对于 Git 仓库根目录的路径，例如 auto_tests/ui/bdd_ui。",
                    "init_file": "__init__.py 相对路径。",
                    "auto_type": "自动化类型，沿用页面保存值。",
                    "test_dir": "list[str]，扫描测试文件的目录配置。",
                    "working_directory": "执行 pytest 时相对于仓库根目录的工作目录。",
                },
                "pytest_case_fields": {
                    "publication_status": "未发布、预发布、已发布；使用 update_pytest_case_publication_status 流转，不能通过资产状态编辑绕过审批。",
                    "project_product_id": "这里指 PytestProduct.id，不是 Mango ProjectProduct.id。",
                    "module_id": "Mango 产品模块 ID。",
                    "case_people_id": "负责人 ID；创建未传时使用当前 MCP APIKey 用户。",
                    "name": "用例名称。",
                    "level": "CaseLevelEnum，0=高、1=中、2=低、3=极低。",
                    "file_status": "FileStatusEnum，0=未绑定、1=已绑定、2=已删除。",
                    "source_status": "源码状态，由仓库同步维护，业务编辑不能修改。",
                    "asset_status": "平台资产状态：草稿、已发布、已停用、已归档或已忽略。",
                    "file_name": "文件名。",
                    "file_path": "py 文件路径。",
                    "feature_file_path": "feature 文件路径，可为空。",
                },
                "file_rules": {
                    "file_type": '只允许 "py" 或 "feature"。',
                    "feature": "file_type=feature 时必须存在 feature_file_path。",
                    "write": "写文件必须先 preview_update_*_impact，再传回 preview_token 和 confirm_text。",
                },
                "sync_rules": {
                    "sync_pytest_products_from_repo": "等价页面拉取代码，只刷新已导入项目，不自动创建项目。",
                    "sync_pytest_cases": "等价页面 pytest/case/update，会扫描仓库并把不存在的文件标记为源码缺失，保留平台业务信息。",
                    "push_pytest_repo": "必须先预览本地 git status/diff 摘要，再二次确认执行 git push。",
                },
            }
        )
