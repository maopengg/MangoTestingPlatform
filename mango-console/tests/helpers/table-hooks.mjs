import { readFileSync } from 'node:fs'
import ts from 'typescript'
import * as vue from 'vue'

export function loadTableHooks() {
  const exports = {}
  const source = ts.transpileModule(readFileSync('src/hooks/table.ts', 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText
  new Function('exports', 'require', source)(exports, id => {
    if (id === 'vue') return vue
    throw new Error(`Unexpected runtime dependency: ${id}`)
  })
  return exports
}
