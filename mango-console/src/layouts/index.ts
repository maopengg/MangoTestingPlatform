import '../styles/transition.css'
import { App, defineComponent, h } from 'vue'
import { TinyEmitter } from 'tiny-emitter'

import { toHump } from '../utils'
import components from '../components'

import ArcoVueIcon from '@arco-design/web-vue/es/icon'
import ArcoVue from '@arco-design/web-vue/es/arco-vue'
import ArcoTable from '@arco-design/web-vue/es/table'
import ArcoTableColumn from '@arco-design/web-vue/es/table/table-column'
import ArcoModal from '@arco-design/web-vue/es/modal'
import ArcoDrawer from '@arco-design/web-vue/es/drawer'
import ArcoAvatar from '@arco-design/web-vue/es/avatar'
import ArcoTreeSelect from '@arco-design/web-vue/es/tree-select'
import { scaleDensityLength } from '@/hooks/useDisplayDensity'

function getComponentName(key: string) {
  if (!key) {
    return ''
  }
  const paths = key.split('/')
  const name = paths
    .filter((it) => !!it && it !== '.')
    .reverse()
    .find(
      (it) =>
        it !== 'index.vue' &&
        it !== 'index.ts' &&
        it !== 'index.js' &&
        it !== 'index.jsx' &&
        it !== 'index.tsx'
    )
    ?.replace('.vue', '')
    ?.replace('.tsx', '')
  return name || ''
}

export function registerComponents(app: App) {
  const components = import.meta.glob('./**/**.{vue,tsx}', { eager: true })
  Object.keys({ ...components }).forEach((it: string) => {
    const component = components[it]
    app.component(
      (component as any).default.name || toHump(getComponentName(it)),
      (component as any).default
    )
  })
}

export const emitKey = Symbol('tiny-emit')

function setupArcoTableDefaults() {
  const tableProps = (ArcoTable as any)?.props
  if (tableProps?.columnResizable) {
    tableProps.columnResizable.default = true
  }
  if (tableProps?.scrollbar) {
    tableProps.scrollbar.default = () => ({ type: 'embed' })
  }
}

function scaleTableColumns(columns: unknown): unknown {
  if (!Array.isArray(columns)) return columns
  return columns.map((column) => ({
    ...column,
    width: scaleDensityLength(column.width),
    children: scaleTableColumns(column.children),
  }))
}

function scaleTableScroll(scroll: unknown) {
  if (!scroll || typeof scroll !== 'object' || Array.isArray(scroll)) return scroll
  const value = scroll as Record<string, unknown>
  return {
    ...value,
    x: scaleDensityLength(value.x),
    y: scaleDensityLength(value.y),
  }
}

const DensityTable = defineComponent({
  name: 'MangoDensityTable',
  inheritAttrs: false,
  setup(_props, { attrs, slots }) {
    return () =>
      h(
        ArcoTable as any,
        {
          ...attrs,
          columns: scaleTableColumns(attrs.columns),
          scroll: scaleTableScroll(attrs.scroll),
        },
        slots
      )
  },
})

const DensityTableColumn = defineComponent({
  name: 'MangoDensityTableColumn',
  inheritAttrs: false,
  setup(_props, { attrs, slots }) {
    return () =>
      h(
        ArcoTableColumn as any,
        {
          ...attrs,
          width: scaleDensityLength(attrs.width),
        },
        slots
      )
  },
})

function createDensityOverlay(name: string, component: any) {
  return defineComponent({
    name,
    inheritAttrs: false,
    setup(_props, { attrs, slots }) {
      return () =>
        h(
          component,
          {
            ...attrs,
            width: scaleDensityLength(attrs.width),
          },
          slots
        )
    },
  })
}

const DensityModal = createDensityOverlay('MangoDensityModal', ArcoModal)
const DensityDrawer = createDensityOverlay('MangoDensityDrawer', ArcoDrawer)

const DensityAvatar = defineComponent({
  name: 'MangoDensityAvatar',
  inheritAttrs: false,
  setup(_props, { attrs, slots }) {
    return () =>
      h(
        ArcoAvatar as any,
        {
          ...attrs,
          size: scaleDensityLength(attrs.size),
        },
        slots
      )
  },
})

function install(app: App) {
  setupArcoTableDefaults()
  // 预构建循环依赖可能让批量 install 捕获未初始化的 TreeSelect；从已就绪的公开导出注册。
  const arcoPlugins = new Set(
    Object.values(ArcoVue).filter(
      (component) =>
        component &&
        typeof component === 'object' &&
        'install' in component &&
        typeof component.install === 'function'
    )
  )
  for (const plugin of arcoPlugins) app.use(plugin as any)
  app.use(ArcoVueIcon)
  app.use(ArcoTreeSelect)
  // 精确使用模板标签名覆盖表格入口，让 JS 数字宽度与全局 rem 密度保持同一比例。
  app.component('a-table', DensityTable)
  app.component('a-table-column', DensityTableColumn)
  app.component('a-modal', DensityModal)
  app.component('a-drawer', DensityDrawer)
  app.component('a-avatar', DensityAvatar)
  registerComponents(app)
  app.use(components, { getComponentName })
  app.provide(emitKey, new TinyEmitter())
}

export function setupGlobalComponent(app: App) {
  install(app)
}
