"""质量效能报告消息构造器。静态正文由 YAML catalog 管理。"""

from src.common.prompts import get_prompt

_SUMMARY_PROMPT = get_prompt("report.quality_effectiveness.summary")
_INSIGHT_PROMPT = get_prompt("report.quality_effectiveness.insight")

QUALITY_EFFECTIVENESS_SUMMARY_PROMPT_VERSION = f"v{_SUMMARY_PROMPT.version}"
QUALITY_EFFECTIVENESS_INSIGHT_PROMPT_VERSION = f"v{_INSIGHT_PROMPT.version}"
QUALITY_EFFECTIVENESS_INSIGHT_CONFIGS = dict(_INSIGHT_PROMPT.values["configs"])


def build_quality_effectiveness_summary_messages(payload: str) -> list[dict]:
    return [
        {"role": "system", "content": _SUMMARY_PROMPT.system},
        {"role": "user", "content": _SUMMARY_PROMPT.render("user", payload=payload)},
    ]


def build_quality_effectiveness_insight_messages(key: str, payload: str) -> list[dict]:
    config = QUALITY_EFFECTIVENESS_INSIGHT_CONFIGS[key]
    return [
        {
            "role": "system",
            "content": _INSIGHT_PROMPT.render(
                "system",
                title=config["title"],
                focus=config["focus"],
            ),
        },
        {"role": "user", "content": _INSIGHT_PROMPT.render("user", payload=payload)},
    ]
