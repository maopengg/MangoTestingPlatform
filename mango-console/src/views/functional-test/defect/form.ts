import type {
  DefectCaseChoice,
  DefectForm,
  DefectMetadata,
  DefectPlanChoice,
  DefectRelation,
  DefectRouteSeed,
} from './types'

// External response fields are narrowed here; forms and component contracts keep finite types.
export function defectFields(value: unknown): Readonly<Record<string, unknown>> {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Readonly<Record<string, unknown>>)
    : {}
}
const text = (value: unknown) => (value === null || value === undefined ? '' : String(value))
export function defectId(value: unknown): number | null {
  if (Array.isArray(value)) return defectId(value[value.length - 1])
  if (value && typeof value === 'object') return defectId(Reflect.get(value, 'id'))
  if (value === null || value === undefined || value === '' || typeof value === 'boolean')
    return null
  if (typeof value !== 'string' && typeof value !== 'number') return null
  const number = Number(value)
  return Number.isSafeInteger(number) && number >= 0 ? number : null
}
const ids = (value: unknown) =>
  Array.isArray(value)
    ? [
        ...new Set(
          value.flatMap((item) => {
            const id = defectId(item)
            return id === null ? [] : [id]
          })
        ),
      ]
    : []
function relations(value: unknown): DefectRelation[] {
  if (!Array.isArray(value)) return []
  return value.flatMap((item) => {
    const fields = defectFields(item),
      id = defectId(fields.id)
    return id === null
      ? []
      : [
          {
            id,
            case: defectId(fields.case),
            plan_case: defectId(fields.plan_case),
            case_no: text(fields.case_no),
            case_title: text(fields.case_title),
            plan_id: defectId(fields.plan_id),
            plan_name: text(fields.plan_name),
            result: defectId(fields.result),
            executor_name: text(fields.executor_name),
            execute_time: text(fields.execute_time),
          },
        ]
  })
}
export function createDefectForm(value?: unknown): DefectForm {
  const row = defectFields(value),
    linked = relations(row.relations)
  return {
    id: defectId(row.id),
    title: text(row.title),
    project_product: defectId(row.project_product),
    module: defectId(row.module),
    requirement_version: defectId(row.requirement_version),
    source_type: defectId(row.source_type) ?? 2,
    defect_type: defectId(row.defect_type) ?? 0,
    severity: defectId(row.severity) ?? 2,
    priority: defectId(row.priority) ?? 1,
    description: text(row.description),
    precondition: text(row.precondition),
    reproduce_steps: Array.isArray(row.reproduce_steps)
      ? row.reproduce_steps.map((step, index) => {
          const item = defectFields(step)
          return {
            sort: index + 1,
            action: text(item.action),
            expected: text(item.expected),
            actual: text(item.actual),
          }
        })
      : [],
    expected_result: text(row.expected_result),
    actual_result: text(row.actual_result),
    environment: text(row.environment),
    attachment_file_ids: ids(row.attachment_file_ids),
    assignee: defectId(row.assignee),
    case_ids: linked.flatMap((item) => (item.case === null ? [] : [item.case])),
    source_plan_id: linked.find((item) => item.plan_id !== null)?.plan_id ?? null,
    plan_case_ids: linked.flatMap((item) => (item.plan_case === null ? [] : [item.plan_case])),
  }
}
export function defectMetadata(value?: unknown): DefectMetadata {
  const row = defectFields(value)
  return {
    defect_no: text(row.defect_no),
    status: defectId(row.status),
    reporter_name: text(defectFields(row.reporter).name),
    create_time: text(row.create_time),
    update_time: text(row.update_time),
    resolution: defectId(row.resolution),
    resolution_note: text(row.resolution_note),
    resolved_at: text(row.resolved_at),
    closed_at: text(row.closed_at),
    relations: relations(row.relations),
  }
}
export function defectPayload(form: DefectForm) {
  return {
    ...(form.id === null ? {} : { id: form.id }),
    title: form.title,
    project_product: defectId(form.project_product),
    module: defectId(form.module),
    requirement_version: form.requirement_version,
    source_type: form.source_type,
    defect_type: form.defect_type,
    severity: form.severity,
    priority: form.priority,
    description: form.description,
    precondition: form.precondition,
    reproduce_steps: form.reproduce_steps.map((item, index) => ({
      sort: index + 1,
      action: item.action,
      expected: item.expected,
      actual: item.actual,
    })),
    expected_result: form.expected_result,
    actual_result: form.actual_result,
    environment: form.environment,
    attachment_file_ids: [...form.attachment_file_ids],
    assignee: defectId(form.assignee),
    case_ids: [...form.case_ids],
    plan_case_ids: [...form.plan_case_ids],
  }
}
export function defectCaseChoices(value: unknown): DefectCaseChoice[] {
  if (!Array.isArray(value)) throw Error('关联用例列表格式错误')
  return value.map((entry) => {
    const row = defectFields(entry),
      id = defectId(row.id)
    if (id === null) throw Error('关联用例缺少 ID')
    return {
      id,
      case_no: text(row.case_no),
      title: text(row.title),
      module_id: defectId(row.module_id ?? row.module),
      precondition: text(row.precondition),
      test_steps: Array.isArray(row.test_steps)
        ? row.test_steps.map((step) => {
            const item = defectFields(step)
            return { action: text(item.action), expected: text(item.expected) }
          })
        : [],
      expected_result: text(row.expected_result),
      actual_result: text(row.actual_result),
    }
  })
}
export function defectPlanChoices(value: unknown): DefectPlanChoice[] {
  if (!Array.isArray(value)) throw Error('关联计划列表格式错误')
  return value.map((entry) => {
    const row = defectFields(entry),
      id = defectId(row.id)
    if (id === null) throw Error('关联计划缺少 ID')
    return { value: id, label: text(row.name), environment: text(row.environment) }
  })
}
export function defectRouteSeed(query: Readonly<Record<string, unknown>>): DefectRouteSeed | null {
  const product = defectId(query.project_product),
    requirementVersion = defectId(query.requirement_version),
    planId = defectId(query.plan_id)
  const parse = (value: unknown) => ids(text(value).split(',')).filter((id) => id > 0)
  const planCaseIds = parse(query.plan_case_ids || query.plan_case_id),
    caseIds = parse(query.case_ids)
  if (!product || (!requirementVersion && !caseIds.length && (!planId || !planCaseIds.length)))
    return null
  return { projectProduct: product, requirementVersion, planId, planCaseIds, caseIds }
}
