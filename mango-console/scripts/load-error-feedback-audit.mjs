import { readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { parse } from '@vue/compiler-sfc'
import { baseParse } from '@vue/compiler-dom'
import { elements, filesUnder } from './simple-modal-layout-audit.mjs'

export function auditLoadErrorFeedback(root = 'src') {
  const issues = []
  for (const filename of filesUnder(root)) {
    const { descriptor } = parse(readFileSync(filename, 'utf8'))
    if (!descriptor.template) continue
    const nodes = elements(baseParse(descriptor.template.content))
    for (const node of nodes) {
      const directText = (node.children || []).filter(child => child.type === 2 || child.type === 5)
        .map(child => child.type === 2 ? child.content : child.content.content).join(' ')
      if (/加载失败|读取失败|获取失败/.test(directText)) issues.push(`${filename}:${node.loc.start.line} 加载错误不得在页面内显示`)
      const condition = node.props.find(prop => prop.type === 7 && ['if', 'else-if'].includes(prop.name))?.exp?.content || ''
      const alert = node.tag === 'a-alert' || node.props.some(prop => prop.type === 6 && prop.name === 'role' && prop.value?.content === 'alert')
      if (alert && /^(listError|listFailed|loadError|loadFailed|readError|usersError|enumsError|optionsError|metadataError)$/.test(condition)) {
        issues.push(`${filename}:${node.loc.start.line} 加载状态只保留重试与编辑门禁，错误使用公共提示`)
      }
    }
  }
  return issues
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const issues = auditLoadErrorFeedback()
  for (const issue of issues) console.log(issue)
  console.log(`Issues: ${issues.length}`)
  process.exitCode = issues.length ? 1 : 0
}
