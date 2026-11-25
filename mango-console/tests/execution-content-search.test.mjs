import assert from 'node:assert/strict'
import test from 'node:test'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import dayjs from 'dayjs'
import * as vue from 'vue'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'

const fixture = (values = {}) => ({ task_id: 'a'.repeat(32), status: 'running',
  query: { project_product_id: 2, test_env: 0, day: dayjs().format('YYYY-MM-DD'), keyword: 'AUTO' },
  scanned: 10, skipped: 0, read_bytes: 100, message: '', count: 0, page: 1, items: [], ...values })

test('both execution pages place content search beside the shared search actions', () => {
  for (const page of ['execution-result', 'sql-execution']) {
    const source = readFileSync(`src/views/system/${page}/index.vue`, 'utf8')
    assert.match(source, /<template #header-extra>\s*<a-button[^>]*@click="contentSearch\?\.open\(\)"[^>]*>执行内容检索<\/a-button>\s*<\/template>/)
    assert.equal(source.match(/>执行内容检索<\/a-button>/g)?.length, 1)
  }
})

test('shared search page displays only per-file limit and incomplete-search warning', () => {
  const source = readFileSync('src/components/reports/ExecutionContentSearchDrawer.vue', 'utf8')
  assert.match(source, /单份文件解压后不超过 20MiB/)
  assert.match(source, /不限制累计大小、记录数、命中数和检索时长/)
  assert.match(source, /文件超限、缺失或内容截断会标记“检索不完整”/)
  assert.match(source, /未命中不代表不是平台创建/)
})

function setup(api = {}) {
  const user = vue.reactive({ userId: 7, roleId: 10, token: 'fixture' })
  const poll = { start() {}, stop() {} }, warnings = []
  const h = harness('ExecutionContentSearchDrawer', 'draft,visible,task,starting,reading,cancelling,page,open,start,cancel,refresh,disabledDate,close', {
    base: path.resolve('src/utils'),
    filename: path.resolve('src/components/reports/ExecutionContentSearchDrawer.vue'),
    props: { kind: 'automation', onOpen: async () => {} },
    api: { startContentSearch: async () => ({ data: fixture() }), getContentSearch: async () => ({ data: fixture() }), cancelContentSearch: async () => ({ data: fixture() }), ...api },
    modules: {
      dayjs: { default: dayjs },
      '@/store/modules/user': { default: () => user },
      '@/store/modules/permission': { default: () => ({ permissionKeys: [] }) },
      '@/store/modules/get-enum': { useEnum: () => ({ environment_type: [], getEnum: async () => {} }) },
      '@/hooks/use-page-polling': { usePagePolling: () => poll },
      '@arco-design/web-vue': { Message: { warning: message => warnings.push(message), error() {} } },
    },
  })
  return { ...h, user, warnings, valid() { Object.assign(h.draft, { product: [1, 2], environment: 0, keyword: 'AUTO' }) } }
}

test('requires one recent date and keyword, and preserves environment zero when selected', async t => {
  const h = setup(); t.after(h.close); await h.open()
  await h.start(); assert.equal(h.warnings.length, 1)
  h.valid(); await flush(); await h.start(); assert.equal(h.task.value.task_id, 'a'.repeat(32))
  assert.equal(h.disabledDate(dayjs().subtract(29, 'day').toDate()), false)
  assert.equal(h.disabledDate(dayjs().subtract(30, 'day').toDate()), true)
  assert.equal(h.disabledDate(dayjs().add(1, 'day').toDate()), true)
})

test('product and environment are optional, date wording describes only the selected day, and refresh button is absent', async t => {
  const calls = []
  const h = setup({ startContentSearch: async (kind, payload) => {
    calls.push(payload)
    return { data: fixture({ query: { ...fixture().query, project_product_id: null, test_env: null } }) }
  } }); t.after(h.close)
  await h.open(); h.draft.keyword = 'AUTO'; await flush(); await h.start()
  assert.equal(calls[0].project_product_id, undefined)
  assert.equal(calls[0].test_env, undefined)
  assert.ok(h.task.value)
  const source = readFileSync('src/components/reports/ExecutionContentSearchDrawer.vue', 'utf8')
  assert.match(source, /label="搜索日期"/)
  assert.match(source, /仅检索所选日期当天的数据/)
  assert.doesNotMatch(source, /label="(?:项目产品|被测环境)" required/)
  assert.doesNotMatch(source, /刷新结果|最近 30 天 · 每次仅检索一个自然日/)
})

test('late start after close cancels the orphaned job but cannot repaint results', async t => {
  const pending = deferred(), cancelled = []
  const h = setup({ startContentSearch: () => pending.promise, cancelContentSearch: async (kind, id) => cancelled.push([kind, id]) })
  t.after(h.close); await h.open(); h.valid(); await flush()
  const start = h.start(); h.exposed.close(); pending.resolve({ data: fixture() }); await start
  assert.equal(h.task.value, null); assert.equal(h.visible.value, false); assert.equal(cancelled.length, 1)
})

test('role switch clears results and ignores the old in-flight response', async t => {
  const pending = deferred()
  const h = setup({ getContentSearch: () => pending.promise }); t.after(h.close)
  await h.open(); h.valid(); await flush(); await h.start()
  const read = h.refresh(false); h.user.roleId = 20
  pending.resolve({ data: fixture({ count: 1, status: 'completed' }) }); await read
  assert.equal(h.visible.value, false); assert.equal(h.task.value, null)
})

test('drawer X and mask v-model close also cancel the current job', async t => {
  const cancelled = []
  const h = setup({ cancelContentSearch: async (kind, id) => cancelled.push([kind, id]) }); t.after(h.close)
  await h.open(); h.valid(); await flush(); await h.start()
  h.visible.value = false; await flush()
  assert.equal(cancelled.length, 1); assert.equal(h.task.value, null)
})

test('matching highlight is literal and text-only, and malformed result contracts are rejected', t => {
  const h = setup(); t.after(h.close)
  const helpers = h.load('execution-content-search.ts')
  assert.equal(helpers.highlightSearchText('<script>AUTO[1]</script>', 'auto[1]').filter(part => part.matched)[0].text, 'AUTO[1]')
  assert.throws(() => helpers.parseContentSearch({ ...fixture(), items: [{}] }))
})
