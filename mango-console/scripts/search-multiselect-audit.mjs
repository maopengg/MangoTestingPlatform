import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import ts from 'typescript'
import { parse as parseSfc } from '@vue/compiler-sfc'
import { baseParse, NodeTypes } from '@vue/compiler-dom'

const scriptDir = path.dirname(fileURLToPath(import.meta.url))
const projectRoot = path.resolve(scriptDir, '..')
const viewsRoot = path.join(projectRoot, 'src/views')

const defaultSingleSelectSearchKeys = new Set([
  'project_product',
  'module',
  'page_id',
  'tasks_id',
  'scheduled_task',
  'report_source',
  'project',
  'scenario_tags',
  'test_envs',
  'is_latest',
])

const exactQueryAllowlist = new Map([
  [
    'src/views/system/error-record/config.ts#conditionItems',
    '聚合异常接口仅 source 支持逗号分隔多值，category 仍是精确单值。',
  ],
])

const directExactQueryAllowlist = new Map()
function allowDirectExactQuery(file, models, reason) {
  models.forEach((model) => directExactQueryAllowlist.set(`${file}#${model}`, reason))
}
allowDirectExactQuery(
  'src/views/gray/repository/index.vue',
  ['query.test_env'],
  '包含代表 NULL 的公共环境；当前接口不支持将 NULL 与环境 ID 组合为 OR 查询。'
)
allowDirectExactQuery(
  'src/views/apitest/mock/components/MockCallLogsPanel.vue',
  ['logs.filters.assertion_passed'],
  'Mock 调用记录接口仅解析 assertion_passed 精确单值，不支持 __in。'
)
allowDirectExactQuery(
  'src/views/apitest/module-coverage/index.vue',
  [
    'filters.interface_status',
    'filters.coverage_policy',
    'filters.api_info_binding_status',
    'filters.status',
    'filters.change_status',
    'filters.coverage_validity',
    'filters.scenario_layer',
    'filters.scenario_type',
    'filters.scenario_tag',
  ],
  '模块覆盖率接口使用自定义精确查询，当前不解析 __in。'
)
allowDirectExactQuery(
  'src/views/functional-test/defect/index.vue',
  [
    'filters.status',
    'filters.severity',
    'filters.priority',
    'filters.defect_type',
    'filters.source_type',
    'filters.assignee',
    'filters.reporter',
    'filters.source_plan',
  ],
  '缺陷列表使用自定义精确查询，当前不解析 __in。'
)
allowDirectExactQuery(
  'src/views/functional-test/suite/details/index.vue',
  [
    'caseFilters.test_type',
    'caseFilters.scenario_layer',
    'caseFilters.scenario_type',
    'caseFilters.scenario_tag',
    'caseFilters.change_status',
    'caseFilters.automation_impact_status',
  ],
  '来源用例复用 ManualTestCaseCRUD.get；test_type/scenario_tag 按 JSON 单元素 contains 过滤，其余枚举精确查询，接口未拆分 __in 逗号集合。'
)
allowDirectExactQuery(
  'src/views/functional-test/suite/index.vue',
  [
    'caseFilter.requirement_name',
    'caseFilter.test_type',
    'caseFilter.scenario_layer',
    'caseFilter.scenario_type',
    'caseFilter.scenario_tag',
    'caseFilter.change_status',
    'caseFilter.automation_impact_status',
  ],
  '功能用例列表包含数组字段和自定义精确查询，当前不统一解析 __in。'
)
allowDirectExactQuery(
  'src/views/timing/tasks/index.vue',
  [
    'taskGroupFilters.status',
    'taskGroupFilters.is_notice',
    'taskGroupFilters.sync_status',
  ],
  '定时任务依赖型筛选与任务组接口使用专用单值查询协议。'
)

function walk(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const target = path.join(directory, entry.name)
    if (entry.isDirectory()) return walk(target)
    return entry.isFile() && entry.name === 'config.ts' ? [target] : []
  })
}

function walkVueIndexes(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const target = path.join(directory, entry.name)
    if (entry.isDirectory()) return walkVueIndexes(target)
    return entry.isFile() && entry.name.endsWith('.vue') ? [target] : []
  })
}

function propertyName(node) {
  if (ts.isIdentifier(node) || ts.isStringLiteral(node)) return node.text
  return ''
}

function unwrapArray(initializer) {
  let current = initializer
  while (current && ts.isCallExpression(current) && current.arguments.length) {
    current = current.arguments[0]
  }
  return current && ts.isArrayLiteralExpression(current) ? current : null
}

function searchChoiceDefinitions(arrayNode, sourceFile) {
  return arrayNode.elements.flatMap((element) => {
    if (!ts.isObjectLiteralExpression(element)) return []
    const properties = Object.fromEntries(
      element.properties.flatMap((property) => {
        if (!ts.isPropertyAssignment(property)) return []
        return [[propertyName(property.name), property.initializer.getText(sourceFile)]]
      })
    )
    if (!/^['"](?:select|cascader)['"]$/.test(properties.type || '')) return []
    return [properties]
  })
}

function escapesRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function usesCollection(vueSource, name) {
  return new RegExp(`\\b${escapesRegExp(name)}\\b`).test(vueSource)
}

function enablesMultiSelect(configSource, name) {
  return new RegExp(`enableMultiSelectSearch\\s*\\(\\s*${escapesRegExp(name)}\\b`).test(
    configSource
  )
}

function hasMultipleBinding(vueSource, indexPath) {
  const components = [...vueSource.matchAll(/import\s+\w+SearchFilters\s+from\s+['"]([^'"]+)['"]/g)]
  if (components.length) {
    return components.every(([, importPath]) => {
      const filename = importPath.startsWith('@/')
        ? path.join(projectRoot, 'src', importPath.slice(2))
        : path.resolve(path.dirname(indexPath), importPath)
      return /:multiple\s*=\s*["'][^"']*item\.multiple/.test(fs.readFileSync(filename, 'utf8'))
    })
  }
  return (
    /:multiple\s*=\s*["']item\.multiple["']/.test(vueSource) ||
    /<ApiResourceSearchFilters\b/.test(vueSource)
  )
}

function hasArrayAwareReset(vueSource) {
  return (
    /\.value\s*=\s*[^\n;]*\.multiple\s*\?\s*\[\]/.test(vueSource) ||
    /\.reset\?\.\(\)/.test(vueSource) ||
    /\.reset\(\)/.test(vueSource)
  )
}

function findSingleSelectSearchModels(vueSource, filename = '') {
  const template = parseSfc(vueSource).descriptor.template?.content
  if (!template) return []
  const models = []
  const ast = baseParse(template)
  function visit(node, insideSearch = false) {
    if (!node || typeof node !== 'object') return
    let isSearch = insideSearch
    if (node.type === NodeTypes.ELEMENT && node.props.some(property =>
      property.type === NodeTypes.DIRECTIVE && property.name === 'if' && property.exp?.content === 'false')) return
    if (node.type === NodeTypes.ELEMENT && node.tag === 'template') {
      isSearch ||= node.props.some(
        (property) =>
          property.type === NodeTypes.DIRECTIVE &&
          property.name === 'slot' &&
          property.arg?.type === NodeTypes.SIMPLE_EXPRESSION &&
          ['search', 'search-content'].includes(property.arg.content)
      )
    }
    if (node.type === NodeTypes.ELEMENT && node.tag === 'TableSearchPanel') isSearch = true
    if (isSearch && node.type === NodeTypes.ELEMENT && node.tag === 'a-select') {
      const model = node.props.find(
        (property) => property.type === NodeTypes.DIRECTIVE && property.name === 'model'
      )
      const multiple = node.props.some(
        (property) =>
          (property.type === NodeTypes.ATTRIBUTE && property.name === 'multiple') ||
          (property.type === NodeTypes.DIRECTIVE && property.arg?.content === 'multiple' &&
            (model?.exp?.content !== 'item.value' || property.exp?.content?.includes('item.multiple')))
      )
      if (!multiple) {
        if (model?.type === NodeTypes.DIRECTIVE && model.exp?.content)
          models.push(model.exp.content)
      }
    }
    ;(node.children || []).forEach((child) => visit(child, isSearch))
  }
  visit(ast, /SearchFilters\.vue$/.test(filename))
  return models
}

const issues = []
const exceptions = []
let checkedCollections = 0

for (const configPath of walk(viewsRoot)) {
  const configSource = fs.readFileSync(configPath, 'utf8')
  const indexPath = path.join(path.dirname(configPath), 'index.vue')
  if (!fs.existsSync(indexPath)) continue
  const vueSource = fs.readFileSync(indexPath, 'utf8')
  const sourceFile = ts.createSourceFile(
    configPath,
    configSource,
    ts.ScriptTarget.Latest,
    true,
    ts.ScriptKind.TS
  )

  for (const statement of sourceFile.statements) {
    if (!ts.isVariableStatement(statement)) continue
    for (const declaration of statement.declarationList.declarations) {
      if (!ts.isIdentifier(declaration.name) || !declaration.initializer) continue
      const name = declaration.name.text
      if (!/ConditionItems$/i.test(name)) continue
      const arrayNode = unwrapArray(declaration.initializer)
      if (!arrayNode) continue
      const choices = searchChoiceDefinitions(arrayNode, sourceFile).filter(
        (item) =>
          !defaultSingleSelectSearchKeys.has(String(item.key || '').replace(/^['"]|['"]$/g, ''))
      )
      if (!choices.length || !usesCollection(vueSource, name)) continue

      checkedCollections += 1
      const relativeConfig = path.relative(projectRoot, configPath)
      const relativeIndex = path.relative(projectRoot, indexPath)
      const allowlistKey = `${relativeConfig}#${name}`
      const allowReason = exactQueryAllowlist.get(allowlistKey)
      const usesHelper = enablesMultiSelect(configSource, name)
      const allExplicitlyMultiple = choices.every(
        (item) =>
          item.multiple === 'true' && /(?:ref(?:<[^>]+>)?\(\[\]\)|\[\])/.test(item.value || '')
      )

      if (!usesHelper && !allExplicitlyMultiple) {
        if (allowReason) {
          exceptions.push(`${allowlistKey}: ${allowReason}`)
          continue
        }
        issues.push(`${allowlistKey}: 活跃搜索下拉框未通过 enableMultiSelectSearch 统一启用多选。`)
        continue
      }

      if (usesHelper && !hasMultipleBinding(vueSource, indexPath)) {
        issues.push(`${relativeIndex}: 搜索选择器未绑定 :multiple="item.multiple"。`)
      }
      if (usesHelper && !hasArrayAwareReset(vueSource)) {
        issues.push(`${relativeIndex}: 搜索重置未按 multiple 恢复为空数组。`)
      }
    }
  }
}

for (const indexPath of walkVueIndexes(viewsRoot)) {
  const vueSource = fs.readFileSync(indexPath, 'utf8')
  const relativeIndex = path.relative(projectRoot, indexPath)
  for (const model of findSingleSelectSearchModels(vueSource, indexPath)) {
    const key = `${relativeIndex}#${model}`
    const reason = directExactQueryAllowlist.get(key)
    if (reason) exceptions.push(`${key}: ${reason}`)
    else issues.push(`${key}: 手写搜索下拉框未启用多选，也未登记后端单值查询原因。`)
  }
  const setupSource = vueSource.match(
    /<script\s+setup(?:\s+lang=["']ts["'])?>([\s\S]*?)<\/script>/
  )?.[1]
  if (!setupSource) continue
  const sourceFile = ts.createSourceFile(
    indexPath,
    setupSource,
    ts.ScriptTarget.Latest,
    true,
    ts.ScriptKind.TS
  )

  for (const statement of sourceFile.statements) {
    if (!ts.isVariableStatement(statement)) continue
    for (const declaration of statement.declarationList.declarations) {
      if (!ts.isIdentifier(declaration.name) || !declaration.initializer) continue
      const name = declaration.name.text
      if (!/ConditionItems$/i.test(name)) continue
      const arrayNode = unwrapArray(declaration.initializer)
      if (!arrayNode) continue
      const choices = searchChoiceDefinitions(arrayNode, sourceFile).filter(
        (item) =>
          !defaultSingleSelectSearchKeys.has(String(item.key || '').replace(/^['"]|['"]$/g, ''))
      )
      if (!choices.length) continue

      checkedCollections += 1
      const usesHelper = enablesMultiSelect(setupSource, name)
      const allExplicitlyMultiple = choices.every(
        (item) =>
          item.multiple === 'true' && /(?:ref(?:<[^>]+>)?\(\[\]\)|\[\])/.test(item.value || '')
      )

      if (!usesHelper && !allExplicitlyMultiple) {
        issues.push(
          `${relativeIndex}#${name}: 页面内搜索下拉框未通过 enableMultiSelectSearch 统一启用多选。`
        )
        continue
      }
      if (usesHelper && !hasMultipleBinding(vueSource, indexPath)) {
        issues.push(`${relativeIndex}: 搜索选择器未绑定 :multiple="item.multiple"。`)
      }
      if (usesHelper && !hasArrayAwareReset(setupSource)) {
        issues.push(`${relativeIndex}: 搜索重置未按 multiple 恢复为空数组。`)
      }
    }
  }
}

console.log('Mango search multi-select audit')
console.log(`Checked active search collections: ${checkedCollections}`)
console.log(`Allowed exact-query exceptions: ${exceptions.length}`)
exceptions.forEach((item) => console.log(`- ${item}`))
console.log(`Issues: ${issues.length}`)
issues.forEach((item) => console.log(`- ${item}`))

if (issues.length) process.exitCode = 1
