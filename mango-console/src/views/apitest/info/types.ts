export type ApiEntityId = number | string
export interface ApiInfoListRow {
  id: ApiEntityId
  name: string
  url: string
  protocol_type: string
  method: number | null
  body_type?: string
  status: number
  project_product?: {
    id: ApiEntityId
    name: string
    api_client_type?: number
    project?: { id: ApiEntityId; name: string }
  } | null
  module?: { id: ApiEntityId; name?: string; full_path?: string } | null
  publication_status?: 'unpublished' | 'published' | 'draft_changed'
  published_release_id?: ApiEntityId | null
  published_revision_id?: ApiEntityId | null
  published_version_label?: string | null
  has_unpublished_changes?: boolean
  mcp_binding?: McpBinding | null
}
export interface McpBinding {
  tool_name?: string
  tool_type?: string
  tool_enabled?: boolean
  transport_type?: number
  // 服务绑定的协议扩展字段在元信息编辑时原样保留。
  [key: string]: unknown
}
export interface ApiInfoMetadataRecord extends Omit<ApiInfoListRow, 'project_product' | 'module'> {
  project_product?: ApiEntityId | ApiInfoListRow['project_product']
  module?: ApiEntityId | ApiInfoListRow['module']
}
export interface ApiInfoDraft {
  project_product: ApiEntityId | ApiEntityId[] | null
  module: ApiEntityId | null
  name: string
  url: string
  protocol_type: string
  method: number | null
  body_type: string
  curl_command: string
  tool_name: string
}
export interface UserOption {
  key: ApiEntityId
  title: string
}
export interface BoundApiCase {
  case_id: ApiEntityId
  case_name: string
  project_product_id?: ApiEntityId | null
  case_people_name?: string | null
  update_user_name?: string | null
  update_time?: string | null
}
export interface GrpcService {
  id: ApiEntityId
  name?: string
  service_name?: string
  project_product_id?: ApiEntityId | null
  module_id?: ApiEntityId | null
}
export interface GrpcMethod {
  id: ApiEntityId
  full_method?: string
  name?: string
  client_streaming?: boolean
  server_streaming?: boolean
  imported_api_info_id?: ApiEntityId | null
}
export interface NavigationDefaults {
  projectProduct?: ApiEntityId | null
  module?: ApiEntityId | null
}
