import path from 'node:path'
import * as vue from 'vue'
import * as jsonc from 'jsonc-parser'
import { harness } from './case-details-harness.mjs'
import { loadModule } from './auth-config-harness.mjs'
export const lossless = loadModule('src/utils/lossless-json.ts', { 'jsonc-parser': jsonc })
export const factoryDto = loadModule('src/components/DataFactory/case-config-record.ts', { '@/utils/lossless-json': lossless })
export const template = (id = 7) => ({ id, name: 'Example template', project_product: { id: 0, name: 'Example product' }, module: 0, entity: { id: 3, name: 'Example entity', table_name: 'example_table', datasource_alias: { id: 0, name: 'Example alias' } }, items: [], field_overrides: {} })
export const factoryRecord = () => factoryDto.readFactoryConfigRows([{ id: 0, source_id: 0, source_type: 2, template: template(), field_overrides: { name: { generator_type: 1, generator_config: { value: 'case override' } } } }])[0]
export function factoryEditor({ props = {}, api = {} } = {}) {
  const previous = { document: globalThis.document, window: globalThis.window }
  const doc = Object.assign(new EventTarget(), { visibilityState: 'visible' })
  globalThis.document = doc; globalThis.window = Object.assign(new EventTarget(), { setTimeout, clearTimeout })
  const user = vue.reactive({ userId: 1, roleId: 2, token: 'example-session', selected_environment: 0 }), permission = vue.reactive({ permissionKeys: ['ui.case:read'] }), route = vue.reactive({ path: '/uitest/case/details', fullPath: '/uitest/case/details?id=0' })
  const calls = []
  const h = harness('index', 'form,visible,open,openReadonly,save,templateList,fieldRows,itemFieldsMap,editorPending,editorFailures,previewResult,previewLoading,loadCasePreview,loadFields,loadDatasourceAliases,loadTemplates,onProjectProductChange,onTemplateChange,readonlyError,datasourceAliasOptions,collection,dependencyTemplateOptions', {
    filename: path.resolve('src/components/DataFactory/CaseConfigPanel.vue'), props: { caseId: 0, sourceType: 2, projectProductId: 0, ...props },
    api: { getDataFactoryCaseConfig: async () => ({ code: 200, data: [] }), getDataFactoryDatasourceAlias: async () => ({ code: 200, data: [{ id: 0, name: 'Example alias' }] }), getDataFactoryTemplate: async () => ({ code: 200, data: [template()] }), getDataFactoryField: async () => ({ code: 200, data: [{ name: 'name', generator_type: 1 }] }), postDataFactoryCaseConfigPreview: async () => ({ code: 200, data: { fields: [{ name: 'name', value: 'example', valid: true, message: '' }] } }), ...Object.fromEntries(['postDataFactoryCaseConfig', 'putDataFactoryCaseConfig'].map(name => [name, async value => { calls.push([name, value]); return { code: 200 } }])), ...api },
    modules: { 'vue-router': { useRoute: () => route }, '@/store/modules/user': { default: () => user }, '@/store/modules/permission': { default: () => permission }, '@/utils/lossless-json': lossless },
  })
  return { ...h, user, permission, route, calls, visibility(value) { doc.visibilityState = value; doc.dispatchEvent(new Event('visibilitychange')) }, cleanup() { h.close(); Object.assign(globalThis, previous) } }
}
