export function resolveSearchFilterOptions(
  item: any,
  userList: any[],
  enumStore: Record<string, any>,
  enumKeys: Record<string, string>,
  userKeys: string[]
) {
  if (userKeys.includes(item.key)) return userList
  const enumKey = enumKeys[item.key]
  if (enumKey) return enumStore[enumKey] || []
  return Array.isArray(item.optionItems) ? item.optionItems : []
}
