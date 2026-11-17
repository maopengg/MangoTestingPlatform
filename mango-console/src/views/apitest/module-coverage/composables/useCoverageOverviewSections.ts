import { onActivated, onBeforeUnmount, onDeactivated, ref, watch } from 'vue'
import { getCoverageInventory, getCoverageModuleProgress } from '@/api/apitest/module-coverage'
import type { CoverageOverview, CoverageModuleOverview } from '@/api/apitest/module-coverage'
import { usePagination } from '@/hooks/table'
import { useDebouncedSearch } from '@/hooks/useDebouncedSearch'
import { reportLoadError } from '@/utils/load-error'

export function useCoverageOverviewSections(scope: () => Record<string, unknown>, refreshKey: () => unknown = () => 0) {
  const inventory = ref<CoverageOverview['project_inventory_summary']>()
  const inventoryLoading = ref(false), modulesLoading = ref(false)
  const modules = ref<CoverageModuleOverview[]>([])
  const keyword = ref(''), gapFilter = ref('all')
  let active = true, inventoryRequest = 0, modulesRequest = 0
  const pagination = usePagination(loadModules, modulesLoading)

  async function loadInventory() {
    const request = ++inventoryRequest
    inventoryLoading.value = true
    try {
      const response = await getCoverageInventory(scope())
      if (active && request === inventoryRequest) inventory.value = response.data.project_inventory_summary
    } catch (error) {
      if (active && request === inventoryRequest) reportLoadError(error, '模块盘点统计加载失败，请重新查询', false)
    } finally {
      if (request === inventoryRequest) inventoryLoading.value = false
    }
  }
  async function loadModules() {
    if (!active) return
    const request = ++modulesRequest
    modulesLoading.value = true
    try {
      const response = await getCoverageModuleProgress({
        ...scope(), page: pagination.page, pageSize: pagination.pageSize,
        keyword: keyword.value.trim(), progress: gapFilter.value,
      })
      if (!active || request !== modulesRequest) return
      modules.value = response.data.items
      pagination.setTotalSize(response.data.count)
    } catch (error) {
      if (active && request === modulesRequest) reportLoadError(error, '模块进度加载失败，请重新查询', false)
    } finally {
      if (request === modulesRequest) modulesLoading.value = false
    }
  }
  function searchModules() {
    ++modulesRequest
    modules.value = []
    pagination.setTotalSize(0)
    pagination.page = 1
    return loadModules()
  }
  const search = useDebouncedSearch(searchModules, () => keyword.value.trim())
  watch(gapFilter, () => { void search.run() })
  function reset() {
    ++inventoryRequest
    ++modulesRequest
    inventory.value = undefined
    modules.value = []
    pagination.setTotalSize(0)
    pagination.page = 1
    search.sync()
    if (active) { void loadInventory(); void loadModules() }
  }
  watch(() => JSON.stringify([scope(), refreshKey()]), reset, { immediate: true })
  function suspend() {
    active = false
    ++inventoryRequest
    ++modulesRequest
    inventoryLoading.value = false
    modulesLoading.value = false
  }
  onBeforeUnmount(suspend)
  onDeactivated(suspend)
  onActivated(() => { if (!active) { active = true; reset() } })
  return { inventory, inventoryLoading, modules, modulesLoading, pagination, keyword, gapFilter,
    scheduleSearch: search.schedule, searchModules: search.run }
}
