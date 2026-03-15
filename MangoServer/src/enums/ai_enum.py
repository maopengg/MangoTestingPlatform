# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: AI写用例相关枚举
# @Author : 毛鹏
from src.enums import BaseEnum


class AiRequirementInputTypeEnum(BaseEnum):
    """需求输入类型"""
    TEXT = 0
    IMAGE = 1
    WORD = 2
    URL = 3

    @classmethod
    def obj(cls):
        return {
            0: "文本",
            1: "图片",
            2: "Word文档",
            3: "URL链接",
        }


class AiRequirementStatusEnum(BaseEnum):
    """需求分析状态（整体流程状态）"""
    PENDING = 0
    SPLITTING = 1
    WAIT_CONFIRM_SPLIT = 2
    GENERATING_POINTS = 3
    WAIT_CONFIRM_POINTS = 4
    GENERATING_CASES = 5
    COMPLETED = 6
    FAILED = 9

    @classmethod
    def obj(cls):
        return {
            0: "待分析",
            1: "拆分需求中",
            2: "待确认拆分",
            3: "生成测试点中",
            4: "待确认测试点",
            5: "生成用例中",
            6: "已完成",
            9: "失败",
        }


class AiConfirmStatusEnum(BaseEnum):
    """子记录确认状态（拆分/测试点通用）"""
    PENDING = 0
    CONFIRMED = 1
    IGNORED = 2

    @classmethod
    def obj(cls):
        return {
            0: "待确认",
            1: "已确认",
            2: "已忽略",
        }


class AiTestPointTypeEnum(BaseEnum):
    """测试点类型"""
    FUNCTIONAL = 0
    BOUNDARY = 1
    EXCEPTION = 2
    PERFORMANCE = 3

    @classmethod
    def obj(cls):
        return {
            0: "功能测试",
            1: "边界测试",
            2: "异常测试",
            3: "性能测试",
        }


class AiCasePriorityEnum(BaseEnum):
    """用例优先级"""
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    CRITICAL = 3

    @classmethod
    def obj(cls):
        return {
            0: "低",
            1: "中",
            2: "高",
            3: "紧急",
        }


class AiCaseTypeEnum(BaseEnum):
    """用例类型"""
    NORMAL = 0
    EXCEPTION = 1
    BOUNDARY = 2

    @classmethod
    def obj(cls):
        return {
            0: "正常用例",
            1: "异常用例",
            2: "边界用例",
        }


class AiCaseStatusEnum(BaseEnum):
    """AI生成用例状态"""
    DRAFT = 0
    VALID = 1
    IGNORED = 2

    @classmethod
    def obj(cls):
        return {
            0: "草稿",
            1: "有效",
            2: "已忽略",
        }


class AiCaseTestResultEnum(BaseEnum):
    """测试结果（开发自测/测试结果/预发结果通用）"""
    NOT_TESTED = 0
    PASS = 1
    FAIL = 2
    BLOCKED = 3
    SKIP = 4

    @classmethod
    def obj(cls):
        return {
            0: "未测试",
            1: "通过",
            2: "失败",
            3: "阻塞",
            4: "跳过",
        }


class AiCaseAutoTagEnum(BaseEnum):
    """自动化标识"""
    NONE = 0
    UI = 1
    API = 2
    UNIT = 3

    @classmethod
    def obj(cls):
        return {
            0: "无需自动化",
            1: "界面自动化",
            2: "接口自动化",
            3: "单元测试",
        }
