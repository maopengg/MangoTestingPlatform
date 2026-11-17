interface MethodGroup {
  value: string
}

// select_value 混有设备操作；通用断言以专用 ass_select_value 目录为准。
const uiContextGroups = new Set(['web', 'android', 'ios', 'ass_web', 'ass_android', 'ass_ios'])

export function mergeUiMethodCatalog<T extends MethodGroup>(operations: T[], assertions: T[]): T[] {
  return [...operations.filter((item) => uiContextGroups.has(item.value)), ...assertions]
}
