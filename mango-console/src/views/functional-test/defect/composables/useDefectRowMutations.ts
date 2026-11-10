import { onActivated, onBeforeUnmount, onDeactivated, reactive, ref, watch } from 'vue'
import type { Ref } from 'vue'
import { Modal } from '@arco-design/web-vue'
import {
  deleteFunctionalDefect,
  putFunctionalDefect,
  transitionFunctionalDefect,
} from '@/api/functional-test'
import { defectFields, defectId } from '../form'
import type { DefectListRecord, DefectQuickField } from '../types'

export function useDefectRowMutations(options: {
  context: () => string
  available: (row: DefectListRecord) => boolean
  rows: Ref<DefectListRecord[]>
  saved: (value: unknown) => void
  deleted: (id: number) => void
}) {
  const busy = reactive(new Map<number, { kind: string; token: symbol }>())
  const error = ref('')
  let active = true,
    generation = 0
  let confirmation: ReturnType<typeof Modal.warning> | null = null
  const current = (version: number, context: string) =>
    active && generation === version && options.context() === context
  const owns = (row: DefectListRecord) =>
    active && options.available(row) && options.rows.value.includes(row)
  function invalidate() {
    ++generation
    error.value = ''
    confirmation?.close()
    confirmation = null
  }
  async function write(row: DefectListRecord, kind: DefectQuickField | 'status', value: unknown) {
    if (!owns(row) || busy.has(row.id)) return
    const selected = value === '' || value === null || value === undefined ? null : defectId(value)
    if (
      (kind !== 'assignee' && selected === null) ||
      (value !== '' && value !== null && value !== undefined && selected === null)
    )
      return
    const original = kind === 'assignee' ? row.assignee?.id ?? null : row[kind]
    if (original === selected) return
    const id = row.id,
      version = generation,
      context = options.context(),
      token = Symbol()
    busy.set(id, { kind, token })
    error.value = ''
    try {
      const payload = { id, [kind]: selected }
      const data: unknown = (
        await (kind === 'status'
          ? transitionFunctionalDefect(payload)
          : putFunctionalDefect(payload))
      ).data
      if (!current(version, context)) return
      if (defectId(defectFields(data).id) !== id) throw Error('更新结果未确认')
      options.saved(data)
    } catch {
      if (current(version, context)) error.value = '缺陷更新失败，请重试'
    } finally {
      if (busy.get(id)?.token === token) busy.delete(id)
    }
  }
  function remove(row: DefectListRecord) {
    if (!owns(row) || busy.has(row.id) || confirmation) return
    const id = row.id,
      version = generation,
      context = options.context()
    let dialog: ReturnType<typeof Modal.warning> | null = null
    dialog = Modal.warning({
      title: '删除缺陷',
      content: `确认删除「${row.defect_no} ${row.title}」？`,
      hideCancel: false,
      onBeforeOk: async () => {
        if (!current(version, context) || busy.has(id) || !options.available(row)) return false
        const token = Symbol()
        busy.set(id, { kind: 'delete', token })
        error.value = ''
        try {
          await deleteFunctionalDefect(id)
          if (!current(version, context)) return false
          options.deleted(id)
          return true
        } catch {
          if (current(version, context)) error.value = '缺陷删除失败，请重试'
          return false
        } finally {
          if (busy.get(id)?.token === token) busy.delete(id)
        }
      },
      onBeforeCancel: () => !busy.has(id),
      onClose: () => {
        if (confirmation === dialog) confirmation = null
      },
    })
    confirmation = dialog
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
  return { busy, error, write, remove }
}
