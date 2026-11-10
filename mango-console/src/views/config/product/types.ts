export type ProductId = string | number
export interface ProductOption {
  key: ProductId
  title: string
}
export interface ProductRecord {
  id: ProductId
  name: string
  project: { id: ProductId; name: string }
  owners: Array<{ id: ProductId; name?: string }>
  ui_client_type: ProductId
  api_client_type: ProductId
  description?: string | null
  update_user?: { id: ProductId } | null
}
export interface ProductDraft {
  project: ProductId | null
  name: string
  owners: ProductId[]
  ui_client_type: ProductId | null
  api_client_type: ProductId | null
  description: string
}
export interface ProductEditorHandle {
  open(record?: ProductRecord, projectId?: string): void
  close(): void
}
