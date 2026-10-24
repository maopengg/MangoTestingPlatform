export const UI_UPLOAD_FILE_METHODS = new Set(['w_upload_files'])

export function isUiUploadFileParam(methodKey: any, fieldKey: any) {
  return UI_UPLOAD_FILE_METHODS.has(String(methodKey || '')) && String(fieldKey || '') === 'file_path'
}

export function buildUiUploadFileExpression(fileId: string | number) {
  return `\${{get_file_by_id(${fileId})}}`
}

export function buildUiUploadFileValue(file: any) {
  return {
    file_id: file.id,
    file_name: file.name,
    download_url: file.download_url || '',
    local_path: buildUiUploadFileExpression(file.id),
  }
}

export function buildUiUploadFileCascaderValue(fileId: string | number) {
  return `file:${fileId}`
}

export function extractUiUploadFileKey(value: any) {
  if (value && typeof value === 'object') {
    return value.file_id || value.id || value.file_name || value.name || ''
  }
  if (typeof value !== 'string') return ''
  const idMatch = value.match(/^\$\{\{get_file_by_id\((.*)\)\}\}$/)
  if (idMatch) return idMatch[1]
  if (value.startsWith('file:')) return value.replace('file:', '')
  const match = value.match(/^\$\{\{get_file\((.*)\)\}\}$/)
  return match ? match[1] : value
}

function normalizeProjectProductId(projectProduct: any) {
  return String(projectProduct?.id || projectProduct || '')
}

export function buildUiUploadFileCascaderOptions(projectProducts: any[], files: any[]) {
  const fileGroups = new Map<string, any[]>()
  ;(files || []).forEach((file: any) => {
    if (!file?.id || !file?.name) return
    const productId = normalizeProjectProductId(file.project_product)
    if (!productId) return
    if (!fileGroups.has(productId)) fileGroups.set(productId, [])
    fileGroups.get(productId)?.push(file)
  })

  return (projectProducts || [])
    .map((project: any) => {
      const projectChildren = (project.children || [])
        .map((product: any) => {
          const productId = String(product.value)
          const fileChildren = (fileGroups.get(productId) || []).map((file: any) => ({
            label: `${file.name}（ID:${file.id}）`,
            value: buildUiUploadFileCascaderValue(file.id),
            fileValue: buildUiUploadFileValue(file),
            fileId: file.id,
            fileName: file.name,
            isLeaf: true,
          }))
          if (!fileChildren.length) return null
          return {
            label: product.label,
            value: `product:${productId}`,
            children: fileChildren,
          }
        })
        .filter(Boolean)
      if (!projectChildren.length) return null
      return {
        label: project.label,
        value: `project:${project.value}`,
        children: projectChildren,
      }
    })
    .filter(Boolean)
}

export function normalizeUiUploadFileValue(value: any, options: any[]) {
  if (!value) return value
  const rawKey = extractUiUploadFileKey(value)
  return rawKey ? buildUiUploadFileCascaderValue(rawKey) : value
}

export function getUiUploadFileValueFromCascader(value: any, options: any[]): any {
  const target = Array.isArray(value) ? value[value.length - 1] : value
  const walk = (items: any[]): any => {
    for (const item of items || []) {
      if (item.value === target && item.fileValue) return item.fileValue
      const child = walk(item.children || [])
      if (child) return child
    }
    return null
  }
  return walk(options) || value
}
