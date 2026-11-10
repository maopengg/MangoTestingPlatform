
import { reportLoadError } from '@/utils/load-error'
import { onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, watch } from 'vue'
import { getGrayFeature, getGrayYamlFile } from '@/api/gray'
import { usePagination } from '@/hooks/table'
import { parseYamlOptions, type Option } from '../editor-form'
import { featurePage, requestParams, type FeatureQuery, type FeatureRow } from '../records'

export function useFeatureList(query: FeatureQuery, contextKey: () => string) {
  const rows = ref<FeatureRow[]>([]),
    loading = ref(false),
    error = ref('')
  const yamlOptions = ref<Option[]>([]),
    optionsLoading = ref(false),
    optionsError = ref('')
  const pagination = usePagination(search, loading)
  let active = true,
    mounted = false,
    generation = 0,
    listSequence = 0,
    optionSequence = 0
  async function search(): Promise<boolean> {
    if (!active) {
      loading.value = false
      return false
    }
    const sequence = ++listSequence,
      version = generation,
      context = contextKey()
    const current = () =>
      active && version === generation && sequence === listSequence && context === contextKey()
    loading.value = true
    error.value = ''
    try {
      const result = featurePage(
        await getGrayFeature(requestParams(query, pagination.page, pagination.pageSize))
      )
      if (!current()) return false
      const last = Math.max(1, Math.ceil(result.total / pagination.pageSize))
      if (pagination.page > last) {
        pagination.page = last
        return await search()
      }
      rows.value = result.rows
      pagination.setTotalSize(result.total)
      return true
    } catch (loadFailure0) {
      if (current()) (reportLoadError(loadFailure0, "灰度开关读取失败，请重试查询", false), error.value = '灰度开关读取失败，请重试查询')
      return false
    } finally {
      if (current()) loading.value = false
    }
  }
  async function loadOptions(): Promise<boolean> {
    if (!active) return false
    const sequence = ++optionSequence,
      version = generation,
      context = contextKey()
    const current = () =>
      active && version === generation && sequence === optionSequence && context === contextKey()
    optionsLoading.value = true
    optionsError.value = ''
    try {
      const result = parseYamlOptions(await getGrayYamlFile({}))
      if (!current()) return false
      yamlOptions.value = result
      return true
    } catch (loadFailure1) {
      if (current()) (reportLoadError(loadFailure1, "配置文件选项读取失败，请重试", false), optionsError.value = '配置文件选项读取失败，请重试')
      return false
    } finally {
      if (current()) optionsLoading.value = false
    }
  }
  function invalidate() {
    ++generation
    ++listSequence
    ++optionSequence
    rows.value = []
    yamlOptions.value = []
    loading.value = false
    optionsLoading.value = false
    error.value = ''
    optionsError.value = ''
    pagination.setTotalSize(0)
  }
  function reload() {
    void search()
    void loadOptions()
  }
  watch(
    contextKey,
    () => {
      invalidate()
      if (mounted && active) reload()
    },
    { flush: 'sync' }
  )
  onMounted(() => {
    mounted = true
    reload()
  })
  onDeactivated(() => {
    active = false
    invalidate()
  })
  onActivated(() => {
    if (!active) {
      active = true
      if (mounted) reload()
    }
  })
  onBeforeUnmount(() => {
    active = false
    invalidate()
  })
  return {
    rows,
    loading,
    error,
    yamlOptions,
    optionsLoading,
    optionsError,
    pagination,
    search,
    loadOptions,
  }
}
