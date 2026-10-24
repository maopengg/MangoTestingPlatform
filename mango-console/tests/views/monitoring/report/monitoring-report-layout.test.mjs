import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import test from 'node:test'

const root = path.resolve(import.meta.dirname, '../../../..')
const source = fs.readFileSync(path.join(root, 'src/views/monitoring/report/index.vue'), 'utf8')

test('monitoring report uses the compact shared table header', () => {
  assert.match(source, /<TableBody ref="tableBody">/)
  assert.match(source, /<TableHeader[^>]*title="预警监控报告"/s)
  assert.doesNotMatch(source, /show-filter/)
  assert.doesNotMatch(source, /:deep\(\.arco-card-body\)/)
})
