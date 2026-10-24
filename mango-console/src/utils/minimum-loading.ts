export const LIVE_ENTRY_MINIMUM_LOADING_MS = 1200

export async function waitForMinimumLoading(
  startedAt: number,
  minimumMs = LIVE_ENTRY_MINIMUM_LOADING_MS
) {
  const remaining = Math.max(0, minimumMs - (Date.now() - startedAt))
  if (remaining > 0) await new Promise<void>((resolve) => window.setTimeout(resolve, remaining))
}
