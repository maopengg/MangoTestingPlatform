"""Render legacy evaluation notes as the case's scenario description."""


def scenario_description(description, assessment=None):
    sections = [description.strip()] if isinstance(description, str) and description.strip() else []
    if isinstance(assessment, dict):
        for key, label in (("objective", "测评目标"), ("scope", "覆盖范围"), ("exclusions", "不覆盖"), ("score_interpretation", "评分口径")):
            value = assessment.get(key)
            if isinstance(value, list):
                value = "；".join(str(item) for item in value if item)
            if isinstance(value, str) and value.strip():
                section = f"{label}：{value.strip()}"
                if not any(section in existing for existing in sections):
                    sections.append(section)
    return "\n\n".join(sections)


def case_description(case):
    return scenario_description(getattr(case, "description", None), (getattr(case, "config", None) or {}).get("assessment"))
