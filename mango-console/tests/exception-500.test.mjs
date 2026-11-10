import assert from 'node:assert/strict'
import test from 'node:test'
import * as Vue from 'vue'
import { deferred } from './helpers/case-details-harness.mjs'
import { mountException, settleException as settle } from './helpers/exception-harness.mjs'

const mount500 = options => mountException({ status: '500', ...options })

test('500 mounts the real error page without querying permissions or echoing arbitrary URL text', async () => {
  const f = await mount500({ path: '/500?error=fixture-internal-error' })
  try {
    assert.equal(f.router.currentRoute.value.path, '/500')
    assert.equal(f.nodes('h1')[0].text, '您访问的页面出错啦')
    assert.match(f.nodes('img')[0].props.src, /img_500.png$/)
    assert.equal(f.nodes('section')[0].props['aria-label'], '您访问的页面出错啦')
    assert.deepEqual(f.refreshes, [])
    assert.deepEqual(f.enumReads, [])
    assert.deepEqual(f.warnings, [])
  } finally { f.dispose() }
})

test('500 return binds loading and deduplicates clicks while permissions are refreshed', async () => {
  const wait = deferred(), f = await mount500({ wait })
  try {
    const button = f.nodes('button')[0], pending = button.props.onClick()
    await Vue.nextTick()
    assert.equal(button.props.loading, true)
    await button.props.onClick()
    assert.deepEqual(f.refreshes, [true])
    wait.resolve(); await pending; await settle()
    assert.equal(f.router.currentRoute.value.path, '/index/home')
    assert.deepEqual(f.hashes, [])
  } finally { f.dispose() }
})

test('500 keeps the fallback on refresh failure and a later manual retry can navigate successfully', async () => {
  let failed = true
  const f = await mount500({ fail: () => failed })
  try {
    const button = f.nodes('button')[0]
    await button.props.onClick(); await Vue.nextTick()
    assert.equal(button.props.loading, false)
    assert.deepEqual(f.hashes, ['https://example.org/console/#/index/home'])
    failed = false
    await button.props.onClick(); await settle()
    assert.equal(f.router.currentRoute.value.path, '/index/home')
    assert.deepEqual(f.refreshes, [true, true])
  } finally { f.dispose() }
})

test('500 is publicly reachable with an expired session and returning uses the login hash', async () => {
  const f = await mount500({ expired: true })
  try {
    assert.equal(f.router.currentRoute.value.path, '/500')
    await f.nodes('button')[0].props.onClick()
    assert.deepEqual(f.hashes, ['https://example.org/console/#/login'])
    assert.deepEqual(f.refreshes, [])
  } finally { f.dispose() }
})

test('500 falls back to the default home if the refreshed home is empty', async () => {
  const f = await mount500({ homePath: '' })
  try {
    await f.nodes('button')[0].props.onClick(); await settle()
    assert.equal(f.router.currentRoute.value.path, '/index/home')
    assert.deepEqual(f.hashes, [])
  } finally { f.dispose() }
})

test('500 respects a refreshed login destination without attempting a business route', async () => {
  const f = await mount500({ homePath: '/login' })
  try {
    const button = f.nodes('button')[0]
    await button.props.onClick(); await Vue.nextTick()
    assert.deepEqual(f.hashes, ['https://example.org/console/#/login'])
    assert.equal(button.props.loading, false)
    assert.equal(f.router.currentRoute.value.path, '/500')
  } finally { f.dispose() }
})

test('500 invalidates a pending return across an actual KeepAlive deactivate/reactivate cycle', async () => {
  const wait = deferred(), f = await mount500({ wait, keepAlive: true })
  try {
    const pending = f.nodes('button')[0].props.onClick()
    await f.router.push('/index/home'); await settle()
    await f.router.push('/500'); await settle()
    const restoredButton = f.nodes('button')[0]
    assert.equal(restoredButton.props.loading, true)
    await restoredButton.props.onClick()
    assert.deepEqual(f.refreshes, [true])
    wait.resolve(); await pending; await settle()
    assert.equal(f.router.currentRoute.value.path, '/500')
    assert.equal(restoredButton.props.loading, false)
    assert.deepEqual(f.hashes, [])
    assert.deepEqual(f.refreshes, [true])
    await restoredButton.props.onClick(); await settle()
    assert.equal(f.router.currentRoute.value.path, '/index/home')
    assert.deepEqual(f.refreshes, [true, true])
    assert.deepEqual(f.warnings, [])
  } finally { f.dispose() }
})

test('500 ignores a pending failure after an identity or URL context change', async () => {
  for (const kind of ['identity', 'url']) {
    const wait = deferred(), f = await mount500({ wait })
    try {
      const pending = f.nodes('button')[0].props.onClick()
      if (kind === 'identity') f.user.token = 'different-fixture-token'
      else { await f.router.push('/500?source=changed'); await settle() }
      wait.reject(Error('late fixture error')); await pending; await Vue.nextTick()
      assert.equal(f.router.currentRoute.value.path, '/500')
      assert.deepEqual(f.hashes, [])
      assert.equal(f.nodes('button')[0].props.loading, false)
    } finally { f.dispose() }
  }
})
