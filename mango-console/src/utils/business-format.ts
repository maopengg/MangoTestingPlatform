export function getOptionId(value: any) {
  if (Array.isArray(value)) {
    return value[value.length - 1] ?? null
  }
  return value?.id ?? value ?? null
}

export function formatProjectProductPath(projectProduct: any) {
  if (!projectProduct) {
    return '-'
  }
  const resolvedProjectProduct = projectProduct?.project_product || projectProduct
  const projectName = resolvedProjectProduct?.project?.name
  const productName = resolvedProjectProduct?.name
  return [projectName, productName].filter(Boolean).join('/') || '-'
}

export function formatModulePath(module: any) {
  if (!module) {
    return '-'
  }
  if (module.full_path) {
    return module.full_path
  }
  const parentPaths: string[] = []
  const visited = new Set<any>()
  let current = module
  while (current && typeof current === 'object' && !visited.has(current.id)) {
    visited.add(current.id)
    if (current.name) parentPaths.unshift(current.name)
    current = current.parent
  }
  return parentPaths.length ? parentPaths.join('/') : '-'
}

export function getEnumTagColor(
  options: Array<{ key: string | number; title: string }> | null | undefined,
  value: string | number | null | undefined,
  colors: string[],
  fallback = 'gray'
) {
  if (!colors.length) return fallback
  const optionIndex = (options || []).findIndex((item) => String(item.key) === String(value))
  return optionIndex >= 0 ? colors[optionIndex % colors.length] : fallback
}

export function getItemValue(items: any[], key: string) {
  return items.find((item: any) => item.key === key)?.value ?? ''
}

export function setItemValue(items: any[], key: string, value: any) {
  const item = items.find((option: any) => option.key === key)
  if (item) {
    item.value = value
  }
}
