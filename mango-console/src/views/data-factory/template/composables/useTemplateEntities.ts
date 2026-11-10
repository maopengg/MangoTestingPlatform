
import { reportLoadError } from '@/utils/load-error'
import { ref } from 'vue'
import { getDataFactoryEntity } from '@/api/data-factory'
import { optionId, formatEntityLabel } from '../form'
import type { EntityOption, Reference } from '../types'
export function useTemplateEntities() {
  const options = ref<EntityOption[]>([]),
    loading = ref(false),
    error = ref(false)
  let sequence = 0
  function clear() {
    ++sequence
    options.value = []
    loading.value = false
    error.value = false
  }
  async function load(product: unknown, module: unknown) {
    const request = ++sequence
    options.value = []
    loading.value = true
    error.value = false
    const query: {
      page: number
      pageSize: number
      project_product?: string | number
      module?: string | number
    } = { page: 1, pageSize: 9999 }
    const productId = optionId(product),
      moduleId = optionId(module)
    if (productId !== null) query.project_product = productId
    if (moduleId !== null) query.module = moduleId
    try {
      const response = await getDataFactoryEntity(query)
      if (request === sequence)
        options.value = (response.data || []).map((item: Reference) => ({
          ...item,
          display_name: formatEntityLabel(item),
        }))
    } catch (loadFailure0) {
      if (request === sequence) (reportLoadError(loadFailure0, "加载失败，请重试", false), error.value = true)
    } finally {
      if (request === sequence) loading.value = false
    }
  }
  return { options, loading, error, load, clear }
}
