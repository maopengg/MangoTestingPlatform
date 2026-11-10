import type { TableColumnData } from '@arco-design/web-vue'
import type { TablePropsType } from '@/types/components'

export const colorTokens = [
  { name: 'Primary', value: 'var(--m-primary)' },
  { name: 'Primary Soft', value: 'var(--m-primary-soft)' },
  { name: 'Background', value: 'var(--m-bg)' },
  { name: 'Surface', value: 'var(--m-surface)' },
  { name: 'Border', value: 'var(--m-border)' },
  { name: 'Text', value: 'var(--m-text)' },
  { name: 'Success', value: 'var(--m-success)' },
  { name: 'Danger', value: 'var(--m-danger)' },
  { name: 'Warning', value: 'var(--m-warning)' },
  { name: 'Muted', value: 'var(--m-muted)' },
]

export const customColumns: TablePropsType[] = [
  { title: '用例名称', key: 'name', sortIndex: 0, checked: true },
  { title: '接口名称', key: 'apiName', sortIndex: 1, checked: true },
  { title: '执行环境', key: 'env', sortIndex: 2, checked: true },
  { title: '测试结果', key: 'status', sortIndex: 3, checked: true },
  { title: '更新时间', key: 'updatedAt', sortIndex: 4, checked: true },
]

export const assertionResultItems = [
  {
    method: '状态码等于',
    actual: '500',
    expect: '200',
    ass_msg: '状态码断言失败，接口返回服务器异常，请检查订单服务日志',
    status: 0,
  },
  {
    method: '响应字段包含',
    actual: 'order_no, status, amount',
    expect: 'order_no',
    ass_msg: '响应字段存在',
    status: 1,
  },
]

export const keyValueItems = [
  { key: 'Authorization', value: 'Bearer ********', type: 'Header', color: 'blue' },
  { key: 'order_no', value: '${orderNo}', type: 'Param', color: 'green' },
  { key: 'cleanup', value: 'after_case', type: 'Config', color: 'orange' },
]

export const progressItems = [
  { label: 'UI 自动化', percent: 0.76 },
  { label: 'API 自动化', percent: 0.92 },
  { label: 'Pytest', percent: 0.58 },
]

export const statusOptions = [
  { label: '成功', value: 'success' },
  { label: '失败', value: 'fail' },
  { label: '进行中', value: 'running' },
]

export const productOptions = [
  {
    label: 'Mango 平台',
    value: 'mango',
    children: [
      { label: '控制台', value: 'console' },
      { label: '执行器', value: 'actuator' },
    ],
  },
]

export const treeData = [
  {
    key: 'team',
    title: '测试团队',
    children: [
      { key: 'admin', title: 'Admin' },
      { key: 'tester', title: 'Tester' },
    ],
  },
]

export const columns: TableColumnData[] = [
  { title: 'ID', dataIndex: 'id', width: 90 },
  {
    title: '用例名称',
    dataIndex: 'name',
    width: 220,
    ellipsis: true,
    tooltip: true,
    align: 'left',
  },
  {
    title: '模块名称',
    dataIndex: 'module',
    width: 150,
    ellipsis: true,
    tooltip: true,
    align: 'left',
  },
  { title: '等级', slotName: 'level', width: 100 },
  { title: '维护人', dataIndex: 'owner', width: 110 },
  { title: '状态', slotName: 'status', width: 110 },
  { title: '启用', slotName: 'enabled', width: 90 },
  { title: '更新时间', dataIndex: 'updatedAt', width: 180 },
  { title: '说明', dataIndex: 'description', width: 260, ellipsis: true, tooltip: true, align: 'left' },
  { title: '操作', slotName: 'actions', fixed: 'right', width: 140 },
]

export const sampleRows = [
  {
    id: '10421',
    name: '订单创建主流程校验',
    module: '订单中心',
    level: 'P0',
    levelColor: 'red',
    owner: 'Admin',
    status: '成功',
    statusColor: 'green',
    enabled: true,
    updatedAt: '2026-05-22 10:32:08',
    description: '覆盖创建订单、库存冻结、支付单生成等关键链路。',
  },
  {
    id: '10422',
    name: '支付回调签名异常场景',
    module: '支付中心',
    level: 'P1',
    levelColor: 'orange',
    owner: 'Mango',
    status: '失败',
    statusColor: 'red',
    enabled: true,
    updatedAt: '2026-05-22 10:34:19',
    description: '断言失败：response.code 期望为 200，实际为 500。',
  },
  {
    id: '10423',
    name: '用户权限边界校验',
    module: '用户权限',
    level: 'P1',
    levelColor: 'orange',
    owner: 'Tester',
    status: '进行中',
    statusColor: 'blue',
    enabled: false,
    updatedAt: '2026-05-22 10:38:01',
    description: '验证角色、菜单、接口权限的组合边界。',
  },
]

export const messages = [
  { type: 'info', title: '通知中心', content: '用于展示 WebSocket 消息、系统通知和执行提醒。' },
  { type: 'success', title: '执行完成', content: '成功反馈轻量出现，不打断用户继续排查。' },
  { type: 'danger', title: '异常提示', content: '失败信息保留红色语义，但避免大面积警告色。' },
]

export const statisticItems = [
  { label: '今日执行', value: 128, precision: 0, trend: '+12%', color: 'blue' },
  { label: '成功率', value: 96.8, precision: 1, trend: '稳定', color: 'green' },
  { label: '失败用例', value: 7, precision: 0, trend: '需关注', color: 'red' },
  { label: '平均耗时', value: 2.35, precision: 2, trend: '秒', color: 'orange' },
]

export const trendItems = [
  { week: 'W1', success: 82, fail: 14 },
  { week: 'W2', success: 104, fail: 18 },
  { week: 'W3', success: 76, fail: 10 },
  { week: 'W4', success: 118, fail: 16 },
  { week: 'W5', success: 94, fail: 20 },
  { week: 'W6', success: 126, fail: 12 },
  { week: 'W7', success: 108, fail: 8 },
  { week: 'W8', success: 132, fail: 15 },
]

export const rankItems = [
  { name: '订单中心', value: 96, count: 428 },
  { name: '支付中心', value: 78, count: 352 },
  { name: '用户权限', value: 62, count: 286 },
  { name: '数据工厂', value: 48, count: 214 },
  { name: '监控任务', value: 36, count: 168 },
]

export const chartStatusItems = [
  { label: '成功', value: 963, percent: 88, type: 'success' },
  { label: '失败', value: 42, percent: 28, type: 'danger' },
  { label: '进行中', value: 18, percent: 18, type: 'running' },
]

export const auditGroups = [
  {
    title: 'Token 使用',
    status: '必需',
    color: 'blue',
    items: ['页面背景使用 --m-bg', '卡片面板使用 --m-surface', '状态反馈使用语义 token'],
  },
  {
    title: '组件覆盖',
    status: '已覆盖',
    color: 'green',
    items: [
      'Arco 表格、表单、弹窗、抽屉读取主题',
      '自定义组件读取 --m-*',
      '图表监听主题变化刷新',
    ],
  },
  {
    title: '允许例外',
    status: '受控',
    color: 'orange',
    items: ['代码高亮保留 PyCharm 风格', '业务枚举色可保留', '图表 fallback 仅作兜底'],
  },
  {
    title: '验收页面',
    status: '建议',
    color: 'purple',
    items: ['登录页', '首页', '报告详情', 'API/UI 详情', '系统设置与数据工厂'],
  },
]

export const notificationItems = [
  {
    title: '执行器节点 online-runner-01',
    description: 'Windows / Chrome 126 / 空闲中',
    avatar: 'UI',
    color: 'var(--m-primary)',
    status: '在线',
    tagColor: 'green',
  },
  {
    title: '接口回归任务完成',
    description: '128 条用例，失败 7 条，耗时 18m 24s',
    avatar: 'API',
    color: 'var(--m-success)',
    status: '已通知',
    tagColor: 'blue',
  },
  {
    title: 'Pytest 环境依赖异常',
    description: 'requirements.txt 安装失败，等待处理',
    avatar: 'PY',
    color: 'var(--m-danger)',
    status: '异常',
    tagColor: 'red',
  },
]

export const jsonExample = `<span class="syntax-brace">{</span>
<span class="syntax-key">"theme"</span>: <span class="syntax-string">"enterprise-data-dense"</span>,
<span class="syntax-key">"primary"</span>: <span class="syntax-string">"var(--m-primary)"</span>,
<span class="syntax-key">"surface"</span>: <span class="syntax-string">"var(--m-surface)"</span>,
<span class="syntax-key">"table"</span>: <span class="syntax-brace">{</span>
  <span class="syntax-key">"bordered"</span>: <span class="syntax-bool">false</span>,
  <span class="syntax-key">"hover"</span>: <span class="syntax-string">"var(--m-primary-soft)"</span>,
  <span class="syntax-key">"density"</span>: <span class="syntax-string">"compact"</span>
<span class="syntax-brace">}</span>
<span class="syntax-brace">}</span>`

export const pythonExample = `<span class="syntax-keyword">import</span> <span class="syntax-module">pytest</span>


<span class="syntax-keyword">def</span> <span class="syntax-function">test_create_order</span><span class="syntax-brace">(</span>api_client, order_payload<span class="syntax-brace">)</span>:
  response = api_client.<span class="syntax-method">post</span><span class="syntax-brace">(</span><span class="syntax-string">"/api/orders"</span>, json=order_payload<span class="syntax-brace">)</span>
  body = response.<span class="syntax-method">json</span><span class="syntax-brace">()</span>

  <span class="syntax-keyword">assert</span> response.status_code == <span class="syntax-number">200</span>
  <span class="syntax-keyword">assert</span> body<span class="syntax-brace">[</span><span class="syntax-string">"code"</span><span class="syntax-brace">]</span> == <span class="syntax-number">0</span>
  <span class="syntax-keyword">assert</span> body<span class="syntax-brace">[</span><span class="syntax-string">"data"</span><span class="syntax-brace">][</span><span class="syntax-string">"order_no"</span><span class="syntax-brace">]</span>`

export const miniJsonExample = `<span class="syntax-brace">{</span>
<span class="syntax-key">"code"</span>: <span class="syntax-number">0</span>,
<span class="syntax-key">"message"</span>: <span class="syntax-string">"success"</span>,
<span class="syntax-key">"trace_id"</span>: <span class="syntax-string">"mango-20260522"</span>
<span class="syntax-brace">}</span>`

export const tableScrollX = columns.reduce((sum, column) => sum + Number(column.width || 0), 40)
