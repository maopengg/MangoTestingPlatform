import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { deferred, flush as flushVue, harness } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/pytest/case'), response = data => ({ code: 200, data })
const row = (id = 1, patch = {}) => ({ id, name: 'Fixture ' + id, project_product: { id: 50, project_product: { id: 10, name: 'Product', project: { id: 20, name: 'Project' } } }, module: { id: 30, name: 'Module', full_path: 'Root/Module' }, asset_status: 0, publication_status: 'unpublished', level: 0, scenario_layer: 0, scenario_type: 0, scenario_tags: ['regression'], scenario_description: '', case_people: { id: 2 }, file_path: 'tests/test_' + id + '.py', feature_file_path: null, missing_since: null, status: 0, source_status: 0, file_status: 1, ...patch })
const file = (id = 1) => ({ key: 'file:' + id, type: 'file', title: 'test_' + id + '.py', case_id: id, path: 'tests/test_' + id + '.py', breadcrumb: ['Repository', 'Project', 'test_' + id + '.py'], repository_id: 4, pytest_project_id: 50, case_count: 1, children: [] })
const tree = ids => [{ key: 'repository:4', type: 'repository', title: 'Repository', path: '', breadcrumb: ['Repository'], repository_id: 4, case_count: ids.length, children: [{ key: 'project:50', type: 'project', title: 'Project', path: 'tests', breadcrumb: ['Repository', 'Project'], repository_id: 4, pytest_project_id: 50, case_count: ids.length, children: ids.map(file) }] }]
const snapshot = (id = 1, type = 'py') => response({ path: 'tests/test_' + id + (type === 'py' ? '.py' : '.feature'), content: 'content ' + id + ' ' + type, commit_hash: null, content_hash: 'fixture-hash-' + id + '-' + type })
const method = () => ({ nodeid: 'tests/test_1.py::test_fixture', node_type: 'method', class_name: null, method_name: 'test_fixture', parameter_id: null, line_number: 1 })
async function flush() { await flushVue(); await new Promise(resolve => setImmediate(resolve)) }
function setup(api = {}, extraProps = {}) {
  const user = vue.reactive({ userId: 1, roleId: 1, token: 'fixture-a', selected_environment: 0 })
  const route = vue.reactive({ path: '/pytest/case/index', fullPath: '/pytest/case/index', query: {} }), reads = [], records = [], sourceReads = [], methodReads = [], writes = [], runs = [], messages = [], confirmations = [], life = { mount: [], unmount: [], activate: [], deactivate: [] }
  const oldDocument = globalThis.document, doc = Object.assign(new EventTarget(), { hidden: false }), listeners = new Set()
  const add = doc.addEventListener.bind(doc), remove = doc.removeEventListener.bind(doc)
  doc.addEventListener = (type, fn) => { listeners.add(fn); add(type, fn) }
  doc.removeEventListener = (type, fn) => { listeners.delete(fn); remove(type, fn) }
  globalThis.document = doc
  const polling = { starts: 0, stops: 0, pauses: 0, callback: null, start() { this.starts++ }, stop() { this.stops++ }, pause() { this.pauses++ } }
  const project = vue.reactive({ projectProduct: [{ label: 'Project', value: 20, children: [{ label: 'Product', value: 10 }] }], allProductModuleTreeCache: { data: [{ key: 30, title: 'Root/Module', project_product_id: 10 }] } })
  const h = harness('index', 'source,selectedExplorerRecord,selectedExplorerFileNode,sourceFiles,currentFile,metadataLoading,metadataFailed,methodsLoading,methodsFailed,explorerFileType,explorerCodeText,directoryTree,directoryTreeLoading,directoryFailed,userOptions,userLoading,userFailed,pageVersion,linkedCaseId,conditionItems,sidebarProjectProductId,sidebarModuleIds,sidebarResetKey,resultHistoryVisible,resultHistoryRecord,batchEditorVisible,batchEditorScopes,mutationBusy,publicationActionCaseId,deleteCaseId,caseRunning,running,methodLineActions,pollingCaseId,reviewPublished,codeDrawerRef,caseEditorRef,syncDialogRef,publicationReviewRef,buildCaseSearchParams,loadDirectoryTree,loadUsers,onSearchRefresh,onResetSearch,onSidebarFilterChange,onDirectorySelect,onBatchEditorSaved,onMetadataSaved,onDirectorySynced,openBatchEditor,onResult,onRun,onRunMethod,onDelete,onPublicationChange,refreshSelectedCaseState,pollSelectedCaseState,startPollingCaseState,clearPollingTimer,onCodeSaved', { base, props: { caseId: undefined, ...extraProps }, modules: {
    vue: { ...vue, onMounted: fn => life.mount.push(fn), onBeforeUnmount: fn => life.unmount.push(fn), onActivated: fn => life.activate.push(fn), onDeactivated: fn => life.deactivate.push(fn) },
    'vue-router': { useRoute: () => route }, '@/store/modules/user': { default: () => user }, '@/store/modules/get-project': { useProject: () => project },
    '@/store/modules/get-enum': { useEnum: () => ({}) },
    '@/components/business/project-product-filter': { flattenProjectProducts: options => options.flatMap(project => project.children.map(product => ({ projectProductId: product.value, title: project.label + '/' + product.label }))) },
    '@/hooks/use-page-polling': { usePagePolling: callback => { polling.callback = callback; return { start: () => polling.start(), stop: () => polling.stop(), pause: () => polling.pause() } }, isPendingExecution: row => row && [2, 3].includes(Number(row.status)) },
    '@arco-design/web-vue': { Message: Object.fromEntries(['success', 'error', 'warning'].map(key => [key, value => messages.push([key, value])])), Modal: { confirm: options => {
      const modal = { options, closed: false, close() { modal.closed = true; options.onClose?.() } }; confirmations.push(modal); return modal
    } } },
    '@/api/user/user': { getUserName: () => api.users ? api.users() : Promise.resolve(response([{ key: 2, title: 'Fixture' }])) },
    '@/api/pytest/case': {
      getPytestCaseDirectoryTree: query => { reads.push(query); return api.tree ? api.tree(query) : Promise.resolve(response(tree([1, 2]))) },
      getPytestCase: query => { records.push(query); return api.record ? api.record(query) : Promise.resolve(response([row(query.id)])) },
      getPytestCaseRead: (id, type) => { sourceReads.push([id, type]); return api.source ? api.source(id, type) : Promise.resolve(snapshot(id, type)) },
      getPytestCaseMethodNodes: id => { methodReads.push(id); return api.methods ? api.methods(id) : Promise.resolve(response([method()])) },
      getPytestCaseTest: (...args) => { runs.push(args); return api.run ? api.run(...args) : Promise.resolve(response({ status: 2 })) },
      deletePytestCase: id => { writes.push(['delete', id]); return api.remove ? api.remove(id) : Promise.resolve(response(null)) },
      putPytestCasePublication: (id, status) => { writes.push(['publication', id, status]); return api.publication ? api.publication(id, status) : Promise.resolve(response({ id, publication_status: status, asset_status: status === 'published' ? 1 : 0 })) },
    },
  } })
  return { ...h, user, route, project, reads, records, sourceReads, methodReads, writes, runs, messages, confirmations, listeners, polling, boundary: h.load('records.ts'), config: h.load('config.ts'),
    async mount() { life.mount.forEach(fn => fn()); await flush() }, pause() { life.deactivate.forEach(fn => fn()) }, resume() { life.activate.forEach(fn => fn()) },
    hide() { doc.hidden = true; doc.dispatchEvent(new Event('visibilitychange')) }, show() { doc.hidden = false; doc.dispatchEvent(new Event('visibilitychange')) },
    close() { life.unmount.forEach(fn => fn()); h.close(); globalThis.document = oldDocument },
  }
}

test('finite record, directory and publication boundaries preserve zeros/nulls, copy nested fields and reject wrong scopes', () => {
  const h = setup(), input = row(), record = h.boundary.readCase(response([input]), 1), directory = h.boundary.readDirectory(response(tree([1, 2])))
  input.scenario_tags.push('later'); input.module.full_path = 'later'
  assert.deepEqual(record.scenario_tags, ['regression']); assert.equal(record.module.full_path, 'Root/Module'); assert.equal(record.status, 0); assert.equal(record.missing_since, null)
  assert.equal('is_product_owner' in record, false); assert.equal(h.boundary.findFile(directory, 2).case_id, 2); assert.equal(h.boundary.firstFile(directory).case_id, 1)
  for (const value of [response([]), response([row(2)]), response([row(), row()]), response([row(1, { status: false })]), response([row(1, { module: { id: 1 } })])]) assert.throws(() => h.boundary.readCase(value, 1))
  for (const value of [response(null), response([file(1), file(1)]), response([{ ...file(1), children: null }]), response([{ ...file(1), case_id: undefined }])]) assert.throws(() => h.boundary.readDirectory(value))
  assert.throws(() => h.boundary.readPublication(response({ id: 2, publication_status: 'published', asset_status: 1 }), 1))
  h.close()
})

test('search factories are independent, normalize comma/dunhao IDs, preserve zero and reset multiselect arrays', () => {
  const h = setup(), first = h.config.createSearchItems(), second = h.config.createSearchItems()
  first.find(item => item.key === 'id').value = '５５７４、5577'; first.find(item => item.key === 'status').value = [0, 2, 2]
  assert.deepEqual(h.config.searchQuery(first), { id__in: '5574,5577', status__in: '0,2' })
  assert.deepEqual(h.config.searchQuery(second), {}); h.config.resetSearchItems(first); assert.deepEqual(first.find(item => item.key === 'status').value, [])
  assert.deepEqual(h.config.searchQuery(first), {}); h.close()
})

test('mount coalesces directory loads, selects first file and renders metadata/source independently', async () => {
  const metadata = deferred(), py = deferred(), feature = deferred(), methods = deferred()
  const h = setup({ record: () => metadata.promise, source: (_, type) => type === 'py' ? py.promise : feature.promise, methods: () => methods.promise })
  await h.mount(); assert.equal(h.reads.length, 1); assert.equal(h.metadataLoading.value, true); assert.equal(h.sourceFiles.py.loading, true)
  metadata.resolve(response([row()])); await flush(); assert.equal(h.selectedExplorerRecord.value.id, 1); assert.equal(h.metadataLoading.value, false); assert.equal(h.sourceFiles.py.loading, true)
  py.resolve(snapshot()); await flush(); assert.equal(h.explorerCodeText.value, 'content 1 py'); assert.equal(h.sourceFiles.py.loading, false); assert.equal(h.methodsLoading.value, true)
  feature.resolve(snapshot(1, 'feature')); methods.resolve(response([method()])); await flush(); assert.equal(h.methodLineActions.value.length, 1)
  const task = h.loadDirectoryTree(), second = h.loadDirectoryTree(); assert.equal(task, second); await task
  h.close()
})

test('directory and metadata failures differ from empty success and retain retry paths', async () => {
  let data = response({}), metadata = response([])
  const h = setup({ tree: () => Promise.resolve(data), record: () => Promise.resolve(metadata) })
  await h.mount(); assert.equal(h.directoryFailed.value, true); assert.equal(h.directoryTreeLoading.value, false)
  data = response([]); await h.loadDirectoryTree(); assert.equal(h.directoryFailed.value, false); assert.equal(h.selectedExplorerRecord.value, null)
  data = response(tree([1])); await h.loadDirectoryTree(1); await flush(); assert.equal(h.metadataFailed.value, true); assert.equal(h.selectedExplorerRecord.value, null)
  assert.equal(h.explorerCodeText.value, 'content 1 py'); metadata = response([row()]); await h.source.loadMetadata(); assert.equal(h.metadataFailed.value, false)
  h.close()
})

test('filter A-B-A invalidates old tree responses/finalizers and submits detached navigation and multiselect query', async () => {
  const pending = [deferred(), deferred(), deferred()]; let index = 0
  const h = setup({ tree: () => pending[index++].promise }); await h.mount()
  h.conditionItems.find(item => item.key === 'status').value = [0, 2]
  h.onSidebarFilterChange({ projectProduct: 10, module: 30, moduleIds: [30, 31] }); await flush()
  h.onSidebarFilterChange({ projectProduct: null, module: null, moduleIds: [] }); await flush()
  assert.deepEqual(h.reads[1], { status__in: '0,2', project_product_id: 10, module_ids: '30,31' }); assert.equal('module_ids' in h.reads[2], false)
  pending[0].resolve(response(tree([1]))); pending[1].reject(Error('old')); await flush(); assert.equal(h.directoryTreeLoading.value, true); assert.deepEqual(h.directoryTree.value, [])
  pending[2].resolve(response(tree([2]))); await flush(); assert.equal(h.selectedExplorerRecord.value.id, 2); assert.equal(h.directoryFailed.value, false)
  h.close()
})

test('file A-B-A ignores old record/source/method responses without inventing fallback records', async () => {
  const pending = [deferred(), deferred(), deferred()]; let index = 0
  const h = setup({ record: () => pending[index++].promise }); await h.mount()
  h.onDirectorySelect(file(2)); await flush(); h.onDirectorySelect(file(1)); await flush()
  pending[0].resolve(response([row(1, { name: 'Old' })])); pending[1].reject(Error('old')); await flush()
  assert.equal(h.selectedExplorerRecord.value, null); assert.equal(h.metadataLoading.value, true)
  pending[2].resolve(response([row(1, { name: 'Current' })])); await flush(); assert.equal(h.selectedExplorerRecord.value.name, 'Current')
  h.close()
})

test('embedded record changes and identity/route A-B-A close windows and ignore old reads', async () => {
  for (const key of ['userId', 'roleId', 'token', 'selected_environment', 'fullPath', 'caseId']) {
    const pending = deferred(); let first = true
    const h = setup({ tree: () => first ? (first = false, pending.promise) : Promise.resolve(response(tree([2]))) })
    await h.mount(); let closed = 0
    h.codeDrawerRef.value = { close: () => closed++ }; h.publicationReviewRef.value = { invalidate: () => closed++ }
    h.batchEditorVisible.value = true; h.resultHistoryVisible.value = true
    const owner = key === 'caseId' ? h.props : key === 'fullPath' ? h.route : h.user, old = owner[key]
    owner[key] = typeof old === 'number' ? old + 1 : 'other'; owner[key] = old; await flush()
    pending.resolve(response(tree([1]))); await flush(); assert.equal(h.selectedExplorerRecord.value.id, 2); assert.equal(h.batchEditorVisible.value, false); assert.equal(h.resultHistoryVisible.value, false); assert.ok(closed >= 2)
    h.close()
  }
})

test('execution captures case/environment zero, prevents duplicates and ignores late results after record switches', async () => {
  const pending = deferred(), h = setup({ run: () => pending.promise }); await h.mount()
  const record = h.selectedExplorerRecord.value, task = h.onRun(record); assert.equal(h.caseRunning.value, true); assert.equal(await h.onRun(record), false)
  assert.deepEqual(h.runs[0], [1, 0, {}]); h.onDirectorySelect(file(2)); await flush(); pending.resolve(response({})); assert.equal(await task, false)
  assert.equal(h.running.value.size, 0); assert.equal(h.messages.some(x => x[0] === 'success'), false)
  assert.equal(await h.onRunMethod({ nodeid: 'foreign' }), false); h.close()
})

test('pending polling remains silent, retries failures and cannot overwrite a newly selected record', async () => {
  let fail = false, pending = null
  const h = setup({ record: query => pending ? pending.promise : fail ? Promise.reject(Error('temporary')) : Promise.resolve(response([row(query.id, { status: 2 })])) })
  await h.mount(); assert.equal(h.pollingCaseId.value, 1); assert.ok(h.polling.starts > 0)
  fail = true; await h.pollSelectedCaseState(1, { isCurrent: () => true }); assert.equal(h.pollingCaseId.value, 1); assert.equal(h.sourceFiles.py.loading, false); assert.equal(h.metadataLoading.value, false)
  fail = false; pending = deferred(); const task = h.refreshSelectedCaseState(1, { isCurrent: () => true }); await flush()
  const old = pending; pending = null; h.onDirectorySelect(file(2)); await flush(); old.resolve(response([row(1, { name: 'Old', status: 0 })])); assert.equal(await task, undefined); assert.equal(h.selectedExplorerRecord.value.id, 2)
  h.close()
})

test('delete confirmation and mutation keep physical locks, retry failures and never refresh a different scope', async () => {
  const pending = deferred(), h = setup({ remove: () => pending.promise }); await h.mount()
  h.onDelete(h.selectedExplorerRecord.value); assert.equal(h.confirmations[0].options.okButtonProps.status, 'danger')
  const task = h.confirmations[0].options.onBeforeOk(); assert.equal(h.mutationBusy.value, true); assert.equal(await h.confirmations[0].options.onBeforeOk(), false)
  h.onDirectorySelect(file(2)); await flush(); const count = h.reads.length
  h.onDelete(h.selectedExplorerRecord.value); assert.equal(h.confirmations.length, 1)
  pending.resolve(response(null)); assert.equal(await task, false); assert.equal(h.reads.length, count); assert.equal(h.mutationBusy.value, false)
  h.close()
})

test('publication preserves passed/prepublished guards, delegates approval and snapshots API transitions', async () => {
  let failed = true
  const h = setup({ publication: (id, publication_status) => Promise.resolve(failed ? { code: 403 } : response({ id, publication_status, asset_status: 0 })) }); await h.mount()
  h.onPublicationChange(h.selectedExplorerRecord.value, 'prepublished'); assert.equal(h.confirmations.length, 0)
  h.selectedExplorerRecord.value.status = 1; h.onPublicationChange(h.selectedExplorerRecord.value, 'prepublished')
  assert.equal(await h.confirmations[0].options.onBeforeOk(), false); assert.equal(h.mutationBusy.value, false); assert.equal(h.selectedExplorerRecord.value.publication_status, 'unpublished')
  failed = false; assert.equal(await h.confirmations[0].options.onBeforeOk(), true)
  await flush(); const approved = [], record = { ...h.selectedExplorerRecord.value, publication_status: 'prepublished' }
  h.publicationReviewRef.value = { open: (...args) => approved.push(args), invalidate() {} }
  h.onPublicationChange(record, 'published'); assert.deepEqual(approved, [['pytest', [1]]]); h.close()
})

test('pause/background/unmount invalidate requests and resume reloads through existing selections', async () => {
  const h = setup(); await h.mount(); h.onResult(h.selectedExplorerRecord.value); h.hide()
  assert.equal(h.resultHistoryVisible.value, false); const count = h.reads.length; assert.equal(await h.loadDirectoryTree(), false); assert.equal(h.reads.length, count)
  h.show(); await flush(); assert.equal(h.reads.length, count + 1); h.pause(); const paused = h.reads.length; h.resume(); await flush(); assert.equal(h.reads.length, paused + 1)
  h.close(); assert.equal(h.listeners.size, 0); assert.equal(await h.loadDirectoryTree(), false)
})

test('embedded case IDs locate the requested file on open and when the prop changes', async () => {
  const h = setup({}, { caseId: 2 }); await h.mount(); assert.equal(h.selectedExplorerRecord.value.id, 2)
  h.props.caseId = 1; await flush(); assert.equal(h.selectedExplorerRecord.value.id, 1); h.close()
})

test('successful deletion reloads the remaining tree while failure retains the current record', async () => {
  let ids = [1, 2], failed = true
  const h = setup({ tree: () => Promise.resolve(response(tree(ids))), remove: () => {
    if (failed) return Promise.reject(Error('temporary'))
    ids = [2]; return Promise.resolve(response(null))
  } }); await h.mount(); h.onDelete(h.selectedExplorerRecord.value)
  assert.equal(await h.confirmations[0].options.onBeforeOk(), false); assert.equal(h.selectedExplorerRecord.value.id, 1)
  failed = false; assert.equal(await h.confirmations[0].options.onBeforeOk(), true); await flush()
  assert.equal(h.selectedExplorerRecord.value.id, 2); assert.equal(h.deleteCaseId.value, null); h.close()
})

test('an old poll cannot overwrite metadata after an explicit save, and an invalidated public polling context stays silent', async () => {
  let mode = 'initial', pending = deferred()
  const h = setup({ record: query => mode === 'poll' ? pending.promise : Promise.resolve(response([row(query.id, { name: mode, status: 2 })])) })
  await h.mount(); mode = 'poll'; const old = h.refreshSelectedCaseState(1, { isCurrent: () => true }); await flush()
  mode = 'saved'; h.onMetadataSaved(); await flush(); pending.resolve(response([row(1, { name: 'old', status: 0 })])); assert.equal(await old, undefined)
  assert.equal(h.selectedExplorerRecord.value.name, 'saved'); const requests = h.records.length
  assert.equal(await h.refreshSelectedCaseState(1, { isCurrent: () => false }), undefined); assert.equal(h.records.length, requests)
  h.close()
})

test('actual workbench template compiles and no frontend owner/permission hiding remains', () => {
  const filename = path.join(base, 'index.vue'), source = readFileSync(filename, 'utf8'), parsed = parse(source, { filename })
  assert.deepEqual(parsed.errors, []); const script = compileScript(parsed.descriptor, { id: filename })
  const template = compileTemplate({ source: parsed.descriptor.template.content, filename, id: filename, compilerOptions: { bindingMetadata: script.bindings } })
  assert.deepEqual(template.errors, []); assert.doesNotMatch(source, /is_product_owner|v-permission|const data: any|useTable\(|onBatchRun|usePageData/)
})
