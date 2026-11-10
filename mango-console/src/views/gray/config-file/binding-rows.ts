import { normalizeEmptyListTotal } from '@/utils/api-response'
import { object, repositories, selectionId } from './forms'
import type { BindingRecord, Repository } from './forms'

export interface BindingRow extends BindingRecord {
  repository: Repository
}

export function bindingRows(value: unknown, yamlId: number): BindingRow[] {
  if (!Array.isArray(value)) throw Error('Invalid binding rows')
  const seen = new Set<number>()
  return value.map((value) => {
    const row = object(value),
      id = selectionId(row.id)
    if (
      !id ||
      seen.has(id) ||
      selectionId(row.yaml_file) !== yamlId ||
      typeof row.file_path !== 'string' ||
      (row.status !== 0 && row.status !== 1)
    )
      throw Error('Invalid binding row')
    seen.add(id)
    return {
      id,
      yaml_file: yamlId,
      repository: repositories([row.repository])[0],
      file_path: row.file_path,
      status: row.status,
    }
  })
}

export function bindingPage(value: unknown, yamlId: number) {
  value = normalizeEmptyListTotal(value)

  const response = object(value)
  // 通用 CRUD 的空列表响应省略 totalSize。
  const total =
    response.totalSize === undefined && Array.isArray(response.data) && response.data.length === 0
      ? 0
      : response.totalSize
  if (
    response.code !== 200 ||
    !Array.isArray(response.data) ||
    typeof total !== 'number' ||
    !Number.isSafeInteger(total) ||
    total < 0
  )
    throw Error('Invalid binding page')
  const rows = bindingRows(response.data, yamlId)
  return { rows, total }
}
