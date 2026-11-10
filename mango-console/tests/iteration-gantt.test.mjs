import assert from 'node:assert/strict'
import path from 'node:path'
import test from 'node:test'
import * as vue from 'vue'
import { readFileSync } from 'node:fs'
import { compileScript, compileStyle, compileTemplate, parse } from '@vue/compiler-sfc'
import { harness, flush } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/functional-test/iteration')
const item = values => ({ id: 'requirement-11', suite_id: 11, requirement_key: 'REQ-11', requirement_name: 'Example requirement', version_no: 1, status: 3, planned_start_date: '2026-11-01', planned_submit_date: '2026-11-03', time_progress: 50, overlap: false, overdue: false, overlap_with: [], ...values })
const data = values => ({ iteration: { id: 1, start_date: '2026-11-01', end_date: '2026-11-10' }, today: '2026-11-03', summary: {}, groups: [{ owner_id: 4, owner_name: 'Example developer', items: [item()] }], ...values })
function setup(props = {}) {
  const hooks = { mount: [], stop: [], activate: [], unmount: [] }, density = vue.ref(1)
  const f = harness('UserScheduleGantt', 'zoom,keyword,ownerFilter,statusFilter,groups,summary,ownerOptions,normalizedStatusOptions,scale,units,timelineWidth,gridStyle,trackStyle,todayOffset,barGeometry,barStyle,openItem,unscheduledText,leftRef,timelineRef,timelineGutter,syncVertical', {
    base, props: { data: data(), contextKey: 'A', ...props },
    modules: { vue: { ...vue, onMounted: fn => hooks.mount.push(fn), onDeactivated: fn => hooks.stop.push(fn), onActivated: fn => hooks.activate.push(fn), onBeforeUnmount: fn => hooks.unmount.push(fn) }, '@/hooks/useDisplayDensity': { scaleDensityPixels: value => value * density.value } },
  })
  return { ...f, hooks, density, math: f.load('gantt.ts'), cleanup: () => { hooks.unmount.forEach(fn => fn()); f.close() } }
}
const sizes = { minimumWidth: 720, dayWidth: 72, weekWidth: 112 }
const near = (actual, expected) => assert.ok(Math.abs(actual - expected) < 1e-7, `${actual} != ${expected}`)

test('calendar parser validates real calendar dates and leap days instead of normalizing invalid input', () => {
  const f = setup()
  try {
    const parse = f.math.ganttCalendarDay
    for (const value of [undefined, null, '', '2026-02-29', '2026-02-30', '2026-13-01', '2026-00-01', '2026-11-00', '2026-1-01', '2026-11-01T00:00:00Z']) assert.equal(parse(value), null)
    assert.equal(parse('2024-03-01') - parse('2024-02-28'), 2)
    assert.equal(parse('2026-03-09') - parse('2026-03-08'), 1)
    assert.equal(parse('2026-11-02') - parse('2026-11-01'), 1)
    assert.equal(parse('0099-01-02') - parse('0099-01-01'), 1)
  } finally { f.cleanup() }
})

test('short periods stretch axis cells and bars using one common day scale', () => {
  const f = setup()
  try {
    const scale = f.math.createGanttScale('2026-11-01', '2026-11-03', 'day', sizes)
    assert.equal(scale.days, 3); assert.equal(scale.width, 720)
    assert.deepEqual(scale.units.map(unit => unit.width), [240, 240, 240])
    assert.equal(scale.units[0].weekend, true)
    assert.deepEqual(f.math.ganttBarGeometry(scale, '2026-11-02', '2026-11-02', 4), { left: 244, width: 232 })
    assert.equal(f.math.ganttTodayOffset(scale, '2026-11-02'), 360)
  } finally { f.cleanup() }
})

test('partial final weeks have proportional widths and align with exact day boundaries', () => {
  const f = setup()
  try {
    const scale = f.math.createGanttScale('2026-11-01', '2026-11-10', 'week', sizes)
    assert.equal(scale.units.length, 2); assert.deepEqual(scale.units.map(unit => unit.width), [504, 216])
    assert.equal(scale.width, 720); assert.equal(scale.units[1].label, '11/8 起')
    const bar = f.math.ganttBarGeometry(scale, '2026-11-08', '2026-11-10', 4)
    assert.deepEqual(bar, { left: 508, width: 208 })
    near(bar.left + bar.width + 4, scale.width)
  } finally { f.cleanup() }
})

test('long periods use the normal scale, and axis widths sum to the entire chart width in either zoom', () => {
  const f = setup()
  try {
    for (const zoom of ['day', 'week']) {
      const scale = f.math.createGanttScale('2026-01-01', '2026-12-31', zoom, sizes)
      near(scale.units.reduce((sum, unit) => sum + unit.width, 0), scale.width)
      assert.ok(Number.isFinite(scale.width)); assert.ok(scale.units.every(unit => unit.width > 0))
    }
  } finally { f.cleanup() }
})

test('out-of-period and invalid bars are absent, partial overlaps are clipped without extending past the chart', () => {
  const f = setup()
  try {
    const scale = f.math.createGanttScale('2026-11-01', '2026-11-10', 'day', sizes), bar = f.math.ganttBarGeometry
    for (const pair of [[null, null], ['bad', 'bad'], ['2026-11-05', '2026-11-04'], ['2026-10-01', '2026-10-31'], ['2026-11-11', '2026-11-12']]) assert.equal(bar(scale, ...pair, 4), null)
    assert.deepEqual(bar(scale, '2026-10-31', '2026-11-02', 4), { left: 4, width: 136 })
    assert.deepEqual(bar(scale, '2026-11-09', '2026-11-15', 4), { left: 580, width: 136 })
    const narrow = f.math.createGanttScale('2026-01-01', '2026-12-31', 'week', sizes)
    const oneDay = bar(narrow, '2026-12-31', '2026-12-31', 100)
    assert.ok(oneDay.width > 0); assert.ok(oneDay.left + oneDay.width <= narrow.width)
  } finally { f.cleanup() }
})

test('invalid period, invalid sizing and out-of-period today values do not produce NaN geometry', () => {
  const f = setup()
  try {
    for (const pair of [[null, null], ['bad', '2026-11-01'], ['2026-11-03', '2026-11-01']]) assert.equal(f.math.createGanttScale(...pair, 'day', sizes), null)
    for (const value of [NaN, Infinity, 0, -1]) assert.equal(f.math.createGanttScale('2026-11-01', '2026-11-03', 'day', { ...sizes, dayWidth: value }), null)
    const scale = f.math.createGanttScale('2026-11-01', '2026-11-03', 'day', sizes)
    for (const today of [null, 'bad', '2026-10-31', '2026-11-04']) assert.equal(f.math.ganttTodayOffset(scale, today), null)
    assert.equal(f.math.ganttTodayOffset(null, '2026-11-01'), null)
  } finally { f.cleanup() }
})

test('density changes reactively resize labels, tracks, bars and today exactly once', async () => {
  const f = setup()
  try {
    const row = f.groups.value[0].items[0], width = f.timelineWidth.value, bar = f.barGeometry(row), today = f.todayOffset.value
    f.density.value = 1.35; await flush()
    near(f.timelineWidth.value, width * 1.35); near(f.barGeometry(row).left, bar.left * 1.35); near(f.barGeometry(row).width, bar.width * 1.35); near(f.todayOffset.value, today * 1.35)
    near(f.units.value.reduce((sum, unit) => sum + unit.width, 0), f.timelineWidth.value)
    f.zoom.value = 'week'; assert.ok(!f.gridStyle.value.gridTemplateColumns.includes('NaN'))
    assert.ok(!f.trackStyle.value.backgroundSize.includes('NaN'))
  } finally { f.cleanup() }
})

test('empty data and invalid period have finite empty geometry', () => {
  for (const value of [undefined, data({ iteration: null }), data({ iteration: { id: 1, start_date: 'bad', end_date: 'bad' } })]) {
    const f = setup({ data: value })
    try { assert.equal(f.scale.value, null); assert.equal(f.timelineWidth.value, 0); assert.deepEqual(f.units.value, []); assert.equal(f.todayOffset.value, null) }
    finally { f.cleanup() }
  }
})

test('multiple owners and statuses can be filtered together, including unassigned and clear values', () => {
  const source = data({ groups: [
    { owner_id: 4, owner_name: 'Example A', items: [item()] },
    { owner_id: 5, owner_name: 'Example B', items: [item({ id: 'task-12', suite_id: 12, status: 4 })] },
    { owner_id: null, owner_name: 'Unassigned', items: [item({ id: 'task-13', suite_id: 13, status: 5 })] },
  ] }), f = setup({ data: source })
  try {
    const before = JSON.stringify(source)
    f.ownerFilter.value = [4, 'unassigned']; f.statusFilter.value = [3, 5]
    assert.equal(f.groups.value.length, 2); assert.equal(f.summary.value.owner_count, 1)
    assert.equal(f.ownerOptions.value[2].value, 'unassigned')
    f.ownerFilter.value = []; f.statusFilter.value = []; assert.equal(f.groups.value.length, 3)
    f.ownerFilter.value = undefined; f.statusFilter.value = undefined; assert.equal(f.groups.value.length, 3)
    assert.equal(JSON.stringify(source), before)
  } finally { f.cleanup() }
})

test('keyword matching is trimmed and case insensitive and summary counts distinct requirements rather than tasks', () => {
  const f = setup({ data: data({ groups: [{ owner_id: 4, owner_name: 'Example', items: [item(), item({ id: 'task-1' }), item({ id: 'requirement-12', suite_id: 12, requirement_name: 'Other' })] }] }) })
  try {
    assert.equal(f.summary.value.requirement_count, 2)
    f.keyword.value = '  EXAMPLE  '; assert.equal(f.groups.value[0].items.length, 2); assert.equal(f.summary.value.requirement_count, 1)
    f.keyword.value = 'missing'; assert.deepEqual(f.groups.value, [])
  } finally { f.cleanup() }
})

test('scope and iteration changes reset filters but ordinary data refreshes preserve them', async () => {
  const f = setup()
  try {
    f.keyword.value = 'Example'; f.ownerFilter.value = [4]; f.statusFilter.value = [3]
    f.props.data = data(); await flush(); assert.equal(f.keyword.value, 'Example')
    f.props.contextKey = 'B'; assert.equal(f.keyword.value, ''); assert.deepEqual(f.ownerFilter.value, []); assert.deepEqual(f.statusFilter.value, [])
    f.keyword.value = 'Second'; f.props.data = data({ iteration: { id: 2, start_date: '2026-11-01', end_date: '2026-11-10' } }); assert.equal(f.keyword.value, '')
  } finally { f.cleanup() }
})

test('current owned items emit an edit; stale, busy, loading, filtered or inactive items do not', () => {
  const f = setup()
  try {
    const row = f.groups.value[0].items[0]
    f.openItem(row); assert.equal(f.events.length, 1); assert.equal(f.events[0][1], row)
    f.openItem({ ...row }); f.props.busyIds = [11]; f.openItem(row)
    f.props.busyIds = []; f.props.loading = true; f.openItem(row)
    f.props.loading = false; f.keyword.value = 'Missing'; f.openItem(row)
    f.keyword.value = ''; f.hooks.stop.forEach(fn => fn()); f.openItem(row)
    assert.equal(f.events.length, 1)
    f.hooks.activate.forEach(fn => fn()); f.openItem(row); assert.equal(f.events.length, 2)
  } finally { f.cleanup() }
})

test('missing, invalid and out-of-period schedules have distinct explanations', () => {
  const f = setup()
  try {
    assert.equal(f.unscheduledText(item({ planned_start_date: null })), '未完成排期')
    assert.equal(f.unscheduledText(item({ planned_start_date: '2026-02-30' })), '排期日期无效')
    assert.equal(f.unscheduledText(item({ planned_start_date: '2026-11-05', planned_submit_date: '2026-11-03' })), '排期日期无效')
    assert.equal(f.unscheduledText(item({ planned_start_date: '2026-12-01', planned_submit_date: '2026-12-02' })), '排期不在当前迭代范围')
  } finally { f.cleanup() }
})

test('scroll sync copies actual CSS coordinates once and cancels animation frames across scope and lifecycle', () => {
  const previousRequest = globalThis.requestAnimationFrame, previousCancel = globalThis.cancelAnimationFrame
  const frames = new Map(), cancelled = []; let nextId = 0
  globalThis.requestAnimationFrame = fn => { const id = ++nextId; frames.set(id, fn); return id }
  globalThis.cancelAnimationFrame = id => { cancelled.push(id); frames.delete(id) }
  const f = setup()
  try {
    const left = { scrollTop: 123, scrollLeft: 0 }, timeline = { scrollTop: 0, scrollLeft: 66 }
    f.leftRef.value = left; f.timelineRef.value = timeline; f.density.value = 1.35
    f.syncVertical('left'); assert.equal(timeline.scrollTop, 123); assert.equal(frames.size, 1)
    timeline.scrollTop = 200; f.syncVertical('timeline'); assert.equal(left.scrollTop, 123)
    const frame = frames.values().next().value; frames.clear(); frame(); f.syncVertical('timeline'); assert.equal(left.scrollTop, 200)
    f.props.contextKey = 'B'; assert.equal(frames.size, 0); assert.equal(timeline.scrollTop, 0); assert.equal(timeline.scrollLeft, 0)
    f.syncVertical('left'); f.hooks.stop.forEach(fn => fn()); assert.equal(frames.size, 0)
    f.syncVertical('left'); assert.equal(frames.size, 0)
    f.hooks.activate.forEach(fn => fn()); f.syncVertical('left'); assert.equal(frames.size, 1)
    f.hooks.unmount.forEach(fn => fn()); assert.equal(frames.size, 0); assert.ok(cancelled.length >= 3)
  } finally { f.cleanup(); globalThis.requestAnimationFrame = previousRequest; globalThis.cancelAnimationFrame = previousCancel }
})

test('native scrollbar gutter is measured without density multiplication and observers reconnect only to the current viewport', async () => {
  const previous = globalThis.ResizeObserver, observers = []
  globalThis.ResizeObserver = class {
    constructor(callback) { this.callback = callback; this.disconnected = false; observers.push(this) }
    observe(target) { this.target = target }
    disconnect() { this.disconnected = true }
  }
  const f = setup()
  try {
    const first = { offsetHeight: 300, clientHeight: 284, scrollTop: 0, scrollLeft: 0 }
    f.timelineRef.value = first; f.density.value = 1.35
    f.hooks.mount.forEach(fn => fn()); await flush()
    assert.equal(f.timelineGutter.value, 16)
    const old = observers.at(-1)
    f.timelineRef.value = { offsetHeight: 400, clientHeight: 390, scrollTop: 0, scrollLeft: 0 }; await flush()
    assert.equal(old.disconnected, true); old.callback(); assert.equal(f.timelineGutter.value, 10)
    f.hooks.stop.forEach(fn => fn()); assert.equal(observers.at(-1).disconnected, true)
    f.hooks.activate.forEach(fn => fn()); assert.equal(observers.at(-1).disconnected, false)
    f.hooks.unmount.forEach(fn => fn()); assert.equal(observers.at(-1).disconnected, true)
  } finally { f.cleanup(); globalThis.ResizeObserver = previous }
})

test('gantt SFC script, template and scoped styles compile', () => {
  const filename = path.join(base, 'components/UserScheduleGantt.vue'), { descriptor, errors } = parse(readFileSync(filename, 'utf8'))
  assert.deepEqual(errors, [])
  const script = compileScript(descriptor, { id: 'gantt' })
  assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename, id: 'gantt', compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
  for (const style of descriptor.styles) assert.deepEqual(compileStyle({ source: style.content, filename, id: 'gantt', scoped: style.scoped, preprocessLang: style.lang }).errors, [])
})
