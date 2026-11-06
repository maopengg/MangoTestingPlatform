import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'
import ts from 'typescript'

const read = (path) => fs.readFileSync(new URL(`../src/${path}`, import.meta.url), 'utf8')

function harness(response = { status: 200, data: { code: 200, data: true } }) {
  const source = read('api/http.ts')
  const start = source.indexOf('export function http<')
  const end = source.indexOf('// 请求方式被固定成', start)
  const js = ts.transpileModule(source.slice(start, end), {
    compilerOptions: { module: ts.ModuleKind.CommonJS },
  }).outputText
  const calls = [], messages = [], expired = []
  const request = Object.fromEntries(['get', 'post', 'put', 'delete'].map((method) => [method,
    async (...args) => { calls.push({ method, args }); return response }]))
  class ApiBusinessError extends Error {
    constructor(message, code) { super(message); this.code = code }
  }
  const exports = {}
  new Function('exports', 'Message', 'ApiBusinessError', 'containsLosslessJsonNumber',
    'request', 'isAuthExpiredResponse', 'handleAuthExpired', js)(exports,
    { error: (message) => messages.push(message) }, ApiBusinessError, () => false,
    request, (status) => status === 401, (message) => expired.push(message))
  return { http: exports.http, calls, messages, expired }
}

test('所有 CRUD 请求均发送，由后端判断权限，不读取前端角色或过期权限缓存', async () => {
  const source = read('api/http.ts')
  assert.doesNotMatch(source, /usePermissionStore|requestPermission|hasPermission|httpPermissions/)
  assert.doesNotMatch(read('store/modules/permission.ts'), /httpPermissions/)
  const { http, calls, messages } = harness()
  let beforeCount = 0
  for (const method of ['GET', 'POST', 'PUT', 'DELETE']) {
    const result = await http({ method, url: '/example/resource', data: { id: 7 },
      beforeRequest: () => { beforeCount++ } })
    assert.equal(result.code, 200)
  }
  assert.deepEqual(calls.map((call) => call.method), ['get', 'post', 'put', 'delete'])
  assert.equal(beforeCount, 4)
  assert.deepEqual(messages, [])
})

test('请求发送后统一展示后端权限错误，并以业务异常拒绝后续成功处理', async () => {
  for (const status of [200, 403]) {
    const { http, calls, messages } = harness({ status, data: { code: 403, msg: '无权修改此资源' } })
    await assert.rejects(http({ method: 'PUT', url: '/example/resource', data: { id: 7 } }),
      (error) => error.code === 403 && error.message === '无权修改此资源')
    assert.equal(calls.length, 1)
    assert.deepEqual(messages, ['无权修改此资源'])
  }
})

test('静默请求仍发送且拒绝权限错误，但不重复弹提示', async () => {
  const { http, calls, messages } = harness({ status: 403, data: { code: 403, msg: '无权访问' } })
  await assert.rejects(http({ url: '/example/resource', silentError: true }), /无权访问/)
  assert.equal(calls.length, 1)
  assert.deepEqual(messages, [])
})

test('移除角色预检查不改变登录失效处理', async () => {
  const { http, calls, messages, expired } = harness({ status: 401, data: { code: 401, msg: '登录已失效' } })
  await assert.rejects(http({ url: '/example/resource' }), /登录已失效/)
  assert.equal(calls.length, 1)
  assert.deepEqual(expired, ['登录已失效'])
  assert.deepEqual(messages, [])
})
