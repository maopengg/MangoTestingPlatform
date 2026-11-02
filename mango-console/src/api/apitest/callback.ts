import { get } from '@/api/http'
import request from '@/api/axios.config'

export function getCallbackResults(data: Record<string, unknown>) {
  return get({ url: '/api/case/callback/results', data: () => data })
}

export function getCallbackDeliveries(data: Record<string, unknown>) {
  return get({ url: '/api/case/callback/deliveries', data: () => data })
}

export function downloadCallbackEvidence(data: Record<string, unknown>) {
  return request.get('/api/case/callback/evidence/download', { params: data, responseType: 'blob' })
}
