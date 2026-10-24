export type StatusColorMap = Readonly<Record<number, string>>

export const AUTH_REFRESH_STATUS_COLORS: StatusColorMap = {
  0: 'gray',
  1: 'green',
  2: 'red',
}

export const MONITORING_LOG_STATUS_COLORS: StatusColorMap = {
  0: 'arcoblue',
  1: 'red',
  2: 'orange',
  3: 'gray',
}

export const MONITORING_TASK_STATUS_COLORS: StatusColorMap = {
  0: 'gray',
  1: 'arcoblue',
  2: 'gray',
  3: 'red',
  4: 'green',
  5: 'orange',
}

export const DATA_FACTORY_CLEANUP_STATUS_COLORS: StatusColorMap = {
  0: 'gray',
  1: 'green',
  2: 'red',
  3: 'gray',
  4: 'orange',
}

export const AI_AGENT_TASK_STATUS_COLORS: StatusColorMap = {
  0: 'red',
  1: 'green',
  2: 'gray',
  3: 'arcoblue',
  4: 'orange',
  5: 'gold',
  6: 'gray',
  7: 'cyan',
  8: 'purple',
}

export const MANUAL_TEST_SYNC_STATUS_COLORS: StatusColorMap = {
  0: 'gray',
  1: 'green',
  2: 'orange',
  3: 'red',
}

export const MANUAL_TEST_CHANGE_STATUS_COLORS: StatusColorMap = {
  0: 'gray',
  1: 'arcoblue',
  2: 'orange',
  3: 'gray',
}

export const MANUAL_TEST_IMPACT_STATUS_COLORS: StatusColorMap = {
  0: 'gray',
  1: 'gold',
  2: 'orange',
  3: 'green',
  4: 'gray',
}

export const MANUAL_TEST_OPTIMIZE_STATUS_COLORS: StatusColorMap = {
  0: 'green',
  1: 'orange',
  2: 'arcoblue',
  3: 'green',
  4: 'gray',
}

export function getStatusTagColor(
  colorMap: StatusColorMap,
  value: string | number | null | undefined,
  fallback = 'gray'
) {
  if (value === null || value === undefined || value === '') return fallback
  return colorMap[Number(value)] || fallback
}
