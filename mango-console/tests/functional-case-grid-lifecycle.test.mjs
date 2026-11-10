import assert from 'node:assert/strict'
import path from 'node:path'
import test from 'node:test'
import * as vue from 'vue'
import { compileScript, compileStyle, compileTemplate, parse } from '@vue/compiler-sfc'
import { readFileSync } from 'node:fs'
import { deferred, flush, harness } from './helpers/case-details-harness.mjs'

async function settle() { await flush(); await new Promise(setImmediate); await flush() }

const base = path.resolve('src/components/table')
const products = [{ value: 1, label: 'Project', children: [{ value: 2, label: 'Product' }] }]
const modules = [{ key: 1, title: 'Parent', level: 1, children: [{ key: 2, title: 'Child', level: 2, children: [{ key: 3, title: 'Leaf', level: 3 }] }] }]
function fixture(options = {}) {
  const originals = { window: globalThis.window, getComputedStyle: globalThis.getComputedStyle, document: globalThis.document }
  const hooks = { mount: [], stop: [], activate: [], unmount: [] }, timers = new Map(), frames = new Map(), listeners = new Map()
  const instances = [], reads = [], messages = [], density = { value: options.scale ?? 1 }
  let sequence = 0, failRender = options.failRender ?? false
  globalThis.window = {
    setTimeout: fn => { const id = ++sequence; timers.set(id, fn); return id }, clearTimeout: id => timers.delete(id),
    requestAnimationFrame: fn => { const id = ++sequence; frames.set(id, fn); return id }, cancelAnimationFrame: id => frames.delete(id),
    addEventListener: (type, handler) => { const set = listeners.get(type) ?? new Set(); set.add(handler); listeners.set(type, set) },
    removeEventListener: (type, handler) => listeners.get(type)?.delete(handler),
  }
  globalThis.document = { documentElement: {} }
  globalThis.getComputedStyle = () => ({ fontFamily: 'Example', getPropertyValue: () => 'rgb(80, 90, 100)' })
  function createSheet() {
    if (failRender) { failRender = false; throw Error('Renderer unavailable') }
    const state = { disposed: 0, handlers: new Map(), widths: new Map(), sizes: [], fonts: [], values: [], cells: new Map(), activations: [], eventsDisposed: 0, zoom: .9, filter: null }
    const range = (...position) => {
      const target = {
        setValues: value => { state.values.push({ position, value }); value.forEach((row, r) => row.forEach((cell, c) => state.cells.set(`${position[0] + r}:${position[1] + c}`, cell))); return proxy },
        getValue: () => state.cells.get(`${position[0]}:${position[1]}`),
        setValue: value => { state.cells.set(`${position[0]}:${position[1]}`, value); return proxy },
        setFontSize: value => { state.fonts.push(value); return proxy },
        activate: () => state.activations.push(position),
        createFilter: () => null,
      }
      const proxy = new Proxy(target, { get: (o, key) => key in o ? o[key] : () => proxy })
      return proxy
    }
    const sheet = {
      getRange: range, getMaxRows: () => 1000, getMaxColumns: () => 1000,
      hideColumns() {}, setFrozenRows() {}, setFrozenColumns() {},
      setRowHeight: (row, height) => state.sizes.push({ row, height }),
      setRowHeights: (row, count, height) => state.sizes.push({ row, count, height }),
      setColumnWidth: (column, width) => state.widths.set(column, width), getColumnWidth: column => state.widths.get(column),
      getFilter: () => state.filter, getVisibleRange: () => ({ startRow: 1, startColumn: 0, endRow: 1 }), getZoom: () => state.zoom,
    }
    const api = {
      Event: new Proxy({}, { get: (_, key) => key }), Enum: { BorderType: {}, BorderStyleTypes: {}, DataValidationRenderMode: {} },
      createWorkbook(config) { state.config = config; state.zoom = config.sheets.cases.zoomRatio;
        for (const [r, row] of Object.entries(config.sheets.cases.cellData)) for (const [c, cell] of Object.entries(row)) state.cells.set(`${r}:${c}`, cell.v)
        return { getActiveSheet: () => sheet, setEditable() {} } },
      addEvent(type, handler) { state.handlers.set(type, handler); return { dispose: () => { ++state.eventsDisposed } } },
      newDataValidation() {
        const rule = new Proxy({}, { get: (_, key) => key === 'getCriteriaValues' ? () => [undefined, 'Values'] : key === 'getCriteriaType' ? () => 'list' : () => rule })
        return rule
      },
    }
    state.sheet = sheet
    state.edit = (row, column, value) => { state.cells.set(`${row}:${column}`, value); state.handlers.get('SheetValueChanged')({ effectedRanges: [{ startRow: row, endRow: row, startColumn: column, endColumn: column }] }) }
    instances.push(state)
    return { univer: { dispose: () => { ++state.disposed } }, univerAPI: api }
  }
  const f = harness('FunctionalCaseGrid', 'container,createGrid,renderLoading,renderError,incrementalLoading,relationOptionsLoading,relationOptionsError,retryRelationOptions,appendRowsToSheet,replaceRowsInSheet,innerColumns', {
    base, filename: path.join(base, 'FunctionalCaseGrid.vue'),
    props: { rows: [{ id: 1, title: 'First', project_product_id: 2 }], columns: [{ field: 'title', title: 'Title', width: 200 }], filterable: false, contextKey: 'A', ...options.props },
    api: {
      getUserProjectProductName: async () => { reads.push('products'); return options.products ? options.products() : { data: products } },
      getUserModuleTree: async id => { reads.push(String(id)); return options.modules ? options.modules(id) : { data: modules } },
    },
    modules: {
      vue: { ...vue, onMounted: fn => hooks.mount.push(fn), onActivated: fn => hooks.activate.push(fn), onDeactivated: fn => hooks.stop.push(fn), onBeforeUnmount: fn => hooks.unmount.push(fn) },
      '@/plugins/univer-sheets': { createFunctionalSheet: createSheet },
      '@/hooks/useDisplayDensity': { scaleDensityPixels: value => Number((value * density.value).toFixed(4)) },
      '@arco-design/web-vue': { Message: Object.fromEntries(['info', 'warning'].map(type => [type, message => messages.push([type, message])])) },
      vuedraggable: {},
    },
  })
  f.container.value = {}
  async function runTimers() { const pending = [...timers.values()]; timers.clear(); pending.forEach(fn => fn()); await settle() }
  return { ...f, hooks, instances, reads, density, timers, frames, listeners, messages,
    mount: async () => { hooks.mount.forEach(fn => fn()); await settle() }, runTimers,
    dispatch: type => listeners.get(type)?.forEach(fn => fn()),
    cleanup: () => { hooks.unmount.forEach(fn => fn()); f.close(); Object.assign(globalThis, originals) },
  }
}

test('a readonly grid renders without fetching relation options and forbids row edits and structure writes', async () => {
  const f = fixture({ props: { editable: false, columns: [{ field: 'project_product_id', title: 'Product', editor: 'project-product' }] } })
  try {
    await f.mount(); assert.equal(f.instances.length, 1); assert.deepEqual(f.reads, [])
    const handlers = f.instances[0].handlers
    const editing = { row: 1, column: 0 }; handlers.get('BeforeSheetEditStart')(editing); assert.equal(editing.cancel, true)
    const pasting = {}; handlers.get('BeforeClipboardPaste')(pasting); assert.equal(pasting.cancel, true)
    for (const id of ['sheet.command.insert-row', 'sheet.command.remove-row']) { const event = { id }; handlers.get('BeforeCommandExecute')(event); assert.equal(event.cancel, true) }
    assert.equal(f.events.some(([type]) => ['insert-rows', 'remove-rows', 'cell-change'].includes(type)), false)
  } finally { f.cleanup() }
})

test('ordinary edits emit typed patches without changing parent records and rejected edits restore cells', async () => {
  const f = fixture()
  try {
    await f.mount(); const sheet = f.instances[0]
    sheet.edit(1, 0, 'Changed')
    assert.equal(f.props.rows[0].title, 'First')
    const event = f.events.filter(([type]) => type === 'cell-change').at(-1)[1]
    assert.equal(event.row, f.props.rows[0]); assert.equal(event.field, 'title')
    assert.deepEqual(event.changes, { title: 'Changed' }); assert.deepEqual(event.displayChanges, {})
    assert.deepEqual(event.oldValues, { title: 'First' }); assert.equal(sheet.cells.get('1:0'), 'First')
  } finally { f.cleanup() }
})

test('an accepting owner updates its record and the grid redraws the accepted value', async () => {
  const f = fixture()
  try {
    const append = f.events.push.bind(f.events)
    f.events.push = (...events) => {
      for (const [type, event] of events) if (type === 'cell-change') Object.assign(event.row, event.changes, event.displayChanges)
      return append(...events)
    }
    await f.mount(); f.instances[0].edit(1, 0, 'Accepted')
    assert.equal(f.props.rows[0].title, 'Accepted'); assert.equal(f.instances[0].cells.get('1:0'), 'Accepted')
    assert.deepEqual(f.events.filter(([type]) => type === 'cell-change').at(-1)[1].oldValues, { title: 'First' })
  } finally { f.cleanup() }
})

test('product selection is only a preview until a third-level module emits one atomic patch', async () => {
  const f = fixture({ products: async () => ({ data: [{ value: 1, label: 'Project', children: [{ value: 2, label: 'Product' }, { value: 4, label: 'New Product' }] }] }),
    modules: async id => ({ data: String(id) === '4' ? [{ key: 8, title: 'New Parent', level: 1, children: [{ key: 9, title: 'New Child', level: 2, children: [{ key: 5, title: 'New Leaf', level: 3 }] }] }] : modules }),
    props: { rows: [{ id: 1, project_product_id: 2, project_product_path: 'Project/Product', module_id: 3, module_path: 'Parent/Child/Leaf' }],
      columns: [{ field: 'project_product_id', title: 'Product', editor: 'project-product', displayField: 'project_product_path' }, { field: 'module_id', title: 'Module', editor: 'module-cascader', displayField: 'module_path' }] } })
  try {
    await f.mount(); const sheet = f.instances[0]
    sheet.edit(1, 0, 'Project/New Product'); await settle()
    assert.equal(f.props.rows[0].project_product_id, 2); assert.equal(f.props.rows[0].module_id, 3)
    assert.equal(f.events.filter(([type]) => type === 'cell-change').length, 0)
    assert.equal(sheet.cells.get('1:0'), 'Project/New Product')
    sheet.edit(1, 1, 'New Parent/New Child/New Leaf')
    const event = f.events.filter(([type]) => type === 'cell-change').at(-1)[1]
    assert.deepEqual(event.changes, { project_product_id: 4, module_id: 5 })
    assert.deepEqual(event.displayChanges, { project_product_path: 'Project/New Product', module_path: 'New Parent/New Child/New Leaf' })
    assert.equal(f.props.rows[0].project_product_id, 2)
  } finally { f.cleanup() }
})

test('readonly transition discards a local relation preview without mutating parent data', async () => {
  const f = fixture({ products: async () => ({ data: [{ value: 1, label: 'Project', children: [{ value: 2, label: 'Product' }, { value: 4, label: 'New' }] }] }),
    props: { columns: [{ field: 'project_product_id', title: 'Product', editor: 'project-product' }] } })
  try {
    await f.mount(); f.instances[0].edit(1, 0, 'Project/New'); await settle()
    f.props.editable = false; await settle()
    assert.equal(f.props.rows[0].project_product_id, 2)
    assert.equal(f.instances[0].cells.get('1:0'), 2)
    assert.equal(f.events.filter(([type]) => type === 'cell-change').length, 0)
  } finally { f.cleanup() }
})

test('pending option reads are local loading and deactivation prevents late canvas creation', async () => {
  const pending = deferred(), f = fixture({ products: () => pending.promise, props: { columns: [{ field: 'project_product_id', title: 'Product', editor: 'project-product' }] } })
  try {
    await f.mount(); assert.equal(f.renderLoading.value, true); assert.equal(f.relationOptionsLoading.value, true)
    f.hooks.stop.forEach(fn => fn()); assert.equal(f.renderLoading.value, false); assert.equal(f.relationOptionsLoading.value, false)
    pending.resolve({ data: products }); await settle(); assert.equal(f.instances.length, 0)
    f.hooks.activate.forEach(fn => fn()); await settle(); assert.equal(f.instances.length, 1)
    assert.equal(f.reads.filter(key => key === 'products').length, 2)
  } finally { f.cleanup() }
})

test('failed options remain retryable and do not turn into a permanent cached empty result', async () => {
  let fail = true
  const f = fixture({ modules: async () => { if (fail) throw Error('Offline'); return { data: modules } }, props: { columns: [{ field: 'module_id', title: 'Module', editor: 'module-cascader' }] } })
  try {
    await f.mount(); assert.equal(f.instances.length, 1); assert.equal(f.relationOptionsError.value, true)
    fail = false; await f.retryRelationOptions()
    assert.equal(f.relationOptionsError.value, false); assert.equal(f.relationOptionsLoading.value, false)
    assert.equal(f.reads.filter(key => key === '2').length, 2)
    await f.retryRelationOptions(); assert.equal(f.reads.filter(key => key === '2').length, 2)
  } finally { f.cleanup() }
})

test('canvas render failure releases loading and a user retry can create it', async () => {
  const f = fixture({ failRender: true })
  try {
    await f.mount(); assert.equal(f.renderError.value, true); assert.equal(f.renderLoading.value, false)
    await f.createGrid(); assert.equal(f.renderError.value, false); assert.equal(f.instances.length, 1)
  } finally { f.cleanup() }
})

test('deactivation disposes once, clears timers/frames and queued third-party callbacks cannot emit', async () => {
  const f = fixture()
  try {
    await f.mount(); const first = f.instances[0], before = f.events.length
    f.hooks.stop.forEach(fn => fn())
    assert.equal(first.disposed, 1); assert.equal(f.frames.size, 0); assert.equal(f.timers.size, 0)
    first.handlers.get('SelectionChanged')({ selections: [{ startRow: 1, endRow: 1 }] })
    first.handlers.get('Scroll')(); assert.equal(f.events.length, before); assert.equal(f.frames.size, 0)
    f.hooks.activate.forEach(fn => fn()); await settle(); assert.equal(f.instances.length, 2)
    first.handlers.get('SelectionChanged')({ selections: [{ startRow: 1, endRow: 1 }] }); assert.equal(f.events.length, before)
    assert.equal(first.disposed, 1)
  } finally { f.cleanup() }
})

test('scope A to B to A invalidates pending choices and accepts only fresh module responses', async () => {
  const old = deferred(), fresh = deferred(); let calls = 0
  const f = fixture({ modules: () => ++calls === 1 ? old.promise : fresh.promise, props: { columns: [{ field: 'module_id', title: 'Module', editor: 'module-cascader' }] } })
  try {
    await f.mount(); f.props.contextKey = 'B'; f.props.contextKey = 'A'; await f.runTimers()
    old.resolve({ data: modules }); await settle(); assert.equal(f.instances.length, 0); assert.equal(f.renderLoading.value, true)
    fresh.resolve({ data: modules }); await settle(); assert.equal(f.instances.length, 1); assert.equal(f.renderLoading.value, false)
    assert.equal(calls, 2)
  } finally { f.cleanup() }
})

test('display density scales design geometry and persisted column widths stay in design units', async () => {
  const f = fixture({ scale: 1.15 })
  try {
    await f.mount(); const first = f.instances[0]
    assert.equal(first.widths.get(0), 230); assert.equal(first.config.sheets.cases.defaultRowHeight, 32.2)
    assert.ok(first.fonts.includes(13.8)); assert.ok(first.sizes.some(row => row.height === 34.5))
    first.widths.set(0, 345); first.handlers.get('CommandExecuted')({ id: 'sheet.command.set-worksheet-col-width' })
    const changed = f.events.filter(([type]) => type === 'view-change').at(-1)[1]
    assert.equal(changed[0].width, 300)
    f.density.value = 1.35; f.dispatch('mango-density-change'); await f.runTimers()
    assert.equal(first.disposed, 1); assert.equal(f.instances[1].widths.get(0), 405)
  } finally { f.cleanup() }
})

test('theme rebuild preserves sheet zoom and viewport, while cached pages do not rebuild', async () => {
  const f = fixture()
  try {
    await f.mount(); const first = f.instances[0]; first.zoom = 1.4
    f.dispatch('mango-theme-change'); await f.runTimers()
    assert.equal(first.disposed, 1); assert.equal(f.instances[1].config.sheets.cases.zoomRatio, 1.4)
    await f.runTimers(); assert.deepEqual(f.instances[1].activations, [[1, 0]])
    f.hooks.stop.forEach(fn => fn()); f.dispatch('mango-density-change'); await f.runTimers()
    assert.equal(f.instances.length, 2)
  } finally { f.cleanup() }
})

test('read-only to editable loads needed choices and malformed option data is retryable', async () => {
  let malformed = true
  const f = fixture({ products: async () => ({ data: malformed ? {} : products }), props: { editable: false, columns: [{ field: 'project_product_id', title: 'Product', editor: 'project-product' }] } })
  try {
    await f.mount(); assert.equal(f.reads.length, 0)
    f.props.editable = true; await settle(); assert.equal(f.relationOptionsError.value, true)
    malformed = false; await f.retryRelationOptions(); assert.equal(f.relationOptionsError.value, false)
  } finally { f.cleanup() }
})

test('concurrent option preparation deduplicates both product and per-product reads', async () => {
  const pending = deferred(), f = fixture({ modules: () => pending.promise })
  const cache = f.load('composables/useFunctionalGridOptions.ts').useFunctionalGridOptions({ current: () => true })
  try {
    const first = cache.prepare([2, '2']), second = cache.prepare(['2']); await settle()
    assert.deepEqual(f.reads.sort(), ['2', 'products']); assert.equal(cache.loading.value, true)
    pending.resolve({ data: modules }); await Promise.all([first, second])
    assert.equal(cache.loading.value, false); assert.equal(cache.error.value, false)
    assert.deepEqual(cache.productOptions.value.map(item => item.path), ['Project/Product'])
    assert.deepEqual(cache.moduleOptions.get('2').map(item => item.path), ['Parent/Child/Leaf'])
    await cache.prepare([2]); assert.equal(f.reads.length, 2)
  } finally { cache.reset(); f.cleanup() }
})

test('successful empty module options are cached but failed module reads alone are retried', async () => {
  let fail = true
  const f = fixture({ modules: async id => { if (id === '2' && fail) throw Error('Offline'); return { data: [] } } })
  const cache = f.load('composables/useFunctionalGridOptions.ts').useFunctionalGridOptions({ current: () => true })
  try {
    await cache.prepare([2, 3]); assert.equal(cache.error.value, true)
    assert.equal(cache.moduleOptions.has('2'), false); assert.deepEqual(cache.moduleOptions.get('3'), [])
    fail = false; await cache.prepare([2, 3])
    assert.equal(cache.error.value, false); assert.equal(f.reads.filter(key => key === '2').length, 2)
    assert.equal(f.reads.filter(key => key === '3').length, 1); assert.equal(f.reads.filter(key => key === 'products').length, 1)
  } finally { cache.reset(); f.cleanup() }
})

test('late cache failure after reset neither marks a new scope failed nor releases its loading', async () => {
  const old = deferred(), fresh = deferred(); let count = 0
  const f = fixture({ modules: () => ++count === 1 ? old.promise : fresh.promise })
  const cache = f.load('composables/useFunctionalGridOptions.ts').useFunctionalGridOptions({ current: () => true })
  try {
    const first = cache.prepare([2]); await settle(); cache.reset()
    const second = cache.prepare([2]); await settle()
    old.reject(Error('Old failure')); await first
    assert.equal(cache.loading.value, true); assert.equal(cache.error.value, false); assert.equal(cache.moduleOptions.size, 0)
    fresh.resolve({ data: modules }); await second
    assert.equal(cache.loading.value, false); assert.equal(cache.moduleOptions.get('2')[0].value, 3)
  } finally { cache.reset(); f.cleanup() }
})

test('module choices include only third-level paths and preserve zero-valued relation IDs', async () => {
  const tree = [...modules, { key: 9, title: 'Empty parent', level: 1 }, { key: 10, title: 'Too deep', level: 4 }]
  const f = fixture({ products: async () => ({ data: [{ key: 0, title: 'Zero' }] }), modules: async () => ({ data: tree }) })
  const cache = f.load('composables/useFunctionalGridOptions.ts').useFunctionalGridOptions({ current: () => true })
  try {
    await cache.prepare([0]); assert.equal(cache.productOptions.value[0].value, 0)
    assert.deepEqual(cache.moduleOptions.get('0').map(item => item.label), ['Parent/Child/Leaf'])
  } finally { cache.reset(); f.cleanup() }
})

test('an inactive option scope issues no new reads', async () => {
  const f = fixture()
  const cache = f.load('composables/useFunctionalGridOptions.ts').useFunctionalGridOptions({ current: () => false })
  try { await cache.prepare([2]); assert.deepEqual(f.reads, []); assert.equal(cache.loading.value, false) }
  finally { cache.reset(); f.cleanup() }
})

test('options no longer required by the visible rows do not keep loading or failure feedback active', async () => {
  const abandoned = deferred()
  const f = fixture({ modules: id => id === '2' ? abandoned.promise : Promise.resolve({ data: modules }) })
  const cache = f.load('composables/useFunctionalGridOptions.ts').useFunctionalGridOptions({ current: () => true })
  try {
    const first = cache.prepare([2]); await settle(); assert.equal(cache.loading.value, true)
    await cache.prepare([3]); assert.equal(cache.loading.value, false)
    abandoned.reject(Error('Obsolete product')); await first
    assert.equal(cache.error.value, false); assert.equal(cache.loading.value, false)
  } finally { cache.reset(); f.cleanup() }
})

test('incremental updates commit only the latest row update and release their local loading', async () => {
  const f = fixture()
  try {
    await f.mount(); const first = f.instances[0]
    const append = f.appendRowsToSheet(0), replace = f.replaceRowsInSheet(2)
    assert.equal(f.incrementalLoading.value, true)
    await Promise.all([append, replace]); assert.equal(f.incrementalLoading.value, false)
    assert.equal(first.values.length, 1); assert.deepEqual(first.values[0].value, [['First']])
  } finally { f.cleanup() }
})

test('unmount removes global listeners and old callbacks cannot recreate work', async () => {
  const f = fixture()
  try {
    await f.mount(); const first = f.instances[0]
    f.hooks.unmount.forEach(fn => fn())
    assert.equal(f.listeners.get('mango-density-change').size, 0); assert.equal(f.listeners.get('mango-theme-change').size, 0)
    first.handlers.get('Scroll')(); await f.createGrid(); await f.runTimers()
    assert.equal(f.instances.length, 1); assert.equal(first.disposed, 1); assert.equal(f.frames.size, 0)
  } finally { f.cleanup() }
})

test('grid and affected callers compile their scripts/templates/styles', () => {
  for (const file of ['src/components/table/FunctionalCaseGrid.vue', 'src/views/functional-test/case-library/index.vue', 'src/views/functional-test/iteration/details/index.vue', 'src/views/functional-test/plan/details.vue']) {
    const { descriptor } = parse(readFileSync(file, 'utf8'))
    const script = compileScript(descriptor, { id: file })
    assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename: file, id: file, compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
    for (const style of descriptor.styles) assert.deepEqual(compileStyle({ source: style.content, filename: file, id: file }).errors, [])
  }
})
