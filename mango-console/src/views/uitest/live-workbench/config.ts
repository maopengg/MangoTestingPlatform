import { routeLiveId } from '@/components/business/ui-live-workbench'

export function liveWorkbenchRoute(query: Record<string, unknown>) {
  return {
    mode: query.mode === 'step' ? 'step' as const : 'element' as const,
    pageId: routeLiveId(query.pageId), pageStepId: routeLiveId(query.pageStepId),
    testEnv: routeLiveId(query.testEnv),
    category: typeof query.category === 'string' ? query.category : undefined,
  }
}
