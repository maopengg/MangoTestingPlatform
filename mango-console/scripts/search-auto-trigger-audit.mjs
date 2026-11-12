import { readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { parse } from '@vue/compiler-sfc'
import { baseParse } from '@vue/compiler-dom'

export const automaticSearchPages = [
  'src/views/apitest/mock/index.vue',
  'src/views/apitest/mock/components/MockCallLogsPanel.vue',
  'src/views/apitest/module-coverage/index.vue',
  'src/views/evaluation/case/index.vue',
  'src/views/evaluation/dataset/index.vue',
  'src/views/evaluation/grader/index.vue',
  'src/views/functional-test/defect/index.vue',
  'src/views/functional-test/iteration/index.vue',
  'src/views/functional-test/plan/components/PlanCasePickerDrawer.vue',
  'src/views/perf/run/index.vue',
  'src/views/pytest/case/index.vue',
  'src/views/report/execution-efficiency/index.vue',
  'src/views/timing/system-jobs/index.vue',
  'src/views/timing/tasks/case/index.vue',
]
const controls = new Set(['a-input', 'a-input-number', 'a-input-tag', 'a-select', 'a-cascader', 'ProductModuleSelect', 'ProjectProductSelect', 'a-range-picker', 'a-date-picker'])

export function auditAutomaticSearchSource(source, filename) {
  const { descriptor } = parse(source)
  const issues = []
  let count = 0
  function walk(node, search = false) {
    for (const child of node.children || []) {
      if (child.type !== 1) continue
      const searchScope = search || child.tag === 'TableHeader' || child.props.some(prop =>
        (prop.type === 7 && prop.name === 'slot' && prop.arg?.content === 'search') ||
        (prop.type === 6 && prop.name === 'class' && /search|filter/.test(prop.value?.content || '')))
      const model = child.props.find(prop => prop.type === 7 && prop.name === 'model')?.exp?.content || ''
      const target = search && controls.has(child.tag) && (!filename.endsWith('timing/tasks/case/index.vue') || model.startsWith('ruleFilter.'))
      if (target) {
        count++
        const expected = child.tag === 'a-input' ? ['blur', 'clear', 'mouseleave'] : child.tag === 'a-input-number' ? ['blur', 'mouseleave'] : ['change']
        for (const event of expected) {
          const handler = child.props.find(prop => prop.type === 7 && prop.name === 'on' && prop.arg?.content === event)?.exp?.content
          if (handler !== 'autoSearch.schedule') issues.push(`${filename}:${child.loc.start.line} ${model} 未通过公共防抖触发 ${event}`)
        }
      }
      walk(child, searchScope)
    }
  }
  if (descriptor.template) walk(baseParse(descriptor.template.content))
  if (count && !source.includes('useDebouncedSearch(')) issues.push(`${filename} 未接入公共搜索防抖`)
  return { count, issues }
}

export function auditAutomaticSearch() {
  const results = automaticSearchPages.map(filename => auditAutomaticSearchSource(readFileSync(filename, 'utf8'), filename))
  return { controls: results.reduce((sum, item) => sum + item.count, 0), issues: results.flatMap(item => item.issues) }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const result = auditAutomaticSearch()
  console.log(`Automatic search audit: ${automaticSearchPages.length} pages, ${result.controls} controls`)
  result.issues.forEach(issue => console.log(issue))
  console.log(`Issues: ${result.issues.length}`)
  process.exitCode = result.issues.length ? 1 : 0
}
