import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync, readdirSync } from 'node:fs'
import path from 'node:path'
import ts from 'typescript'
import { loadModule } from './helpers/auth-config-harness.mjs'
import { harness } from './helpers/case-details-harness.mjs'

const normalize = loadModule('src/utils/api-response.ts').normalizeEmptyListTotal

test('only successful empty arrays with an absent total receive zero, without mutating the response', () => {
  for (const totalSize of [undefined, null]) {
    const source = Object.freeze({ code: 200, data: [], totalSize })
    assert.deepEqual(normalize(source), { code: 200, data: [], totalSize: 0 })
    assert.equal(source.totalSize, totalSize)
  }
  for (const source of [
    { code: 403, data: [] }, { code: 500, data: [] }, { data: [] },
    { code: 200, data: {} }, { code: 200, data: [{}] },
    ...[-1, '0', false, 20].map(totalSize => ({ code: 200, data: [], totalSize })),
  ]) assert.equal(normalize(source), source)
})

test('request errors are notified once and silent request creation cannot leak into concurrent manual requests', async () => {
  const messages = [], requests = []
  const feedback = loadModule('src/utils/load-error.ts', { '@arco-design/web-vue': { Message: { error: message => messages.push(message) } } })
  const business = loadModule('src/api/errors.ts')
  const request = { get: async (url, config) => {
    requests.push({ url, config })
    return { status: 200, data: { code: 400, msg: `Failure ${url}`, data: [] } }
  } }
  const api = loadModule('src/api/http.ts', {
    './axios.config': { default: request }, './errors': business,
    './auth-expired': { isAuthExpiredResponse: () => false, handleAuthExpired() {} },
    '@/utils/load-error': feedback, '@/utils/api-response': { normalizeEmptyListTotal: normalize },
    '@/utils/lossless-json': { containsLosslessJsonNumber: () => false },
  })
  const quiet = feedback.runLoadRequest(true, () => api.get({ url: '/quiet' })).catch(error => { feedback.reportLoadError(error); return error })
  const manual = api.get({ url: '/manual' }).catch(error => { feedback.reportLoadError(error); return error })
  await Promise.all([quiet, manual])
  assert.equal(requests[0].config.silentError, true)
  assert.equal(requests[1].config.silentError, false)
  assert.deepEqual(messages, ['Failure /manual'])
  assert.equal(feedback.isSilentLoadRequest(), false)
  assert.throws(() => feedback.runLoadRequest(true, () => { throw Error('creation failed') }))
  assert.equal(feedback.isSilentLoadRequest(), false)
})

test('all strict list DTO readers accept a successful empty response without totalSize', () => {
  const h = harness('ApiCaseScenarioEditor', 'draft')
  const scan = directory => readdirSync(directory, { withFileTypes: true }).flatMap(entry => {
    const filename = path.join(directory, entry.name)
    return entry.isDirectory() ? scan(filename) : filename.endsWith('.ts') ? [filename] : []
  })
  const files = scan('src/views').filter(filename => readFileSync(filename, 'utf8').includes('normalizeEmptyListTotal('))
  try {
    for (const filename of files) {
      const source = ts.createSourceFile(filename, readFileSync(filename, 'utf8'), ts.ScriptTarget.Latest, true)
      const readers = source.statements.filter(node => ts.isFunctionDeclaration(node) && node.modifiers?.some(m => m.kind === ts.SyntaxKind.ExportKeyword)
        && node.body?.getText(source).includes('= normalizeEmptyListTotal(') && node.body?.getText(source).includes('.totalSize'))
      const module = h.load(path.relative('src/views/apitest/case/details', filename))
      for (const node of readers) {
        const read = module[node.name.text]
        const result = read({ code: 200, data: [] })
        assert.equal(result.total, 0, `${filename}:${node.name.text}`)
        assert.throws(() => read({ code: 200, data: [], totalSize: -1 }), `${filename}:${node.name.text}`)
        assert.throws(() => read({ code: 500, data: [] }), `${filename}:${node.name.text}: failed response`)
      }
    }
  } finally { h.close() }
})
