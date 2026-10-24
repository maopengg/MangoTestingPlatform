import assert from 'node:assert/strict'
import { readFileSync, readdirSync } from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import { parse, compileTemplate } from '@vue/compiler-sfc'
import { baseParse } from '@vue/compiler-dom'

function vueFiles(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const target = path.join(directory, entry.name)
    return entry.isDirectory() ? vueFiles(target) : target.endsWith('.vue') ? [target] : []
  })
}

test('all Vue templates parse and compile', () => {
  for (const filename of vueFiles('src')) {
    const { descriptor, errors } = parse(readFileSync(filename, 'utf8'), { filename })
    assert.deepEqual(errors, [], filename)
    if (!descriptor.template || descriptor.template.src) continue
    const result = compileTemplate({ source: descriptor.template.content, filename, id: 'ui-layout-audit' })
    assert.deepEqual(result.errors, [], filename)
  }
})

test('explicit spinner roots do not style every descendant spin child', () => {
  for (const filename of vueFiles('src')) {
    const source = readFileSync(filename, 'utf8')
    const { descriptor } = parse(source, { filename })
    if (!descriptor.template) continue
    const classes = new Set()
    function visit(node) {
      if (node.type === 1 && ['a-spin', 'mango-panel-spin'].includes(node.tag)) {
        const value = node.props.find((prop) => prop.type === 6 && prop.name === 'class')?.value?.content
        for (const name of value?.split(/\s+/) || []) classes.add(name)
      }
      for (const child of node.children || []) visit(child)
    }
    visit(baseParse(descriptor.template.content))
    for (const name of classes) {
      assert.ok(!source.includes(`.${name} :deep(.mango-panel-spin__content)`), `${filename}: ${name}`)
      assert.ok(!source.includes(`:deep(.${name} .mango-panel-spin__content)`), `${filename}: ${name}`)
    }
  }
})

test('section titles cannot be shrunk by a finite flex panel', () => {
  const css = readFileSync('src/styles/index.css', 'utf8')
  assert.match(css, /\.mango-section-title\s*\{[^}]*flex-shrink: 0/)
})
