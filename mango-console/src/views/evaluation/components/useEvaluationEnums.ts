import { useEnum } from '@/store/modules/get-enum'

export function useEvaluationEnums() {
  const store = useEnum()
  type Key =
    | 'evaluation_case_status'
    | 'evaluation_version_status'
    | 'evaluation_target_type'
    | 'evaluation_execution_status'
    | 'evaluation_item_execution_status'
    | 'evaluation_grade_status'
    | 'evaluation_verdict'
    | 'evaluation_answer_verdict'
    | 'evaluation_memory_fact_status'
    | 'evaluation_workflow_stage'
    | 'evaluation_workflow_scope'
    | 'evaluation_sequence'
    | 'evaluation_turn_kind'
    | 'evaluation_item_source'
  const title = (key: Key, value: unknown) =>
    store[key]?.find((item) => String(item.key) === String(value))?.title || String(value ?? '—')
  const options = (key: Key) =>
    (store[key] || []).map((item) => ({ label: item.title, value: item.key }))
  const color = (value: string) =>
    ((
      {
        passed: 'green',
        success: 'green',
        completed: 'green',
        graded: 'green',
        enabled: 'green',
        published: 'green',
        failed: 'red',
        timeout: 'orange',
        warning: 'orange',
        invalid: 'orange',
        running: 'arcoblue',
        grading: 'arcoblue',
        preparing: 'arcoblue',
        pending: 'gray',
        draft: 'orange',
      } as Record<string, string>
    )[value] || 'gray')
  return { title, options, color }
}
