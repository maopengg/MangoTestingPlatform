import { nextTick } from 'vue'

function waitFrame() {
  return new Promise<void>((resolve) => requestAnimationFrame(() => resolve()))
}

function delay(ms: number) {
  return new Promise<void>((resolve) => window.setTimeout(resolve, ms))
}

export function useApiCasePanelLoader(state: { caseDetailTabLoading: boolean }) {
  let generation = 0
  let activeLoads = 0
  const loadedPanelKeys = new Set<string>()

  function panelLoaded(key: string) {
    return loadedPanelKeys.has(key)
  }

  function markPanelLoaded(key: string) {
    loadedPanelKeys.add(key)
  }

  function clearPanelCache() {
    generation++
    activeLoads = 0
    state.caseDetailTabLoading = false
    loadedPanelKeys.clear()
  }

  async function runWithPanelLoading(task: () => void | Promise<void>) {
    const current = generation
    activeLoads++
    let finished = false
    const loadingTimer = window.setTimeout(() => {
      if (!finished && current === generation) state.caseDetailTabLoading = true
    }, 180)
    try {
      await task()
      await nextTick()
      await waitFrame()
      await waitFrame()
      if (state.caseDetailTabLoading) await delay(120)
    } finally {
      finished = true
      window.clearTimeout(loadingTimer)
      if (current === generation) {
        activeLoads = Math.max(0, activeLoads - 1)
        if (!activeLoads) state.caseDetailTabLoading = false
      }
    }
  }

  return { panelLoaded, markPanelLoaded, clearPanelCache, runWithPanelLoading }
}
