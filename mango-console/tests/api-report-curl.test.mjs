import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import ts from 'typescript'
import { ref } from 'vue'
import { parse } from '@vue/compiler-sfc'
import { deferred, harness } from './helpers/case-details-harness.mjs'

function curlHook(writeText, options = {}) {
  const messages = [], exports = {}
  const source = readFileSync('src/hooks/useScenarioCurl.ts', 'utf8')
  const code = ts.transpileModule(source, { compilerOptions: {
    module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022,
  } }).outputText
  new Function('exports', 'require', 'navigator', 'window', 'document', code)(exports,
    name => name === 'vue' ? { ref } : { Message: {
      success: value => messages.push(['success', value]), error: value => messages.push(['error', value]),
    } }, { clipboard: { writeText } }, { isSecureContext: options.secure !== false }, options.document)
  return { ...exports.useScenarioCurl(), messages }
}

test('报告 cURL 复用实际请求快照，包含请求头、查询参数、JSON 和 shell 转义', async () => {
  const copies = [], h = curlHook(async value => copies.push(value))
  await h.copyScenarioCurl({ result_data: {
    request: { method: 'post', url: 'https://example.com/api', headers: { ignored: 'old' } },
    response: { request_headers: { 'X-Example': "it's" }, request_params: { page: 0 },
      request_body: { enabled: false, name: '示例' } },
  } })
  assert.match(copies[0], /--request 'POST' 'https:\/\/example.com\/api\?page=0'/)
  assert.ok(copies[0].includes("--header 'X-Example: it'\\''s'"))
  assert.ok(copies[0].includes('--data-raw \'{"enabled":false,"name":"示例"}\''))
  assert.equal(copies[0].includes('ignored'), false)
  assert.deepEqual(h.messages, [['success', '复制 cURL 成功']])
  assert.equal(h.copying.value, false)
})

test('沿用 multipart 文件和普通表单字段生成方式', async () => {
  const copies = [], h = curlHook(async value => copies.push(value))
  await h.copyScenarioCurl({ result_data: { request: { method: 'POST', url: 'https://example.com/upload',
    request_files: { file: '/tmp/example.txt' }, request_body: { note: 'example' } } } })
  assert.ok(copies[0].includes("--form 'file=@/tmp/example.txt'"))
  assert.ok(copies[0].includes("--form 'note=example'"))
})

test('复制 loading 防重复，剪贴板失败释放状态，缺少请求 URL 不复制', async () => {
  const pending = deferred(), copies = [], h = curlHook(value => { copies.push(value); return pending.promise })
  const item = { result_data: { request: { method: 'GET', url: 'https://example.com/one' } } }
  const first = h.copyScenarioCurl(item)
  assert.equal(h.copying.value, true)
  await h.copyScenarioCurl(item); assert.equal(copies.length, 1)
  pending.reject(Error('clipboard rejected')); await first
  assert.equal(h.copying.value, false); assert.equal(h.messages[0][0], 'error')
  await h.copyScenarioCurl({ result_data: {} })
  assert.equal(copies.length, 1); assert.match(h.messages[1][1], /暂无实际请求 URL/)
})

test('非安全上下文使用已有 textarea 复制回退', async () => {
  let selected = false, removed = false
  const textarea = { value: '', style: {}, setAttribute() {}, select() { selected = true } }
  const h = curlHook(() => assert.fail('不应使用安全剪贴板'), { secure: false, document: {
    createElement: () => textarea, body: { appendChild() {}, removeChild() { removed = true } },
    execCommand: command => command === 'copy',
  } })
  await h.copyScenarioCurl({ result_data: { request: { method: 'GET', url: 'https://example.com' } } })
  assert.equal(selected, true); assert.equal(removed, true)
  assert.match(textarea.value, /^curl /); assert.equal(h.messages[0][0], 'success')
})

test('公共报告 tab extra 使用当前选中原始结果，不沿用上一次场景', async () => {
  const filename = path.resolve('src/components/reports/ApiTestReport.vue'), copies = [], copying = ref(false)
  const first = { request: { url: 'https://example.com/one' } }
  const h = harness('ApiTestReport', 'copyCurl,copying', { filename, props: { resultData: first }, modules: {
    '@/hooks/useScenarioCurl': { useScenarioCurl: () => ({ copying, copyScenarioCurl: item => copies.push(item) }) },
  } })
  try {
    await h.copyCurl()
    h.props.resultData = { request: { url: 'https://example.com/two' } }
    await h.copyCurl()
    assert.equal(copies[0].result_data.request.url, 'https://example.com/one')
    assert.equal(copies[1].result_data.request.url, 'https://example.com/two')
    assert.equal(h.copying, copying)
    const template = parse(readFileSync(filename, 'utf8')).descriptor.template.content
    assert.match(template, /<template #extra>[\s\S]*?:loading="copying"[\s\S]*?@click="copyCurl"[\s\S]*?复制 cURL/)
  } finally { h.close() }
})

test('协议失败保留跳过原因，关联 ID 只读取明确白名单且不泄露凭据', () => {
  const filename = path.resolve('src/components/reports/ApiTestReport.vue')
  const h = harness('ApiTestReport', 'resultData,correlationIds', { filename, props: { resultData: {
    status: 0, failure_category: 'protocol_call_failed', protocol_status: 'HTTP 500',
    posterior_skipped_reason: '已跳过响应后置处理和业务断言。',
    assertion_skipped_reason: '已跳过响应后置处理和业务断言。',
    response: { code: 500, json: null, headers: { 'X-Request-ID': 'request-example',
      'xlog': 'log-example', Authorization: 'example-secret', 'Set-Cookie': 'example-session',
      'x-trace-id': { secret: 'not-an-id' }, 'x-log-id': 'invalid\nvalue' } },
  } } })
  assert.deepEqual(h.correlationIds.value, [
    { name: 'x-request-id', value: 'request-example' }, { name: 'xlog', value: 'log-example' },
  ])
  assert.equal(h.resultData.value.failure_category, 'protocol_call_failed')
  assert.equal(h.resultData.value.protocol_status, 'HTTP 500')
  assert.equal(h.resultData.value.posterior_skipped_reason, '已跳过响应后置处理和业务断言。')
  h.close()
})
