import { get } from '@/api/http'

export const getPerfCapacityOverview = () => get<unknown>({ url: '/perf/capacity/overview' })
