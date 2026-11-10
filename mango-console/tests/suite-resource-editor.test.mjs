import test from 'node:test'
import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import { parse, compileScript, compileTemplate, compileStyle } from '@vue/compiler-sfc'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/functional-test/suite/details')
const bindings = 'open,save,cancel,form,visible,rawText,saving,saveError,onFileChange,removeFile'
const resource = (overrides = {}) => ({
  id: 7,
  suite: 1,
  context_key: 0,
  title: 'Source',
  content_type: 0,
  url_type: 0,
  content: 'Original',
  extracted_text: 'Parsed',
  enabled: true,
  file: null,
  file_name: '',
  file_path: '',
  mime_type: '',
  file_size: null,
  ...overrides,
})
function editor(api = {}, modules = {}) {
  return harness('SuiteResourceEditor', bindings, {
    base,
    props: {
      suiteId: 1,
      productId: 2,
      contextKey: 'one',
      available: true,
      groupOptions: [],
      typeOptions: [],
    },
    api: {
      postFunctionalContextResource: async () => ({ data: resource() }),
      putFunctionalContextResource: async () => ({ data: resource() }),
      ...api,
    },
    modules,
  })
}
const selectFile = (e, name = 'source.txt') => {
  const file = new File(['content'], name, { type: 'text/plain' })
  e.onFileChange([{ uid: '1', file }], { uid: '1', file })
  return file
}
test('draft is isolated and reopening maps only editable fields', () => {
  const e = editor(),
    record = resource({ update_user: 99, parse_error: 'readonly' })
  e.open(0, '', record)
  e.form.content = 'Changed'
  assert.equal(record.content, 'Original')
  assert.equal('update_user' in e.form, false)
  assert.equal('parse_error' in e.form, false)
  e.cancel()
  e.open(0, '', record)
  assert.equal(e.form.content, 'Original')
  e.close()
})
test('new resources reset id and preserve context key zero', async () => {
  let body
  const e = editor({
    postFunctionalContextResource: async (p) => {
      body = p
      return { data: resource() }
    },
  })
  e.open(0, '', resource())
  e.cancel()
  e.open(0, 'New')
  assert.equal(e.form.id, null)
  assert.equal(await e.save(), true)
  assert.equal('id' in body, false)
  assert.equal(body.context_key, 0)
  assert.deepEqual(e.events, [
    ['busy', true],
    ['changed', 1],
    ['busy', false],
  ])
  e.close()
})
test('raw text save submits only the text field and frozen owner', async () => {
  let body
  const e = editor({
    putFunctionalContextResource: async (p) => {
      body = p
      return { data: resource() }
    },
  })
  e.open(0, '', resource(), true)
  e.rawText.value = 'Updated'
  await e.save()
  assert.deepEqual(body, { id: 7, suite: 1, content: 'Updated' })
  e.close()
})
test('file raw save updates extracted text rather than file metadata', async () => {
  let body
  const e = editor({
    putFunctionalContextResource: async (p) => {
      body = p
      return { data: resource() }
    },
  })
  e.open(0, '', resource({ content_type: 2 }), true)
  e.rawText.value = 'Updated'
  await e.save()
  assert.deepEqual(body, { id: 7, suite: 1, extracted_text: 'Updated' })
  e.close()
})
test('failed metadata save reuses the uploaded file on retry', async () => {
  let uploads = 0,
    writes = 0
  const bodies = []
  const e = editor({
    postUserFile: async (data) => {
      uploads++
      assert.equal(data.get('project_product'), '2')
      assert.equal(data.get('test_file').name, 'source.txt')
      return { data: { id: 31, test_file: '/media/source.txt' } }
    },
    postFunctionalContextResource: async (body) => {
      bodies.push(body)
      if (++writes === 1) throw Error('offline')
      return { data: resource() }
    },
  })
  e.open(0, 'New')
  e.form.content_type = 2
  selectFile(e)
  assert.equal(await e.save(), false)
  assert.equal(e.saveError.value, true)
  assert.equal(e.visible.value, true)
  assert.equal(e.form.title, 'New')
  assert.equal(await e.save(), true)
  assert.equal(uploads, 1)
  assert.equal(bodies[1].file, 31)
  assert.equal(bodies[1].file_size, 7)
  assert.equal(bodies[1].parse_status, 0)
  e.close()
})
test('replacing file after failed save invalidates cached upload', async () => {
  let uploads = 0
  const e = editor({
    postUserFile: async () => ({ data: { id: ++uploads } }),
    postFunctionalContextResource: async () => {
      throw Error('offline')
    },
  })
  e.open(0, 'New')
  e.form.content_type = 2
  selectFile(e)
  await e.save()
  selectFile(e, 'replacement.txt')
  await e.save()
  assert.equal(uploads, 2)
  e.close()
})
test('failed upload retains draft and restores retry availability', async () => {
  let writes = 0
  const e = editor({
    postUserFile: async () => {
      throw Error('offline')
    },
    postFunctionalContextResource: async () => {
      writes++
    },
  })
  e.open(0, 'New')
  e.form.content_type = 2
  selectFile(e)
  assert.equal(await e.save(), false)
  assert.equal(writes, 0)
  assert.equal(e.saving.value, false)
  assert.equal(e.form.title, 'New')
  e.close()
})
test('save is physically serialized and blocks normal cancel and reopening', async () => {
  const pending = deferred()
  let writes = 0
  const e = editor({
    postFunctionalContextResource: () => {
      writes++
      return pending.promise
    },
  })
  e.open(0, 'New')
  const request = e.save()
  e.cancel()
  e.open(1, 'Other')
  await e.save()
  assert.equal(e.visible.value, true)
  assert.equal(e.form.title, 'New')
  assert.equal(writes, 1)
  pending.resolve({ data: resource() })
  await request
  e.close()
})
for (const [name, change] of [
  [
    'identity',
    (e) => {
      e.props.contextKey = 'two'
    },
  ],
  [
    'suite',
    (e) => {
      e.props.suiteId = 2
    },
  ],
  [
    'product',
    (e) => {
      e.props.productId = 3
    },
  ],
  [
    'availability',
    (e) => {
      e.props.available = false
    },
  ],
]) {
  test(`${name} change during upload prevents metadata write and late feedback`, async () => {
    const pending = deferred()
    let writes = 0
    const e = editor({
      postUserFile: () => pending.promise,
      postFunctionalContextResource: async () => {
        writes++
      },
    })
    e.open(0, 'New')
    e.form.content_type = 2
    selectFile(e)
    const request = e.save()
    change(e)
    await flush()
    assert.equal(e.visible.value, false)
    assert.equal(e.saving.value, true)
    e.open(0, 'Must wait')
    assert.equal(e.visible.value, false)
    pending.resolve({ data: { id: 31 } })
    await request
    assert.equal(writes, 0)
    assert.deepEqual(
      e.events.filter(([event]) => event === 'changed'),
      []
    )
    assert.equal(e.saving.value, false)
    e.close()
  })
}
test('identity change during save ignores late success and permits reopening after settlement', async () => {
  const pending = deferred()
  const e = editor({ postFunctionalContextResource: () => pending.promise })
  e.open(0, 'New')
  const request = e.save()
  e.props.contextKey = 'two'
  await flush()
  pending.resolve({ data: resource() })
  await request
  assert.deepEqual(
    e.events.filter(([event]) => event === 'changed'),
    []
  )
  e.open(0, 'Again')
  assert.equal(e.form.title, 'Again')
  e.close()
})
test('deactivation during upload cannot create resources after unmount', async () => {
  const pending = deferred()
  let writes = 0
  const e = editor({
    postUserFile: () => pending.promise,
    postFunctionalContextResource: async () => {
      writes++
    },
  })
  e.open(0, 'New')
  e.form.content_type = 2
  selectFile(e)
  const request = e.save()
  e.close()
  pending.resolve({ data: { id: 31 } })
  await request
  assert.equal(writes, 0)
  assert.deepEqual(
    e.events.filter(([event]) => event === 'changed'),
    []
  )
})
test('invalid upload acknowledgement never creates a metadata record', async () => {
  let writes = 0
  const e = editor({
    postUserFile: async () => ({ data: {} }),
    postFunctionalContextResource: async () => {
      writes++
    },
  })
  e.open(0, 'New')
  e.form.content_type = 2
  selectFile(e)
  assert.equal(await e.save(), false)
  assert.equal(writes, 0)
  assert.equal(e.saveError.value, true)
  e.close()
})
test('wrong resource acknowledgement retains editor and does not emit success', async () => {
  const e = editor({
    putFunctionalContextResource: async () => ({ data: resource({ id: 8, suite: 2 }) }),
  })
  e.open(0, '', resource())
  assert.equal(await e.save(), false)
  assert.equal(e.visible.value, true)
  assert.deepEqual(
    e.events.filter(([event]) => event === 'changed'),
    []
  )
  e.close()
})
test('saved original text is treated as content, not empty-state placeholder', () => {
  const e = editor()
  e.open(0, '', resource({ content: '暂无原文内容' }), true)
  assert.equal(e.rawText.value, '暂无原文内容')
  e.close()
})
test('foreign owner and reserved platform group cannot open editor', () => {
  const e = editor()
  e.open(0, '', resource({ suite: 2 }))
  assert.equal(e.visible.value, false)
  e.open(6, 'Reserved')
  assert.equal(e.visible.value, false)
  e.close()
})
test('whitespace title and unavailable Feishu type preserve validation', async () => {
  let writes = 0
  const e = editor({
    postFunctionalContextResource: async () => {
      writes++
    },
  })
  e.open(0, '   ')
  assert.equal(await e.save(), false)
  e.form.title = 'New'
  e.form.url_type = 1
  assert.equal(await e.save(), false)
  assert.equal(writes, 0)
  e.close()
})
test('upload freezes resource values and ignores file changes until settlement', async () => {
  const upload = deferred()
  let body
  const e = editor({
    postUserFile: () => upload.promise,
    postFunctionalContextResource: async (payload) => {
      body = payload
      return { data: resource() }
    },
  })
  e.open(0, 'Frozen')
  e.form.content_type = 2
  selectFile(e)
  const saving = e.save()
  e.form.title = 'Later'
  e.form.content_type = 0
  selectFile(e, 'later.txt')
  assert.equal(await e.removeFile(), false)
  upload.resolve({ data: { id: 31 } })
  await saving
  assert.equal(body.title, 'Frozen')
  assert.equal(body.content_type, 2)
  assert.equal(body.file_name, 'source.txt')
  e.close()
})
test('cancel and reopen discard upload cache from the prior draft', async () => {
  let uploads = 0
  const e = editor({
    postUserFile: async () => ({ data: { id: ++uploads } }),
    postFunctionalContextResource: async () => {
      throw Error('offline')
    },
  })
  e.open(0, 'First')
  e.form.content_type = 2
  selectFile(e)
  await e.save()
  e.cancel()
  e.open(0, 'Next')
  e.form.content_type = 2
  selectFile(e)
  await e.save()
  assert.equal(uploads, 2)
  e.close()
})
test('main page and resource editor SFC scripts/templates/styles compile', () => {
  for (const filename of ['index.vue', 'components/SuiteResourceEditor.vue']) {
    const full = path.join(base, filename),
      { descriptor, errors } = parse(readFileSync(full, 'utf8'))
    assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: filename })
    const template = compileTemplate({
      source: descriptor.template.content,
      filename: full,
      id: filename,
      compilerOptions: { bindingMetadata: script.bindings },
    })
    assert.deepEqual(template.errors, [])
    for (const style of descriptor.styles)
      assert.deepEqual(
        compileStyle({ source: style.content, filename: full, id: filename, scoped: true }).errors,
        []
      )
  }
})
