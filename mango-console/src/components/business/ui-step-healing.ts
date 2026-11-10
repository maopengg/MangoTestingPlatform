import { liveObject } from './ui-live-workbench'
import { requiredStepId, stepArray, type StepId } from './ui-page-step'
import type { UiStepConditionGroup, UiStepHealingPolicy } from '@/types/ui-test/case'

export interface HealingDraft { goal: string; healing_enabled: boolean; healing_policy: UiStepHealingPolicy; entry_criteria: UiStepConditionGroup; success_criteria: UiStepConditionGroup }
export interface HealingCheckpoint { id: StepId; title: string; precondition: UiStepConditionGroup; postcondition: UiStepConditionGroup; originalSignature: string }
export interface HealingAction { action: string; reason: string }
export interface HealingRecord {
  id: StepId; page_step?: StepId; create_time: string; status: string; writeback_status: string; action_types: string[]
  trigger: string; confidence: number; source_version: number; user_message: string; error_message: string
  before_state: { matched_checkpoints: string[] }; after_state: { matched_checkpoints: string[] }
  executed_plan: { actions: HealingAction[] } | null; proposed_plan: { actions: HealingAction[] } | null
}
export interface HealingVersion { id?: StepId; version: number; source: string; create_time: string }
export function readHealingRecord(value: unknown): HealingRecord {
  const row = liveObject(value), plan = (value: unknown) => value == null ? null : { actions: stepArray(liveObject(value).actions ?? []).map(value => { const item = liveObject(value); return { action: String(item.action ?? ''), reason: String(item.reason ?? '') } }) }
  const state = (value: unknown) => ({ matched_checkpoints: stepArray(liveObject(value).matched_checkpoints ?? []).map(String) })
  return { id: requiredStepId(row.id), page_step: row.page_step == null ? undefined : requiredStepId(liveObject(row.page_step).id ?? row.page_step), create_time: String(row.create_time ?? ''), status: String(row.status ?? ''), writeback_status: String(row.writeback_status ?? ''), action_types: stepArray(row.action_types ?? []).map(String), trigger: String(row.trigger ?? ''), confidence: Number(row.confidence ?? 0), source_version: Number(row.source_version ?? 0), user_message: String(row.user_message ?? ''), error_message: String(row.error_message ?? ''), before_state: state(row.before_state), after_state: state(row.after_state), executed_plan: plan(row.executed_plan), proposed_plan: plan(row.proposed_plan) }
}
