import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'

const filename = 'src/views/pytest/repository/index.vue'
const source = readFileSync(new URL('../../../src/views/pytest/repository/index.vue', import.meta.url), 'utf8')
const resetCode = source.slice(source.indexOf('  function resetForm('), source.indexOf('  function openEditor('))
const saveCode = source.slice(source.indexOf('  async function saveRepository('), source.indexOf('  async function runAction('))
function harness() {
  const form = {}, saved = [], saving = { value: false }
  const { outputText } = ts.transpileModule(resetCode + saveCode, { compilerOptions: { target: ts.ScriptTarget.ES2020 } })
  const methods = new Function('repositoryForm', 'saving', 'publicRepositoryProviders', 'repositoryHost',
    'providerOptions', 'Message', 'savePytestRepository', 'loadRepositories',
    `${outputText}; return { resetForm, saveRepository }`)(
      form, saving, {}, () => '', [], { error: () => {}, success: () => {} },
      async data => { saved.push(data); return { msg: 'OK' } }, async () => {})
  return { form, saved, saving, ...methods }
}

test('new public repositories default to no authentication and selector can be cleared', () => {
  const h = harness(); h.resetForm()
  assert.equal(h.form.credential_auth_type, 'none')
  assert.match(source, /value: 'none'/)
  assert.match(source, /v-model="repositoryForm.credential_auth_type"\s+allow-clear/)
  assert.doesNotMatch(source, /Gitee 下载仓库快照需要 Token/)
})

test('cleared selector sends explicit anonymous access and excludes stale secrets', async () => {
  for (const cleared of [undefined, null, '', 'none']) {
    const h = harness(); h.resetForm()
    Object.assign(h.form, { name: 'Public', repo_url: 'https://example.com/public.git',
      credential_auth_type: cleared, credential_username: 'old-user', credential_secret: 'old-secret' })
    let closed; await h.saveRepository(value => { closed = value })
    assert.equal(closed, true)
    assert.equal(h.saved[0].credential_auth_type, 'none')
    assert.equal(h.saved[0].credential_username, '')
    assert.equal(h.saved[0].credential_secret, '')
    assert.equal(h.saving.value, false)
  }
})

test('editing retains the existing authentication method and empty secret behavior', async () => {
  const h = harness()
  h.resetForm({ id: 1, name: 'Private', repo_url: 'https://example.com/private.git',
    credential: { auth_type: 'username_password', username: 'existing-user' } })
  await h.saveRepository(() => {})
  assert.equal(h.saved[0].credential_auth_type, 'username_password')
  assert.equal(h.saved[0].credential_username, 'existing-user')
  assert.equal(h.saved[0].credential_secret, '')
})

test('repository editor template and script compile', () => {
  const { descriptor } = parse(source, { filename })
  const script = compileScript(descriptor, { id: 'repository-auth' })
  const result = compileTemplate({ source: descriptor.template.content, filename, id: 'repository-auth',
    compilerOptions: { bindingMetadata: script.bindings } })
  assert.deepEqual(result.errors, [])
})
