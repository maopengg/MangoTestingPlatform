# -*- coding: utf-8 -*-
from src.common.enums import BaseEnum


class AiSkillStatusEnum(BaseEnum):
    DRAFT = 0
    PUBLISHED = 1
    DISABLED = 2
    ARCHIVED = 3

    @classmethod
    def obj(cls):
        return {0: "草稿", 1: "已发布", 2: "已停用", 3: "已归档"}


class AiSkillTypeEnum(BaseEnum):
    FUNCTIONAL_TEST = 0
    API_AUTOMATION = 1
    UI_AUTOMATION = 2

    @classmethod
    def obj(cls):
        return {0: "功能测试", 1: "API自动化", 2: "UI自动化"}


class AiMcpStatusEnum(BaseEnum):
    DISABLED = 0
    ENABLED = 1

    @classmethod
    def obj(cls):
        return {0: "停用", 1: "启用"}


class AiMcpTransportTypeEnum(BaseEnum):
    STREAMABLE_HTTP = 0
    SSE = 1
    STDIO = 2

    @classmethod
    def obj(cls):
        return {0: "Streamable HTTP", 1: "SSE", 2: "STDIO"}


class AiMcpAuthTypeEnum(BaseEnum):
    NONE = 0
    BEARER = 1
    API_KEY = 2

    @classmethod
    def obj(cls):
        return {0: "无鉴权", 1: "Bearer Token", 2: "API Key"}


class AiMcpToolRiskLevelEnum(BaseEnum):
    READ = 0
    PREVIEW = 1
    WRITE = 2
    EXECUTE = 3
    DELETE = 4

    @classmethod
    def obj(cls):
        return {
            0: "查询",
            1: "预览",
            2: "写入",
            3: "执行",
            4: "删除/清理",
        }


class AiAgentTaskTypeEnum(BaseEnum):
    FEISHU_IMPORT = 0
    MANUAL_CASE_SYNC = 1
    GENERATE_API_CASE = 2

    @classmethod
    def obj(cls):
        return {0: "飞书文档解析", 1: "同步功能测试Case", 2: "生成API自动化"}


class AiAgentTaskStatusEnum(BaseEnum):
    FAIL = 0
    SUCCESS = 1
    PENDING = 2
    RUNNING = 3
    WAITING_CONFIRM = 4
    PARTIAL_SUCCESS = 5
    CANCELLED = 6

    @classmethod
    def obj(cls):
        return {
            0: "失败",
            1: "成功",
            2: "待开始",
            3: "运行中",
            4: "等待确认",
            5: "部分成功",
            6: "已取消",
        }


class AiAgentToolCallStatusEnum(BaseEnum):
    FAIL = 0
    SUCCESS = 1

    @classmethod
    def obj(cls):
        return {0: "失败", 1: "成功"}
