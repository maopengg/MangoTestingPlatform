import assert from 'node:assert/strict'
import path from 'node:path'
import test from 'node:test'
import * as vue from 'vue'
import { harness, deferred, flush as microtasks } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/report/effectiveness')
async function flush() { await microtasks(); await new Promise(resolve => setImmediate(resolve)); await microtasks() }
function chart(settings = {}) {
  const previous = { window: globalThis.window, document: globalThis.document, ResizeObserver: globalThis.ResizeObserver, getComputedStyle: globalThis.getComputedStyle }
  const win = new EventTarget(), doc = Object.assign(new EventTarget(), { visibilityState: 'visible' })
  const listeners = new Set(), life = { mount: [], unmount: [], activate: [], deactivate: [] }, charts = [], observers = [], ticks = []
  for (const [target, prefix] of [[win, 'window'], [doc, 'document']]) {
    const add = target.addEventListener.bind(target), remove = target.removeEventListener.bind(target)
    target.addEventListener = (event, callback) => { listeners.add(`${prefix}:${event}`); add(event, callback) }
    target.removeEventListener = (event, callback) => { listeners.delete(`${prefix}:${event}`); remove(event, callback) }
  }
  globalThis.window = win; globalThis.document = doc
  let token = 'theme-a', fail = settings.fail ?? false
  globalThis.getComputedStyle = () => ({ getPropertyValue: () => token })
  class Observer {
    constructor(callback) { this.callback = callback; this.nodes = new Set(); observers.push(this) }
    observe(node) { this.nodes.add(node) }
    disconnect() { this.nodes.clear() }
  }
  globalThis.ResizeObserver = settings.withoutObserver ? undefined : Observer
  const density = vue.ref(1), route = vue.reactive({ path: '/report/effectiveness/index' })
  const useEcharts = node => {
    let instance = charts.find(item => item.node === node && !item.disposed)
    if (instance) return instance
    instance = { node, disposed: false, clears: 0, sizes: 0, options: [], handlers: new Map(),
      clear() { this.clears++ }, resize() { this.sizes++ },
      setOption(option) { if (fail) throw new Error('render failed'); this.options.push(option) },
      on(event, handler) { this.handlers.set(event, handler) }, off(event, handler) { if (this.handlers.get(event) === handler) this.handlers.delete(event) },
      isDisposed() { return this.disposed }, dispose() { this.disposed = true; this.disposals = (this.disposals || 0) + 1 },
    }
    charts.push(instance); return instance
  }
  const h = harness('EffectivenessChart', 'chartRef,chartHeight,rendering,renderError,scheduleRender,resizeChart', {
    base, filename: path.join(base, 'components/EffectivenessChart.vue'), props: { option: { color: ['var(--m-success)'], series: [] } },
    modules: {
      vue: { ...vue, nextTick: settings.deferTicks ? () => { const tick = deferred(); ticks.push(tick); return tick.promise } : vue.nextTick,
        onMounted: fn => life.mount.push(fn), onBeforeUnmount: fn => life.unmount.push(fn), onActivated: fn => life.activate.push(fn), onDeactivated: fn => life.deactivate.push(fn) },
      'vue-router': { useRoute: () => route }, '@/hooks/useEcharts': { default: useEcharts },
      '@/hooks/useDisplayDensity': { scaleDensityLength: value => value.replace(/([\d.]+)px/g, (_, raw) => `${Number(raw) * density.value}px`) },
    },
  })
  h.chartRef.value = vue.markRaw({ id: 'chart-node' })
  return { ...h, life, charts, observers, listeners, doc, win, density, route, ticks,
    mount() { life.mount.forEach(fn => fn()); life.activate.forEach(fn => fn()) },
    setToken(value) { token = value }, setFail(value) { fail = value },
    async settleTicks() { await flush(); while (ticks.length) { ticks.splice(0).forEach(tick => tick.resolve()); await flush() } },
    close() { life.unmount.forEach(fn => fn()); h.close(); Object.assign(globalThis, previous) },
  }
}

test('图表实例由组件拥有，重复更新复用且只保留一次点击绑定，卸载完整清理', async t => {
  const h = chart(); t.after(h.close); h.mount(); await flush()
  assert.equal(h.charts.length, 1); assert.equal(h.charts[0].options[0].color[0], 'theme-a')
  assert.equal(h.rendering.value, false); assert.equal(h.charts[0].handlers.size, 1)
  h.props.option = { series: [{ data: [0, 1] }] }; await flush()
  assert.equal(h.charts.length, 1); assert.equal(h.charts[0].handlers.size, 1)
  h.charts[0].handlers.get('click')({ dataIndex: 0 }); assert.equal(h.events.length, 1)
  h.life.unmount.forEach(fn => fn())
  assert.equal(h.charts[0].disposals, 1); assert.equal(h.charts[0].handlers.size, 0); assert.equal(h.listeners.size, 0)
  assert.equal(h.observers[0].nodes.size, 0)
})

test('卸载后迟到 nextTick 不重新创建图表，连点重试只渲染最后一代配置', async t => {
  const h = chart({ deferTicks: true }); t.after(h.close); h.mount(); await flush()
  h.props.option = { title: { text: 'latest' } }; const pending = h.scheduleRender(); await h.settleTicks(); await pending
  assert.equal(h.charts.length, 1); assert.equal(h.charts[0].options.length, 1); assert.equal(h.charts[0].options[0].title.text, 'latest')
  const old = h.scheduleRender(); h.life.unmount.forEach(fn => fn()); await h.settleTicks(); await old
  assert.equal(h.charts.length, 1); assert.equal(h.charts[0].options.length, 1)
})

test('后台与 KeepAlive 暂停释放实例，恢复使用最新配置，旧点击事件不会作用新页面', async t => {
  const h = chart(); t.after(h.close); h.mount(); await flush()
  const old = h.charts[0], click = old.handlers.get('click')
  h.doc.visibilityState = 'hidden'; h.doc.dispatchEvent(new Event('visibilitychange'))
  assert.equal(old.disposed, true); assert.equal(h.observers[0].nodes.size, 0)
  h.props.option = { title: { text: 'background-update' } }; await flush(); h.resizeChart(); assert.equal(h.charts.length, 1)
  h.doc.visibilityState = 'visible'; h.doc.dispatchEvent(new Event('visibilitychange')); await flush()
  assert.equal(h.charts.length, 2); assert.equal(h.charts[1].options[0].title.text, 'background-update')
  click({ dataIndex: 0 }); assert.equal(h.events.length, 0)
  h.life.deactivate.forEach(fn => fn()); assert.equal(h.charts[1].disposed, true)
  await h.scheduleRender(); assert.equal(h.charts.length, 2)
  h.life.activate.forEach(fn => fn()); await flush(); assert.equal(h.charts.length, 3)
})

test('路由切换、DOM换目标和迟到观察者不创建无主实例', async t => {
  const h = chart(); t.after(h.close); h.mount(); await flush(); const old = h.charts[0]
  h.route.path = '/report/index'; h.observers[0].callback(); await flush(); assert.equal(old.disposed, true); assert.equal(h.charts.length, 1)
  h.route.path = '/report/effectiveness/index'; await flush(); assert.equal(h.charts.length, 2)
  h.chartRef.value = vue.markRaw({ id: 'replacement' }); await flush()
  assert.equal(h.charts[1].disposed, true); assert.equal(h.charts.length, 3); assert.equal(h.charts[2].node.id, 'replacement')
  h.life.unmount.forEach(fn => fn()); h.observers[0].callback(); await flush(); assert.equal(h.charts.length, 3)
})

test('主题与全局密度变化重解 token 和高度，不改变数据坐标或回调', async t => {
  const h = chart(); t.after(h.close); const formatter = () => 'example'
  h.props.option = { color: ['var(--m-success)'], series: [{ data: [0, 100] }], tooltip: { formatter } }
  h.mount(); await flush(); assert.equal(h.chartHeight.value, '280px')
  h.setToken('theme-b'); h.win.dispatchEvent(new Event('mango-theme-change')); await flush()
  assert.equal(h.charts[0].options.at(-1).color[0], 'theme-b')
  h.density.value = 1.35; h.win.dispatchEvent(new Event('mango-density-change')); await flush()
  assert.equal(h.chartHeight.value, '378px'); assert.deepEqual(h.charts[0].options.at(-1).series[0].data, [0, 100])
  assert.equal(h.charts[0].options.at(-1).tooltip.formatter, formatter)
})

test('渲染失败局部错误可重试，父级加载期间不绘制和发点击', async t => {
  const h = chart({ fail: true }); t.after(h.close); h.mount(); await flush()
  assert.ok(h.renderError.value); assert.equal(h.rendering.value, false)
  h.setFail(false); await h.scheduleRender(); assert.equal(h.renderError.value, ''); assert.equal(h.charts.length, 1)
  const click = h.charts[0].handlers.get('click'), before = h.charts[0].options.length
  h.props.loading = true; await flush(); click({ dataIndex: 0 }); assert.equal(h.events.length, 0); assert.equal(h.charts[0].options.length, before)
  h.props.loading = false; await flush(); assert.equal(h.charts[0].options.length, before + 1)
})

test('无 ResizeObserver 时保留窗口 resize，循环/非法 option 不导致未捕获异常', async t => {
  const h = chart({ withoutObserver: true }); t.after(h.close); h.mount(); await flush()
  h.win.dispatchEvent(new Event('resize')); assert.ok(h.charts[0].sizes > 1)
  const cyclic = {}; cyclic.self = cyclic; h.props.option = cyclic; await flush(); assert.ok(h.renderError.value); assert.equal(h.rendering.value, false)
  h.props.option = null; await flush(); assert.ok(h.renderError.value)
  h.props.option = { series: [] }; await flush(); assert.equal(h.renderError.value, '')
})

test('token解析不修改原配置，未知回调边界与HTML文案不透传对象', () => {
  const h = harness('PeriodQualityTrend', 'normalizedItems', { base, filename: path.join(base, 'components/PeriodQualityTrend.vue') })
  try {
    const boundary = h.load('chart-boundary.ts'), formatter = () => 0, source = { series: [{ data: [0], itemStyle: { color: 'var(--m-success)' } }], formatter }
    const result = boundary.resolveChartOption(source, () => 'resolved')
    assert.equal(result.series[0].itemStyle.color, 'resolved'); assert.equal(source.series[0].itemStyle.color, 'var(--m-success)'); assert.equal(result.formatter, formatter)
    assert.equal(boundary.chartHtml('<img src="example"/>'), '&lt;img src=&quot;example&quot;/&gt;')
    assert.equal(boundary.chartHtml({}), '-'); assert.equal(boundary.chartPoint(null), null); assert.deepEqual(boundary.chartPoints([null, false]), [])
    assert.equal(boundary.chartPoint({ dataIndex: 0, value: 0 }).dataIndex, 0)
  } finally { h.close() }
})

function period(items) { return harness('PeriodQualityTrend', 'sourceItems,normalizedItems,periodDays,currentRateText,currentStatusTotal,passRateDelta,deltaText,chartOption,onChartClick', { base, filename: path.join(base, 'components/PeriodQualityTrend.vue'), props: { items } }) }

test('周期输入采用有限类型，null/NaN/错误数组不变为通过率0，日期不产生NaN', t => {
  const h = period([null, { key: 'current', start: '2026-02-30', end: 'invalid', final_pass_rate: NaN, success_count: false }]); t.after(h.close)
  assert.equal(h.periodDays.value, 0); assert.equal(h.currentRateText.value, '-'); assert.equal(h.currentStatusTotal.value, 0)
  assert.equal(h.passRateDelta.value, null); assert.doesNotMatch(h.deltaText.value, /NaN/)
  h.props.items = {}; assert.equal(h.normalizedItems.value.length, 0)
})

test('周期保留0值与原状态系列，环比正确；非法点击不回退首周期，loading不发事件', t => {
  const h = period([{ key: 'previous', start: '2026-01-01', end: '2026-01-07', final_pass_rate: 100, suite_count: 1 },
    { key: 'current', start: '2026-01-08', end: '2026-01-14', final_pass_rate: 0, success_count: 0, proceed_count: 1, suite_count: 1 }]); t.after(h.close)
  assert.equal(h.periodDays.value, 7); assert.equal(h.currentRateText.value, '0.00%'); assert.equal(h.passRateDelta.value, -100); assert.equal(h.currentStatusTotal.value, 1)
  assert.deepEqual(h.chartOption.value.series.map(item => item.name), ['通过', '已停止', '待开始', '进行中', '失败', '警告', '最终通过率'])
  for (const params of [undefined, null, {}, { dataIndex: false }, { dataIndex: '' }, { dataIndex: -1 }, { dataIndex: 0.5 }, { dataIndex: 100 }]) h.onChartClick(params)
  assert.equal(h.events.length, 0); h.onChartClick({ dataIndex: 0 }); assert.equal(h.events[0][1].key, 'previous')
  h.props.loading = true; h.onChartClick({ dataIndex: 1 }); assert.equal(h.events.length, 1)
})

test('周期 tooltip 无索引不选首项，文本转义，坏比例不显示NaN%', t => {
  const h = period([{ key: 'custom', label: '<script>example</script>', start: '2026-01-01', end: '2026-01-07', suite_count: 1, final_pass_rate: null }]); t.after(h.close)
  const format = h.chartOption.value.tooltip.formatter
  assert.equal(format(null), ''); assert.equal(format([]), ''); assert.equal(format([{ dataIndex: false }]), '')
  const tooltip = format([{ dataIndex: 0 }]); assert.match(tooltip, /&lt;script&gt;/); assert.doesNotMatch(tooltip, /<script>|NaN/)
})
