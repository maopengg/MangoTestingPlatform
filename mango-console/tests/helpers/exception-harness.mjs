import { loadFeedbackModule } from './load-feedback-modules.mjs'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import ts from 'typescript'
import * as Vue from 'vue'
import * as VueRouter from 'vue-router'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'

const base = path.resolve('src')
const read = file => readFileSync(path.join(base, file), 'utf8')
const run = (source, resolve) => {
  const module = { exports: {} }
  new Function('module', 'exports', 'require', ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
  }).outputText)(module, module.exports, resolve)
  return module.exports
}
export const settleException = async () => {
  await new Promise(resolve => setImmediate(resolve))
  await Vue.nextTick()
}

export async function mountException(options = {}) {
  const status = options.status || '404'
  const hashes = [], refreshes = [], enumReads = [], warnings = []
  const originalWindow = globalThis.window
  globalThis.window = { location: { origin: 'https://example.org', pathname: '/console/', search: '', hash: `#/${status}`,
    replace: value => hashes.push(value) } }
  const user = Vue.reactive({ userId: 1, roleId: 2, token: 'fixture', selected_environment: 3,
    isTokenExpire: () => !!options.expired })
  const permission = {
    homePath: options.homePath ?? '/index/home', isEmptyPermissionRoute: () => false,
    async initPermissionRoute(force) {
      refreshes.push(force)
      await options.wait?.promise
      if (typeof options.fail === 'function' ? options.fail() : options.fail) throw Error('fixture network failure')
    },
  }
  const emptyPage = { render: () => Vue.h('home') }
  const constants = run(read('router/routes/constants.ts'), name => {
    assert.equal(name, '@/store/keys')
    return { LAYOUT: emptyPage }
  })
  const entry = constants.constantRoutes.find(route => route.path === `/${status}`)
  assert.equal(entry.name, status)
  assert.equal(entry.meta.hidden, true)
  assert.equal(entry.meta.permissionKey, undefined)
  assert.match(String(entry.component), new RegExp(`views/exception/${status}.vue`))
  const cache = new Map()
  function loadComponent(file) {
    if (cache.has(file)) return cache.get(file)
    const { descriptor } = parse(read(file), { filename: file })
    const script = compileScript(descriptor, { id: file })
    const resolve = name => {
      if (name === 'vue') return Vue
      if (name === 'vue-router') return VueRouter
      if (name === '@/store/modules/user') return { default: () => user }
      if (name === '@/store/modules/permission') return { default: () => permission }
      if (name.endsWith('.png')) return { default: name }
      if (name.endsWith('.vue')) return { default: loadComponent(path.join(path.dirname(file), name)) }
      { if (['@/utils/load-error', '@/utils/api-response'].includes(name)) return loadFeedbackModule(name); throw Error(`Unexpected dependency ${name}`) }
    }
    const component = run(script.content, resolve).default
    component.render = run(compileTemplate({ source: descriptor.template.content, filename: file, id: file,
      compilerOptions: { bindingMetadata: script.bindings } }).code, resolve).render
    cache.set(file, component)
    return component
  }
  const page = loadComponent(`views/exception/${status}.vue`)
  const router = VueRouter.createRouter({ history: VueRouter.createMemoryHistory(), routes: [
    { ...entry, component: page }, { path: '/index/home', component: emptyPage },
  ] })
  // Read the actual dynamic-route action so the fallback registration is not duplicated in the test.
  const tree = ts.createSourceFile('permission.ts', read('store/modules/permission.ts'), ts.ScriptTarget.Latest, true)
  let initRoute
  function visit(node) {
    if (ts.isMethodDeclaration(node) && node.name.getText(tree) === 'initPermissionRoute') initRoute = node
    ts.forEachChild(node, visit)
  }
  visit(tree)
  assert.ok(initRoute)
  const action = new Function('router', 'mapTwoLevelRouter', 'findRootPathRoute', 'constantRoutes',
    ts.transpileModule(`let removePermissionRoutes = []; const actions = { ${initRoute.getText(tree)} }; return actions.initPermissionRoute`, {
      compilerOptions: { target: ts.ScriptTarget.ES2020 },
    }).outputText)(router, routes => routes, () => '/index/home', constants.constantRoutes)
  await action.call({ getRoutes: async () => [], homePath: '', permissionRoutes: [] }, true)
  run(read('router/guard/permission.ts'), name => {
    const deps = {
      '@/store/modules/user': { default: () => user },
      '@/store/modules/permission': { default: () => permission },
      '@/store/modules/get-enum': { useEnum: () => ({ getEnum: async () => { enumReads.push(true) } }) },
      '..': { default: router }, '@/utils/socket': { connectWebSocket: () => assert.fail('Unexpected socket') },
    }
    assert.ok(name in deps, name)
    return deps[name]
  }).default()
  await router.push(options.path || `/${status}`)
  await router.isReady()
  const renderer = Vue.createRenderer({
    createElement: tag => ({ tag, children: [], props: {} }), createText: text => ({ text }), createComment: text => ({ text }),
    insert(node, parent, anchor) {
      if (node.parent) node.parent.children.splice(node.parent.children.indexOf(node), 1)
      const index = anchor ? parent.children.indexOf(anchor) : -1
      parent.children.splice(index < 0 ? parent.children.length : index, 0, node); node.parent = parent
    },
    remove(node) { if (node.parent) node.parent.children.splice(node.parent.children.indexOf(node), 1) },
    parentNode: node => node.parent, nextSibling: node => node.parent?.children[node.parent.children.indexOf(node) + 1],
    setText(node, text) { node.text = text }, setElementText(node, text) { node.text = text },
    patchProp(node, key, _previous, value) { node.props[key] = value },
  })
  const root = { children: [] }
  const app = renderer.createApp({ render: () => options.keepAlive
    ? Vue.h(VueRouter.RouterView, {}, { default: ({ Component }) => Vue.h(Vue.KeepAlive, null, { default: () => Component }) })
    : Vue.h(VueRouter.RouterView) })
  app.config.warnHandler = message => warnings.push(message)
  app.component('a-button', { props: { loading: Boolean }, setup(props, { attrs, slots }) {
    return () => Vue.h('button', { ...attrs, loading: props.loading }, slots.default?.())
  } })
  app.use(router); app.mount(root)
  const nodes = (tag, node = root) => [ ...(node.tag === tag ? [node] : []), ...(node.children || []).flatMap(child => nodes(tag, child)) ]
  return { router, root, nodes, hashes, refreshes, enumReads, warnings, user,
    dispose() { app.unmount(); globalThis.window = originalWindow } }
}

