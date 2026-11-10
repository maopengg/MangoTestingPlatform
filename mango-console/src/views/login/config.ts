import {
  IconFindReplace, IconThunderbolt, IconStorage, IconCalendarClock, IconFile,
  IconSchedule, IconCommand, IconExperiment, IconCodeBlock, IconDashboard,
  IconPlayCircle, IconRobot,
} from '@arco-design/web-vue/es/icon'

export const loginEmailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export const loginCapabilities = [
  { icon: IconFindReplace, title: 'UI自动化', description: '页面、元素、步骤、公共能力与执行链路统一管理' },
  { icon: IconThunderbolt, title: 'API自动化', description: '接口用例、断言、环境变量和场景编排' },
  { icon: IconStorage, title: '数据工厂', description: '实体、关系、变量与测试数据快速构造' },
  { icon: IconCalendarClock, title: '报告分析', description: '执行趋势、失败定位和质量结果追踪' },
  { icon: IconFile, title: '研发协同', description: '迭代、需求、用例、计划与缺陷协同管理' },
  { icon: IconSchedule, title: '任务调度', description: '定时任务、任务组、触发策略与结果通知' },
  { icon: IconCommand, title: '测试配置', description: '项目产品、模块、环境、文件和测试对象配置' },
  { icon: IconExperiment, title: '评测中心', description: '评测数据集、测试用例与评分器管理' },
  { icon: IconCodeBlock, title: 'Pytest自动化', description: '代码用例、Fixture、Allure 和分层架构管理' },
  { icon: IconDashboard, title: '性能测试', description: '压测场景、执行容量和性能结果分析' },
  { icon: IconPlayCircle, title: '监控中心', description: '脚本定时运行、异常预警与监控报告' },
  { icon: IconRobot, title: '智能能力', description: 'Skill、MCP 工具与 AI 任务执行' },
]
