export type ProductSelection = string | number | Array<string | number> | null
export interface TestFileRecord {
  id: number
  name: string
  file_size?: number | string | null
  file_size_display?: string
  allow_download?: boolean | number | string | null
  project_product?: number | string | { id: number | string; name?: string } | null
  update_user?: { name?: string; username?: string } | null
}
export interface TestFileDraft {
  project_product: ProductSelection
  allow_download: boolean
}
export interface TestFileEditorHandle {
  open(record: TestFileRecord): void
  close(): void
}
export interface TestFileUploadHandle {
  open(product?: string | number | null): void
  close(): void
}
