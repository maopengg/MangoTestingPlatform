import { readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { parse } from '@vue/compiler-sfc'
import { baseParse } from '@vue/compiler-dom'
import ts from 'typescript'
import { elements, filesUnder } from './simple-modal-layout-audit.mjs'

function displaysError(expression) {
  const source = ts.createSourceFile('feedback.ts', `(${expression})`, ts.ScriptTarget.Latest, true)
  function visit(node) {
    if (ts.isConditionalExpression(node)) return visit(node.whenTrue) || visit(node.whenFalse)
    if (ts.isIdentifier(node) && /^(?:error|\w*Error|errorText|errorMessage)$/.test(node.text)) return true
    return ts.forEachChild(node, visit) || false
  }
  return visit(source)
}

export function auditFeedbackSource(source, filename = 'component.vue') {
  const issues = []
    const { descriptor } = parse(source)
    if (!descriptor.template) return issues
    const nodes = elements(baseParse(descriptor.template.content))
    for (const node of nodes) {
      const successCondition = node.props.find(prop => prop.type === 7 && prop.name === 'if')?.exp?.content || ''
      if (node.tag === 'template' && /^!\s*(?:loadFailed|listFailed|loadError|listError)$/.test(successCondition) && !node.children.some(child => child.type !== 2 || child.content.trim())) {
        issues.push(`${filename}:${node.loc.start.line} 正常加载分支不得为空，移除失败提示时必须保留成功内容`)
      }
      if (node.tag === 'MangoRequestFeedback') {
        if ((node.children || []).some(child => child.type === 5 || (child.type === 2 && child.content.trim()))) {
          issues.push(`${filename}:${node.loc.start.line} MangoRequestFeedback 插槽只保留重试操作，不放错误文案`)
        }
        continue
      }
      const kind = node.props.find(prop => prop.type === 6 && prop.name === 'data-feedback-kind')?.value?.content
      if (['validation', 'execution-result'].includes(kind)) continue
      const directText = (node.children || []).filter(child => child.type === 2 || child.type === 5)
        .map(child => child.type === 2 ? child.content : child.content.content).join(' ')
      const interpolation = (node.children || []).some(child => child.type === 5 && displaysError(child.content.content))
      const errorAlert = node.tag === 'a-alert' && node.props.some(prop => prop.type === 6 && prop.name === 'type' && prop.value?.content === 'error')
      const conditional = node.props.find(prop => prop.type === 7 && ['if', 'else-if'].includes(prop.name))?.exp?.content || ''
      const alertRole = node.props.some(prop => prop.type === 6 && prop.name === 'role' && prop.value?.content === 'alert')
      const failureText = /(?:加载|读取|获取|请求|保存|删除|提交|跳转|刷新|渲染|绑定|取消关联|状态更新)[^。；，\n]{0,12}失败/.test(directText)
        && (node.tag === 'a-alert' || alertRole || /error|fail/i.test(conditional))
      if (interpolation || errorAlert || failureText) issues.push(`${filename}:${descriptor.template.loc.start.line + node.loc.start.line - 1} 请求错误使用 MangoRequestFeedback 或公共提示；业务校验和执行结果须显式标记 data-feedback-kind`)
    }
  return issues
}

export function auditLoadErrorFeedback(root = 'src') {
  return filesUnder(root).flatMap(filename => auditFeedbackSource(readFileSync(filename, 'utf8'), filename))
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const issues = auditLoadErrorFeedback()
  for (const issue of issues) console.log(issue)
  console.log(`Issues: ${issues.length}`)
  process.exitCode = issues.length ? 1 : 0
}
