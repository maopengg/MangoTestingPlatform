import path from 'node:path'
import * as vue from 'vue'
import { loadModule } from './auth-config-harness.mjs'
import { liveHarness } from './ui-live-workbench-harness.mjs'
export const flow = () => ({ nodes: [{ id: 'node-0', type: 0, label: 'Example node', position: { x: 0, y: 0 }, config: { id: 0 } }], edges: [] })
export const detail = (extra = {}) => ({ id: 0, name: 'Example node', type: 0, ope_key: 'click', ele_name: { id: 0, name: 'Example element', category: 'Example', exp: 0, loc: '//button' }, ope_value: [{ f: 'locating', d: false, v: '' }], ...extra })
export const step = (extra = {}) => ({ id: 0, name: 'Example step', page: { id: 0, name: 'Example page', url: 'https://example.com/page' }, project_product: { id: 0, ui_client_type: 0 }, status: 2, flow_data: flow(), healing_enabled: false, ...extra })
export const healing = (extra = {}) => ({ id: 0, page_step: 0, status: 'suggested', writeback_status: 'pending_review', action_types: ['retry_node'], ...extra })
export const methodDefinition = { value: 'click', label: 'Click', parameter: [{ f: 'locating', d: false, v: '', n: 'Locator', p: '' }] }
const writes = loadModule('src/hooks/use-ui-step-healing-write.ts')
export function stepHarness({ api = {}, props = {}, bindings, component = 'page' } = {}) {
  const confirms = [], notices = []
  const modules = {
    '@/store/page-data': { usePageData: () => ({ record: null }) },
    '@/store/modules/get-project': { useProject: () => ({ projectProduct: [], projectProductName: async () => {} }) },
    '@/store/modules/get-ope-value': { useSelectValueStore: () => ({ getSelectValue: async () => {}, findItemByValue: value => value === 'click' ? methodDefinition : undefined, getTopLevelLabelByValue: () => ({ label: 'Example operations' }), getSelectLabel: value => value || '', getOperationOptions: () => [], getAssertionOptions: () => [] }) },
    '@/components/display/ui-flow': loadModule('src/components/display/ui-flow.ts'),
    '@/hooks/use-ui-step-healing-write': writes,
    '@vue-flow/core': { Handle: {}, ConnectionMode: {}, Position: {}, useVueFlow: () => ({ fitView: async () => {}, screenToFlowCoordinate: point => point }) },
    '@arco-design/web-vue': { Message: Object.fromEntries(['success', 'error', 'warning', 'loading'].map(kind => [kind, value => notices.push([kind, value])])), Modal: Object.fromEntries(['warning', 'confirm'].map(kind => [kind, options => { const modal = { ...options, closed: false, close() { this.closed = true } }; confirms.push(modal); return modal }])) },
  }
  const filename = component === 'page' ? 'src/views/uitest/page-steps/details/index.vue' : component === 'canvas' ? 'src/views/uitest/page-steps/details/FlowChart.vue' : `src/components/business/${component}.vue`
  const h = liveHarness({ filename: path.resolve(filename), routePath: '/uitest/page/steps/details',
    bindings: bindings || (component === 'page' ? 'currentPageStepsId,currentPageId,currentStepRecord,stepResources,initializeStep,doRefreshSteps,doRefresh,nodeDetails,nodeDraft,nodeFields,nodeType,flowData,flowSave,flowRevision,flowSaveStatus,flowSaving,selectedNode,configEditing,onNodeClick,onNodeSelect,onFlowChange,onNodeDelete,onNodeDuplicate,saveFormData,updateNodeField,changeStatus,formSaving,nodeDeleting,stepDebug,onRunCase,onRunSelectedNode,onOpenStepBrowser,browserOpening,actionError,elementChecks,loadSelectedNodeElement,getEleName,methodsLoading,methodsError,loadMethods,elementOptions,stepCachePanel,pageElementsPanel,healingPanelVisible,processOptionData,selectedMethodKey,sqlOperationRows,stepsTitle' : component === 'canvas' ? 'flowNodes,flowEdges,legacyFlowData,deleteNodeById,onDrop,onConnect,onNodeDragStop,emitSelectedNode,selectedNodeId,decisionMethodDrafts,controlState' : 'draft,save,records,versions,reloadHealing:load,loadResource,resourceLoading,resourceErrors,nodeCheckpoints,selectedDetail,detailVisible,detailLoading,detailError,showDetail,loadDetail,applyRecord,rejectRecord,rollback,saving,error'),
    props: { pageStepsId: 0, pageId: 0, embedded: false, compact: false, caseInputMode: false, caseId: '', caseStepId: '', caseData: [], caseResult: null, refreshToken: 0, flowData: flow(), tableData: [detail()], nodeTypes: [{ type: 0, label: 'Element', color: 'var(--m-primary)' }], visible: true, pageStepId: 0, record: step(), ...props },
    api: { getUiSteps: async ({ id }) => ({ code: 200, data: [step({ id })] }), getUiPageStepsDetailed: async () => ({ code: 200, data: [detail()] }), getUiPageStepsDetailedById: async id => ({ code: 200, data: [detail({ id })] }), getUiUiElementName: async () => ({ code: 200, data: [detail().ele_name] }), getDataFactoryDatasourceAlias: async () => ({ code: 200, data: [] }), getExecutionResultLatestResolved: async () => ({ code: 200, data: null }), getActiveExecutorTasks: async () => ({ code: 200, data: [] }), getUiPageStepHealRecords: async () => ({ code: 200, data: { items: [healing()] } }), getUiPageStepVersions: async () => ({ code: 200, data: [{ version: 1, source: 'Example', create_time: '' }] }), getUiPageStepReferencedCases: async () => ({ code: 200, data: [] }), postUiPageStepsDetailed: async () => ({ code: 200, data: { ...detail(), flow_data: flow() } }), putUiSteps: async () => ({ code: 200 }), deleteUiPageStepsDetailed: async () => ({ code: 200 }), postUiPageStepHealApply: async () => ({ code: 200 }), getUiStepsTest: async () => ({ code: 200, data: { task_id: 'example-task', slot_id: 'example-slot' } }), ...api }, modules,
  })
  return { ...h, confirms, notices }
}
