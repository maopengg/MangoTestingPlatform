import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { parse } from '@vue/compiler-sfc'
import { baseParse } from '@vue/compiler-dom'
import { filesUnder, elements } from '../scripts/simple-modal-layout-audit.mjs'

test('every Arco form supplies its required model binding', () => {
  const missing = []
  for (const filename of filesUnder('src')) {
    const { descriptor } = parse(readFileSync(filename, 'utf8'))
    if (!descriptor.template) continue
    for (const form of elements(baseParse(descriptor.template.content)).filter(node => node.tag === 'a-form')) {
      if (!form.props.some(prop => prop.type === 7 && prop.arg?.content === 'model' && prop.exp?.content.trim())) {
        missing.push(`${filename}:${form.loc.start.line}`)
      }
    }
  }
  assert.deepEqual(missing, [])
})
