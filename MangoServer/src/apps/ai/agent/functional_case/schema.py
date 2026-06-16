# -*- coding: utf-8 -*-
from src.apps.ai.agent.roles import AgentRole
from src.apps.ai.agent.skill.service import AgentSkillService


CASE_SCHEMA_PROMPT = """输出必须是 JSON object。
顶层字段：
- suite: object
- cases: array
- warnings: array

cases 每一项必须包含：
- case_no: string，用例编号。统一按 FT-{四位序号} 生成，例如 FT-0001、FT-0002；不要使用模块缩写，不要使用原始文档中的 TC-* 编号。
- title: string，用例标题。
- precondition: string，前置条件。
- test_point: string，测试点。
- test_data: string，测试数据。
- test_types: number[]，多选。
- priority: number。
- scenario_layer: number。
- scenario_type: number。
- scenario_tags: number[]。
- remark: string。
- source_text: string，原文片段或生成依据。

枚举只能使用平台 value：
测试类型 test_types：0=手工测试，1=API自动化，2=UI自动化，3=Pytest自动化，4=性能测试，5=监控任务。
优先级 priority：0=高(P0)，1=中(P1)，2=低(P2)，3=极低(P3)。
场景层级 scenario_layer：0=接口/组件层，1=Integration集成，2=E2E端到端。
场景类型 scenario_type：0=正常场景，1=异常场景，2=边界场景，3=权限场景，4=数据场景，5=流程场景。
场景标签 scenario_tags：0=冒烟，1=回归，2=主流程，3=核心链路，4=高频，5=阻塞，6=生产巡检，10=生产回归。

重要规则：
- 必须完整生成，不允许只生成前 10 条，不允许示例化，不允许省略。
- 如果原文已有 80 条用例，最终 cases 应接近或等于原文数量；如认为合并，必须在 warnings 说明。
- 每条用例都必须可落库，不能使用中文枚举、英文枚举或 null 写入数字枚举字段。
"""

ROLE_PROMPTS = {
    AgentRole.BUSINESS_TEST_EXPERT: AgentRole.PROMPTS[AgentRole.BUSINESS_TEST_EXPERT],
    AgentRole.API_AUTOMATION_EXPERT: AgentRole.PROMPTS[AgentRole.API_AUTOMATION_EXPERT],
}


def build_system_prompt(skill, ai_role: str | None) -> str:
    role_key = AgentRole.normalize(ai_role, AgentRole.BUSINESS_TEST_EXPERT)
    role = ROLE_PROMPTS.get(role_key) or ROLE_PROMPTS[AgentRole.BUSINESS_TEST_EXPERT]
    skill_prompt = AgentSkillService.build_skill_prompt(skill)
    return "\n\n".join([role, CASE_SCHEMA_PROMPT, skill_prompt]).strip()
