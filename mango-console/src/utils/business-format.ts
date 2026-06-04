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
  const projectName = projectProduct?.project?.name
  const productName = projectProduct?.name
  return [projectName, productName].filter(Boolean).join('/') || '-'
}

export function formatModulePath(module: any) {
  if (!module) {
    return '-'
  }
  const paths = [
    module.superior_module_1 || module.superior_module,
    module.superior_module_2,
    module.name,
  ].filter(Boolean)
  return paths.length ? paths.join('/') : '-'
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
