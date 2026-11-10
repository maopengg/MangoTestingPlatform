import assert from 'node:assert/strict'
import path from 'node:path'
import test from 'node:test'
import * as vue from 'vue'
import { deferred, flush as flushVue, harness } from './helpers/case-details-harness.mjs'

async function flush() { await flushVue(); await new Promise(resolve => setImmediate(resolve)) }
const response = id => ({ code: 200, data: { id, name: 'Fixture ' + id, publication_status: 'prepublished', status: 1, eligibility_reasons: [], scenario_tags: [], sql_count: 0, factory_count: 0 } })
function setup(api = {}) {
  const user = vue.reactive({ userId: 1, roleId: 1, token: 'fixture-a', selected_environment: 0 }), route = vue.reactive({ fullPath: '/pytest/case/index' })
  const writes = [], messages = [], life = { mount: [], unmount: [], activate: [], deactivate: [] }
  const oldDocument = globalThis.document, doc = Object.assign(new EventTarget(), { hidden: false }), listeners = new Set()
  const add = doc.addEventListener.bind(doc), remove = doc.removeEventListener.bind(doc)
  doc.addEventListener = (type, fn) => { listeners.add(fn); add(type, fn) }; doc.removeEventListener = (type, fn) => { listeners.delete(fn); remove(type, fn) }
  globalThis.document = doc
  const write = (domain, id) => { writes.push([domain, id]); return api.write ? api.write(domain, id) : Promise.resolve({ code: 200 }) }
  const h = harness('review', 'visible,loading,publishing,rows,selectedIds,acknowledged,configurationDrawerRef,detailVisible,detailCaseId,open,reload,closeDialog:close,invalidate,publishSelected,selectRows,openConfiguration,openCaseDetail', {
    filename: path.resolve('src/components/business/CasePublicationReviewModal.vue'), modules: {
      vue: { ...vue, onMounted: fn => life.mount.push(fn), onBeforeUnmount: fn => life.unmount.push(fn), onActivated: fn => life.activate.push(fn), onDeactivated: fn => life.deactivate.push(fn) },
      'vue-router': { useRoute: () => route }, '@/store/modules/user': { default: () => user },
      '@/api/http': { get: query => api.read ? api.read(query.data().case_id) : Promise.resolve(response(query.data().case_id)) },
      '@/api/apitest/case-version': { approveApiCasePrepublication: id => write('api', id) },
      '@/api/uitest/case': { putUiCasePublication: id => write('ui', id) }, '@/api/pytest/case': { putPytestCasePublication: id => write('pytest', id) },
      '@arco-design/web-vue': { Message: { success: value => messages.push(value) } },
    },
  })
  return { ...h, user, route, writes, messages, listeners,
    mount() { life.mount.forEach(fn => fn()) }, pause() { life.deactivate.forEach(fn => fn()) }, resume() { life.activate.forEach(fn => fn()) },
    hide() { doc.hidden = true; doc.dispatchEvent(new Event('visibilitychange')) }, show() { doc.hidden = false; doc.dispatchEvent(new Event('visibilitychange')) },
    close() { life.unmount.forEach(fn => fn()); h.close(); globalThis.document = oldDocument },
  }
}

test('actual review SFC ignores late summaries after synchronous identity/route A-B-A invalidation', async () => {
  for (const key of ['userId', 'roleId', 'token', 'selected_environment', 'fullPath']) {
    const pending = deferred(), h = setup({ read: () => pending.promise }), task = h.open('pytest', [1])
    const owner = key === 'fullPath' ? h.route : h.user, old = owner[key]
    owner[key] = typeof old === 'number' ? old + 1 : old + '-b'; owner[key] = old
    pending.resolve(response(1)); await task
    assert.equal(h.visible.value, false); assert.deepEqual(h.rows.value, []); assert.equal(h.loading.value, false); h.close()
  }
})

test('active publication keeps its physical lock while invalidation stops the queue in every domain', async () => {
  for (const domain of ['api', 'ui', 'pytest']) {
    const pending = deferred(), h = setup({ write: () => pending.promise }); await h.open(domain, [1, 2])
    h.selectRows([1, 2]); h.acknowledged.value = true; const task = h.publishSelected()
    assert.equal(h.publishing.value, true); h.user.roleId = 2; assert.equal(h.visible.value, false)
    await h.open(domain, [3]); assert.equal(h.visible.value, false); assert.equal(h.publishing.value, true)
    pending.resolve({ code: 200 }); await task; assert.deepEqual(h.writes, [[domain, 1]]); assert.deepEqual(h.events, []); assert.deepEqual(h.messages, [])
    assert.equal(h.publishing.value, false); await h.open(domain, [3]); assert.equal(h.visible.value, true); h.close()
  }
})

test('context invalidation closes nested details and configuration snapshots', async () => {
  const h = setup(); await h.open('pytest', [1]); let closed = 0
  h.configurationDrawerRef.value = { close: () => closed++ }; h.detailVisible.value = true; h.detailCaseId.value = 1
  h.invalidate(); assert.equal(closed, 1); assert.equal(h.detailVisible.value, false); assert.equal(h.detailCaseId.value, null); assert.deepEqual(h.selectedIds.value, [])
  h.close()
})

test('background/KeepAlive/unmount close review, reject inactive opens and clean up listeners', async () => {
  const h = setup(); h.mount(); await h.open('pytest', [1]); h.hide(); assert.equal(h.visible.value, false)
  await h.open('pytest', [1]); assert.equal(h.visible.value, false); h.show(); await h.open('pytest', [1]); assert.equal(h.visible.value, true)
  h.pause(); assert.equal(h.visible.value, false); await h.open('pytest', [1]); assert.equal(h.visible.value, false)
  h.resume(); await h.open('pytest', [1]); h.close(); assert.equal(h.visible.value, false); assert.equal(h.listeners.size, 0)
  await h.open('pytest', [1]); assert.equal(h.visible.value, false)
})

test('actual review SFC rejects malformed summaries and never spreads extra server state', async () => {
  const h = setup({ read: async id => id === 2 ? { code: 200, data: { id, eligibility_reasons: [] } } : { ...response(id), data: { ...response(id).data, extra: 'ignored' } } })
  await h.open('pytest', [1, 2])
  assert.equal(h.rows.value[0].extra, undefined)
  assert.equal(h.rows.value[0].sql_count, 0)
  assert.match(h.rows.value[1].error, /加载失败/)
  h.openCaseDetail(2)
  assert.equal(h.detailVisible.value, false)
  h.openCaseDetail(1)
  assert.equal(h.detailCaseId.value, 1)
  h.close()
})

test('actual UI/Pytest approval failures cannot mark success on malformed HTTP envelopes', async () => {
  for (const domain of ['ui', 'pytest']) {
    const h = setup({ write: async () => ({ code: 500 }) })
    await h.open(domain, [1])
    h.selectRows([1]); h.acknowledged.value = true
    await h.publishSelected()
    assert.equal(h.rows.value[0].published, undefined)
    assert.match(h.rows.value[0].error, /发布失败/)
    assert.equal(h.publishing.value, false)
    assert.deepEqual(h.events, [])
    h.close()
  }
})
