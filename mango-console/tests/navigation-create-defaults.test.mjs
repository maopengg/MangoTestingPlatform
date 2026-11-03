import assert from 'node:assert/strict'
import { readFileSync, readdirSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'

function harness() {
  const ticks = []
  const exports = {}
  const source = readFileSync('src/utils/navigation-create-defaults.ts', 'utf8')
  const compiled = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
  }).outputText
  new Function('exports', 'require', compiled)(exports, name => {
    assert.equal(name, 'vue')
    return { nextTick: () => new Promise(resolve => ticks.push(resolve)) }
  })
  return { ...exports, flush: () => ticks.splice(0).forEach(resolve => resolve()) }
}
const navigation = (projectProduct = 10, module = 20) => ({ getCreateDefaults: () => ({ projectProduct, module }) })
const items = () => [{ key: 'project_product', value: '' }, { key: 'module', value: '' }, { key: 'name', value: '' }]

test('create fills product then module after product-change clearing; keeps ordinary fields untouched', async () => {
  const h = harness(), fields = items()
  fields[2].value = '保留输入'
  const done = h.prefillNavigationFormItems(navigation(), fields, () => true)
  assert.equal(fields[0].value, 10)
  assert.equal(fields[1].value, '')
  fields[1].value = ''
  h.flush(); await done
  assert.equal(fields[1].value, 20)
  assert.equal(fields[2].value, '保留输入')
})

test('all products and parent-module selections never choose an arbitrary product or child', async () => {
  const h = harness(), model = { project_product: '', module: '' }
  await h.prefillNavigationModel(navigation(null, null), model)
  assert.deepEqual(model, { project_product: '', module: '' })
  const done = h.prefillNavigationModel(navigation(10, null), model)
  h.flush(); await done
  assert.deepEqual(model, { project_product: 10, module: '' })
})

test('editing existing records is untouched, including empty optional module', async () => {
  const h = harness(), model = { id: 7, project_product: 99, module: null }
  await h.prefillNavigationModel(navigation(), model)
  assert.deepEqual(model, { id: 7, project_product: 99, module: null })
  const fields = items()
  await h.prefillNavigationFormItems(navigation(), fields, () => false)
  assert.deepEqual(fields, items())
})

test('a late create update never overwrites a switched edit form or manually changed product/module', async () => {
  const h = harness(), fields = items()
  let create = true
  const done = h.prefillNavigationFormItems(navigation(), fields, () => create)
  create = false; fields[0].value = 99; fields[1].value = 88
  h.flush(); await done
  assert.deepEqual(fields.slice(0, 2).map(field => field.value), [99, 88])
  create = true; fields[0].value = ''; fields[1].value = ''
  const changed = h.prefillNavigationFormItems(navigation(), fields, () => create)
  fields[0].value = [1, 30]
  h.flush(); await changed
  assert.equal(fields[1].value, '')
  const manual = h.prefillNavigationFormItems(navigation(30, 40), fields, () => create)
  fields[1].value = 50
  h.flush(); await manual
  assert.equal(fields[1].value, 50)
})

test('continuous create reads fresh navigation and cancels a previous pending module default', async () => {
  const h = harness(), fields = items()
  const first = h.prefillNavigationFormItems(navigation(10, 20), fields, () => true)
  fields[0].value = ''; fields[1].value = ''
  const second = h.prefillNavigationFormItems(navigation(30, 40), fields, () => true)
  h.flush(); await Promise.all([first, second])
  assert.deepEqual(fields.slice(0, 2).map(field => field.value), [30, 40])
})

test('partial forms only receive fields they own, and explicit product context wins', async () => {
  const h = harness(), upload = { project_product: '' }
  const done = h.prefillNavigationModel(navigation(), upload)
  h.flush(); await done
  assert.deepEqual(upload, { project_product: 10 })
  const plan = { project_product: 99, name: '' }
  const explicit = h.prefillNavigationModel(navigation(), plan)
  h.flush(); await explicit
  assert.deepEqual(plan, { project_product: 99, name: '' })
})

function vueFiles(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap(entry => {
    const path = `${directory}/${entry.name}`
    return entry.isDirectory() ? vueFiles(path) : path.endsWith('.vue') ? [path] : []
  })
}

test('all changed navigation surfaces compile and Pytest creation is not opted in', () => {
  const files = vueFiles('src').filter(file => readFileSync(file, 'utf8').includes('navigation-create-defaults'))
  assert.ok(files.length >= 20)
  for (const filename of files) {
    const source = readFileSync(filename, 'utf8')
    assert.ok(!filename.includes('/pytest/'), filename)
    const { descriptor, errors } = parse(source, { filename })
    assert.deepEqual(errors, [], filename)
    const script = compileScript(descriptor, { id: filename })
    const template = compileTemplate({ source: descriptor.template.content, filename, id: filename,
      compilerOptions: { bindingMetadata: script.bindings } })
    assert.deepEqual(template.errors, [], filename)
    const body = descriptor.scriptSetup?.content || descriptor.script?.content || ''
    const ast = ts.createSourceFile(filename, body, ts.ScriptTarget.Latest, true)
    for (const node of ast.statements) {
      if (ts.isFunctionDeclaration(node) && /^(onUpdate|onEdit)$/.test(node.name?.text || '')) {
        assert.ok(!node.getText(ast).includes('prefillNavigation'), `${filename}: edit must not prefill`)
      }
    }
  }
})
