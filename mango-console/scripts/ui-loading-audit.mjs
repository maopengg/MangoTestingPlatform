import { readFileSync, readdirSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { parse } from '@vue/compiler-sfc'
import { baseParse } from '@vue/compiler-dom'

// 初始遮罩要求没有实体；子面板所在分支要求已经有实体，两者不会同时渲染。
const exclusiveBranches = new Map([
  ['src/views/data-factory/template/preview/index.vue', new Set(['initialPageLoading:scenePanelLoading'])],
])

export function findNestedLoading(source, filename = '') {
  const { descriptor, errors } = parse(source, { filename })
  if (errors.length) throw new Error(`Unable to parse ${filename}`)
  if (!descriptor.template) return []
  const issues = []
  const offset = descriptor.template.loc.start.line - 1
  function visit(node, ancestors = []) {
    if (node.type === 1) {
      const binding = node.props.find(
        (prop) => prop.type === 7 && prop.name === 'bind' && prop.arg?.content === 'loading'
      )
      const expression = binding?.exp?.content || ''
      const mask = /^(a-spin|mango-panel-spin|a-table|a-list|\w+Table|TemplateFieldConfigEditor)$/.test(node.tag)
      if (expression && mask) {
        for (const parent of ancestors) {
          const excluded = exclusiveBranches.get(filename)?.has(`${parent}:${expression}`)
          const escapedParent = parent.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
          const guarded = new RegExp(`^!\\s*${escapedParent}\\s*&&`).test(expression)
          if (!excluded && !guarded) {
            issues.push({ line: node.loc.start.line + offset, parent, expression, tag: node.tag })
          }
        }
      }
      if (['a-spin', 'mango-panel-spin'].includes(node.tag) && expression && expression !== 'false') {
        ancestors = [...ancestors, expression]
      }
    }
    for (const child of node.children || []) visit(child, ancestors)
  }
  visit(baseParse(descriptor.template.content))
  return issues
}

function collectVueFiles(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const target = path.join(directory, entry.name)
    return entry.isDirectory() ? collectVueFiles(target) : target.endsWith('.vue') ? [target] : []
  })
}

export function findInvalidSpinSizes(source, filename = '') {
  const { descriptor, errors } = parse(source, { filename })
  if (errors.length) throw new Error(`Unable to parse ${filename}`)
  if (!descriptor.template) return []
  const findings = [], offset = descriptor.template.loc.start.line - 1
  function visit(node) {
    if (node.type === 1 && ['a-spin', 'mango-panel-spin', 'Spin', 'MangoPanelSpin'].includes(node.tag)) {
      for (const prop of node.props) {
        const staticSize = prop.type === 6 && prop.name === 'size'
        const stringBinding = prop.type === 7 && prop.name === 'bind' && prop.arg?.content === 'size'
          && /^(['"]).*\1$/.test(prop.exp?.content.trim() || '')
        if (staticSize || stringBinding) findings.push({ line: prop.loc.start.line + offset, tag: node.tag, message: 'Spin size must be a bound number, not a string' })
      }
    }
    for (const child of node.children || []) visit(child)
  }
  visit(baseParse(descriptor.template.content))
  return findings
}

export function auditLoading(root = process.cwd()) {
  const files = collectVueFiles(path.join(root, 'src'))
  const findings = files.flatMap((file) => {
    const filename = path.relative(root, file).split(path.sep).join('/')
    const source = readFileSync(file, 'utf8')
    return [...findNestedLoading(source, filename), ...findInvalidSpinSizes(source, filename)].map((issue) => ({ filename, ...issue }))
  })
  return { scanned: files.length, findings }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const { scanned, findings } = auditLoading()
  console.log(`Mango nested loading audit\nScanned Vue files: ${scanned}\nIssues: ${findings.length}`)
  for (const issue of findings) {
    console.log(`- ${issue.filename}:${issue.line} ${issue.message || `${issue.parent} → ${issue.expression}`} (${issue.tag})`)
  }
  if (findings.length) process.exitCode = 1
}
