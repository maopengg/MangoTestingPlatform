import assert from 'node:assert/strict'
import test from 'node:test'
import { loadModule } from './helpers/auth-config-harness.mjs'
test('case APIs retain exact endpoints and payload keys without converting long or zero IDs', () => {
  const calls = [], request = value => { calls.push({ url: value.url, data: value.data() }); return Promise.resolve({ code: 200 }) }
  const api = loadModule('src/api/uitest/case.ts', { '@/api/http': { get: request, post: request, put: request, deleted: request } }), long = '90071992547409930000'
  api.getUiCaseRun(long, 0, 'example-actuator'); api.postUiRunCaseBatch([0, long], 0); api.deleteUiCase(long); api.postUiCaseCopy(long); api.putUiCasePublication(long, 'prepublished')
  assert.deepEqual(calls, [
    { url: '/ui/case/test', data: { case_id: long, test_env: 0, actuator_username: 'example-actuator' } },
    { url: 'ui/case/batch', data: { case_id_list: [0, long], test_env: 0 } },
    { url: '/ui/case', data: { id: long } }, { url: '/ui/case/copy', data: { case_id: long } },
    { url: '/ui/case/publication', data: { case_id: long, target_status: 'prepublished' } },
  ])
})
test('task binding and option lookup preserve zero values and existing shared query protocol', () => {
  const calls = [], request = value => { calls.push({ url: value.url, data: value.data() }); return Promise.resolve({ code: 200 }) }, http = { get: request, post: request, put: request, deleted: request }
  const tasks = loadModule('src/api/system/tasks.ts', { '@/api/http': http }), binding = loadModule('src/api/system/tasks_details.ts', { '@/api/http': http })
  tasks.getSystemTasksName(0, 0, 0); tasks.getSystemTasksName(null, null, 1, 'manual'); binding.postSystemTasksBatchSetCases([0, '90071992547409930000'], 0, 0)
  assert.deepEqual(calls, [ { url: 'system/tasks/name', data: { project_product_id: 0, module_id: 0, case_type: 0 } }, { url: 'system/tasks/name', data: { case_type: 1, execution_scope: 'manual' } }, { url: 'system/tasks/details/batch/set/cases', data: { case_id_list: [0, '90071992547409930000'], scheduled_tasks_id: 0, type: 0 } } ])
})
