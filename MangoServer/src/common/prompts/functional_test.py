from src.common.prompts import get_prompt

_PROMPT = get_prompt("functional.case")
FUNCTIONAL_CASE_PROMPT_VERSION = _PROMPT.version
FUNCTIONAL_CASE_SCHEMA_PROMPT = _PROMPT.system
DEFAULT_FUNCTIONAL_CASE_SKILL_CONTENT = _PROMPT.template("default_skill")


def render_functional_case_prompt(template: str, **variables) -> str:
    return _PROMPT.render(template, **variables)
