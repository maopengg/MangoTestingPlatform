import { loadFeedbackModule } from '../../helpers/load-feedback-modules.mjs'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import ts from 'typescript'
import { parse } from '@vue/compiler-sfc'
import * as vue from 'vue'
import * as vueRouter from 'vue-router'

const routeSource = fs.readFileSync(new URL('../../../src/router/index.ts', import.meta.url), 'utf8')
const routeAst = ts.createSourceFile('index.ts', routeSource, ts.ScriptTarget.Latest, true)
const declaration = routeAst.statements.find((statement) =>
  ts.isVariableStatement(statement) && statement.declarationList.declarations.some(
    (item) => item.name.getText(routeAst) === 'extraRoutes'
  )
)
const routeExports = {}
const emptyPage = { render: () => null }
new Function('exports', 'Layout', ts.transpileModule(declaration.getText(routeAst), {
  compilerOptions: { module: ts.ModuleKind.CommonJS },
}).outputText)(routeExports, emptyPage)

const breadcrumbSource = fs.readFileSync(
  new URL('../../../src/layouts/breadcrumb/index.vue', import.meta.url), 'utf8'
)
const { descriptor } = parse(breadcrumbSource)
const breadcrumbExports = {}
new Function('exports', 'require', ts.transpileModule(descriptor.script.content, {
  compilerOptions: { module: ts.ModuleKind.CommonJS },
}).outputText)(breadcrumbExports, (name) => {
  if (name === 'vue') return vue
  if (name === 'vue-router') return vueRouter
  { if (['@/utils/load-error', '@/utils/api-response'].includes(name)) return loadFeedbackModule(name); throw new Error(`Unexpected dependency: ${name}`) }
})

const renderer = vue.createRenderer({
  createElement: (tag) => ({ tag, children: [] }),
  createText: (text) => ({ text }),
  createComment: (text) => ({ text }),
  insert(node, parent) { parent.children.push(node) },
  remove() {},
  setText(node, text) { node.text = text },
  setElementText(node, text) { node.text = text },
  parentNode: () => null,
  nextSibling: () => null,
  patchProp() {},
})

function routeRecords(routes, parent = '/') {
  return routes.map((route) => ({
    ...route,
    path: path.posix.resolve(parent, route.path),
    component: emptyPage,
    children: route.children ? routeRecords(route.children, path.posix.resolve(parent, route.path)) : [],
  }))
}

const affectedRoutes = [
  ['/apitest/case/details', '/apitest/case/index', '测试用例'],
  ['/uitest/case/details', '/uitest/case/index', '测试用例'],
  ['/apitest/info/details', '/apitest/info/index', '服务调用'],
  ['/uitest/page/elements', '/uitest/page/index', '页面元素'],
  ['/uitest/page/steps/details', '/uitest/page-steps/index', '页面步骤'],
  ['/timing/case', '/timing/tasks/index', '定时任务'],
  ['/data-factory/template/preview', '/data-factory/template/index', '场景模板'],
  ['/config/product/module', '/config/product/index', '产品配置'],
  ['/config/product/datasource', '/config/product/index', '产品配置'],
  ['/config/project/notice', '/config/project/index', '项目配置'],
]

for (const [detailPath, listPath, label] of affectedRoutes) {
  test(`${detailPath}: clicking the list breadcrumb returns to ${listPath}, not 404`, async () => {
    // Menu-driven list routes are registered separately from the static detail routes.
    const router = vueRouter.createRouter({
      history: vueRouter.createMemoryHistory(),
      routes: [
        ...routeRecords(routeExports.extraRoutes),
        { path: listPath, component: emptyPage, meta: { title: label } },
        { path: '/404', component: emptyPage },
        { path: '/:pathMatch(.*)*', redirect: '/404' },
      ],
    })
    await router.push({ path: detailPath, query: { id: '4428' } })
    await router.isReady()
    const app = renderer.createApp({ ...breadcrumbExports.default, render: () => null })
    app.use(router)
    const instance = app.mount({ children: [] })
    try {
      const link = instance.breadcrumbs.find((item) => item.path && item.label === label)
      assert.ok(link, `Missing ${label} breadcrumb`)
      assert.equal(instance.breadcrumbs.at(-1).path, undefined)
      assert.equal(link.path, listPath)
      instance.handleSelect(link.path)
      await new Promise((resolve) => setImmediate(resolve))
      await vue.nextTick()
      assert.equal(router.currentRoute.value.path, listPath)
      assert.notEqual(router.currentRoute.value.path, '/404')
      assert.deepEqual(router.currentRoute.value.query, {})
    } finally {
      app.unmount()
    }
  })
}

test('list destinations match the backend menu and existing frontend page entries', () => {
  const menuSource = fs.readFileSync(
    new URL('../../../../MangoServer/src/apps/system/services/menu.py', import.meta.url), 'utf8'
  )
  for (const listPath of new Set(affectedRoutes.map((item) => item[1]))) {
    assert.ok(menuSource.includes(`leaf("${listPath}",`), `Missing menu route: ${listPath}`)
    assert.ok(fs.existsSync(new URL(`../../../src/views${listPath}.vue`, import.meta.url)), listPath)
  }
})
