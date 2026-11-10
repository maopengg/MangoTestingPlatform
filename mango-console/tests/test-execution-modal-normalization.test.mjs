import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate, compileStyleAsync } from '@vue/compiler-sfc'
import { harness } from './helpers/case-details-harness.mjs'

function setup(props = {}) {
  const calls = [], deactivated = []
  const h = harness('TestExecutionModal', 'form,submitting,modalRef,show,close,onConfirm,onCancel,setConfirmLoading,environmentName', {
    base: path.resolve('src/components/overlays'), filename: path.resolve('src/components/overlays/TestExecutionModal.vue'),
    props: { platformLimit: 4, ...props }, modules: {
      vue: { ...vue, onDeactivated: fn => deactivated.push(fn) },
      '@/store/modules/get-enum': { useEnum: () => ({ environment_type: [{ key: 0, title: 'Zero' }, { key: '2', title: 'Two' }], colors: {} }) },
    },
  })
  h.modalRef.value = { show: () => { calls.push('show'); return Promise.resolve(true) }, close: () => { calls.push('close'); return Promise.resolve(false) }, setConfirmLoading: value => calls.push(['loading', value]) }
  return { ...h, calls, deactivated }
}
const initial = { executionName: 'Example', testEnv: 0, apiConcurrencyLimit: null }
test('执行草稿独立复制、取消/关闭/再次打开恢复默认，0环境正确回显', async t => {
  const h = setup({ environmentMultiple: true }); t.after(h.close)
  const value = { ...initial, testEnvs: [0, 2], executionVersion: 'published' }
  await h.show(value); h.form.testEnvs.push(3); assert.deepEqual(value.testEnvs, [0, 2])
  h.onCancel(); assert.equal(h.events.at(-1)[0], 'cancel'); assert.deepEqual(h.form.testEnvs, []); assert.equal(h.form.testEnv, null)
  await h.show(initial); assert.equal(h.form.testEnv, 0); assert.equal(h.form.executionVersion, 'editing'); assert.equal(h.environmentName(0), 'Zero')
})
test('空环境不能因Number(null)=0通过校验；仅合法环境/并发/版本可以确认', async t => {
  const h = setup({ versionSelectable: true }); t.after(h.close)
  for (const environment of [null, '', false, NaN, -1, 1.5, 99]) {
    await h.show(initial); h.form.testEnv = environment; h.onConfirm(); assert.equal(h.events.length, 0); assert.equal(h.submitting.value, false)
  }
  for (const concurrency of [0, -1, 5, 1.5, NaN]) {
    await h.show({ ...initial, apiConcurrencyLimit: concurrency }); h.onConfirm(); assert.equal(h.events.length, 0)
  }
  await h.show(initial); h.form.executionVersion = 'unknown'; h.onConfirm(); assert.equal(h.events.length, 0)
  await h.show({ ...initial, apiConcurrencyLimit: 2 }); h.onConfirm()
  assert.deepEqual(h.events[0][1], { executionName: 'Example', testEnv: 0, testEnvs: [], apiConcurrencyLimit: 2, executionVersion: 'editing' })
})
test('确认防重复，失败解除loading后可重试；提交内容与后续草稿无别名', async t => {
  const h = setup({ environmentMultiple: true }); t.after(h.close)
  await h.show({ ...initial, testEnvs: [0, 2] }); h.onConfirm(); h.onConfirm()
  assert.equal(h.events.length, 1); assert.equal(h.submitting.value, true)
  assert.equal(await h.show({ ...initial, executionName: 'Other' }), false)
  h.form.testEnvs.push(9); assert.deepEqual(h.events[0][1].testEnvs, [0, 2])
  h.setConfirmLoading(false); h.form.testEnvs = [2]; h.onConfirm(); assert.equal(h.events.length, 2)
  h.deactivated.forEach(fn => fn()); assert.equal(h.submitting.value, false); assert.equal(h.events.at(-1)[0], 'cancel')
})
test('只读环境保留原配置协议，多选复制且生成独立提交数组', async t => {
  const h = setup({ environmentSelectable: false }); t.after(h.close)
  await h.show({ ...initial, testEnvs: [] }); h.onConfirm(); assert.equal(h.events.length, 0)
  await h.show({ ...initial, testEnvs: [0, 2] }); h.onConfirm()
  assert.equal(h.events[0][1].testEnv, null); assert.deepEqual(h.events[0][1].testEnvs, [0, 2])
})
test('非法平台容量不进入提交，恢复有效容量后可正常确认', async t => {
  const h = setup({ platformLimit: NaN }); t.after(h.close)
  await h.show(initial); h.onConfirm(); assert.equal(h.events.length, 0); assert.equal(h.submitting.value, false)
  h.props.platformLimit = 4; h.onConfirm(); assert.equal(h.events[0][0], 'confirm')
})
test('ModalDialog实际模板取消事件向父级报告，确认/连续提交互斥并可失败恢复', () => {
  const file = 'src/components/overlays/ModalDialog.vue', descriptor = parse(readFileSync(file, 'utf8')).descriptor
  const transpile = source => ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText
  const exports = {}, events = []
  new Function('exports', 'require', transpile(descriptor.script.content))(exports, () => vue)
  const state = exports.default.setup({}, { emit: (...event) => events.push(event) })
  state.show(); state.onConfirm(); state.onConfirm(); state.onContinuousSubmit(); assert.deepEqual(events, [['confirm']])
  state.setConfirmLoading(false); state.onContinuousSubmit(); assert.deepEqual(events.at(-1), ['continuousSubmit'])
  const compiled = compileTemplate({ id: 'modal', filename: file, source: descriptor.template.content })
  const template = {}
  new Function('exports', 'require', transpile(compiled.code))(template, () => ({ ...vue, resolveComponent: name => name, renderSlot: () => [] }))
  const node = template.render(vue.proxyRefs(state), [])
  node.props.onCancel()
  assert.deepEqual(events.at(-1), ['cancel']); assert.equal(state.showModal.value, false); assert.equal(state.confirmLoading.value, false); assert.equal(state.continuousLoading.value, false)
})
test('共享执行弹窗及三个真实调用页面脚本、模板与样式编译', async () => {
  for (const filename of ['src/components/overlays/TestExecutionModal.vue', 'src/components/overlays/ModalDialog.vue', 'src/views/report/index.vue', 'src/views/timing/tasks/index.vue', 'src/views/apitest/case/index.vue']) {
    const { descriptor, errors } = parse(readFileSync(filename, 'utf8'), { filename }); assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: filename })
    assert.deepEqual(compileTemplate({ id: filename, source: descriptor.template.content, filename, compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
    for (const style of descriptor.styles) assert.deepEqual((await compileStyleAsync({ id: filename, source: style.content, filename, scoped: style.scoped, preprocessLang: style.lang })).errors, [])
  }
})
