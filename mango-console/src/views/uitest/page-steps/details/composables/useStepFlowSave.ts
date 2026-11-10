import { ref } from 'vue'
import { putUiSteps } from '@/api/uitest/page-steps'
import { cloneLosslessJson } from '@/utils/lossless-json'
import { stepResponse, type StepFlow, type StepId } from '@/components/business/ui-page-step'

export function useStepFlowSave(options: { capture: () => () => boolean; id: () => StepId | null; enabled: () => boolean; flow: () => StepFlow; reconcile?: (id: StepId) => void }) {
  const saving = ref(false), status = ref<'saved' | 'dirty' | 'saving' | 'error'>('saved'), error = ref('')
  const revision = ref(0), savedRevision = ref(0)
  let timer: ReturnType<typeof setTimeout> | null = null, pending: Promise<void> | null = null, epoch = 0
  function cancelTimer() { if (timer !== null) clearTimeout(timer); timer = null }
  function markSaved(value = revision.value) { savedRevision.value = value; status.value = revision.value === value ? 'saved' : 'dirty'; error.value = '' }
  function invalidate() { epoch++; cancelTimer(); revision.value = savedRevision.value = 0; status.value = 'saved'; error.value = '' }
  function schedule() {
    cancelTimer(); const current = options.capture(), generation = epoch
    if (!current() || !options.enabled()) return
    timer = setTimeout(() => { timer = null; if (current() && generation === epoch) void persist() }, 1000)
  }
  function persist(): Promise<void> {
    const current = options.capture(), generation = epoch, id = options.id()
    if (!current() || !options.enabled() || id === null) return Promise.resolve()
    if (pending) return pending.then(() => { if (current() && generation === epoch && revision.value !== savedRevision.value) return persist() })
    cancelTimer()
    const version = revision.value, snapshot = { id, flow_data: cloneLosslessJson(options.flow()) }
    saving.value = true; status.value = 'saving'; error.value = ''
    const request = Promise.resolve().then(async () => {
      try { if (!current() || generation !== epoch) return; stepResponse(await putUiSteps(snapshot)); if (current() && generation === epoch) markSaved(version) }
      catch { if (current() && generation === epoch) { status.value = 'error'; error.value = '画布保存失败，请重试保存' } }
      finally {
        if (pending === request) { pending = null; saving.value = false }
        if (current() && generation === epoch && status.value === 'dirty') schedule()
        // A hidden workspace may have reloaded before its outstanding write settled.
        // Re-read that same asset; never apply the old response to its replacement.
        if (!current() && options.capture()() && String(id) === String(options.id()) && revision.value === 0) options.reconcile?.(id)
      }
    })
    pending = request; return request
  }
  return { saving, status, error, revision, savedRevision, cancelTimer, markSaved, invalidate, schedule, persist, wait: () => pending ?? Promise.resolve() }
}
