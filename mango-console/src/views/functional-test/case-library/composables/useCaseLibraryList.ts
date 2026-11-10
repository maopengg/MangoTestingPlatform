
import { reportLoadError } from '@/utils/load-error'
import {
  computed,
  nextTick,
  onActivated,
  onBeforeUnmount,
  onDeactivated,
  onMounted,
  reactive,
  ref,
  watch,
} from 'vue'
import type { Ref } from 'vue'
import { getManualCase } from '@/api/functional-test'

interface CaseListRow {
  id: string | number
  __draft?: boolean
}

export function useCaseLibraryList<Row extends CaseListRow>(options: {
  rows: Ref<Row[]>
  context: () => string
  identity: () => string
  available: () => boolean
  query: () => Record<string, unknown>
  normalize: (record: unknown) => Row
  clearSelection: () => void
}) {
  const { rows } = options
  const pageState = reactive({ page: 1, pageSize: 50, total: 0 })
  const loading = ref(false),
    loadingMore = ref(false),
    loadError = ref(false)
  const filterActive = ref(false),
    loadingAllForFilter = ref(false)
  const persistedRowCount = computed(() => rows.value.filter((row) => !row.__draft).length)
  const hasMore = computed(() => persistedRowCount.value < pageState.total)
  let active = true,
    generation = 0,
    request = 0
  let lastIdentity = options.identity()
  let failedAppend = false
  const available = () => active && options.available()
  const current = (version: number, context: string) =>
    available() && version === generation && context === options.context()

  function invalidate() {
    ++generation
    ++request
    loading.value = false
    loadingMore.value = false
    loadError.value = false
    loadingAllForFilter.value = false
  }

  async function loadCases(showLoading = true, append = false): Promise<boolean> {
    if (!available()) return false
    if (append && (loading.value || loadingMore.value || !hasMore.value)) return false
    const version = generation,
      context = options.context(),
      ownRequest = ++request
    const owns = () => current(version, context) && ownRequest === request
    const firstPage = append ? pageState.page + 1 : 1
    const lastPage = append ? firstPage : firstPage + 3
    const query = Object.fromEntries(
      Object.entries(options.query()).filter(
        ([, value]) => value !== '' && value !== null && value !== undefined
      )
    )
    let resultRows = append ? rows.value.filter((row) => !row.__draft) : []
    if (append) loadingMore.value = true
    else {
      loading.value = showLoading
      loadingMore.value = false
    }
    loadError.value = false
    try {
      for (let page = firstPage; page <= lastPage; ++page) {
        const response = await getManualCase({ ...query, page, pageSize: pageState.pageSize })
        if (!owns()) return false
        const records: unknown[] = response.data ?? []
        const loaded = records.map(options.normalize)
        const known = new Set(resultRows.map((row) => String(row.id)))
        const additions = loaded.filter((row) => {
          if (known.has(String(row.id))) return false
          known.add(String(row.id))
          return true
        })
        if (!additions.length && resultRows.length < response.totalSize) {
          failedAppend = append || resultRows.length > 0
          loadError.value = true
          return false
        }
        resultRows = [...resultRows, ...additions]
        // Drafts may change while a read is pending; never reinsert a captured old draft list.
        rows.value = [...rows.value.filter((row) => row.__draft), ...resultRows]
        pageState.page = page
        pageState.total = response.totalSize ?? 0
        options.clearSelection()
        loading.value = false
        loadingMore.value = page < lastPage && resultRows.length < pageState.total
        if (!loaded.length || resultRows.length >= pageState.total) break
      }
      return true
    } catch (loadFailure0) {
      if (owns()) {
        failedAppend = append || (pageState.page >= firstPage && resultRows.length > 0)
        void (reportLoadError(loadFailure0, "加载失败，请重试", false), loadError.value = true)
      }
      return false
    } finally {
      if (owns()) {
        loading.value = false
        loadingMore.value = false
      }
    }
  }

  async function loadAllForFilter() {
    if (
      !available() ||
      !filterActive.value ||
      loadingAllForFilter.value ||
      loading.value ||
      loadingMore.value ||
      loadError.value ||
      !hasMore.value
    )
      return
    const version = generation,
      context = options.context()
    loadingAllForFilter.value = true
    try {
      while (current(version, context) && filterActive.value && hasMore.value) {
        const previousCount = persistedRowCount.value
        if (!(await loadCases(false, true)) || previousCount === persistedRowCount.value) break
      }
    } finally {
      if (current(version, context)) loadingAllForFilter.value = false
    }
  }

  function restart() {
    invalidate()
    const version = generation,
      context = options.context()
    void nextTick().then(() => {
      if (current(version, context)) void loadCases()
    })
  }

  watch(
    options.context,
    () => {
      const identityChanged = lastIdentity !== options.identity()
      lastIdentity = options.identity()
      rows.value = identityChanged ? [] : rows.value.filter((row) => row.__draft)
      pageState.page = 1
      pageState.total = 0
      options.clearSelection()
      restart()
    },
    { flush: 'sync' }
  )
  watch([filterActive, hasMore, loading, loadingMore, loadError, loadingAllForFilter], () => {
    if (filterActive.value) void loadAllForFilter()
  })
  onMounted(restart)
  onDeactivated(() => {
    active = false
    invalidate()
  })
  onActivated(() => {
    if (!active) {
      active = true
      restart()
    }
  })
  onBeforeUnmount(() => {
    active = false
    invalidate()
  })
  return {
    pageState,
    loading,
    loadingMore,
    loadError,
    filterActive,
    loadingAllForFilter,
    persistedRowCount,
    hasMore,
    loadCases,
    loadMoreCases: () => loadCases(false, true),
    retryCases: () => loadCases(!failedAppend, failedAppend),
    handleGridFilterChange: (value: { active: boolean }) => {
      filterActive.value = value.active
    },
  }
}
