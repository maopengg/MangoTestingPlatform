import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'
import ts from 'typescript'

const read = (path) => fs.readFileSync(new URL(`../src/${path}`, import.meta.url), 'utf8')
const transpile = (source) => ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS },
}).outputText
const exported = {}
new Function('exports', transpile(read('utils/permission.ts')))(exported)
const { requestPermission, hasPermissionKeys } = exported

const rules = [
  { method: 'GET', pattern: '^/api/case/\\d+$', permissions: ['api.case:read'] },
  { method: 'POST', pattern: '^/api/case/run$', permissions: ['api.case:read'] },
  { method: 'POST', pattern: '^/api/case/save$', permissions: ['api.case:change'] },
  { method: 'DELETE', pattern: '^/api/case$', permissions: ['api.case:remove'] },
  { method: 'POST', pattern: '^/pytest/repository$', permissions: ['pytest.repository:add'], updatePermissions: ['pytest.repository:change'] },
]

test('公共请求按后端显式分类匹配，不根据 GET/POST 或按钮名称猜权限', () => {
  assert.deepEqual(requestPermission(rules, 'get', 'https://example.com/api/api/case/7', {}), ['api.case:read'])
  assert.deepEqual(requestPermission(rules, 'get', '/api/case/7', {}), ['api.case:read'])
  assert.deepEqual(requestPermission(rules, 'POST', 'api/case/run', {}), ['api.case:read'])
  assert.deepEqual(requestPermission(rules, 'DELETE', '/api/case', {}), ['api.case:remove'])
  assert.equal(requestPermission(rules, 'GET', '/api/case/run', {}), undefined)
  assert.equal(requestPermission(rules, 'POST', '/unknown', {}), undefined)
})

test('同一保存接口按是否带 ID 区分新增和修改', () => {
  assert.deepEqual(requestPermission(rules, 'POST', '/pytest/repository', {}), ['pytest.repository:add'])
  assert.deepEqual(requestPermission(rules, 'POST', '/pytest/repository', { id: 7 }), ['pytest.repository:change'])
})

test('仅查看权限不能自动扩展为旧版操作、修改或删除', () => {
  assert.equal(hasPermissionKeys(['api.case:read'], false, requestPermission(rules, 'POST', '/api/case/run', {})), true)
  assert.equal(hasPermissionKeys(['api.case:read'], false, 'api.case:change'), false)
  assert.equal(hasPermissionKeys(['api.case:read'], false, 'api.case:remove'), false)
  assert.equal(hasPermissionKeys(['api.case:edit'], false, 'api.case:change'), false)
  assert.equal(hasPermissionKeys(['api.case:create'], false, 'api.case:add'), false)
})

test('子窗口按钮未声明权限时，公共请求层仍拒绝越权，权限刷新后立即生效', async () => {
  const source = read('api/http.ts')
  const start = source.indexOf('export function http<')
  const end = source.indexOf('// 请求方式被固定成', start)
  const js = transpile(source.slice(start, end))
  let granted = ['api.case:read']
  const calls = []
  const messages = []
  const store = { httpPermissions: rules, hasPermission: (required) => hasPermissionKeys(granted, false, required) }
  const request = {
    post: async (...args) => { calls.push(args); return { status: 200, data: { code: 200, data: true } } },
  }
  class ApiBusinessError extends Error {}
  const exports = {}
  new Function('exports', 'requestPermission', 'usePermissionStore', 'Message', 'ApiBusinessError',
    'containsLosslessJsonNumber', 'request', js)(exports, requestPermission, () => store,
    { error: (message) => messages.push(message) }, ApiBusinessError, () => false, request)
  const clickFromAnyDrawer = () => exports.http({ method: 'POST', url: '/api/case/save', data: {} })
  await assert.rejects(clickFromAnyDrawer(), /没有此操作权限/)
  assert.equal(calls.length, 0)
  assert.equal(messages.length, 1)
  granted = ['api.case:change']
  await clickFromAnyDrawer()
  assert.equal(calls.length, 1)
  granted = ['api.case:read']
  await assert.rejects(clickFromAnyDrawer(), /没有此操作权限/)
  assert.equal(calls.length, 1)
})
