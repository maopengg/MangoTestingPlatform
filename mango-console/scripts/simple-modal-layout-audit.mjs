import { readFileSync, readdirSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { parse } from '@vue/compiler-sfc'
import { baseParse } from '@vue/compiler-dom'

export function elements(node) {
  return (node.children || []).flatMap(child => child.type === 1 ? [child, ...elements(child)] : [])
}

export function classifyModal(modal) {
  const nodes = elements(modal)
  if (!nodes.some(node => node.tag === 'a-form')) return 'other'
  if (nodes.some(node => /^(section|header|a-tabs|a-tab-pane|a-collapse|a-divider|fieldset|h[1-6])$/.test(node.tag)
    || node.props.some(prop => prop.type === 6 && prop.name === 'class' && /section|group-title|form-group/.test(prop.value?.content || '')))) return 'grouped'
  if (nodes.some(node => /^(a-table|a-tree|TableBody|TableSearchPanel|MangoJsonEditDrawer)$/.test(node.tag))) return 'workbench'
  return 'simple'
}

export function modalInventory(source) {
  const { descriptor } = parse(source)
  if (!descriptor.template) return []
  return elements(baseParse(descriptor.template.content))
    .filter(node => ['a-modal', 'ModalDialog'].includes(node.tag))
    .map(node => ({ node, kind: classifyModal(node) }))
}

export function filesUnder(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap(entry => {
    const filename = path.join(directory, entry.name)
    return entry.isDirectory() ? filesUnder(filename) : filename.endsWith('.vue') ? [filename] : []
  })
}

export function auditSimpleModals(root = 'src') {
  const issues = [], counts = { simple: 0, grouped: 0, workbench: 0, other: 0 }
  for (const filename of filesUnder(root)) {
    for (const { node, kind } of modalInventory(readFileSync(filename, 'utf8'))) {
      counts[kind]++
      const marked = node.props.some(prop => prop.type === 6 && prop.name === 'modal-class' && prop.value?.content.split(/\s+/).includes('mango-simple-form-modal'))
      if (kind === 'simple' && !marked) issues.push(`${filename}:${node.loc.start.line} 普通表单弹窗未接入统一布局`)
      if (kind === 'simple') {
        const width = node.props.find(prop => prop.name === 'width' || (prop.type === 7 && prop.arg?.content === 'width'))
        if ((width?.value?.content || width?.exp?.content) !== '560') issues.push(`${filename}:${node.loc.start.line} 普通表单弹窗宽度应为 560`)
        for (const form of elements(node).filter(item => item.tag === 'a-form')) {
          const shared = form.props.some(prop => prop.type === 6 && prop.name === 'class' && prop.value?.content.split(/\s+/).includes('mango-simple-form'))
          const horizontal = form.props.some(prop => prop.type === 6 && prop.name === 'layout' && prop.value?.content === 'horizontal')
          if (!shared || !horizontal) issues.push(`${filename}:${form.loc.start.line} 普通表单必须使用统一的单列左右布局`)
          if (!form.props.some(prop => prop.type === 6 && prop.name === 'auto-label-width')) issues.push(`${filename}:${form.loc.start.line} 普通表单必须按最长标签自动对齐，不能固定预留标签宽度`)
          for (const field of elements(form).filter(item => item.tag === 'a-form-item')) {
            const sharedField = field.props.some(prop => prop.type === 6 && prop.name === 'class' && prop.value?.content.split(/\s+/).includes('mango-simple-form-item'))
            if (!sharedField) issues.push(`${filename}:${field.loc.start.line} 普通表单字段未接入统一布局`)
          }
        }
      }
      if (kind === 'grouped' && marked) issues.push(`${filename}:${node.loc.start.line} 分类弹窗不得使用普通表单布局`)
    }
  }
  return { counts, issues }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const { counts, issues } = auditSimpleModals()
  console.log('Mango simple modal layout audit', counts)
  for (const issue of issues) console.log(issue)
  console.log(`Issues: ${issues.length}`)
  process.exitCode = issues.length ? 1 : 0
}
