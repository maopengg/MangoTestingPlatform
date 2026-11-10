import { ref, watch, onScopeDispose, onDeactivated } from 'vue'
import { cloneLosslessJson } from '@/utils/lossless-json'
import type { ApiCaseScenario, ScenarioPatch } from '../types'
import type { ApiCaseParameterPayload } from '@/types/api-test/case-parameter'

type Save = (payload: ApiCaseParameterPayload) => Promise<{ msg: string } | null>
export function useApiCaseScenarioDraft(
  source: () => ApiCaseScenario,
  onPatch: (patch: ScenarioPatch) => void,
  persist?: Save,
  context: () => unknown = () => undefined
) {
  const draft = ref<ApiCaseScenario>(cloneLosslessJson(source()))
  let baseline = cloneLosslessJson(source())
  let previousContext = context()
  let generation = 0
  onScopeDispose(() => {
    generation++
  })
  onDeactivated(() => {
    generation++
  })
  watch(
    () => [source(), context()] as const,
    ([value, nextContext]) => {
      if (String(value.id) !== String(baseline.id) || nextContext !== previousContext) {
        generation++
        draft.value = cloneLosslessJson(value)
      } else {
        const previous = new Map(Object.entries(baseline))
        const current = new Map(Object.entries(draft.value))
        for (const [key, field] of Object.entries(value)) {
          if (JSON.stringify(current.get(key)) === JSON.stringify(previous.get(key))) {
            Object.assign(draft.value, { [key]: cloneLosslessJson(field) })
          }
        }
      }
      baseline = cloneLosslessJson(value)
      previousContext = nextContext
    },
    { flush: 'sync' }
  )
  watch(
    () => source().result_data,
    (value) => {
      draft.value.result_data = cloneLosslessJson(value)
    },
    { flush: 'sync' }
  )
  async function save(payload: ApiCaseParameterPayload) {
    const current = generation
    const snapshot = cloneLosslessJson(payload)
    if (!persist) return null
    const response = await persist(snapshot)
    if (current === generation && String(snapshot.id) === String(source().id)) {
      const { id, ...changes } = snapshot
      onPatch({ id: Number(id), changes })
    }
    return response
  }
  return { draft, save }
}
