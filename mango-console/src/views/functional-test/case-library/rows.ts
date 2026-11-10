import { formatModulePath, formatProjectProductPath } from '@/utils/business-format'
import { formatAutomationBindings } from './config'
import { createLibraryCaseForm } from './form'
import type {
  CaseSelection,
  LibraryCaseRow,
  LibraryDraftDefaults,
  LibraryPersistedCaseRow,
} from './types'

function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw Error('用例记录格式错误')
  return value as Record<string, unknown>
}
function text(value: unknown, fallback = ''): string {
  if (value === undefined || value === null) return fallback
  if (typeof value !== 'string') throw Error('用例文本字段格式错误')
  return value
}
function integer(value: unknown, fallback?: number): number {
  if (value === undefined || value === null) {
    if (fallback !== undefined) return fallback
    throw Error('用例 ID 或版本缺失')
  }
  if (typeof value !== 'number' || !Number.isSafeInteger(value)) throw Error('用例数字字段格式错误')
  return value
}
function selection(value: unknown): CaseSelection | null {
  if (value === undefined || value === null) return null
  if (typeof value === 'string' || typeof value === 'number') return value
  return integer(object(value).id)
}
function list(value: unknown): unknown[] {
  if (value === undefined || value === null) return []
  if (!Array.isArray(value)) throw Error('用例多值字段格式错误')
  return value
}

export function normalizeLibraryCaseRow(value: unknown): LibraryPersistedCaseRow {
  const source = object(value)
  const id = integer(source.id),
    version = integer(source.version_no)
  if (id <= 0 || version <= 0) throw Error('用例 ID 或版本无效')
  const owner = source.owner && typeof source.owner === 'object' ? object(source.owner) : null
  const bindings = list(source.bindings).map((item) => {
    const binding = object(item)
    return {
      automation_type: integer(binding.automation_type),
      automation_case_id: integer(binding.automation_case_id),
      automation_case_name: text(binding.automation_case_name),
    }
  })
  return {
    id,
    version_no: version,
    case_no: text(source.case_no),
    title: text(source.title),
    category_level_1: text(source.category_level_1),
    category_level_2: text(source.category_level_2),
    category_level_3: text(source.category_level_3),
    priority: integer(source.priority, 1),
    test_types: list(source.test_types).map((item) => integer(item)),
    story_refs: list(source.story_refs).map((item) => text(item)),
    precondition: text(source.precondition),
    test_point: text(source.test_point),
    test_steps: list(source.test_steps).map((item) => {
      const step = object(item)
      return { action: text(step.action), expected: text(step.expected) }
    }),
    expected_result: text(source.expected_result),
    acceptance_source: text(source.acceptance_source),
    test_data: text(source.test_data),
    scenario_layer: integer(source.scenario_layer, 0),
    scenario_type: integer(source.scenario_type, 0),
    scenario_tags: list(source.scenario_tags).map((item) => text(item)),
    automation_status: text(source.automation_status, 'not_automated'),
    remark: text(source.remark),
    status: integer(source.status, 1),
    project_product_id: selection(source.project_product_id ?? source.project_product),
    module_id: selection(source.module_id ?? source.module),
    owner_id: selection(source.owner_id ?? source.owner),
    project_product_path: formatProjectProductPath(source.project_product),
    module_path: formatModulePath(source.module),
    owner_name: text(owner?.name) || text(owner?.username) || '-',
    bindings,
    automation_bindings: formatAutomationBindings(bindings),
    update_time: text(source.update_time, '-'),
    __draft: false,
    __touched: false,
  }
}

export function isPersistedCaseRow(row: LibraryCaseRow): row is LibraryPersistedCaseRow {
  return !row.__draft && typeof row.id === 'number' && typeof row.version_no === 'number'
}

export function createLibraryDraftRow(
  id: string,
  defaults: LibraryDraftDefaults,
  source?: LibraryCaseRow
): LibraryCaseRow {
  const form = createLibraryCaseForm()
  const {
    id: _id,
    version_no: _version,
    project_product: _product,
    module: _module,
    owner: _owner,
    ...fields
  } = form
  return {
    ...fields,
    project_product_id: defaults.productId,
    project_product_path: defaults.productPath,
    module_id: defaults.moduleId,
    module_path: defaults.modulePath,
    owner_id: defaults.ownerId,
    owner_name: defaults.ownerName,
    automation_bindings: '-',
    __touched: false,
    ...source,
    test_types: [...(source?.test_types ?? fields.test_types)],
    story_refs: [...(source?.story_refs ?? fields.story_refs)],
    scenario_tags: [...(source?.scenario_tags ?? fields.scenario_tags)],
    // Every copy owns its nested draft, not just a new outer row.
    test_steps: (source?.test_steps ?? []).map((step) => ({
      action: step.action,
      expected: step.expected,
    })),
    bindings: (source?.bindings ?? []).map((binding) => ({ ...binding })),
    id,
    draft_id: id,
    __draft: true,
    version_no: '草稿',
    update_time: '-',
  }
}

export function libraryDraftHasContent(row: LibraryCaseRow): boolean {
  return (
    row.__touched ||
    [
      row.case_no,
      row.title,
      row.test_point,
      row.precondition,
      row.expected_result,
      row.remark,
    ].some((value) => String(value ?? '').trim().length > 0)
  )
}

export function libraryDraftPayload(row: LibraryCaseRow) {
  return {
    draft_id: row.draft_id,
    case_no: String(row.case_no ?? '').trim(),
    title: String(row.title ?? '').trim(),
    category_level_1: String(row.category_level_1 ?? '').trim(),
    category_level_2: String(row.category_level_2 ?? '').trim(),
    category_level_3: String(row.category_level_3 ?? '').trim(),
    priority: row.priority,
    test_types: [...row.test_types],
    story_refs: [...row.story_refs],
    precondition: row.precondition ?? '',
    test_point: String(row.test_point ?? '').trim(),
    test_steps: row.test_steps.map((step) => ({ action: step.action, expected: step.expected })),
    expected_result: row.expected_result ?? '',
    acceptance_source: row.acceptance_source ?? '',
    test_data: row.test_data ?? '',
    scenario_layer: row.scenario_layer,
    scenario_type: row.scenario_type,
    scenario_tags: [...row.scenario_tags],
    automation_status: row.automation_status,
    remark: row.remark ?? '',
    status: row.status,
    owner_id: row.owner_id,
    project_product_id: row.project_product_id,
    module_id: row.module_id,
  }
}
