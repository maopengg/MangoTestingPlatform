import { computed, onActivated, onBeforeUnmount, onDeactivated, ref, watch } from 'vue'
import { putFunctionalPlanCase } from '@/api/functional-test'
import { readGridRecord } from '@/components/table/functional-case-grid'
import type {
  FunctionalGridCellChange,
  FunctionalGridCellValue,
  FunctionalGridColumn,
} from '@/components/table/functional-case-grid'

interface PendingWrite {
  row: object
  id: string | number
  version: number
  context: string
  changes: Record<string, FunctionalGridCellValue>
  values: Record<string, FunctionalGridCellValue>
  originals: Record<string, unknown>
  cancelled: boolean
}
const clone = (value: unknown) => (Array.isArray(value) ? [...value] : value)
const equal = (left: unknown, right: unknown) =>
  Array.isArray(left) || Array.isArray(right)
    ? JSON.stringify(left) === JSON.stringify(right)
    : left === right
function cell(value: unknown): value is FunctionalGridCellValue {
  return (
    value === null ||
    value === undefined ||
    typeof value === 'string' ||
    typeof value === 'number' ||
    typeof value === 'boolean' ||
    (Array.isArray(value) &&
      value.every((item) => typeof item === 'string' || typeof item === 'number'))
  )
}

export function usePlanCaseSave(options: {
  context: () => string
  ownsRow: (row: object) => boolean
  columns: () => FunctionalGridColumn[]
  editable: () => boolean
  refresh: (row: object) => void
  normalizeResponse?: (value: unknown) => object
}) {
  const physicalWrite = ref(false),
    queuedCount = ref(0)
  const caseSaving = computed(() => physicalWrite.value || queuedCount.value > 0)
  const savedOnce = ref(false),
    saveFailed = ref(false)
  const failedRows = new Set<object>()
  let active = true,
    generation = 0,
    tail: Promise<void> = Promise.resolve()
  let pending: PendingWrite[] = []
  const current = (entry: PendingWrite) =>
    active &&
    generation === entry.version &&
    options.context() === entry.context &&
    options.ownsRow(entry.row)
  function refresh(row: object) {
    try {
      options.refresh(row)
    } catch {
      /* Canvas feedback must not turn an accepted write into a failed save. */
    }
  }
  function rollback(entry: PendingWrite) {
    const row = readGridRecord(entry.row)
    for (const [key, value] of Object.entries(entry.values)) {
      if (equal(row[key], value)) Reflect.set(entry.row, key, clone(entry.originals[key]))
    }
    if (options.ownsRow(entry.row)) refresh(entry.row)
  }
  function invalidate() {
    ++generation
    for (const entry of [...pending].reverse()) {
      entry.cancelled = true
      if (options.ownsRow(entry.row)) rollback(entry)
    }
    pending = []
    queuedCount.value = 0
    failedRows.clear()
    savedOnce.value = false
    saveFailed.value = false
  }
  async function submit(entry: PendingWrite) {
    if (entry.cancelled || !current(entry)) return
    physicalWrite.value = true
    try {
      const response = await putFunctionalPlanCase({ id: entry.id, ...entry.changes })
      if (entry.cancelled || !current(entry)) return
      const data: unknown = options.normalizeResponse
        ? options.normalizeResponse(response.data)
        : response.data
      if (
        !data ||
        typeof data !== 'object' ||
        Array.isArray(data) ||
        String(Reflect.get(data, 'id')) !== String(entry.id)
      )
        throw Error('保存结果未确认')
      const protectedFields = new Set(
        pending
          .filter((item) => item !== entry && !item.cancelled && item.row === entry.row)
          .flatMap((item) => Object.keys(item.values))
      )
      for (const [key, value] of Object.entries(data))
        if (!protectedFields.has(key)) Reflect.set(entry.row, key, clone(value))
      failedRows.delete(entry.row)
      saveFailed.value = failedRows.size > 0
      savedOnce.value = true
      refresh(entry.row)
    } catch {
      if (!entry.cancelled && current(entry)) {
        // Roll newer edits back first, then the failed write's original baseline.
        for (const item of [...pending].reverse()) {
          if (item.row !== entry.row || item.version !== entry.version) continue
          item.cancelled = true
          rollback(item)
        }
        failedRows.add(entry.row)
        saveFailed.value = true
      }
    } finally {
      physicalWrite.value = false
    }
  }
  function savePlanCase(event: FunctionalGridCellChange): Promise<void> {
    if (!active || !options.editable() || !options.ownsRow(event.row)) return Promise.resolve()
    const row = readGridRecord(event.row),
      id = row.id
    if (typeof id !== 'number' && typeof id !== 'string') return Promise.resolve()
    const allowed = new Set(
      options
        .columns()
        .filter((column) => column.editable !== false)
        .map((column) => column.field)
    )
    const changes = Object.entries(event.changes)
    if (
      !allowed.has(event.field) ||
      !changes.length ||
      changes.some(([field, value]) => !allowed.has(field) || !cell(value))
    )
      return Promise.resolve()
    const display = Object.entries(event.displayChanges)
    if (
      display.some(
        ([key, value]) =>
          typeof value !== 'string' ||
          (key === 'module_path'
            ? !('module_id' in event.changes)
            : key === 'project_product_path'
            ? !('project_product_id' in event.changes)
            : true)
      )
    )
      return Promise.resolve()
    const entry: PendingWrite = {
      row: event.row,
      id,
      context: options.context(),
      version: generation,
      cancelled: false,
      changes: Object.fromEntries(
        changes.map(([key, value]) => [key, Array.isArray(value) ? [...value] : value])
      ),
      values: { ...event.changes, ...event.displayChanges },
      originals: {},
    }
    for (const [key, value] of Object.entries(entry.values)) {
      entry.originals[key] = clone(row[key])
      entry.values[key] = Array.isArray(value) ? [...value] : value
      Reflect.set(entry.row, key, clone(value))
    }
    pending.push(entry)
    queuedCount.value = pending.filter((item) => !item.cancelled).length
    const task = tail
      .then(() => submit(entry))
      .finally(() => {
        pending = pending.filter((item) => item !== entry)
        queuedCount.value = pending.filter((item) => !item.cancelled).length
      })
    tail = task.catch(() => {})
    return task
  }
  watch(options.context, invalidate, { flush: 'sync' })
  watch(
    options.editable,
    (editable) => {
      if (!editable) invalidate()
    },
    { flush: 'sync' }
  )
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
  return { savePlanCase, caseSaving, savedOnce, saveFailed }
}
