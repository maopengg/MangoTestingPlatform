export const requestColumns = [
  { title: '请求', key: 'request', dataIndex: 'request_name', width: 280 },
  { title: '请求数', key: 'request_count', dataIndex: 'request_count', width: 100, align: 'center' },
  { title: '失败数', key: 'failure_count', dataIndex: 'failure_count', width: 100, align: 'center' },
  { title: '错误率', key: 'error_rate', width: 100, align: 'center' },
  { title: '平均(ms)', key: 'avg_ms', dataIndex: 'avg_ms', width: 110, align: 'center' },
  { title: 'P50(ms)', key: 'p50_ms', dataIndex: 'p50_ms', width: 110, align: 'center' },
  { title: 'P95(ms)', key: 'p95_ms', dataIndex: 'p95_ms', width: 110, align: 'center' },
  { title: 'P99(ms)', key: 'p99_ms', dataIndex: 'p99_ms', width: 110, align: 'center' },
  { title: '平均/峰值 RPS', key: 'rps', dataIndex: 'rps', width: 140, align: 'center' },
]
export const nodeColumns = [
  { title: '分片', key: 'shard_index', dataIndex: 'shard_index', width: 80, align: 'center' },
  { title: '执行器', key: 'executor_fingerprint', dataIndex: 'executor_fingerprint', width: 180 },
  { title: '状态', key: 'status', dataIndex: 'status', width: 110, align: 'center' },
  { title: '引擎版本', key: 'engine_version', dataIndex: 'engine_version', width: 120 },
  { title: '最后指标', key: 'last_metric_at', dataIndex: 'last_metric_at', width: 180 },
  { title: '请求记录', key: 'capture', width: 190 },
  { title: '错误', key: 'error_message', dataIndex: 'error_message', width: 260, ellipsis: true, tooltip: true },
]
export const comparisonColumns = [
  { title: '指标', key: 'metric', dataIndex: 'metric', width: 170 },
  { title: '当前值', key: 'current', dataIndex: 'current', width: 140, align: 'center' },
  { title: '基线值', key: 'baseline', dataIndex: 'baseline', width: 140, align: 'center' },
  { title: '变化量', key: 'delta', dataIndex: 'delta', width: 140, align: 'center' },
  { title: '变化率', key: 'delta_percent', dataIndex: 'delta_percent', width: 140, align: 'center' },
]

export const REQUEST_TABLE_SCROLL_X = 1250
export const NODE_TABLE_SCROLL_X = 1290
export const COMPARISON_TABLE_SCROLL_X = 760
