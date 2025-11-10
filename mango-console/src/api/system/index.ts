import { get } from '@/api/http'

export function getSystemActivityLevel() {
  return get({
    url: 'system/index/activity/level',
    data: () => {
      return {}
    },
  })
}

export function getSystemIndexStatistics() {
  return get({
    url: 'system/index/statistics',
    data: () => {
      return {}
    },
  })
}

export function getSystemCaseResultWeekSum() {
  return get({
    url: 'system/index/result/week/sum',
    data: () => {
      return {}
    },
  })
}

export function getSystemCaseRunSum() {
  return get({
    url: 'system/index/run/sum',
    data: () => {
      return {}
    },
  })
}

export function getSystemCaseSum() {
  return get({
    url: 'system/index/sum',
    data: () => {
      return {}
    },
  })
}
