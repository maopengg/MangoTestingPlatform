import { get } from '@/api/http'

export function getRuntimeOverview() {
  return get({
    url: 'system/runtime/overview',
    data: () => ({}),
  })
}

export function getRuntimeServices() {
  return get({
    url: 'system/runtime/services',
    data: () => ({}),
  })
}

export function getRuntimeQueues() {
  return get({
    url: 'system/runtime/queues',
    data: () => ({}),
  })
}

export function getRuntimeDiagnostics() {
  return get({
    url: 'system/runtime/diagnostics',
    data: () => ({}),
  })
}
