import assert from 'node:assert/strict'
import fs from 'node:fs'
import { fileURLToPath } from 'node:url'

function read(relativePath) {
  return fs.readFileSync(fileURLToPath(new URL(relativePath, import.meta.url)), 'utf8')
}

const configSource = read('../../../../src/views/apitest/info/config.ts')
const pageSource = read('../../../../src/views/apitest/info/index.vue')
const policySource = read('../../../../src/utils/api-info-revision.ts')

for (const contract of ["title: '发布状态'", "key: 'publication_status'"]) {
  assert.ok(configSource.includes(contract), `interface table config must include ${contract}`)
}

for (const contract of [
  "item.key === 'publication_status'",
  'getApiInfoPublicationMeta(',
  'record.published_version_label',
  'record.has_unpublished_changes',
]) {
  assert.ok(pageSource.includes(contract), `interface table must include ${contract}`)
}

for (const contract of ['已发布', '有未发布变更', '未发布']) {
  assert.ok(policySource.includes(contract), `publication policy must include ${contract}`)
}

console.log('api info list publication status contract passed')
