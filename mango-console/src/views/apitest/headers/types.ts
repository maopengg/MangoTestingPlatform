export type HeaderEntityId = number | string

export interface HeaderProduct {
  id: HeaderEntityId
  name: string
  api_client_type?: number
  project?: { id: HeaderEntityId; name: string }
}

export interface HeaderRecord {
  id: number
  project_product: HeaderProduct | null
  key: string
  value: string
  status: number
  update_user?: { id: HeaderEntityId; name: string } | null
  update_time?: string
}

export interface HeaderDraft {
  project_product: HeaderEntityId | HeaderEntityId[] | null
  key: string
  value: string
}

export interface HeaderUserOption {
  key: HeaderEntityId
  title: string
}
