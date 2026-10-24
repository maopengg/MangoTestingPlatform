import { get, post } from '@/api/http'

export function getAutomationEffectivenessOverview(data: Record<string, any>) {
  return get({
    url: 'system/test/suite/effectiveness/overview',
    data: () => data,
  })
}

export function postAutomationEffectivenessCacheClear() {
  return post({
    url: 'system/test/suite/effectiveness/cache/clear',
  })
}

export function postAutomationEffectivenessAiSummary(data: Record<string, any>) {
  return post({
    url: 'system/test/suite/effectiveness/ai-summary',
    data,
    silentError: true,
  })
}
