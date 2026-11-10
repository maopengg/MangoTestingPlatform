import { computed, onActivated, onBeforeUnmount, onDeactivated, ref, watch } from 'vue'
import { Message } from '@arco-design/web-vue'
import { putManualCaseBatch } from '@/api/functional-test'
import {
  cloneInlineValue,
  inlineCellValue,
  inlineValuesEqual,
  isCaseInlineField,
} from '../inline-save'
import type { CaseInlineChanges, CaseInlineEvent, CaseInlineRow } from '../inline-save'

interface PendingCaseUpdate {
  row: CaseInlineRow
  changes: CaseInlineChanges
  originals: CaseInlineChanges
  projectPath?: string
  modulePath?: string
}

interface InFlightCaseUpdate extends PendingCaseUpdate {
  version: string | number
}

export function useCaseInlineSave(options: {
  context: () => string
  ownsRow: (row: CaseInlineRow) => boolean
  refreshCells: (id: string | number, fields: string[]) => void
  reload: () => Promise<unknown>
}) {
  const pendingInlineCellCount = ref(0),
    inflightInlineCellCount = ref(0)
  const inlineRecovering = ref(false)
  const inlineSaveState = ref<'saved' | 'pending' | 'saving' | 'error' | 'conflict'>('saved')
  const pending = new Map<string | number, PendingCaseUpdate>()
  let timer: ReturnType<typeof setTimeout> | undefined
  let running: Promise<boolean> | null = null
  let active = true,
    generation = 0
  const current = (version: number) => active && version === generation
  const inlineSavingCount = computed(
    () => pendingInlineCellCount.value + inflightInlineCellCount.value
  )
  const inlineSaveMeta = computed(() => {
    if (inlineSaveState.value === 'pending')
      return { text: `待保存 ${pendingInlineCellCount.value} 项`, color: 'orange' }
    if (inlineSaveState.value === 'saving')
      return { text: `正在保存 ${inflightInlineCellCount.value} 项…`, color: 'arcoblue' }
    if (inlineSaveState.value === 'conflict') return { text: '保存冲突', color: 'red' }
    if (inlineSaveState.value === 'error') return { text: '保存失败', color: 'red' }
    return { text: '已保存', color: 'green' }
  })
  const count = () => {
    pendingInlineCellCount.value = [...pending.values()].reduce(
      (total, item) => total + Object.keys(item.changes).length,
      0
    )
  }
  const snapshot = (changes: CaseInlineChanges): CaseInlineChanges =>
    Object.fromEntries(
      Object.entries(changes).map(([key, value]) => [key, cloneInlineValue(value)])
    )

  function rollback(item: PendingCaseUpdate) {
    for (const [field, value] of Object.entries(item.changes)) {
      if (!isCaseInlineField(field) || !inlineValuesEqual(item.row[field], value)) continue
      item.row[field] = cloneInlineValue(item.originals[field])
      if (field === 'project_product_id' && item.projectPath !== undefined)
        item.row.project_product_path = item.projectPath
      if (field === 'module_id' && item.modulePath !== undefined)
        item.row.module_path = item.modulePath
    }
    if (options.ownsRow(item.row)) options.refreshCells(item.row.id, [])
  }

  function invalidate() {
    ++generation
    clearTimeout(timer)
    timer = undefined
    for (const item of pending.values()) rollback(item)
    pending.clear()
    pendingInlineCellCount.value = 0
    inflightInlineCellCount.value = 0
    inlineRecovering.value = false
    inlineSaveState.value = 'saved'
  }

  function schedule() {
    clearTimeout(timer)
    if (active)
      timer = setTimeout(() => {
        void flushInlineUpdates(false)
      }, 450)
  }

  async function reload(version: number) {
    if (!current(version)) return
    inlineRecovering.value = true
    try {
      await options.reload()
    } catch {
      /* Read failure must not reject an already handled write. */
    } finally {
      if (current(version)) inlineRecovering.value = false
    }
  }

  async function send(batch: InFlightCaseUpdate[], version: number) {
    try {
      const response = await putManualCaseBatch({
        updates: batch.map((item) => ({
          id: item.row.id,
          version_no: item.version,
          changes: item.changes,
        })),
      })
      if (!current(version)) return false
      if (response.data?.conflicts?.length) {
        for (const item of pending.values()) rollback(item)
        pending.clear()
        count()
        batch.forEach(rollback)
        inlineSaveState.value = 'conflict'
        Message.warning(
          `${response.data.conflicts.length} 条用例已被其他用户修改，当前编辑未保存，正在刷新最新数据`
        )
        await reload(version)
        return false
      }
      const updates = new Map((response.data?.updated ?? []).map((item) => [String(item.id), item]))
      // Validate the whole acknowledgement before applying any row metadata.
      for (const item of batch) {
        const ack = updates.get(String(item.row.id))
        if (!ack || !Number.isSafeInteger(ack.version_no) || ack.version_no <= Number(item.version))
          throw Error('服务器未确认保存结果')
        for (const field of ['project_product_id', 'module_id'] as const) {
          if (
            field in item.changes &&
            String(ack[field] ?? '') !== String(item.changes[field] ?? '')
          )
            throw Error('服务器未确认项目产品或模块更新')
        }
      }
      for (const item of batch) {
        if (!options.ownsRow(item.row)) continue
        const ack = updates.get(String(item.row.id))!
        if (Number(item.row.version_no) > ack.version_no) continue
        const newer = pending.get(item.row.id)
        item.row.version_no = ack.version_no
        item.row.update_time = ack.update_time
        for (const [idField, pathField] of [
          ['project_product_id', 'project_product_path'],
          ['module_id', 'module_path'],
        ] as const) {
          if (newer && idField in newer.changes) continue
          item.row[idField] = ack[idField]
          item.row[pathField] = ack[pathField]
        }
        options.refreshCells(item.row.id, [
          'project_product_id',
          'project_product_path',
          'module_id',
          'module_path',
          'version_no',
          'update_time',
        ])
      }
      inlineSaveState.value = pending.size ? 'pending' : 'saved'
      return true
    } catch (error: unknown) {
      if (!current(version)) return false
      for (const item of pending.values()) rollback(item)
      pending.clear()
      count()
      batch.forEach(rollback)
      inlineSaveState.value = 'error'
      Message.error(error instanceof Error ? error.message : '批量保存失败，正在刷新服务器数据')
      await reload(version)
      return false
    } finally {
      if (current(version)) inflightInlineCellCount.value = 0
    }
  }

  async function flushInlineUpdates(drain = true): Promise<boolean> {
    clearTimeout(timer)
    timer = undefined
    if (!active) return false
    if (running) {
      const previous = await running
      return pending.size && active ? flushInlineUpdates(drain) : previous
    }
    if (!pending.size)
      return inlineSaveState.value !== 'error' && inlineSaveState.value !== 'conflict'
    const version = generation
    const batch = [...pending.values()]
      .filter((item) => options.ownsRow(item.row))
      .map((item) => ({
        ...item,
        version: item.row.version_no,
        changes: snapshot(item.changes),
        originals: snapshot(item.originals),
      }))
    pending.clear()
    count()
    if (!batch.length) {
      inlineSaveState.value = 'saved'
      return true
    }
    inflightInlineCellCount.value = batch.reduce(
      (total, item) => total + Object.keys(item.changes).length,
      0
    )
    inlineSaveState.value = 'saving'
    const task = send(batch, version)
    running = task
    let result: boolean
    try {
      result = await task
    } finally {
      if (running === task) running = null
      if (current(version) && pending.size) schedule()
    }
    if (!current(version)) return false
    return drain && active && pending.size ? flushInlineUpdates(true) : result
  }

  function saveInline(event: CaseInlineEvent) {
    if (!active || !event.field || !isCaseInlineField(event.field) || !options.ownsRow(event.row))
      return
    if (inlineRecovering.value) return
    const changes = Object.entries(event.changes)
    if (
      !changes.length ||
      changes.some(
        ([field, value]) =>
          !isCaseInlineField(field) || !inlineCellValue(value) || !inlineCellValue(event.row[field])
      )
    )
      return
    const display = Object.entries(event.displayChanges)
    if (
      display.some(
        ([field, value]) =>
          (field !== 'project_product_path' && field !== 'module_path') ||
          typeof value !== 'string' ||
          !(field === 'module_path'
            ? 'module_id' in event.changes
            : 'project_product_id' in event.changes)
      )
    )
      return
    const item: PendingCaseUpdate = pending.get(event.row.id) ?? {
      row: event.row,
      changes: {},
      originals: {},
    }
    for (const [field, value] of changes) {
      if (!isCaseInlineField(field)) continue
      const original = event.row[field]
      if (!isCaseInlineField(field) || !inlineCellValue(value) || !inlineCellValue(original))
        continue
      if (!(field in item.originals)) item.originals[field] = cloneInlineValue(original)
      item.changes[field] = cloneInlineValue(value)
    }
    if (!Object.keys(item.changes).length) return
    if ('project_product_id' in item.changes && item.projectPath === undefined)
      item.projectPath = event.row.project_product_path
    if ('module_id' in item.changes && item.modulePath === undefined)
      item.modulePath = event.row.module_path
    for (const [field, value] of changes) {
      if (isCaseInlineField(field) && inlineCellValue(value))
        event.row[field] = cloneInlineValue(value)
    }
    for (const [field, value] of display) {
      if (
        (field === 'project_product_path' || field === 'module_path') &&
        typeof value === 'string'
      )
        event.row[field] = value
    }
    if (event.row.__draft) {
      event.row.__touched = true
      return
    }
    pending.set(event.row.id, item)
    count()
    inlineSaveState.value = 'pending'
    schedule()
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
    saveInline,
    flushInlineUpdates,
    invalidate,
    inlineSaveState,
    inlineSaveMeta,
    inlineSavingCount,
    pendingInlineCellCount,
    inflightInlineCellCount,
    inlineRecovering,
  }
}
