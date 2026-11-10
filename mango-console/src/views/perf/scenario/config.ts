export const scenarioColumns = [
  { title: 'ID', key: 'index', dataIndex: 'index', width: 80, align: 'center' },
  { title: '场景名称', key: 'name', dataIndex: 'name', width: 220, ellipsis: true, tooltip: true },
  { title: '负载模型', key: 'load_type', dataIndex: 'load_type', width: 120, align: 'center' },
  { title: '目标负载', key: 'load_target', dataIndex: 'load_target', width: 130, align: 'center' },
  {
    title: '持续时间',
    key: 'duration_seconds',
    dataIndex: 'duration_seconds',
    width: 100,
    align: 'center',
  },
  { title: '步骤', key: 'step_count', dataIndex: 'step_count', width: 80, align: 'center' },
  {
    title: '执行器数',
    key: 'default_executor_count',
    dataIndex: 'default_executor_count',
    width: 100,
    align: 'center',
  },
  { title: '状态', key: 'status', dataIndex: 'status', width: 90, align: 'center' },
  { title: '更新时间', key: 'update_time', dataIndex: 'update_time', width: 180, align: 'center' },
  { title: '项目/产品', key: 'project_product', dataIndex: 'project_product', width: 140 },
  { title: '模块', key: 'module', dataIndex: 'module', width: 220, ellipsis: true, tooltip: true },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    width: 140,
    align: 'center',
    fixed: 'right',
  },
]

export const loadTypeOptions = [
  { label: '并发用户', value: 'concurrency' },
  { label: '到达率', value: 'arrival_rate' },
  { label: '迭代率', value: 'iteration_rate' },
]

export const loadProfileOptions = [
  { label: '固定并发 · 指定人数持续运行', value: 'constant_concurrency' },
  { label: '定量任务 · 完成指定 Case 次数', value: 'fixed_iterations' },
  { label: '阶梯加压 · 每隔一段时间增加并发', value: 'staircase' },
  { label: '线性爬坡 · 平滑增加并发', value: 'linear_ramp' },
  { label: '突刺测试 · 短时跃升后恢复', value: 'spike' },
  { label: '长稳态测试 · 固定并发持续观察', value: 'soak' },
  { label: '固定到达率 · 按速率启动 Case', value: 'constant_arrival_rate' },
  { label: '固定迭代率 · 每秒启动指定 Case', value: 'constant_iteration_rate' },
]

export const engineOptions = [{ label: 'k6', value: 'k6' }]

export const scenarioScrollX = 1620
