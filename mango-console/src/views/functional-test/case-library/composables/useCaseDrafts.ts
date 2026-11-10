import { computed, onActivated, onBeforeUnmount, onDeactivated, ref, watch } from 'vue'
import type { Ref } from 'vue'
import { Message, Modal } from '@arco-design/web-vue'
import { deleteManualCase, postManualCaseBatch } from '@/api/functional-test'
import {
  createLibraryDraftRow,
  isPersistedCaseRow,
  libraryDraftHasContent,
  libraryDraftPayload,
  normalizeLibraryCaseRow,
} from '../rows'
import type { LibraryCaseRow, LibraryDraftDefaults } from '../types'

export function useCaseDrafts(options: {
  rows: Ref<LibraryCaseRow[]>
  selection: Ref<LibraryCaseRow[]>
  context: () => string
  identity: () => string
  available: () => boolean
  blocked: () => boolean
  defaults: () => LibraryDraftDefaults
  enableEditing: () => void
  flush: () => Promise<boolean>
  countChange: (delta: number) => void
}) {
  const { rows, selection } = options
  const batchMode = ref(false),
    batchSaving = ref(false),
    deleting = ref(false)
  const draftRows = computed(() => rows.value.filter((row) => row.__draft))
  const selectedDraftRows = computed(() => selection.value.filter((row) => row.__draft))
  const busy = computed(() => batchSaving.value || deleting.value || options.blocked())
  let sequence = 0,
    active = true,
    generation = 0
  let confirmation: ReturnType<typeof Modal.confirm> | null = null
  const available = () => active && options.available()
  function scope() {
    const context = options.context(),
      version = generation
    return () => available() && context === options.context() && version === generation
  }
  function createDraft(source?: LibraryCaseRow) {
    return createLibraryDraftRow(`draft-${Date.now()}-${++sequence}`, options.defaults(), source)
  }
  function insertDraftRows(payload: { index: number; count: number }) {
    if (!available() || busy.value) return
    const count = Math.min(Math.max(Math.trunc(Number(payload.count)) || 1, 1), 100)
    const index = Math.min(Math.max(Math.trunc(Number(payload.index)) || 0, 0), rows.value.length)
    rows.value = [
      ...rows.value.slice(0, index),
      ...Array.from({ length: count }, () => createDraft()),
      ...rows.value.slice(index),
    ]
    batchMode.value = true
    options.enableEditing()
  }
  function startBatchCreate() {
    if (!available() || busy.value) return
    if (!draftRows.value.length) insertDraftRows({ index: 0, count: 20 })
    else {
      batchMode.value = true
      options.enableEditing()
    }
  }
  function copyDraftRows() {
    if (!available() || busy.value) return
    const copies = selectedDraftRows.value
      .filter((row) => rows.value.includes(row))
      .map((row) => {
        const copy = createDraft(row)
        copy.case_no = row.case_no ? `${row.case_no}-COPY` : ''
        return copy
      })
    rows.value = [...copies, ...rows.value]
    selection.value = []
    if (copies.length) batchMode.value = true
  }
  function removeLocal(ids: Set<string | number>) {
    rows.value = rows.value.filter((row) => !ids.has(row.id))
    selection.value = selection.value.filter((row) => !ids.has(row.id))
    batchMode.value = draftRows.value.length > 0
  }
  function removeSelectedDraftRows() {
    if (!available() || busy.value) return
    removeLocal(new Set(selectedDraftRows.value.map((row) => row.id)))
  }
  async function saveDraftRows() {
    if (!available() || busy.value) return
    const candidates = draftRows.value.filter(libraryDraftHasContent)
    if (!candidates.length) {
      Message.warning('请至少填写一条用例')
      return
    }
    const invalid = candidates.findIndex(
      (row) =>
        !String(row.case_no ?? '').trim() ||
        !String(row.title ?? '').trim() ||
        !String(row.test_point ?? '').trim() ||
        !row.project_product_id ||
        !row.module_id ||
        !row.owner_id
    )
    if (invalid >= 0) {
      Message.warning(`第 ${invalid + 1} 条草稿缺少编号、标题、测试场景、项目、模块或负责人`)
      return
    }
    const current = scope(),
      ids = new Set(candidates.map((row) => row.id))
    const items = candidates.map(libraryDraftPayload)
    batchSaving.value = true
    try {
      if (!(await options.flush()) || !current()) return
      const response = await postManualCaseBatch({ items })
      if (!current()) return
      const data: unknown = response.data
      if (!Array.isArray(data) || data.length !== items.length)
        throw Error('服务器未完整确认批量创建结果，请核对服务器数据')
      const created = data.map(normalizeLibraryCaseRow)
      if (new Set(created.map((row) => row.id)).size !== created.length)
        throw Error('服务器返回重复的创建记录，请核对服务器数据')
      const known = new Set(rows.value.filter(isPersistedCaseRow).map((row) => row.id))
      const additions = created.filter((row) => !known.has(row.id))
      rows.value = [...additions, ...rows.value.filter((row) => !ids.has(row.id))]
      selection.value = []
      batchMode.value = draftRows.value.length > 0
      options.countChange(additions.length)
      Message.success(`已创建 ${created.length} 条用例`)
    } catch (error: unknown) {
      if (current())
        Message.error(error instanceof Error ? error.message : '批量创建失败，请检查草稿行')
    } finally {
      batchSaving.value = false
    }
  }
  function removeGridRows(targetRows: LibraryCaseRow[]) {
    if (!available() || busy.value || confirmation) return
    const targets = (targetRows.length ? targetRows : selection.value).filter((row) =>
      rows.value.includes(row)
    )
    const drafts = targets.filter((row) => row.__draft),
      persisted = targets.filter(isPersistedCaseRow)
    const ids = new Set(targets.map((row) => row.id))
    if (!persisted.length) {
      removeLocal(new Set(drafts.map((row) => row.id)))
      return
    }
    const current = scope(),
      deleteIds = [...new Set(persisted.map((row) => row.id))]
    const dialog = Modal.confirm({
      title: '删除用例',
      content: `确定删除选中的 ${deleteIds.length} 条正式用例吗？该操作不可撤销。`,
      okButtonProps: { status: 'danger' },
      onBeforeCancel: () => !deleting.value,
      onBeforeOk: async () => {
        if (!current() || confirmation !== dialog || busy.value) return false
        deleting.value = true
        try {
          if (!(await options.flush()) || !current() || confirmation !== dialog) return false
          await deleteManualCase(deleteIds)
          if (current() && confirmation === dialog) {
            removeLocal(ids)
            options.countChange(-deleteIds.length)
            Message.success(`已删除 ${deleteIds.length} 条用例`)
            dialog.close()
          }
        } catch {
          if (current() && confirmation === dialog) Message.error('删除失败，请重试')
        } finally {
          deleting.value = false
        }
        return false
      },
      onClose: () => {
        if (confirmation === dialog) confirmation = null
      },
    })
    confirmation = dialog
  }
  function exitBatchCreate() {
    if (!available() || busy.value || confirmation) return
    if (!draftRows.value.length) {
      batchMode.value = false
      return
    }
    const current = scope(),
      ids = new Set(draftRows.value.map((row) => row.id))
    const dialog = Modal.confirm({
      title: '退出批量新增',
      content: '未保存的草稿行将被移除，是否继续？',
      onBeforeOk: () => {
        if (current() && confirmation === dialog && !busy.value) {
          removeLocal(ids)
          dialog.close()
        }
        return false
      },
      onClose: () => {
        if (confirmation === dialog) confirmation = null
      },
    })
    confirmation = dialog
  }
  function invalidate() {
    ++generation
    const dialog = confirmation
    confirmation = null
    dialog?.close()
  }
  watch(options.context, invalidate, { flush: 'sync' })
  watch(
    options.identity,
    () => {
      batchMode.value = false
    },
    { flush: 'sync' }
  )
  onDeactivated(() => {
    active = false
    invalidate()
  })
  onActivated(() => {
    active = true
    batchMode.value = draftRows.value.length > 0
  })
  onBeforeUnmount(() => {
    active = false
    invalidate()
  })
  return {
    busy,
    batchMode,
    batchSaving,
    deleting,
    draftRows,
    selectedDraftRows,
    insertDraftRows,
    startBatchCreate,
    copyDraftRows,
    removeSelectedDraftRows,
    saveDraftRows,
    removeGridRows,
    exitBatchCreate,
  }
}
