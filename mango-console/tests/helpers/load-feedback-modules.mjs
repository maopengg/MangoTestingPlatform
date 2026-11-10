import { readFileSync } from 'node:fs'
import ts from 'typescript'

const modules = new Map()
export function loadFeedbackModule(id) {
  if (!['@/utils/load-error', '@/utils/api-response'].includes(id)) return undefined
  if (modules.has(id)) return modules.get(id)
  const exports = {}
  const source = ts.transpileModule(readFileSync(`src/${id.slice(2)}.ts`, 'utf8'), {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS },
  }).outputText
  new Function('exports', 'require', source)(exports, name => {
    if (name === '@arco-design/web-vue') return { Message: { error() {} } }
    throw Error(`Unexpected feedback dependency ${name}`)
  })
  modules.set(id, exports)
  return exports
}
