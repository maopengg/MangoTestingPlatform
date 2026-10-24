import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import test from 'node:test'
import { createSSRApp, h } from 'vue'
import { renderToString } from '@vue/server-renderer'

const require = createRequire(import.meta.url)
const Pagination = require('@arco-design/web-vue/lib/pagination')

test('nine-page pagination collapses numbers at the beginning, middle and end', async () => {
  for (const [current, expected] of [[1, [1, 2, 3, 9]], [5, [1, 4, 5, 6, 9]], [9, [1, 7, 8, 9]]]) {
    const html = await renderToString(createSSRApp({
      render: () => h(Pagination, { total: 169, pageSize: 20, current,
        baseSize: 4, bufferSize: 1, autoAdjust: false }),
    }))
    const numbers = [...html.matchAll(/<li[^>]*><!--\[-->(\d+)<!--\]--><\/li>/g)]
      .map(match => Number(match[1]))
    assert.deepEqual(numbers, expected)
    assert.match(html, /arco-pagination-item-ellipsis/)
  }
})

test('compact pagination is opt-in for both module coverage views', () => {
  const footer = readFileSync('src/components/table/TableFooter.vue', 'utf8')
  assert.match(footer, /compactPages:[\s\S]*?default: false/)
  assert.match(footer, /:base-size="compactPages \? 4 : 6"/)
  assert.match(footer, /:buffer-size="compactPages \? 1 : 2"/)
  for (const file of ['index.vue', 'components/CoverageOverview.vue']) {
    const source = readFileSync(`src/views/apitest/module-coverage/${file}`, 'utf8')
    assert.match(source, /<TableFooter[^>]*compact-pages/)
  }
})
