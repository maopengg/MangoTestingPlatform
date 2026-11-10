import assert from 'node:assert/strict'
import test from 'node:test'
import * as Vue from 'vue'
import { deferred } from './helpers/case-details-harness.mjs'
import { mountException as mount404, settleException as settle } from './helpers/exception-harness.mjs'

test('404 route mounts its real page, image, heading and return control without loading permissions', async () => {
  const f = await mount404()
  try {
    assert.equal(f.router.currentRoute.value.path, '/404')
    assert.equal(f.nodes('h1')[0].text, '您访问的页面不存在')
    assert.match(f.nodes('img')[0].props.src, /img_404.png$/)
    assert.equal(f.nodes('img')[0].props.alt, '')
    assert.equal(f.nodes('button')[0].props.loading, false)
    assert.deepEqual(f.refreshes, [])
    assert.deepEqual(f.enumReads, [])
    assert.deepEqual(f.warnings, [])
  } finally { f.dispose() }
})

test('the existing dynamic route catch-all reaches the 404 entry', async () => {
  const f = await mount404({ path: '/missing-fixture-page' })
  try {
    assert.equal(f.router.currentRoute.value.path, '/404')
    assert.equal(f.nodes('h1')[0].text, '您访问的页面不存在')
  } finally { f.dispose() }
})

test('the rendered return button shows loading, deduplicates clicks and navigates using Vue Router', async () => {
  const wait = deferred(), f = await mount404({ wait })
  try {
    const button = f.nodes('button')[0]
    const pending = button.props.onClick()
    await Vue.nextTick()
    assert.equal(button.props.loading, true)
    await button.props.onClick()
    assert.deepEqual(f.refreshes, [true])
    wait.resolve(); await pending; await settle()
    assert.equal(f.router.currentRoute.value.path, '/index/home')
    assert.equal(f.nodes('home').length, 1)
    assert.deepEqual(f.hashes, [])
  } finally { f.dispose() }
})

test('a mounted 404 remains publicly reachable with an expired session, and returning goes to login', async () => {
  const f = await mount404({ expired: true })
  try {
    await f.nodes('button')[0].props.onClick()
    assert.deepEqual(f.hashes, ['https://example.org/console/#/login'])
    assert.deepEqual(f.refreshes, [])
  } finally { f.dispose() }
})

test('a failed refresh releases the rendered loading state and preserves the full-page fallback', async () => {
  const f = await mount404({ fail: true })
  try {
    const button = f.nodes('button')[0]
    await button.props.onClick(); await Vue.nextTick()
    assert.equal(button.props.loading, false)
    assert.deepEqual(f.hashes, ['https://example.org/console/#/index/home'])
    await button.props.onClick()
    assert.equal(f.refreshes.length, 2)
  } finally { f.dispose() }
})

test('actual RouterView unmount prevents a late 404 return task from redirecting', async () => {
  const wait = deferred(), f = await mount404({ wait })
  try {
    const pending = f.nodes('button')[0].props.onClick()
    await f.router.push('/index/home'); await settle()
    wait.reject(Error('late fixture failure')); await pending
    assert.equal(f.router.currentRoute.value.path, '/index/home')
    assert.deepEqual(f.hashes, [])
    assert.equal(f.nodes('home').length, 1)
  } finally { f.dispose() }
})
