import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'

const source = readFileSync(new URL('../../../src/layouts/avatar/index.vue', import.meta.url), 'utf8')
const handler = source.slice(source.indexOf('  const visible = ref(false)'), source.indexOf('</script>'))
const { outputText } = ts.transpileModule(handler, { compilerOptions: { target: ts.ScriptTarget.ES2020 } })

function harness(get) {
  let mount, dispose
  const state = new Function('ref', 'branding', 'onMounted', 'onBeforeUnmount', `${outputText}; return { visible, authorPopupLoading }`)(
    value => ({ value }), { loadPublicConfig: async () => (await get({ url: '/user/registration-config' })).data },
    callback => { mount = callback }, callback => { dispose = callback },
  )
  return { ...state, mount, dispose }
}

test('automatic author popup follows the server switch, not build-time configuration', async () => {
  for (const enabled of [true, false]) {
    const h = harness(async options => {
      assert.equal(options.url, '/user/registration-config')
      return { data: { show_home_author_popup: enabled } }
    })
    assert.equal(h.visible.value, false)
    assert.equal(h.authorPopupLoading.value, true)
    await h.mount()
    assert.equal(h.visible.value, enabled)
    assert.equal(h.authorPopupLoading.value, false)
  }
  assert.doesNotMatch(source, /VITE_IS_INDEX_WINDOW/)
})

test('a failed config request does not block the workbench or open a popup', async () => {
  const h = harness(async () => { throw new Error('offline') })
  await h.mount()
  assert.equal(h.visible.value, false)
  assert.equal(h.authorPopupLoading.value, false)
})

test('a stale response after leaving the layout cannot open the popup', async () => {
  let resolve
  const h = harness(() => new Promise(done => { resolve = done }))
  const pending = h.mount()
  h.dispose()
  resolve({ data: { show_home_author_popup: true } })
  await pending
  assert.equal(h.visible.value, false)
})
