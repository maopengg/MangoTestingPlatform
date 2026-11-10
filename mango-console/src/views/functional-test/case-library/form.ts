import type {
  CaseCategoryOptions,
  CaseProductSelection,
  LibraryCaseEditorRecord,
  LibraryCaseForm,
} from './types'

export function emptyCaseCategories(): CaseCategoryOptions {
  return { category_level_1: [], category_level_2: [], category_level_3: [] }
}

export function caseProductId(value: CaseProductSelection) {
  return Array.isArray(value) ? value[value.length - 1] ?? null : value
}

function relationId(value: LibraryCaseEditorRecord['owner']) {
  return typeof value === 'object' && value !== null ? value.id : value ?? null
}

export function createLibraryCaseForm(record?: LibraryCaseEditorRecord): LibraryCaseForm {
  return {
    id: record?.id ?? null,
    version_no: record?.version_no ?? null,
    case_no: record?.case_no ?? '',
    title: record?.title ?? '',
    project_product: record?.project_product_id ?? relationId(record?.project_product),
    module: record?.module_id ?? relationId(record?.module),
    owner: record?.owner_id ?? relationId(record?.owner),
    category_level_1: record?.category_level_1 ?? '',
    category_level_2: record?.category_level_2 ?? '',
    category_level_3: record?.category_level_3 ?? '',
    priority: record?.priority ?? 1,
    test_types: [...(record?.test_types ?? [0])],
    story_refs: [...(record?.story_refs ?? [])],
    precondition: record?.precondition ?? '',
    test_point: record?.test_point ?? '',
    test_steps: (record?.test_steps ?? [{ action: '', expected: '' }]).map((step) => ({
      action: step.action ?? '',
      expected: step.expected ?? '',
    })),
    expected_result: record?.expected_result ?? '',
    acceptance_source: record?.acceptance_source ?? '',
    automation_status: record?.automation_status ?? 'not_automated',
    scenario_layer: record?.scenario_layer ?? 0,
    scenario_type: record?.scenario_type ?? 0,
    scenario_tags: [...(record?.scenario_tags ?? ['routine_regression'])],
    test_data: record?.test_data ?? '',
    remark: record?.remark ?? '',
    status: record?.status ?? 1,
  }
}

export function libraryCasePayload(form: LibraryCaseForm) {
  // Re-map even typed drafts: grid/display fields must never enter the write contract.
  const fields = createLibraryCaseForm({
    ...form,
    project_product: caseProductId(form.project_product),
    project_product_id: null,
    module_id: null,
    owner_id: null,
  })
  const { id, version_no, ...payload } = fields
  return {
    ...payload,
    test_steps: fields.test_steps.filter((step) => step.action || step.expected),
    ...(id === null ? {} : { id }),
    ...(id === null || version_no === null ? {} : { version_no }),
  }
}
