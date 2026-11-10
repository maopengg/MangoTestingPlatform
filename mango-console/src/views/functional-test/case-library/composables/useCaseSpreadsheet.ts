import { computed, onActivated, onBeforeUnmount, onDeactivated, ref, watch } from 'vue'
import * as XLSX from 'xlsx'
import { Message } from '@arco-design/web-vue'
import { ApiBusinessError } from '@/api/errors'
import { getManualCaseExport, postManualCase } from '@/api/functional-test'
import { caseExportRows, caseImportPayload } from '../spreadsheet'

export function useCaseSpreadsheet(options: {
  context: () => string
  available: () => boolean
  exportQuery: () => Record<string, unknown>
  flush: () => Promise<unknown>
  reload: () => Promise<unknown>
}) {
  const importing = ref(false),
    exporting = ref(false)
  const importFeedback = ref(''),
    importRetryable = ref(false)
  const importedCount = ref(0),
    importTotal = ref(0)
  const importProgress = computed(() =>
    importing.value
      ? importTotal.value
        ? `已导入 ${importedCount.value} / ${importTotal.value} 条`
        : '正在读取文件或等待上次请求结束…'
      : importFeedback.value
  )
  let active = true,
    generation = 0
  let pending: Array<ReturnType<typeof caseImportPayload>> | null = null
  let cursor = 0
  const available = () => active && options.available()
  const scope = () => {
    const version = generation,
      context = options.context()
    return () => available() && version === generation && context === options.context()
  }
  function discardImport() {
    if (importing.value) return
    pending = null
    cursor = 0
    importFeedback.value = ''
    importRetryable.value = false
    importedCount.value = 0
    importTotal.value = 0
  }
  async function submitImport(current: () => boolean) {
    const items = pending
    if (!items || !current()) return
    importRetryable.value = false
    let acknowledged = 0
    try {
      for (; cursor < items.length; ) {
        if (!current()) return
        await postManualCase(items[cursor])
        if (!current()) return
        ++cursor
        ++acknowledged
        importedCount.value = cursor
      }
      pending = null
      importFeedback.value = `成功导入 ${cursor} 条用例`
      Message.success(importFeedback.value)
    } catch (error: unknown) {
      if (!current()) return
      // These case validators run before the transactional create. Other errors may occur after commit.
      importRetryable.value =
        error instanceof ApiBusinessError && (error.code === 35014 || error.code === 35051)
      importFeedback.value = `已导入 ${cursor} / ${items.length} 条，第 ${cursor + 1} 条${
        importRetryable.value
          ? `失败：${
              error instanceof Error ? error.message : '校验失败'
            }。可处理问题后继续，或清除记录并重新选择修正后的文件`
          : '提交结果未确认，请核对服务器数据后重新准备未导入的文件'
      }`
      Message.error(importFeedback.value)
    } finally {
      if (current() && acknowledged) {
        try {
          await options.reload()
        } catch {
          if (current()) Message.warning('导入记录已保存，列表读取失败，请重试刷新')
        }
      }
    }
  }
  async function importCases(event: Event) {
    const input = event.target
    if (!(input instanceof HTMLInputElement)) return
    const file = input.files?.[0]
    if (!file || importing.value || !available()) return
    if (pending) {
      Message.warning('请先继续或清除上次导入记录')
      input.value = ''
      return
    }
    const current = scope()
    importing.value = true
    importFeedback.value = ''
    importedCount.value = 0
    importTotal.value = 0
    try {
      const content = await file.arrayBuffer()
      if (!current()) return
      const workbook = XLSX.read(content)
      const first = workbook.SheetNames[0]
      if (!first || !workbook.Sheets[first]) throw Error('文件中没有工作表')
      const records = XLSX.utils.sheet_to_json<Record<string, unknown>>(workbook.Sheets[first], {
        defval: '',
      })
      if (!records.length) throw Error('工作表中没有数据')
      // Parse every row before issuing writes, so malformed later rows cannot cause partial imports.
      const payloads = records.map((row, index) => {
        try {
          return caseImportPayload(row)
        } catch (error: unknown) {
          throw Error(
            `第 ${index + 1} 条数据：${error instanceof Error ? error.message : '格式错误'}`
          )
        }
      })
      if (!current()) return
      await options.flush()
      if (!current()) return
      pending = payloads
      cursor = 0
      importTotal.value = payloads.length
      await submitImport(current)
    } catch (error: unknown) {
      if (current()) {
        importFeedback.value = error instanceof Error ? error.message : '导入文件读取失败'
        Message.error(importFeedback.value)
      }
    } finally {
      importing.value = false
      input.value = ''
    }
  }
  async function retryImport() {
    if (importing.value || !importRetryable.value || !pending || !available()) return
    const current = scope()
    importing.value = true
    try {
      await options.flush()
      if (!current()) return
      await submitImport(current)
    } catch {
      if (current()) Message.error('等待当前修改保存失败，请重试')
    } finally {
      importing.value = false
    }
  }
  async function exportCases() {
    if (exporting.value || !available()) return
    const current = scope(),
      query = { ...options.exportQuery() }
    exporting.value = true
    try {
      await options.flush()
      if (!current()) return
      const response = await getManualCaseExport(
        Object.fromEntries(
          Object.entries(query).filter(
            ([, value]) => value !== '' && value !== null && value !== undefined
          )
        )
      )
      if (!current()) return
      const workbook = XLSX.utils.book_new()
      XLSX.utils.book_append_sheet(
        workbook,
        XLSX.utils.json_to_sheet(caseExportRows(response.data)),
        '测试用例'
      )
      XLSX.writeFile(workbook, `测试用例_${new Date().toISOString().slice(0, 10)}.xlsx`)
    } catch {
      if (current()) Message.error('导出失败，请重试')
    } finally {
      exporting.value = false
    }
  }
  function invalidate() {
    ++generation
    pending = null
    cursor = 0
    importFeedback.value = ''
    importRetryable.value = false
    importedCount.value = 0
    importTotal.value = 0
    // Physical in-flight writes keep their mutex until settlement, even after reactivation.
  }
  watch(options.context, invalidate, { flush: 'sync' })
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
  return {
    importing,
    exporting,
    importProgress,
    importRetryable,
    importCases,
    retryImport,
    discardImport,
    exportCases,
  }
}
