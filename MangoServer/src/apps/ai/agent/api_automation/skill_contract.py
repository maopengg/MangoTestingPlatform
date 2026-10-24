# -*- coding: utf-8 -*-
import json

from src.apps.ai.model_gateway.client import AgentModelGateway
from src.apps.ai.services.core import extract_ai_json
from src.common.prompts import get_prompt


class ApiAutomationSkillContractCompiler:
    BASE_REQUIRED = ["api_info", "api_case", "assertion", "execution"]
    ALLOWED_CAPABILITIES = {
        "api_info",
        "api_case",
        "assertion",
        "execution",
        "headers",
        "extractor",
        "data_factory",
        "diagnosis",
    }

    @classmethod
    def compile(cls, skill, skill_version=None, task=None) -> dict:
        if skill_version and skill_version.compiled_contract:
            return cls.normalize(skill_version.compiled_contract, skill)
        contract = None
        try:
            contract = cls.compile_with_model(skill, task=task)
        except Exception:
            contract = cls.compile_fallback(skill)
        contract = cls.normalize(contract, skill)
        if skill_version and skill_version.compiled_contract != contract:
            skill_version.compiled_contract = contract
            skill_version.save(update_fields=["compiled_contract"])
        return contract

    @classmethod
    def compile_with_model(cls, skill, task=None) -> dict:
        prompt = get_prompt("api.automation")
        payload = {
            "task": prompt.values["skill_contract_task"],
            "capabilities": sorted(cls.ALLOWED_CAPABILITIES),
            "platform_required": cls.BASE_REQUIRED,
            "skill": {
                "name": getattr(skill, "name", ""),
                "description": getattr(skill, "description", ""),
                "content": (getattr(skill, "content", "") or "")[:50000],
            },
            "response_schema": prompt.values["skill_contract_response_schema"],
        }
        messages = [
            {
                "role": "system",
                "content": prompt.template("skill_contract_system"),
            },
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ]
        return extract_ai_json(
            AgentModelGateway.json_chat(
                task=task,
                messages=messages,
                temperature=0,
                max_tokens=4000,
            ),
            task=task,
        )

    @classmethod
    def compile_fallback(cls, skill) -> dict:
        content = (getattr(skill, "content", "") or "").lower()
        required = list(cls.BASE_REQUIRED)
        keyword_capabilities = {
            "data_factory": ("数据工厂", "data factory"),
            "extractor": ("提取器", "extractor"),
            "headers": ("请求头", "header"),
            "diagnosis": ("诊断", "diagnos"),
        }
        for capability, keywords in keyword_capabilities.items():
            if any(keyword in content for keyword in keywords):
                required.append(capability)
        return {
            "required_capabilities": required,
            "optional_capabilities": [],
            "forbidden_capabilities": [],
            "ordered_rules": [line.strip() for line in content.splitlines() if line.strip()][:200],
            "completion_rules": ["存在 API Case ID", "至少存在一条断言", "完成一次 API Case 执行"],
            "quality_rules": ["已绑定用例覆盖旧 ID", "MCP 返回的资产必须可查询"],
        }

    @classmethod
    def normalize(cls, contract: dict | None, skill) -> dict:
        value = dict(contract or {})
        required = []
        for item in [*cls.BASE_REQUIRED, *(value.get("required_capabilities") or [])]:
            key = str(item or "").strip().lower()
            if key in cls.ALLOWED_CAPABILITIES and key not in required:
                required.append(key)
        optional = []
        for item in value.get("optional_capabilities") or []:
            key = str(item or "").strip().lower()
            if key in cls.ALLOWED_CAPABILITIES and key not in required and key not in optional:
                optional.append(key)
        forbidden = []
        for item in value.get("forbidden_capabilities") or []:
            key = str(item or "").strip().lower()
            if key in cls.ALLOWED_CAPABILITIES and key not in required and key not in forbidden:
                forbidden.append(key)
        return {
            "required_capabilities": required,
            "optional_capabilities": optional,
            "forbidden_capabilities": forbidden,
            "ordered_rules": [str(item) for item in value.get("ordered_rules") or []][:200],
            "completion_rules": [str(item) for item in value.get("completion_rules") or []]
                                or ["存在 API Case ID", "至少存在一条断言", "完成一次 API Case 执行"],
            "quality_rules": [str(item) for item in value.get("quality_rules") or []]
                             or ["已绑定用例覆盖旧 ID", "MCP 返回的资产必须可查询"],
            "skill_id": getattr(skill, "id", None),
        }
