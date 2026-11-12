from __future__ import annotations

import re


def normalize_element_guidance(
        location_description: str | None,
        surrounding_text: str | None,
) -> tuple[str, str]:
    """兼容旧版将正向周边文字和排除条件混存在同一字段的内容。"""
    positive = str(location_description or "").strip()
    exclusion = str(surrounding_text or "").strip()
    match = re.search(r"[，；。\n](?:排除|不是)", exclusion)
    if not match:
        return positive, exclusion
    legacy_positive = exclusion[:match.start()].strip("，；。 \n")
    exclusion = exclusion[match.end():].strip("，；。 \n")
    if legacy_positive and legacy_positive not in positive:
        positive = "；".join(value for value in (positive, legacy_positive) if value)
    return positive, exclusion


def build_element_description(
        *,
        name: str | None,
        category: str | None,
        location_description: str | None = None,
        surrounding_text: str | None = None,
        legacy_prompt: str | None = None,
) -> str:
    """将结构化元素信息合成为执行器使用的统一定位描述。"""
    location_description, surrounding_text = normalize_element_guidance(
        location_description, surrounding_text,
    )
    has_structured_description = any(
        str(value or "").strip()
        for value in (location_description, surrounding_text)
    )
    if not has_structured_description and str(legacy_prompt or "").strip():
        return str(legacy_prompt).strip()
    values = {
        "元素名称": name,
        "元素分类": category if str(category or "").strip() != "未分类" else None,
        "元素位置与周边文字": location_description,
        "排除项": surrounding_text,
        "补充描述": legacy_prompt,
    }
    parts = [
        f"{label}：{str(value).strip()}"
        for label, value in values.items()
        if str(value or "").strip()
    ]
    return "\n".join(parts)
