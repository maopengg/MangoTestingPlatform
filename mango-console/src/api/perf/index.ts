import { deleted, get, post, put } from '@/api/http'
import request from '@/api/axios.config'

export const getPerfScenarios = (data: Record<string, unknown>) =>
  get({ url: '/perf/scenario', data: () => data })
export const createPerfScenario = (data: Record<string, unknown>) =>
  post({ url: '/perf/scenario', data: () => data })
export const updatePerfScenario = (data: Record<string, unknown>) =>
  put({ url: '/perf/scenario', data: () => data })
export const deletePerfScenario = (id: number) =>
  deleted({ url: '/perf/scenario', data: () => ({ id }) })
export const getPerfScenario = (id: number | string) =>
  get({ url: `/perf/scenario/${id}`, data: () => ({}) })
export const getPerfExecutors = () => get({ url: '/perf/scenario/executors', data: () => ({}) })
export const getPerfScenarioSourceCases = (id: number | string) =>
  get({ url: `/perf/scenario/${id}/source-api-cases`, data: () => ({}) })
export const savePerfScenarioConfiguration = (id: number | string, data: Record<string, unknown>) =>
  put({ url: `/perf/scenario/${id}/configuration`, data: () => data })
export const validatePerfScenario = (id: number | string) =>
  post({ url: `/perf/scenario/${id}/validate`, data: () => ({}) })
export const getPerfScenarioScriptPreview = (id: number | string) =>
  get({ url: `/perf/scenario/${id}/script-preview`, data: () => ({}) })
export const executePerfScenario = (id: number | string, data: Record<string, unknown>) =>
  post({ url: `/perf/scenario/${id}/execute`, data: () => data })
export const preflightPerfScenario = (id: number | string, data: Record<string, unknown>) =>
  post({ url: `/perf/scenario/${id}/preflight`, data: () => data })

export const getPerfRuns = (data: Record<string, unknown>) =>
  get({ url: '/perf/run', data: () => data })
export const getPerfRun = (id: number | string) => get({ url: `/perf/run/${id}`, data: () => ({}) })
export const getPerfRunOverview = (id: number | string) =>
  get({ url: `/perf/run/${id}/overview`, data: () => ({}) })
export const getPerfRunMetrics = (id: number | string, data: Record<string, unknown>) =>
  get({ url: `/perf/run/${id}/metrics`, data: () => data })
export const getPerfRunRequests = (id: number | string) =>
  get({ url: `/perf/run/${id}/requests`, data: () => ({}) })
export const getPerfRunStages = (id: number | string) =>
  get({ url: `/perf/run/${id}/stages`, data: () => ({}) })
export const getPerfRunNodes = (id: number | string) =>
  get({ url: `/perf/run/${id}/nodes`, data: () => ({}) })
export const getPerfRunCaptureDownload = (id: number | string, nodeId: number) =>
  get({ url: `/perf/run/${id}/nodes/${nodeId}/capture/download`, data: () => ({}) })
export const getPerfRunThresholds = (id: number | string) =>
  get({ url: `/perf/run/${id}/thresholds`, data: () => ({}) })
export const getPerfRunValidity = (id: number | string) =>
  get({ url: `/perf/run/${id}/validity`, data: () => ({}) })
export const getPerfRunErrors = (id: number | string) =>
  get({ url: `/perf/run/${id}/errors`, data: () => ({}) })
export const stopPerfRun = (id: number | string) =>
  post({ url: `/perf/run/${id}/stop`, data: () => ({}) })
export const cancelPerfRun = (id: number | string) =>
  post({ url: `/perf/run/${id}/cancel`, data: () => ({}) })
export const setPerfRunBaseline = (id: number | string, name: string) =>
  post({ url: `/perf/run/${id}/set-baseline`, data: () => ({ name }) })
export const getPerfRunComparison = (id: number | string) =>
  get({ url: `/perf/run/${id}/comparison`, data: () => ({}) })
export const exportPerfRun = (id: number | string) =>
  request.get(`/perf/run/${id}/export`, { responseType: 'blob' })
export const rerunPerfRun = (id: number | string, productionLoadConfirmed = false) =>
  post({
    url: `/perf/run/${id}/rerun`,
    data: () => ({ production_load_confirmed: productionLoadConfirmed }),
  })
export const subscribePerfRun = (id: number | string) =>
  post({ url: `/perf/run/${id}/realtime-subscription`, data: () => ({}) })
export const unsubscribePerfRun = (id: number | string) =>
  deleted({ url: `/perf/run/${id}/realtime-subscription`, data: () => ({}) })
