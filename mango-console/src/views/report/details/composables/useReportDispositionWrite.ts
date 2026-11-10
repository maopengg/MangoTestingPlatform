import { readonly, reactive } from 'vue'

// Table refreshes can replace a row component while its write is still in flight.
const busyIds = reactive(new Set<string>())
export function useReportDispositionWrite() {
  function acquire(id: string): (() => void) | null {
    if (busyIds.has(id)) return null
    busyIds.add(id)
    let released = false
    return () => {
      if (released) return
      released = true
      busyIds.delete(id)
    }
  }
  return { busyIds: readonly(busyIds), acquire }
}
