import type {
  ApiCaseVersionListRow,
  ApiCaseBatchRunRequestItem,
} from '@/types/api-test/case-version'
import type { ApiParametrizeSuite } from '@/types/api-test/case'
export type CaseEntityId = string | number
export interface CaseListRow extends ApiCaseVersionListRow {
  module?: { id: number; name?: string; full_path?: string } | null
  case_people?: { id: number; name?: string } | null
  level?: number | null
  scenario_layer?: number | null
  scenario_type?: number | null
  scenario_tags?: string[]
  scenario_description?: string | null
  parametrize?: CaseParametrizeSuite[]
}
export interface CaseMetadataDraft {
  project_product: CaseEntityId | CaseEntityId[] | null
  module: CaseEntityId | null
  name: string
  level: number | null
  scenario_layer: number
  scenario_type: number
  scenario_tags: string[]
  scenario_description: string
  case_people: number | null
}
export interface CaseParametrizeSuite extends Omit<ApiParametrizeSuite, 'parametrize'> {
  parametrize: Array<{ key: string; value: string | null; test_envs?: number[] }>
}
export interface UserOption {
  key: number
  title: string
}
export interface RelatedTask {
  relation_key: string
  relation_type: 'manual' | 'automatic'
  task_id: number
  task_name: string
  task_detail_id?: number
  project_product_id?: number
  module_id?: number | null
  module_name?: string
  timing_strategies?: Array<{ name: string }>
  case_people_name?: string
  status: number
  matching_test_envs?: number[]
  execution_scenes?: string[]
}
export type TaskBindingItem = ApiCaseBatchRunRequestItem
