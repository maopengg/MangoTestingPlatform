import type { CaseMetadataDraft, CaseListRow } from './types'
import { getOptionId } from '@/utils/business-format'
export function createMetadataDraft(
  record?: CaseListRow,
  defaults: { projectProduct?: string | number | null; module?: string | number | null } = {}
): CaseMetadataDraft {
  return {
    project_product: record?.project_product?.id ?? defaults.projectProduct ?? null,
    module: record?.module?.id ?? (defaults.module === '__all__' ? null : defaults.module) ?? null,
    name: record?.name ?? '',
    level: record?.level ?? null,
    scenario_layer: record?.scenario_layer ?? 0,
    scenario_type: record?.scenario_type ?? 0,
    scenario_tags: [...(record?.scenario_tags ?? [])],
    scenario_description: record?.scenario_description ?? '',
    case_people: record?.case_people?.id ?? null,
  }
}
export function metadataPayload(draft: CaseMetadataDraft) {
  return {
    ...draft,
    project_product: getOptionId(draft.project_product),
    module: getOptionId(draft.module),
    scenario_tags: [...draft.scenario_tags],
    level: draft.level ?? undefined,
    case_people: draft.case_people ?? undefined,
  }
}
