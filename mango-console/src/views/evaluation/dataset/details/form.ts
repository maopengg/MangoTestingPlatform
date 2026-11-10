import { cloneLosslessJson } from '@/utils/lossless-json'
import type { DatasetItem, DatasetItemForm } from '../types'

export function createItemForm(
  versionId: number | null = null,
  record?: DatasetItem
): DatasetItemForm {
  return {
    id: record?.id,
    version_id: versionId,
    input_text: JSON.stringify(record?.input_data ?? {}),
    expected_text: JSON.stringify(record?.expected_output ?? {}),
    context_text: JSON.stringify(record?.context ?? {}),
    tags_text: (record?.tags || []).join(','),
    priority: record?.priority || 'P1',
    weight: record?.weight ?? 1,
    enabled: record?.enabled ?? true,
    grading_config: cloneLosslessJson(
      record?.grading_config ?? { schema_version: 1, mode: 'inherit', graders: [] }
    ),
    scenario: cloneLosslessJson(record?.scenario ?? { group_key: '', order: 0, turns: [] }),
    data_source: cloneLosslessJson(record?.data_source ?? { kind: 'manual' }),
  }
}

export function itemPayload(form: DatasetItemForm) {
  return {
    id: form.id,
    input_data: JSON.parse(form.input_text) as unknown,
    expected_output: JSON.parse(form.expected_text) as unknown,
    context: JSON.parse(form.context_text || '{}') as unknown,
    tags: form.tags_text
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean),
    priority: form.priority || 'P1',
    weight: form.weight ?? 1,
    enabled: form.enabled,
    grading_config: cloneLosslessJson(form.grading_config),
    scenario: cloneLosslessJson(form.scenario),
    data_source: cloneLosslessJson(form.data_source),
  }
}
