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
