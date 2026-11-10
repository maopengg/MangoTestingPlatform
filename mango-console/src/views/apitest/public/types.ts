export type PublicEntityId = number | string
export type PublicEnvironment = number | string
export interface PublicProduct {
  id: PublicEntityId
  name: string
  project?: { id: PublicEntityId; name: string }
}
export interface PublicDatasource {
  id: PublicEntityId
  name: string
  status?: number | string
  db_type?: number | string
  disabled?: boolean
}
export interface PublicRecord {
  id: number
  project_product: PublicProduct | PublicEntityId | null
  type: number
  name: string
  key: string
  value: string
  status: number
  test_envs?: PublicEnvironment[] | null
  test_env?: PublicEnvironment | null
  datasource_alias?: PublicDatasource | PublicEntityId | null
  update_user?: { id: PublicEntityId; name: string } | null
  update_time?: string
}
export interface PublicDraft {
  project_product: PublicEntityId | PublicEntityId[] | null
  type: number | null
  test_envs: PublicEnvironment[]
  name: string
  key: string
  value: string
  datasource_alias: PublicEntityId | null
}
export interface PublicUserOption {
  key: PublicEntityId
  title: string
}
