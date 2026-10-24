import type {
  ApiGeneralAssertionItem,
  ApiGeneralAssertionParameter,
} from '@/types/api-test/case-parameter'
import type {
  AssertionEditorGroup,
  AssertionMethodItem,
  AssertionMethodTypeGroup,
} from '@/types/assertion'

let assertionStorageSequence = 0

function createAssertionStorageId(prefix: string) {
  assertionStorageSequence += 1
  return `${prefix}-${Date.now()}-${assertionStorageSequence}`
}

function flattenMethods(methods: AssertionMethodTypeGroup[]) {
  return methods.flatMap((typeGroup) =>
    (typeGroup.children || []).flatMap((classGroup) => classGroup.children || [])
  )
}

function serializeParameterValue(value: unknown) {
  if (value === undefined || value === null) return ''
  if (typeof value === 'string') return value
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

function methodParameters(
  method: AssertionMethodItem | undefined,
  values: Record<string, unknown>
): ApiGeneralAssertionParameter[] {
  return (method?.parameter || []).map((parameter) => ({
    d: Boolean(parameter.d),
    f: parameter.f,
    n: parameter.n || '',
    p: parameter.p || '',
    v: serializeParameterValue(values[parameter.f]),
  }))
}

/**
 * 将公共断言编辑模型转换成现有 API Case 的 ass_general 存储结构。
 * 编辑器内部 ID 和嵌套分组仅服务界面，不会写入数据库。
 */
export function toApiGeneralAssertions(
  groups: AssertionEditorGroup[],
  methods: AssertionMethodTypeGroup[]
): ApiGeneralAssertionItem[] {
  const methodMap = new Map(flattenMethods(methods).map((method) => [method.value, method]))
  return groups.flatMap((group) =>
    group.assertions.map((assertion) => {
      const method = methodMap.get(assertion.method)
      return {
        group_name: group.name,
        group_logic: group.logic,
        method: assertion.method,
        value: {
          label: method?.label || assertion.method,
          value: assertion.method,
          parameter: methodParameters(method, assertion.values),
        },
      }
    })
  )
}

/** 将已有 ass_general 数据还原成公共断言编辑模型。 */
export function fromApiGeneralAssertions(
  assertions: ApiGeneralAssertionItem[]
): AssertionEditorGroup[] {
  const groups = new Map<string, AssertionEditorGroup>()
  assertions.forEach((assertion, index) => {
    const storedName = assertion.group_name?.trim()
    const groupKey = storedName || `__ungrouped_${index}`
    const group = groups.get(groupKey) || {
      id: createAssertionStorageId('group'),
      name: storedName || `断言组${groups.size + 1}`,
      logic: assertion.group_logic === 'OR' ? 'OR' : 'AND',
      assertions: [],
    }
    group.assertions.push({
      id: createAssertionStorageId('assertion'),
      method: assertion.value?.value || assertion.method || '',
      values: Object.fromEntries(
        (assertion.value?.parameter || []).map((parameter) => [parameter.f, parameter.v])
      ),
    })
    groups.set(groupKey, group)
  })
  return Array.from(groups.values())
}
