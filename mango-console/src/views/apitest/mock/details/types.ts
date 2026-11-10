import type { MockConfigPayload } from '@/api/apitest/mock'
export type MockDraft = Omit<MockConfigPayload, 'project_product'> & {
  project_product: number | string | Array<number | string> | null
}
export type MockRecord = Omit<MockConfigPayload, 'project_product'> & {
  project_product: number | string | { id: number | string }
}
export interface MockDebugTarget {
  id: number
  requestPath: string
  methods: number[]
}
