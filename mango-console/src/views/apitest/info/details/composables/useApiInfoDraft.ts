import { ref, reactive, onScopeDispose } from 'vue'
import { putApiInfo } from '@/api/apitest/info'
import { cloneLosslessJson, stringifyLosslessJson } from '@/utils/lossless-json'
import { normalizeApiInfoRecord } from '../record'
import type { ApiInfoId, ApiInfoRecord, ApiInfoPatch } from '../types'

export function useApiInfoDraft(id: () => ApiInfoId, editable: () => boolean) {
  const draft = ref<ApiInfoRecord>(normalizeApiInfoRecord(null, id()))
  const saved = ref<ApiInfoRecord>(normalizeApiInfoRecord(null, id()))
  const pendingFields = reactive(new Map<string, number>())
  let generation = 0
  let queue: Promise<unknown> = Promise.resolve()
  let lastRequest: Promise<unknown> = queue
  function invalidate() {
    generation++
    lastRequest = queue
  }
  function reset(record: ApiInfoRecord) {
    invalidate()
    saved.value = cloneLosslessJson(record)
    draft.value = cloneLosslessJson(record)
  }
  function view(record: ApiInfoRecord) {
    invalidate()
    draft.value = cloneLosslessJson(record)
  }
  function persist(payload: ApiInfoPatch) {
    if (!editable()) return Promise.resolve(null)
    const token = generation,
      target = id()
    const patch = cloneLosslessJson(payload),
      submittedDraft = cloneLosslessJson(draft.value)
    const keys = Object.keys(patch) as Array<keyof ApiInfoPatch>
    keys.forEach((key) => pendingFields.set(key, (pendingFields.get(key) || 0) + 1))
    const current = () => token === generation && String(target) === String(id()) && editable()
    const request = queue
      .catch(() => undefined)
      .then(async () => {
        if (!current()) return null
        const response = await putApiInfo({ id: target, ...patch })
        if (!current()) return null
        const confirmed = response.data ? normalizeApiInfoRecord(response.data, target) : null
        for (const key of keys) {
          const value = cloneLosslessJson(
            confirmed && Object.prototype.hasOwnProperty.call(response.data, key)
              ? confirmed[key]
              : patch[key]
          )
          Object.assign(saved.value, { [key]: value })
          if (
            stringifyLosslessJson(draft.value[key]) === stringifyLosslessJson(submittedDraft[key])
          )
            Object.assign(draft.value, { [key]: cloneLosslessJson(value) })
        }
        return response
      })
      .finally(() => {
        keys.forEach((key) => {
          const count = (pendingFields.get(key) || 1) - 1
          if (count) pendingFields.set(key, count)
          else pendingFields.delete(key)
        })
      })
    lastRequest = request
    queue = request.catch(() => undefined)
    return request
  }
  function waitForSaves() {
    return lastRequest
  }
  onScopeDispose(invalidate)
  return { draft, saved, pendingFields, reset, view, persist, invalidate, waitForSaves }
}
