import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import {
  createRenderer,
  defineComponent,
  effectScope,
  h,
  nextTick,
  onMounted,
  reactive,
  ref,
  watch,
} from 'vue'
import { createMemoryHistory, createRouter, RouterView, useRoute } from 'vue-router'

const exports = {}
const code = fs.readFileSync(new URL('../../../../src/router/view-key.ts', import.meta.url), 'utf8')
new Function(
  'exports',
  ts.transpileModule(code, {
    compilerOptions: { module: ts.ModuleKind.CommonJS },
  }).outputText
)(exports)
const { getRouteViewKey } = exports

// Use Vue's renderer and memory history without launching a browser.
const renderer = createRenderer({
  createElement: (tag) => ({ tag, children: [] }),
  createText: (text) => ({ text }),
  createComment: (text) => ({ text }),
  insert(node, parent, anchor) {
    if (node.parent) this.remove(node)
    node.parent = parent
    const index = anchor ? parent.children.indexOf(anchor) : -1
    if (index < 0) parent.children.push(node)
    else parent.children.splice(index, 0, node)
  },
  remove(node) {
    const parent = node.parent
    if (parent) parent.children.splice(parent.children.indexOf(node), 1)
    node.parent = null
  },
  setText: (node, text) => {
    node.text = text
  },
  setElementText: (node, text) => {
    node.text = text
  },
  parentNode: (node) => node.parent,
  nextSibling: (node) => node.parent?.children[node.parent.children.indexOf(node) + 1] || null,
  patchProp() {},
})

test('connection query changes reuse the page and do not reload the connection list', async () => {
  let connectionListRequests = 0
  const page = defineComponent({
    setup() {
      const route = useRoute()
      onMounted(() => {
        connectionListRequests++
      })
      return () => h('span', String(route.query.data_source_id || ''))
    },
  })
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/config/data-source/index', component: page, meta: { reuseOnQueryChange: true } },
      { path: '/other', component: page },
    ],
  })
  const app = renderer.createApp({
    render: () =>
      h(RouterView, null, {
        default: ({ Component, route }) => h(Component, { key: getRouteViewKey(route) }),
      }),
  })
  app.use(router)
  await router.push('/config/data-source/index?data_source_id=1')
  await router.isReady()
  const root = { children: [] }
  app.mount(root)
  try {
    assert.equal(connectionListRequests, 1)
    await router.replace('/config/data-source/index?data_source_id=2')
    await nextTick()
    assert.equal(connectionListRequests, 1)
    assert.equal(root.children[0].text, '2')
    await router.push('/other?id=1')
    await nextTick()
    assert.equal(connectionListRequests, 2)
    await router.replace('/other?id=2')
    await nextTick()
    assert.equal(connectionListRequests, 3)
  } finally {
    app.unmount()
  }
})

test('route reuse is explicitly enabled for the data source workbench', () => {
  const main = fs.readFileSync(new URL('../../../../src/layouts/Main.vue', import.meta.url), 'utf8')
  const routes = fs.readFileSync(
    new URL('../../../../src/router/index.ts', import.meta.url),
    'utf8'
  )
  assert.match(main, /:key="getRouteViewKey\(route\)"/)
  assert.match(
    routes,
    /path: 'data-source\/index',[\s\S]*?permissionKey: 'config.datasource',\s*reuseOnQueryChange: true/
  )
})

test('URL connection changes update the reused workbench selection', async () => {
  const source = fs.readFileSync(
    new URL(
      '../../../../src/views/config/data-source/components/DataSourceWorkbench.vue',
      import.meta.url
    ),
    'utf8'
  )
  const start = source.indexOf('  watch(\n    () => route.query.data_source_id,')
  assert.ok(start >= 0)
  const end = source.indexOf('  watch(\n    () => selected.value', start)
  const js = ts.transpileModule(source.slice(start, end), {}).outputText
  const route = reactive({ query: { data_source_id: '1' } })
  const selectedId = ref(1)
  const scope = effectScope()
  scope.run(() =>
    new Function('watch', 'route', 'props', 'selectedId', 'firstSourceId', js)(
      watch,
      route,
      { sources: [{ id: 1 }, { id: 2 }] },
      selectedId,
      ref(1)
    )
  )
  try {
    route.query.data_source_id = '2'
    await nextTick()
    assert.equal(selectedId.value, 2)
    route.query.data_source_id = 'unknown'
    await nextTick()
    assert.equal(selectedId.value, 1)
    route.query.data_source_id = '1'
    await nextTick()
    assert.equal(selectedId.value, 1)
  } finally {
    scope.stop()
  }
})
