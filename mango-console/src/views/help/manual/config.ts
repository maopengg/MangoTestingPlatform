export type ManualSectionId = 'ui' | 'api' | 'settings'

interface ManualSection {
  id: ManualSectionId
  title: string
  testId: string
  description: string
}

export const manualSections: readonly ManualSection[] = [
  { id: 'ui', title: 'UI自动化', testId: 'qa-views-help-manual-a-ui自动化', description: '本节内容尚未维护。' },
  { id: 'api', title: 'API自动化', testId: 'qa-views-help-manual-a-API自动化', description: '本节内容尚未维护。' },
  { id: 'settings', title: '系统设置', testId: 'qa-views-help-manual-a-系统设置', description: '本节内容尚未维护。' },
]
