import test from 'node:test'
import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate, compileStyle } from '@vue/compiler-sfc'
import { harness, deferred, flush, method } from './helpers/case-details-harness.mjs'
const base = path.resolve('src/views/gray/config-file')
const yaml = (extra = {}) => ({
  id: 11,
  name: 'Example config',
  project_product: { id: 2 },
  effect_wait_seconds: 0,
  status: 0,
  ...extra,
})
const repo = (id = 3) => ({ id, name: `Repository ${id}`, branch: 'main', test_env: null })
const binding = (extra = {}) => ({
  id: 21,
  yaml_file: 11,
  repository: repo(),
  file_path: 'config/example.yml',
  status: 0,
  ...extra,
})
function editor(kind, api = {}, modules = {}) {
  const hooks = { stop: [], activate: [], unmount: [] }
  const defaults = {
    getGrayRepository: async () => ({ code: 200, data: [repo()] }),
    getGrayYamlRepositoryFiles: async () => ({ code: 200, data: ['config/example.yml'] }),
    postGrayYamlFile: async (p) => ({ code: 200, data: { ...p, id: 12 } }),
    putGrayYamlFile: async (p) => ({ code: 200, data: { ...p } }),
    postGrayYamlFileBinding: async (p) => ({ code: 200, data: { ...p, id: 22 } }),
    putGrayYamlFileBinding: async (p) => ({ code: 200, data: { ...p } }),
  }
  const names =
    kind === 'file'
      ? 'open,save,onVisibleChange,visible,saving,saveError,form,recordId'
      : 'open,save,onVisibleChange,onRepositoryChange,loadRepositories,loadFiles,visible,saving,saveError,form,recordId,yamlId,repositoryOptions,fileOptions,repositoriesLoading,repositoriesError,filesLoading,filesError,files'
  const f = harness(kind === 'file' ? 'YamlFileEditor' : 'YamlBindingEditor', names, {
    base,
    props: { contextKey: 'one', blocked: false },
    api: { ...defaults, ...api },
    modules: {
      vue: {
        ...vue,
        onDeactivated: (fn) => hooks.stop.push(fn),
        onActivated: (fn) => hooks.activate.push(fn),
        onBeforeUnmount: (fn) => hooks.unmount.push(fn),
      },
      ...modules,
    },
  })
  return {
    ...f,
    hooks,
    cleanup() {
      hooks.unmount.forEach((fn) => fn())
      f.close()
    },
  }
}
test('file edit isolates draft and retains zero wait/status', () => {
  const e = editor('file'),
    original = yaml()
  e.open(original)
  e.form.name = 'Edited'
  assert.equal(original.name, 'Example config')
  assert.equal(e.form.project_product, 2)
  assert.equal(e.form.effect_wait_seconds, 0)
  assert.equal(e.form.status, 0)
  e.cleanup()
})
test('file create synchronously initializes navigation product and drops old edit fields', () => {
  const e = editor('file')
  e.open(yaml())
  e.onVisibleChange(false)
  e.open(undefined, [1, '9'])
  assert.equal(e.visible.value, true)
  assert.equal(e.recordId.value, null)
  assert.equal(e.form.project_product, 9)
  assert.equal(e.form.name, '')
  assert.equal(e.form.effect_wait_seconds, 10)
  assert.equal(e.form.status, 1)
  e.cleanup()
})
test('file save uses fixed target and explicit payload whitelist with leaf product ID', async () => {
  let payload
  const e = editor('file', {
    putGrayYamlFile: async (p) => {
      payload = p
      return { code: 200, data: p }
    },
  })
  const original = yaml({ bindings: [{ id: 99 }], update_time: 'Readonly', last_update_user: 88 })
  e.open(original)
  original.id = 99
  e.form.project_product = [1, '2']
  await e.save()
  assert.deepEqual(payload, {
    id: 11,
    project_product: 2,
    name: 'Example config',
    effect_wait_seconds: 0,
    status: 0,
  })
  assert.equal(e.visible.value, false)
  assert.equal(e.saving.value, false)
  assert.deepEqual(
    e.events.filter(([event]) => event === 'saved'),
    [['saved', 11]]
  )
  e.cleanup()
})
test('file validation preserves required fields and zero while rejecting invalid waits', async () => {
  let count = 0
  const e = editor('file', {
    putGrayYamlFile: async (p) => {
      count++
      return { code: 200, data: p }
    },
  })
  e.open(yaml())
  const original = { ...e.form }
  for (const [key, value] of [
    ['name', ' '],
    ['project_product', null],
    ['effect_wait_seconds', null],
    ['effect_wait_seconds', -1],
    ['effect_wait_seconds', 0.5],
  ]) {
    Object.assign(e.form, original)
    e.form[key] = value
    await e.save()
  }
  assert.equal(count, 0)
  assert.equal(e.visible.value, true)
  Object.assign(e.form, original)
  await e.save()
  assert.equal(count, 1)
  e.cleanup()
})
for (const kind of ['file', 'binding']) {
  const open = (e) => (kind === 'file' ? e.open(yaml()) : e.open(yaml(), binding()))
  const api = kind === 'file' ? 'putGrayYamlFile' : 'putGrayYamlFileBinding'
  test(`${kind} save physical lock prevents duplicate, close and reopen while payload remains frozen`, async () => {
    const pending = deferred()
    let payload,
      count = 0
    const e = editor(kind, {
      [api]: (p) => {
        payload = p
        count++
        return pending.promise
      },
    })
    open(e)
    const saving = e.save()
    e.form.status = 1
    e.onVisibleChange(false)
    open(e)
    await e.save()
    assert.equal(count, 1)
    assert.equal(payload.status, 0)
    assert.equal(e.visible.value, true)
    pending.resolve({ code: 200, data: payload })
    assert.equal(await saving, false)
    assert.equal(e.saving.value, false)
    assert.equal(e.visible.value, false)
    e.cleanup()
  })
  test(`${kind} save failure retains draft and allows retry`, async () => {
    let fail = true
    const e = editor(kind, {
      [api]: async (p) => {
        if (fail) throw Error('Offline')
        return { code: 200, data: p }
      },
    })
    open(e)
    await e.save()
    assert.equal(e.saveError.value, true)
    assert.equal(e.visible.value, true)
    assert.equal(e.saving.value, false)
    fail = false
    await e.save()
    assert.equal(e.visible.value, false)
    e.cleanup()
  })
  for (const transition of ['context', 'roundtrip', 'stop', 'stop-activate', 'unmount']) {
    test(`${kind} ${transition} suppresses late save but keeps the physical lock until settled`, async () => {
      const pending = deferred()
      let payload
      const e = editor(kind, {
        [api]: (p) => {
          payload = p
          return pending.promise
        },
      })
      open(e)
      const saving = e.save()
      if (transition === 'context' || transition === 'roundtrip') {
        e.props.contextKey = 'two'
        if (transition === 'roundtrip') e.props.contextKey = 'one'
      } else if (transition === 'unmount') e.hooks.unmount.forEach((fn) => fn())
      else {
        e.hooks.stop.forEach((fn) => fn())
        if (transition === 'stop-activate') e.hooks.activate.forEach((fn) => fn())
      }
      open(e)
      assert.equal(e.visible.value, false)
      assert.equal(e.saving.value, true)
      pending.resolve({ code: 200, data: payload })
      await saving
      assert.equal(e.saving.value, false)
      assert.equal(
        e.events.some(([event]) => event === 'saved'),
        false
      )
      e.cleanup()
    })
  }
  test(`${kind} parent blocked state prevents open and save`, async () => {
    let count = 0
    const e = editor(kind, {
      [api]: async () => {
        count++
        return { code: 200, data: {} }
      },
    })
    e.props.blocked = true
    open(e)
    assert.equal(e.visible.value, false)
    e.props.blocked = false
    open(e)
    e.props.blocked = true
    await e.save()
    assert.equal(count, 0)
    e.cleanup()
  })
  test(`${kind} cancel and reopen restore the original draft`, () => {
    const e = editor(kind)
    open(e)
    e.form.status = 1
    e.onVisibleChange(false)
    open(e)
    assert.equal(e.form.status, 0)
    e.cleanup()
  })
}
test('binding opens immediately with original repository/path fallback before slow options resolve', async () => {
  const pending = deferred(),
    e = editor('binding', {
      getGrayRepository: () => pending.promise,
      getGrayYamlRepositoryFiles: () => pending.promise,
    })
  e.open(yaml(), binding())
  assert.equal(e.visible.value, true)
  assert.equal(e.repositoriesLoading.value, true)
  assert.equal(e.filesLoading.value, true)
  assert.match(e.repositoryOptions.value[0].label, /Repository 3.*环境通用.*main/)
  assert.equal(e.fileOptions.value[0].children[0].value, 'config/example.yml')
  pending.resolve({ code: 200, data: [] })
  await flush()
  assert.equal(e.form.file_path, 'config/example.yml')
  e.cleanup()
})
test('binding repository echo retains path; real change clears it and ignores older file results', async () => {
  const a = deferred(),
    b = deferred()
  const e = editor('binding', {
    getGrayYamlRepositoryFiles: (p) => (p.repository_id === 3 ? a : b).promise,
  })
  e.open(yaml(), binding())
  e.onRepositoryChange('3')
  assert.equal(e.form.file_path, 'config/example.yml')
  e.form.repository = 4
  e.onRepositoryChange(4)
  assert.equal(e.form.file_path, '')
  b.resolve({ code: 200, data: ['new/file.yml'] })
  await flush()
  a.resolve({ code: 200, data: ['old/file.yml'] })
  await flush()
  assert.deepEqual(e.files.value, ['new/file.yml'])
  assert.equal(e.filesLoading.value, false)
  e.cleanup()
})
test('binding file error is local and retryable while the existing selected path stays intact', async () => {
  let fail = true
  const e = editor('binding', {
    getGrayYamlRepositoryFiles: async () => {
      if (fail) throw Error('Git unavailable')
      return { code: 200, data: ['new/file.yml'] }
    },
  })
  e.open(yaml(), binding())
  await flush()
  assert.equal(e.filesError.value, true)
  assert.equal(e.filesLoading.value, false)
  assert.equal(e.form.file_path, 'config/example.yml')
  fail = false
  await e.loadFiles()
  assert.equal(e.filesError.value, false)
  assert.equal(e.fileOptions.value.length, 2)
  e.cleanup()
})
test('repository option failure can retry independently without discarding selected values', async () => {
  let fail = true
  const e = editor('binding', {
    getGrayRepository: async () => {
      if (fail) throw Error('Offline')
      return { code: 200, data: [repo()] }
    },
  })
  e.open(yaml(), binding())
  await flush()
  assert.equal(e.repositoriesError.value, true)
  assert.equal(e.repositoriesLoading.value, false)
  assert.equal(e.form.repository, 3)
  fail = false
  await e.loadRepositories()
  assert.equal(e.repositoriesError.value, false)
  e.cleanup()
})
test('binding save freezes owner, source and path leaf while excluding nested repository and audit data', async () => {
  let payload
  const e = editor('binding', {
    putGrayYamlFileBinding: async (p) => {
      payload = p
      return { code: 200, data: p }
    },
  })
  const original = binding({ last_update_user: { id: 99 }, create_time: 'Readonly' })
  e.open(yaml(), original)
  original.id = 99
  original.yaml_file = 99
  e.form.file_path = ['config', 'config/example.yml']
  await e.save()
  assert.deepEqual(payload, {
    id: 21,
    yaml_file: 11,
    repository: 3,
    file_path: 'config/example.yml',
    status: 0,
  })
  assert.equal(e.visible.value, false)
  e.cleanup()
})
test('binding required fields reject empty path arrays and missing repository before HTTP', async () => {
  let count = 0
  const e = editor('binding', {
    postGrayYamlFileBinding: async (p) => {
      count++
      return { code: 200, data: { ...p, id: 22 } }
    },
  })
  e.open(yaml())
  await e.save()
  e.form.repository = 3
  e.form.file_path = []
  await e.save()
  assert.equal(count, 0)
  e.form.file_path = ['config', 'config/example.yml']
  await e.save()
  assert.equal(count, 1)
  e.cleanup()
})
test('binding with another YAML owner cannot be opened', () => {
  const e = editor('binding')
  e.open(yaml(), binding({ yaml_file: 99 }))
  assert.equal(e.visible.value, false)
  e.cleanup()
})
test('binding close and reopen invalidate late repository and file options', async () => {
  const pending = deferred()
  const e = editor('binding', {
    getGrayRepository: () => pending.promise,
    getGrayYamlRepositoryFiles: () => pending.promise,
  })
  e.open(yaml(), binding())
  e.onVisibleChange(false)
  e.open(yaml())
  pending.resolve({ code: 200, data: [repo(9)] })
  await flush()
  assert.equal(e.form.repository, null)
  assert.equal(e.form.file_path, '')
  assert.equal(e.filesLoading.value, false)
  e.cleanup()
})
for (const [kind, field, value] of [
  ['file', 'id', 99],
  ['file', 'project_product', 99],
  ['binding', 'yaml_file', 99],
  ['binding', 'repository', 99],
  ['binding', 'id', 99],
]) {
  test(`${kind} bad ${field} acknowledgment retains draft without emitting saved`, async () => {
    const api = kind === 'file' ? 'putGrayYamlFile' : 'putGrayYamlFileBinding'
    const e = editor(kind, { [api]: async (p) => ({ code: 200, data: { ...p, [field]: value } }) })
    kind === 'file' ? e.open(yaml()) : e.open(yaml(), binding())
    await e.save()
    assert.equal(e.saveError.value, true)
    assert.equal(e.visible.value, true)
    assert.equal(
      e.events.some(([event]) => event === 'saved'),
      false
    )
    e.cleanup()
  })
}
test('path tree normalizes separators, deduplicates nodes and removes leaf children without mutating inputs', () => {
  const e = editor('binding'),
    { pathTree } = e.load('forms.ts')
  const input = [' config\\b.yml ', '/config/a.yml/', 'config/a.yml']
  const tree = pathTree(input)
  assert.deepEqual(tree, [
    {
      label: 'config',
      value: 'config',
      children: [
        { label: 'a.yml', value: 'config/a.yml' },
        { label: 'b.yml', value: 'config/b.yml' },
      ],
    },
  ])
  assert.equal(input[0], ' config\\b.yml ')
  e.cleanup()
})
for (const kind of ['file', 'binding'])
  test(`${kind} rejects a non-success save envelope even when data resembles a valid acknowledgment`, async () => {
    const api = kind === 'file' ? 'putGrayYamlFile' : 'putGrayYamlFileBinding'
    const e = editor(kind, { [api]: async (p) => ({ code: 400, data: p }) })
    kind === 'file' ? e.open(yaml()) : e.open(yaml(), binding())
    await e.save()
    assert.equal(e.visible.value, true)
    assert.equal(e.saveError.value, true)
    assert.equal(
      e.events.some(([name]) => name === 'saved'),
      false
    )
    e.cleanup()
  })
test('repository failure envelope cannot become valid options', async () => {
  const e = editor('binding', { getGrayRepository: async () => ({ code: 400, data: [repo()] }) })
  e.open(yaml())
  await flush()
  assert.equal(e.repositoriesError.value, true)
  assert.deepEqual(e.repositoryOptions.value, [])
  e.cleanup()
})
test('file failure envelope cannot become valid file options', async () => {
  const e = editor('binding', {
    getGrayYamlRepositoryFiles: async () => ({ code: 400, data: ['other.yml'] }),
  })
  e.open(yaml(), binding())
  await flush()
  assert.equal(e.filesError.value, true)
  assert.deepEqual(e.files.value, [])
  assert.equal(e.form.file_path, 'config/example.yml')
  e.cleanup()
})
test('parent create captures navigation defaults immediately and write guards prevent opening another editor', () => {
  const opened = [],
    yamlSaving = vue.ref(false),
    bindingSaving = vue.ref(false),
    actionLoading = vue.ref(''),
    bindingEditorVisible = vue.ref(false)
  const onAdd = method(
    'onAdd',
    {
      yamlSaving,
      bindingSaving,
      actionLoading,
      bindingEditorVisible,
      actionBlocked: () =>
        yamlSaving.value ||
        bindingSaving.value ||
        !!actionLoading.value ||
        bindingEditorVisible.value,
      bindingDrawer: { visible: false },
      navigationCreateRef: vue.ref({ getCreateDefaults: () => ({ projectProduct: 9, module: 8 }) }),
      yamlEditorRef: vue.ref({ open: (...args) => opened.push(args) }),
    },
    path.join(base, 'index.vue')
  )
  onAdd()
  assert.deepEqual(opened, [[undefined, 9]])
  bindingSaving.value = true
  onAdd()
  assert.equal(opened.length, 1)
})
test('parent and two editor SFC scripts, templates and styles compile', () => {
  for (const name of [
    'index.vue',
    'components/YamlFileEditor.vue',
    'components/YamlBindingEditor.vue',
  ]) {
    const filename = path.join(base, name),
      { descriptor, errors } = parse(readFileSync(filename, 'utf8'))
    assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: filename })
    assert.deepEqual(
      compileTemplate({
        source: descriptor.template.content,
        filename,
        id: filename,
        compilerOptions: { bindingMetadata: script.bindings },
      }).errors,
      []
    )
    for (const style of descriptor.styles)
      assert.deepEqual(
        compileStyle({
          source: style.content,
          filename,
          id: filename,
          scoped: style.scoped,
          preprocessLang: style.lang,
        }).errors,
        []
      )
  }
})
