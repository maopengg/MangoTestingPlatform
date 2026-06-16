import { deleted, get, post, put } from '@/api/http'

export function getManualSuite(data: Record<string, unknown>) {
  return get({ url: '/functional-test/suite', data: () => data })
}

export function postManualSuite(data: Record<string, unknown>) {
  return post({ url: '/functional-test/suite', data: () => data })
}

export function putManualSuite(data: Record<string, unknown>) {
  return put({ url: '/functional-test/suite', data: () => data })
}

export function deleteManualSuite(id: number) {
  return deleted({ url: '/functional-test/suite', data: () => ({ id }) })
}

export function getManualCase(data: Record<string, unknown>) {
  return get({ url: '/functional-test/case', data: () => data })
}

export function getManualCaseModules(data: Record<string, unknown>) {
  return get({ url: '/functional-test/case/modules', data: () => data })
}

export function postManualCase(data: Record<string, unknown>) {
  return post({ url: '/functional-test/case', data: () => data })
}

export function putManualCase(data: Record<string, unknown>) {
  return put({ url: '/functional-test/case', data: () => data })
}

export function deleteManualCase(data: number | Array<number | string> | Record<string, unknown>) {
  return deleted({
    url: '/functional-test/case',
    data: () => {
      if (typeof data === 'number' || Array.isArray(data)) {
        return { id: data }
      }
      if (Array.isArray(data.ids)) {
        return { ...data, id: data.ids }
      }
      return data
    },
  })
}

export function getManualCaseDetail(id: number) {
  return get({ url: '/functional-test/case/detail', data: () => ({ id }) })
}

export function getFunctionalContextResource(data: Record<string, unknown>) {
  return get({ url: '/functional-test/context-resource', data: () => data })
}

export function postFunctionalContextResource(data: Record<string, unknown>) {
  return post({ url: '/functional-test/context-resource', data: () => data })
}

export function putFunctionalContextResource(data: Record<string, unknown>) {
  return put({ url: '/functional-test/context-resource', data: () => data })
}

export function deleteFunctionalContextResource(id: number) {
  return deleted({ url: '/functional-test/context-resource', data: () => ({ id }) })
}

export function postManualAutomationBind(data: Record<string, unknown>) {
  return post({ url: '/functional-test/case/automation/bind', data: () => data })
}
