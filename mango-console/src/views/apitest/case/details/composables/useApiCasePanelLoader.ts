import { nextTick } from 'vue'

function waitFrame() {
  return new Promise<void>((resolve) => requestAnimationFrame(() => resolve()))
}

function delay(ms: number) {
  return new Promise<void>((resolve) => window.setTimeout(resolve, ms))
}

export function useApiCasePanelLoader(state: { caseDetailTabLoading: boolean }) {
  const loadedPanelKeys = new Set<string>()

  function panelLoaded(key: string) {
    return loadedPanelKeys.has(key)
  }

  function markPanelLoaded(key: string) {
    loadedPanelKeys.add(key)
  }

  function clearPanelCache() {
    loadedPanelKeys.clear()
  }

  async function runWithPanelLoading(task: () => void | Promise<void>) {
    let finished = false
    const loadingTimer = window.setTimeout(() => {
      if (!finished) state.caseDetailTabLoading = true
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
      state.caseDetailTabLoading = false
    }
  }

  return { panelLoaded, markPanelLoaded, clearPanelCache, runWithPanelLoading }
}
