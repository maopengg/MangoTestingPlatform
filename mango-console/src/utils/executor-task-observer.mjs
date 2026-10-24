const STORAGE_PREFIX = 'mango:executor-task:'
const MAX_OBSERVATION_AGE_MS = 24 * 60 * 60 * 1000

function storageAvailable() {
  return typeof window !== 'undefined' && window.sessionStorage
}

function storageKey(scope, businessId = '') {
  return `${STORAGE_PREFIX}${String(scope || '')}:${String(businessId ?? '')}`
}

export function saveExecutorTaskObservation(scope, businessId, observation) {
  if (!storageAvailable() || !scope || !observation?.taskId) return false
  const value = {
    ...observation,
    taskId: String(observation.taskId),
    businessId: String(businessId ?? ''),
    savedAt: Date.now(),
  }
  window.sessionStorage.setItem(storageKey(scope, businessId), JSON.stringify(value))
  return true
}

export function loadExecutorTaskObservation(scope, businessId) {
  if (!storageAvailable() || !scope) return null
  const key = storageKey(scope, businessId)
  const text = window.sessionStorage.getItem(key)
  if (!text) return null
  try {
    const value = JSON.parse(text)
    if (!value?.taskId) throw new Error('invalid task observation')
    if (!value.savedAt || Date.now() - Number(value.savedAt) > MAX_OBSERVATION_AGE_MS) {
      throw new Error('expired task observation')
    }
    return value
  } catch (_error) {
    window.sessionStorage.removeItem(key)
    return null
  }
}

export function clearExecutorTaskObservation(scope, businessId, taskId = '') {
  if (!storageAvailable() || !scope) return
  const key = storageKey(scope, businessId)
  if (taskId) {
    const current = loadExecutorTaskObservation(scope, businessId)
    if (current && String(current.taskId) !== String(taskId)) return
  }
  window.sessionStorage.removeItem(key)
}
