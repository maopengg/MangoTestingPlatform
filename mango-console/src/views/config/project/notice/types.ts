export interface NoticeRecord {
  id: number
  name: string
  mail?: string[] | string | null
  work_weixin?: string | null
  feishu?: string | null
  dingding?: string | null
  project?: number | { id: number; name?: string }
  update_time?: string
  update_user?: { name?: string; username?: string } | null
}
export interface NoticeDraft {
  name: string
  mail: string[]
  work_weixin: string
  feishu: string
  dingding: string
}
export interface NoticeEditorHandle {
  open(record?: NoticeRecord): void
  close(): void
}
export interface NoticeProjectContext {
  id: number | null
  name: string
}
