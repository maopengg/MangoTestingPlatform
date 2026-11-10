import type { ApiCaseConfigurationItem } from '@/types/api-test/case'

export interface PublicationReviewSummary {
  id: number
  name: string
  owner: string
  product: string
  module: string
  status: number
  publication_status: 'unpublished' | 'prepublished' | 'published'
  scenario_tags: string[]
  sql_count: number
  factory_count: number
  revision_id?: number | null
  configuration_details?: ApiCaseConfigurationItem[]
  eligibility_reasons: string[]
}

function reviewObject(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : null
}

export function readPublicationReview(value: unknown, id: number): PublicationReviewSummary {
  const response = reviewObject(value), row = reviewObject(response?.data)
  const count = (value: unknown): value is number => typeof value === 'number' && Number.isSafeInteger(value) && value >= 0
  const strings = (value: unknown): value is string[] => Array.isArray(value) && value.every(item => typeof item === 'string')
  if (!response || response.code !== 200 || !row || row.id !== id || typeof row.name !== 'string' || typeof row.status !== 'number' || !Number.isInteger(row.status) || !count(row.sql_count) || !count(row.factory_count) || !strings(row.scenario_tags) || !strings(row.eligibility_reasons)) throw new Error('Invalid publication review')
  const publication = row.publication_status
  if (publication !== 'unpublished' && publication !== 'prepublished' && publication !== 'published') throw new Error('Invalid publication state')
  const revision = row.revision_id
  if (revision !== undefined && revision !== null && !count(revision)) throw new Error('Invalid publication revision')
  let configurations: ApiCaseConfigurationItem[] | undefined
  if (row.configuration_details !== undefined) {
    if (!Array.isArray(row.configuration_details)) throw new Error('Invalid review configurations')
    configurations = row.configuration_details.map(value => {
      const item = reviewObject(value), configuration = reviewObject(item?.configuration)
      if (!item || !configuration || (item.kind !== 'sql' && item.kind !== 'data_factory') || typeof item.location !== 'string' || (item.enabled !== null && typeof item.enabled !== 'boolean')) throw new Error('Invalid review configuration')
      return { kind: item.kind, location: item.location, enabled: item.enabled, configuration }
    })
  }
  return {
    id, name: row.name, owner: typeof row.owner === 'string' ? row.owner : '', product: typeof row.product === 'string' ? row.product : '', module: typeof row.module === 'string' ? row.module : '',
    status: row.status, publication_status: publication, sql_count: row.sql_count, factory_count: row.factory_count,
    scenario_tags: [...row.scenario_tags], eligibility_reasons: [...row.eligibility_reasons], revision_id: revision,
    configuration_details: configurations,
  }
}

export function publicationReviewEnumTitle(options: unknown, value: unknown): string {
  const fallback = typeof value === 'string' || typeof value === 'number' ? String(value) : '-'
  if (!Array.isArray(options)) return fallback
  const item = options.map(reviewObject).find(item => item && String(item.key) === String(value) && typeof item.title === 'string')
  return typeof item?.title === 'string' ? item.title : fallback
}

export function checkPublicationResponse(value: unknown): void {
  if (reviewObject(value)?.code !== 200) throw new Error('Invalid publication response')
}

/** 场景标签对应的人工审核要求，不代表配置检测或审批结论。 */
export function requiresCaseReview(tags: unknown): boolean {
  return Array.isArray(tags) && tags.some((tag) => tag === 'production_inspection' || tag === 'production_regression')
}

export function reviewRequirements(tags: unknown): string[] {
  const scenes = new Set(Array.isArray(tags) ? tags : [])
  const inspection = scenes.has('production_inspection')
  const regression = scenes.has('production_regression')
  const requirements: string[] = []
  if (inspection || regression) requirements.push('确认无 SQL、数据工厂配置。')
  if (inspection) requirements.push('仅限只读，禁止新增、修改、删除。')
  if (regression) requirements.push('写操作仅限专用测试数据，隔离运行，失败也清理。')
  if (inspection && regression) requirements.push('生产巡检与生产回归要求不同，请确认标签是否准确。')
  if (!requirements.length) requirements.push('核对步骤、断言与前后置，确保影响可控。')
  return requirements
}

export function reviewRequirementParts(text: string): Array<{ text: string; emphasis: boolean }> {
  const keyPhrases = /^(无 SQL、数据工厂|只读|禁止新增、修改、删除|专用测试数据|隔离运行|失败也清理|影响可控)$/
  return text.split(/(无 SQL、数据工厂|只读|禁止新增、修改、删除|专用测试数据|隔离运行|失败也清理|影响可控)/)
    .filter(Boolean).map((part) => ({ text: part, emphasis: keyPhrases.test(part) }))
}
