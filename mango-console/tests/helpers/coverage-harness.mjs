import path from 'node:path'
import { reactive, ref } from 'vue'
import { harness } from './case-details-harness.mjs'
const base = path.resolve('src/views/apitest/module-coverage')
const pagination = () =>
  reactive({
    page: 1,
    pageSize: 20,
    pageCount: 0,
    setTotalSize(total) {
      this.pageCount = total
    },
  })
export function coveragePage(api = {}) {
  const paging = pagination(),
    confirmations = []
  const state = harness(
    'index',
    'activeTab,filters,rows,loading,rowsError,overview,overviewLoading,overviewError,projectProductId,moduleId,moduleIds,pagination,loadRows,loadOverview,reloadAll,search,onTabChange,onNavigationFilterChange,resetFilters,drillOverview,deactivate,archiveRow,archivingIds,assetPanel,openApiInfo,openApiCase',
    {
      base,
      api,
      Modal: {
        warning: (options) => {
          const handle = {
            options,
            close() {
              options.onClose?.()
            },
          }
          confirmations.push(handle)
          return handle
        },
      },
      modules: { '@/hooks/table': { usePagination: () => paging } },
    }
  )
  return { ...state, confirmations }
}
