import test from 'node:test'
import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import { unzipSync, strFromU8 } from 'fflate'
import { parse, compileScript, compileTemplate, compileStyle } from '@vue/compiler-sfc'
import ts from 'typescript'
import { deferred, flush } from './helpers/case-details-harness.mjs'
import { resourcePanel } from './helpers/home-resource-harness.mjs'

const keyResponse = key => ({ code: 200, data: { api_key: key } })

test('MCP 首次读取局部 loading、失败重试与短凭据遮罩；缓存首次激活不重复读取', async () => {
  let fail = true
  const p = resourcePanel('McpWorkbench', { read: async () => fail ? { code: 500 } : keyResponse('example-key') })
  p.mount(); p.activate(); assert.equal(p.apiKeyLoading.value, true); await flush()
  assert.equal(p.reads.length, 1); assert.equal(p.apiKeyFailed.value, true); assert.equal(p.apiKeyLoading.value, false)
  fail = false; await p.loadCurrentUserApiKey(); assert.equal(p.apiKey.value, 'example-key'); assert.equal(p.apiKeyFailed.value, false)
  assert.equal(p.maskedApiKey.value, '••••••••'); p.dispose()
})

for (const field of ['userId', 'roleId', 'token', 'selected_environment']) {
  test(`MCP ${field} 同步往返清理凭据/配置窗口，旧读取与 finally 不覆盖当前状态`, async () => {
    const requests = [], p = resourcePanel('McpWorkbench', { read: () => { const r = deferred(); requests.push(r); return r.promise } })
    p.mount(); p.openConfig(); const previous = p.user[field]; p.user[field] = field === 'token' ? 'changed' : 9; p.user[field] = previous
    assert.equal(requests.length, 3); assert.equal(p.configVisible.value, false); assert.equal(p.apiKey.value, '')
    requests[0].resolve(keyResponse('example-old')); requests[1].reject(Error('old')); await flush(); assert.equal(p.apiKeyLoading.value, true)
    requests[2].resolve(keyResponse('example-current')); await flush(); assert.equal(p.apiKey.value, 'example-current'); assert.equal(p.apiKeyFailed.value, false); p.dispose()
  })
}

test('MCP 重置固定确认窗口，失败不关闭且可重试，成功回执直接替换凭据而不额外重读', async () => {
  let fail = true
  const p = resourcePanel('McpWorkbench', { write: async () => fail ? { code: 500 } : keyResponse('example-new') })
  p.mount(); await flush(); p.resetApiKey(); const first = p.dialogs[0]; first.config.onClose()
  p.resetApiKey(); const second = p.dialogs[1]; first.config.onClose()
  assert.equal(await first.config.onBeforeOk(), false); assert.equal(p.writes.length, 0)
  assert.equal(await second.config.onBeforeOk(), false); assert.equal(p.resetting.value, false); assert.equal(p.messages.at(-1).kind, 'error')
  fail = false; assert.equal(await second.config.onBeforeOk(), true); assert.equal(p.apiKey.value, 'example-new'); assert.equal(p.reads.length, 1); p.dispose()
})

test('MCP 重置物理锁保持到请求完成；身份变化关闭旧确认，迟到成功不能写入新身份', async () => {
  const request = deferred(), p = resourcePanel('McpWorkbench', { write: () => request.promise })
  p.mount(); await flush(); p.resetApiKey(); const dialog = p.dialogs[0], work = dialog.config.onBeforeOk()
  assert.equal(dialog.config.onBeforeCancel(), false); assert.equal(await dialog.config.onBeforeOk(), false)
  p.user.roleId = 9; assert.equal(dialog.closed, true); assert.equal(p.resetting.value, true); p.resetApiKey(); assert.equal(p.dialogs.length, 1)
  request.resolve(keyResponse('example-obsolete')); assert.equal(await work, false); await flush()
  assert.equal(p.resetting.value, false); assert.notEqual(p.apiKey.value, 'example-obsolete'); assert.equal(p.messages.length, 0); assert.equal(p.reads.length, 2); p.dispose()
})

test('MCP 复制防重复，剪贴板失败正确回退；双重失败不假报成功且移除临时节点', async () => {
  const request = deferred(), p = resourcePanel('McpWorkbench', { copy: () => request.promise, fallback: () => false })
  p.mount(); await flush(); const work = p.copyAuthHeader(); await p.copyInstallPrompt(); assert.equal(p.copied.length, 1)
  request.reject(Error('clipboard rejected')); await work
  assert.equal(p.messages.at(-1).kind, 'error'); assert.equal(p.copyingLabel.value, null); assert.equal(p.elements.size, 0); p.dispose()
  const q = resourcePanel('McpWorkbench', { copy: async () => { throw Error('clipboard rejected') } })
  q.mount(); await flush(); await q.copyInstallPrompt(); assert.equal(q.messages.at(-1).kind, 'success'); assert.equal(q.elements.size, 0); q.dispose()
})

test('MCP 身份改变后不把迟到复制失败回退成旧凭据写入，停用/卸载后也无迟到读取', async () => {
  const request = deferred(); let fallbacks = 0
  const p = resourcePanel('McpWorkbench', { copy: () => request.promise, fallback: () => { fallbacks++; return true } })
  p.mount(); await flush(); const work = p.copyAuthHeader(); p.user.roleId = 9; request.reject(Error('old')); await work
  assert.equal(fallbacks, 0); assert.equal(p.messages.length, 0); p.dispose()
  const reads = [], q = resourcePanel('McpWorkbench', { read: () => { const r = deferred(); reads.push(r); return r.promise } })
  q.mount(); q.deactivate(); reads[0].resolve(keyResponse('example-late')); await flush(); assert.equal(q.apiKey.value, '')
  q.activate(); assert.equal(reads.length, 2); q.dispose(); reads[1].resolve(keyResponse('example-unmounted')); await flush(); assert.equal(q.apiKey.value, '')
})

test('Skill 初始可见时加载，关闭/重开重置检索与选中；旧 nextTick 不结束新窗口加载', async () => {
  const p = resourcePanel('SkillCenterDrawer', { props: { visible: true } }); assert.equal(p.loading.value, true); await flush()
  assert.equal(p.skills.value.length, 1); assert.equal(p.detail.value.key, 'example'); assert.equal(p.detailLoading.value, false)
  p.keyword.value = 'EXAMPLE'; assert.equal(p.filteredSkills.value.length, 1)
  p.props.visible = false; assert.equal(p.selectedKey.value, null); assert.equal(p.keyword.value, '')
  p.props.visible = true; p.props.visible = false; p.props.visible = true; await flush()
  assert.equal(p.detail.value.key, 'example'); assert.equal(p.loading.value, false); assert.equal(p.detailLoading.value, false); p.dispose()
})

test('Skill 清单错误有重试，修复源内容后可恢复，不与合法空目录混淆', async () => {
  const assets = { documents: { '../../../../../skill/example/SKILL.md': null }, introductions: {}, urls: {} }
  const p = resourcePanel('SkillCenterDrawer', { props: { visible: true }, assets }); await flush()
  assert.equal(p.loadFailed.value, true); assert.equal(p.loading.value, false)
  assets.documents['../../../../../skill/example/SKILL.md'] = '## Example\nExample content'
  await p.loadSkills(); await flush(); assert.equal(p.loadFailed.value, false); assert.equal(p.skills.value.length, 1); p.dispose()
  const q = resourcePanel('SkillCenterDrawer', { props: { visible: true }, assets: { documents: {}, introductions: {}, urls: {} } }); await flush()
  assert.equal(q.loadFailed.value, false); assert.equal(q.detail.value, null); assert.equal(q.detailLoading.value, false); q.dispose()
})

test('Skill 真实 ZIP 保留目录和文件，下载只触发一次且清理临时链接与对象 URL', async () => {
  const p = resourcePanel('SkillCenterDrawer', { props: { visible: true } }); await flush()
  await p.downloadSkill(p.detail.value); assert.equal(p.fetched.length, 2); assert.equal(p.clicks.length, 1); assert.equal(p.elements.size, 0)
  const files = unzipSync(new Uint8Array(await p.archives[0].arrayBuffer()))
  assert.deepEqual(Object.keys(files).sort(), ['SKILL.md', 'references/example.txt']); assert.equal(strFromU8(files['SKILL.md']), 'Example asset')
  p.releaseUrls(); assert.equal(p.revoked.length, 1); assert.equal(p.timers.size, 0); assert.equal(p.downloadingKey.value, null); p.dispose()
})

test('Skill 单文件失败等待其他网络请求结束后才释放锁，可恢复重试', async () => {
  const pending = [], p = resourcePanel('SkillCenterDrawer', { props: { visible: true }, fetch: () => { const r = deferred(); pending.push(r); return r.promise } })
  await flush(); const work = p.downloadSkill(p.detail.value); await p.downloadSkill(p.detail.value); assert.equal(p.fetched.length, 2)
  pending[0].reject(Error('one file failed')); await flush(); assert.equal(p.downloadingKey.value, 'example'); assert.equal(p.messages.length, 0)
  pending[1].resolve({ ok: true, arrayBuffer: async () => new ArrayBuffer(0) }); await work
  assert.equal(p.downloadingKey.value, null); assert.equal(p.messages.at(-1).kind, 'error'); assert.equal(p.clicks.length, 0); p.dispose()
})

test('Skill 关闭窗口取消旧下载并保留物理锁；重开后旧结果不触发打包、链接或提示', async () => {
  const pending = [], p = resourcePanel('SkillCenterDrawer', { props: { visible: true }, fetch: () => { const r = deferred(); pending.push(r); return r.promise } })
  await flush(); const work = p.downloadSkill(p.detail.value); p.close(); p.props.visible = false
  assert.ok(p.fetched.every(call => call.config.signal.aborted)); assert.equal(p.downloadingKey.value, 'example')
  p.props.visible = true; await flush(); await p.downloadSkill(p.detail.value); assert.equal(p.fetched.length, 2)
  pending.forEach(r => r.resolve({ ok: true, arrayBuffer: async () => new ArrayBuffer(0) })); await work
  assert.equal(p.downloadingKey.value, null); assert.equal(p.archives.length, 0); assert.equal(p.clicks.length, 0); assert.equal(p.messages.length, 0); p.dispose()
})

for (const field of ['userId', 'roleId', 'token', 'selected_environment']) {
  test(`Skill ${field} 切换失效窗口，不让原窗口下载在新上下文落地`, async () => {
    const pending = [], p = resourcePanel('SkillCenterDrawer', { props: { visible: true }, fetch: () => { const r = deferred(); pending.push(r); return r.promise } })
    await flush(); const work = p.downloadSkill(p.detail.value); p.user[field] = field === 'token' ? 'changed' : 9
    assert.equal(p.detail.value, null); assert.ok(p.events.some(event => event[0] === 'update:visible' && event[1] === false))
    pending.forEach(r => r.resolve({ ok: true, arrayBuffer: async () => new ArrayBuffer(0) })); await work
    assert.equal(p.clicks.length, 0); assert.equal(p.messages.length, 0); p.dispose()
  })
}

test('Skill 元数据仅接受已知字段，Markdown 保持转义；缓存停用关闭窗口并清理资源', async () => {
  const p = resourcePanel('SkillCenterDrawer', { props: { visible: true } }); await flush(); const helpers = p.helpers()
  assert.deepEqual(helpers.parseIntroductions({ file: '{"example":{"title":3,"description":"Example","category":"Guide","extra":"ignore"}}' }), { example: { title: undefined, description: 'Example', category: 'Guide' } })
  assert.deepEqual(helpers.parseIntroductions({ file: '[]' }), {})
  const html = helpers.renderMarkdown('## Example\n<script>example()</script>\n```\n<img src=x>\n```')
  assert.ok(html.includes('&lt;script&gt;')); assert.equal(html.includes('<script>'), false); assert.ok(html.includes('&lt;img src=x&gt;'))
  p.deactivate(); assert.equal(p.detail.value, null); assert.equal(p.loading.value, false); assert.equal(p.timers.size, 0); p.dispose()
})

test('资源入口仅发出四个既有业务事件；联系作者的取消、确认及缓存停用关闭窗口', () => {
  const p = resourcePanel('ResourceCenter')
  p.handleDownloadExecutor(); p.handleViewSkill(); p.handleViewHelp(); p.handleContactAuthor()
  assert.deepEqual(p.events, [['download-executor'], ['view-skill'], ['view-help'], ['contact-author']]); p.dispose()
  const q = resourcePanel('ContactAuthor', { props: { visible: true } })
  q.handleCancel(); assert.equal(q.props.visible, false); q.props.visible = true
  q.handleOk(); assert.equal(q.props.visible, false); q.props.visible = true; q.deactivate()
  assert.equal(q.props.visible, false); assert.ok(q.events.every(event => event[0] === 'update:visible' && event[1] === false)); q.dispose()
})

test('悬停详情在停用/卸载时关闭，拒绝旧显示事件，恢复后可重新打开', () => {
  const p = resourcePanel('HoverTaskDetail'); p.setPopupVisible(true); assert.equal(p.popupVisible.value, true)
  p.deactivate(); p.setPopupVisible(true); assert.equal(p.popupVisible.value, false); assert.equal(p.active.value, false)
  p.activate(); p.setPopupVisible(true); assert.equal(p.popupVisible.value, true)
  p.dispose(); p.setPopupVisible(true); assert.equal(p.popupVisible.value, false)
})

function vnodeText(node) {
  if (node == null) return ''
  if (typeof node !== 'object') return String(node)
  const children = node.children
  return Array.isArray(children) ? children.map(vnodeText).join(' ') : typeof children === 'string' ? children : ''
}
test('未挂载标题候选只维护每秒本地时钟，跨日更新日期，后台/缓存暂停且清理资源', async () => {
  const p = resourcePanel('CenterTitle'); p.mount(); p.activate(); await flush()
  assert.equal(p.reads.length, 1); assert.equal(p.timers.size, 1); assert.equal([...p.timers.values()][0].delay, 1000)
  p.setNow(['2026-11-08', '00:00:01']); p.tickClock(); assert.ok(vnodeText(p.render()).includes('2026-11-08'))
  assert.ok(vnodeText(p.render()).includes('00:00:01')); p.visibility('hidden'); assert.equal(p.timers.size, 0)
  p.visibility('visible'); assert.equal(p.timers.size, 1); p.deactivate(); assert.equal(p.timers.size, 0)
  p.activate(); await flush(); assert.equal(p.reads.length, 2); assert.equal(p.timers.size, 1)
  p.dispose(); assert.equal(p.timers.size, 0); assert.ok([...p.listeners.values()].every(set => set.size === 0))
})
test('旧标题候选在线数读取失败可重试，身份改变后不回填旧值', async () => {
  let fail = true
  const p = resourcePanel('CenterTitle', { read: async () => fail ? { code: 500 } : { code: 200, data: { sum: 0 } } })
  p.mount(); await flush(); const render = p.render(), right = render.children[2], retry = right.children[0]
  assert.ok(vnodeText(render).includes('加载失败'))
  fail = false; await retry.props.onClick(); await flush(); assert.ok(vnodeText(p.render()).includes('0')); p.dispose()
  const requests = [], q = resourcePanel('CenterTitle', { read: () => { const r = deferred(); requests.push(r); return r.promise } })
  q.mount(); q.user.roleId = 9; requests[0].resolve({ code: 200, data: { sum: 99 } }); await flush()
  assert.equal(vnodeText(q.render()).includes('99'), false); requests[1].resolve({ code: 200, data: { sum: 0 } }); await flush(); q.dispose()
})

test('首页菜单图标只读取导航元数据，尾斜线归一化，目录变更后使用当前图标或原 fallback', () => {
  const store = { getPermissionSideBar: [{ path: '/apitest/', meta: { icon: 'ExampleIcon' } }] }
  const filename = path.resolve('src/views/index/composables/use-home-menu-icon.ts'), exports = {}
  const code = ts.transpileModule(readFileSync(filename, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText
  new Function('exports', 'require', code)(exports, () => ({ default: () => store }))
  const icons = exports.useHomeMenuIcon(), fallback = { name: 'Fallback' }
  assert.equal(icons.resolveMenuIcon('/apitest', fallback), 'ExampleIcon')
  store.getPermissionSideBar = []; assert.equal(icons.resolveMenuIcon('/apitest/', fallback), fallback)
})

test('资源窗口 SFC 脚本、模板和 LESS 编译', () => {
  for (const name of ['McpWorkbench', 'SkillCenterDrawer', 'ResourceCenter', 'ContactAuthor', 'HoverTaskDetail', 'Title', 'CenterTitle']) {
    const filename = path.resolve(`src/views/index/components/${name}.vue`), { descriptor, errors } = parse(readFileSync(filename, 'utf8'), { filename }); assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: filename })
    if (descriptor.template) assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename, id: filename, compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
    if (descriptor.script?.lang === 'tsx') assert.deepEqual(ts.transpileModule(descriptor.script.content, { fileName: 'component.tsx', compilerOptions: { jsx: ts.JsxEmit.Preserve }, reportDiagnostics: true }).diagnostics, [])
    for (const style of descriptor.styles) assert.deepEqual(compileStyle({ source: style.content, filename, id: filename, scoped: style.scoped, preprocessLang: style.lang }).errors, [])
  }
  const titleTsx = readFileSync(path.resolve('src/views/index/components/Title.tsx'), 'utf8')
  assert.deepEqual(ts.transpileModule(titleTsx, { fileName: 'title.tsx', compilerOptions: { jsx: ts.JsxEmit.Preserve }, reportDiagnostics: true }).diagnostics, [])
})
