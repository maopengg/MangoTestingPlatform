import path from 'node:path'
import * as vue from 'vue'
import { harness } from './case-details-harness.mjs'
export function evaluationComponent(name, bindings, options = {}) {
  const user = vue.reactive({ userId: 1, roleId: 1, token: 'fixture', selected_environment: 2 })
  const lifecycle = {},
    notices = [],
    navigations = [],
    route = vue.reactive({ path: '/evaluation/case/details', query: { id: '1' } }),
    polling = { starts: 0, stops: 0 }
  let pollingRefresh,
    pollingPause,
    pollingVersion = 0
  const state = harness(name, bindings, {
    ...options,
    filename: options.filename || path.resolve('src/views/evaluation/components', `${name}.vue`),
    base: path.resolve('src/views/evaluation'),
    modules: {
      vue: {
        ...vue,
        useId: () => 'fixture-field',
        useSlots: () => ({}),
        onBeforeUnmount: (fn) => (lifecycle.unmount = fn),
        onDeactivated: (fn) => (lifecycle.deactivate = fn),
        onActivated: (fn) => (lifecycle.activate = fn),
      },
      'vue-router': {
        useRoute: () => route,
        useRouter: () => ({ push: (value) => navigations.push(value) }),
        onBeforeRouteLeave: (fn) => (lifecycle.leave = fn),
        onBeforeRouteUpdate: (fn) => (lifecycle.update = fn),
      },
      '@/store/modules/user': { default: () => user },
      '@/hooks/use-page-polling': {
        usePagePolling: (refresh, pause) => {
          pollingRefresh = refresh
          pollingPause = pause
          return {
            start: () => polling.starts++,
            stop: () => polling.stops++,
            isAvailable: () => true,
          }
        },
      },
      './useEvaluationEnums': {
        useEvaluationEnums: () => ({
          options: () => [],
          title: (_key, value) => value,
          color: () => 'blue',
        }),
      },
      '@arco-design/web-vue': {
        Modal: options.Modal,
        Message: {
          success: (value) => notices.push(value),
          error: (value) => notices.push(value),
          warning: (value) => notices.push(value),
        },
      },
      ...options.modules,
    },
  })
  return {
    ...state,
    user,
    notices,
    navigations,
    lifecycle,
    route,
    polling,
    poll() {
      const version = pollingVersion
      return pollingRefresh?.({ isCurrent: () => version === pollingVersion })
    },
    pausePolling() {
      ++pollingVersion
      pollingPause?.()
    },
    dispose() {
      lifecycle.unmount?.()
      state.close()
    },
  }
}
export const caseConfig = () => ({
  schema_version: 1,
  ai: { judge_profile_id: null, summary_profile_id: null, answer_profile_id: null },
  data_selection: { exclude: false, item_ids: [] },
  target: {
    type: 'script',
    ref_id: null,
    version_ref: null,
    parameters: { code: 'def main(input, context): return {}' },
  },
  mapping: { output: { paths: [] } },
  grading: {
    default_graders: [],
    required_graders: [],
    quality_gates: [],
    aggregation: { policy_version: 2, min_valid_rate: 0.95, min_effect_pass_rate: 0.8 },
  },
  execution: {
    max_concurrency: 1,
    item_timeout_seconds: 600,
    retry_count: 0,
    repeat_count: 1,
    stop_on_critical_failure: false,
  },
})
export const caseRecord = () => ({
  id: 1,
  name: 'Example',
  status: 'enabled',
  dataset_id: 2,
  dataset_version: 3,
  dataset_version_no: 1,
  config: caseConfig(),
})
export function caseEditor(api = {}, props = {}) {
  return evaluationComponent(
    'CaseEditor',
    'form,config,catalog,ready,loading,saving,saveError,dirty,baseline,open,cancel,flushConfiguration:flush,save,loadDatasets,datasetsError,loadVersions,versionsError,loadAiProfiles,aiError,datasets,versions,aiProfiles,advancedSection,jsonSection',
    {
      props: {
        embedded: true,
        caseId: 1,
        initialRecord: caseRecord(),
        initialCatalog: [],
        ...props,
      },
      api: {
        getEvaluationDatasets: async () => ({ data: [{ id: 2, name: 'Example dataset' }] }),
        getDatasetVersions: async () => ({
          data: { items: [{ id: 3, version_no: 1, status: 'published' }], count: 1 },
        }),
        getEvaluationAiProfiles: async () => ({ data: [] }),
        getEvaluationCase: async () => ({ data: caseRecord() }),
        updateEvaluationCase: async () => ({ code: 200 }),
        ...api,
      },
    }
  )
}
