
import { reportLoadError } from '@/utils/load-error'
import { onBeforeUnmount, onDeactivated, ref, watch } from 'vue'
import { getGrader } from '@/api/evaluation'
import type { GraderCatalogEntry } from '../../types'

type GraderSelection = Pick<GraderCatalogEntry, 'grader_key' | 'grader_version'>

export function useGraderDetail() {
  const selectedGrader = ref<GraderSelection | null>(null)
  const detail = ref<GraderCatalogEntry | null>(null)
  const visible = ref(false),
    detailLoading = ref(false),
    detailError = ref(false)
  let requestId = 0
  function close() {
    ++requestId
    visible.value = false
    selectedGrader.value = null
    detail.value = null
    detailLoading.value = false
    detailError.value = false
  }
  async function show(row: GraderSelection) {
    if (!row.grader_key || !Number.isSafeInteger(row.grader_version) || row.grader_version <= 0)
      return false
    const request = ++requestId
    const selection = { grader_key: row.grader_key, grader_version: row.grader_version }
    selectedGrader.value = selection
    detail.value = null
    detailError.value = false
    visible.value = true
    detailLoading.value = true
    try {
      const response: { data: GraderCatalogEntry } = await getGrader(
        selection.grader_key,
        selection.grader_version
      )
      if (request !== requestId || !visible.value) return false
      detail.value = response.data
      return true
    } catch (loadFailure0) {
      if (request === requestId && visible.value) (reportLoadError(loadFailure0, "加载失败，请重试", false), detailError.value = true)
      return false
    } finally {
      if (request === requestId) detailLoading.value = false
    }
  }
  watch(
    visible,
    (value) => {
      if (!value) close()
    },
    { flush: 'sync' }
  )
  onDeactivated(close)
  onBeforeUnmount(close)
  return { selectedGrader, detail, visible, detailLoading, detailError, show, close }
}
