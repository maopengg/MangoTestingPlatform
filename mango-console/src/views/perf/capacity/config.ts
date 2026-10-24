export const capacityColumns = [
  { title: '执行器', key: 'executor', dataIndex: 'executor_name', width: 210 },
  { title: '状态', key: 'online', dataIndex: 'online', width: 90, align: 'center' },
  { title: '性能引擎', key: 'engine', dataIndex: 'engine', width: 120, align: 'center' },
  { title: '容量策略', key: 'calibration', dataIndex: 'calibration_status', width: 120, align: 'center' },
  { title: '安全容量', key: 'safe_capacity', width: 190 },
  { title: '默认可调度容量', key: 'available_capacity', width: 220 },
  { title: '策略有效期', key: 'valid_until', dataIndex: 'valid_until', width: 180 },
]

export const CAPACITY_TABLE_SCROLL_X = 1130
