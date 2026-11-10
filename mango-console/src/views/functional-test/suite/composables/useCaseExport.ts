import { onActivated, onBeforeUnmount, onDeactivated, ref, watch } from 'vue'
import { Message } from '@arco-design/web-vue'
import * as XLSX from 'xlsx'
import { getManualCaseExport } from '@/api/functional-test'
import { caseExportPage, caseExportRows } from '../export-rows'
import type { CaseExportEnums } from '../export-rows'

export function useCaseExport(options: {
  contextKey: () => string
  query: () => Record<string, unknown>
  enums: () => CaseExportEnums
}) {
  const exportLoading = ref(false)
  const exportError = ref(false)
  let active = true
  let generation = 0
  let pending = false

  const invalidate = () => {
    ++generation
    exportError.value = false
  }
  watch(options.contextKey, invalidate, { flush: 'sync' })
  onDeactivated(() => {
    active = false
    invalidate()
  })
  onActivated(() => {
    active = true
  })
  onBeforeUnmount(() => {
    active = false
    invalidate()
  })

  async function exportCases() {
    if (pending || !active) return
    pending = true
    exportLoading.value = true
    exportError.value = false
    const sequence = generation,
      context = options.contextKey()
    const current = () => active && generation === sequence && options.contextKey() === context
    try {
      // 查询只包含接口生成的标量条件；复制后每页不再读取正在编辑的筛选器。
      const query: Record<string, string | number | boolean> = {}
      for (const [key, value] of Object.entries(options.query())) {
        if (
          value === '' ||
          value === null ||
          value === undefined ||
          key === 'page' ||
          key === 'pageSize'
        )
          continue
        if (!['string', 'number', 'boolean'].includes(typeof value))
          throw Error('Invalid export filter')
        query[key] = value as string | number | boolean
      }
      const enums = options.enums()
      const cloneOptions = (values: CaseExportEnums['priorities']) =>
        values.map((item) => ({ key: item.key, title: item.title }))
      const enumSnapshot: CaseExportEnums = {
        testTypes: cloneOptions(enums.testTypes),
        priorities: cloneOptions(enums.priorities),
        layers: cloneOptions(enums.layers),
        types: cloneOptions(enums.types),
        tags: cloneOptions(enums.tags),
        changes: cloneOptions(enums.changes),
        impacts: cloneOptions(enums.impacts),
      }
      const rows: Record<string, unknown>[] = []
      const ids = new Set<number>()
      let total: number | null = null
      const pageSize = 1000
      for (let page = 1; total === null || rows.length < total; page += 1) {
        if (!current()) return
        const response = await getManualCaseExport({ ...query, page, pageSize })
        if (!current()) return
        const result = caseExportPage(response)
        if (total !== null && result.total !== total) throw Error('Export data changed')
        total = result.total
        if (
          result.rows.length > pageSize ||
          rows.length + result.rows.length > total ||
          (!result.rows.length && rows.length < total)
        )
          throw Error('Incomplete export page')
        for (const row of result.rows) {
          const id = row.id as number
          if (ids.has(id)) throw Error('Duplicate export record')
          ids.add(id)
          rows.push(row)
        }
      }
      if (!current()) return
      if (!rows.length) {
        Message.warning('暂无可导出的用例')
        return
      }
      const worksheet = XLSX.utils.json_to_sheet(caseExportRows(rows, enumSnapshot))
      const workbook = XLSX.utils.book_new()
      XLSX.utils.book_append_sheet(workbook, worksheet, '测试用例')
      const stamp = new Date().toISOString().replace('T', '_').replaceAll(':', '-').split('.')[0]
      XLSX.writeFile(workbook, `功能测试用例_${stamp}.xlsx`)
      Message.success('导出成功')
    } catch {
      if (current()) {
        exportError.value = true
        Message.error('导出失败或数据已变化，请重新导出')
      }
    } finally {
      pending = false
      exportLoading.value = false
    }
  }
  return { exportLoading, exportError, exportCases }
}
