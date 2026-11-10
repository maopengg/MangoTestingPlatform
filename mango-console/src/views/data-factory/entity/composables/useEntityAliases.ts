
import { reportLoadError } from '@/utils/load-error'
import { ref } from 'vue'
import { getDataFactoryDatasourceAlias } from '@/api/data-factory'
import { optionId } from '../form'
import type { LogicalSource } from '../types'
export function useEntityAliases() {
  const options = ref<LogicalSource[]>([]),
    loading = ref(false),
    error = ref(false)
  let request = 0
  function clear() {
    ++request
    options.value = []
    loading.value = false
    error.value = false
  }
  async function load(product: unknown) {
    const id = optionId(product),
      current = ++request
    options.value = []
    error.value = false
    if (id === null) {
      loading.value = false
      return
    }
    loading.value = true
    try {
      const response = await getDataFactoryDatasourceAlias({ project_product: id })
      if (current === request) options.value = response.data || []
    } catch (loadFailure0) {
      if (current === request) (reportLoadError(loadFailure0, "加载失败，请重试", false), error.value = true)
    } finally {
      if (current === request) loading.value = false
    }
  }
  return { options, loading, error, clear, load }
}
