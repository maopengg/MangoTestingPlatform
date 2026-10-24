import { onScopeDispose, ref } from 'vue'
import { getApiCaseConfigurationSummary } from '@/api/apitest/case'
import type { ApiCaseConfigurationSummary } from '@/types/api-test/case'

export function useCaseConfigurationSummary() {
  const summaries = ref<Record<number, ApiCaseConfigurationSummary>>({})
  const loading = ref(false)
  let version = 0

  function reset(pending = false) {
    version += 1
    summaries.value = {}
    loading.value = pending
  }

  async function load(caseIds: number[]) {
    reset()
    const request = version
    const ids = [...new Set(caseIds)].filter(id => Number.isSafeInteger(id) && id > 0)
    if (!ids.length) return
    loading.value = true
    try {
      for (let start = 0; start < ids.length; start += 200) {
        const res = await getApiCaseConfigurationSummary(ids.slice(start, start + 200))
        if (request !== version) return
        for (const summary of res.data as ApiCaseConfigurationSummary[]) {
          summaries.value[summary.id] = summary
        }
      }
    } catch {
      // 未回填的行显示失败入口，不能将请求失败当成“无配置”。
    } finally {
      if (request === version) loading.value = false
    }
  }

  onScopeDispose(reset)
  return { summaries, loading, load, reset }
}
