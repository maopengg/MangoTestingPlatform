import { computed, shallowReactive } from 'vue'
const writes = shallowReactive(new Set<string>())
export function useStepHealingWrite(id: () => string | number) {
  const saving = computed(() => writes.has(String(id())))
  async function executeLocked(action: () => Promise<boolean>) {
    const key = String(id())
    if (writes.has(key)) return false
    writes.add(key)
    try { return await action() } finally { writes.delete(key) }
  }
  return { saving, executeLocked }
}
