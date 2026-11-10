import type { TestTargetConfig } from './target-config'
export type TargetId = string | number
export type ProductSelection = TargetId | TargetId[] | null
export interface ProbeAddress {
  label: string
  value: string
}
export interface TestObjectRecord {
  id: number
  name: string
  project_product?: TargetId | { id: TargetId; name?: string } | null
  environment: TargetId | null
  auto_type: TargetId | null
  value?: string | null
  target_config?: TestTargetConfig | null
  network_test_addresses?: ProbeAddress[]
  update_user?: { name?: string; username?: string } | null
}
export interface TestObjectDraft {
  project_product: ProductSelection
  name: string
  environment: TargetId | null
  auto_type: TargetId | null
  legacyMode: boolean
  legacyValue: string
  targetConfig: TestTargetConfig
}
export interface TestObjectEditorHandle {
  open(record?: TestObjectRecord, product?: TargetId | null): void
  close(): void
}
export interface ConnectionDialogHandle {
  open(record: TestObjectRecord): void
  close(): void
}
