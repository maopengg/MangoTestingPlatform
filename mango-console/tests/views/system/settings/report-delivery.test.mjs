import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
const root = new URL('../../../../', import.meta.url)
const read = (path) => fs.readFileSync(new URL(path, root), 'utf8')

test('report delivery editor and export dialog compile as real Vue components', () => {
  for (const path of ['src/views/system/settings/components/ReportDeliveryEditor.vue', 'src/components/reports/OfflineReportExportDialog.vue']) {
    const source = read(path)
    const { descriptor, errors } = parse(source, { filename: path })
    assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: path })
    const template = compileTemplate({ id: path, source: descriptor.template.content, filename: path, compilerOptions: { bindingMetadata: script.bindings } })
    assert.deepEqual(template.errors, [])
  }
})

test('configuration has one shared notification policy and always inherits platform storage', () => {
  const source = read('src/views/system/settings/components/ReportDeliveryEditor.vue')
  assert.match(source, /system.settings:edit/)
  assert.match(source, /system.settings:debug/)
  const fields = read('src/views/system/settings/config.ts')
  assert.match(fields, /复用平台文件存储/)
  assert.doesNotMatch(source, /draft\.(auto_generate|link_mode|failure_policy|storage|max_size_mb|endpoint|bucket)|botOptions|v-for="channel/)
  assert.match(source, /Object.entries\(defaults.value\)/)
  assert.match(fields, /请求响应内容.*仅失败 Case/)
  assert.doesNotMatch(source, /payload_scope|public_custom_domain|public_base_url|客户端访问地址/)
  assert.match(source, /@change="save"/)
  assert.match(source, /@blur="save"/)
  assert.match(source, /下载 HTML/)
  assert.doesNotMatch(source, /保存报告配置|测试已保存|mango-report-delivery__hint|inheritedBackend|MinIO 或 TOS/)
  const settings = read('src/views/system/settings/index.vue')
  assert.doesNotMatch(settings, /mango-system-settings__row--report/)
  assert.match(settings, /:deep\(\.mango-report-delivery \.mango-system-settings__row\)/)
  assert.match(source, /metadataError/)
})

test('report export downloads immediately and cancels requests without queue polling', () => {
  const source = read('src/components/reports/OfflineReportExportDialog.vue')
  assert.match(source, /onBeforeUnmount\(cancelRequest\)/)
  assert.match(source, /request.signal.aborted/)
  assert.match(source, /生成并下载/)
  assert.doesNotMatch(source, /setTimeout|poll\(|artifact|队列/)
  const api = read('src/api/system/offline_report.ts')
  assert.match(api, /responseType: 'blob'/)
  assert.match(api, /request.post\('\/system\/test\/suite\/offline'/)
  assert.match(api, /URL.revokeObjectURL/)
  assert.doesNotMatch(api, /window.open|token=/)
  assert.match(read('src/views/report/index.vue'), /permission: 'report:export', label: '导出离线 HTML'/)
  assert.doesNotMatch(read('src/views/system/settings/components/ReportDeliveryEditor.vue'), /retention_days|文件保留（天）/)
})
