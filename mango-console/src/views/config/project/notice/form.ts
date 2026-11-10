import type { NoticeRecord, NoticeDraft } from './types'
export function noticeMail(value: unknown): string[] {
  if (Array.isArray(value))
    return value.filter((email): email is string => typeof email === 'string')
  if (typeof value === 'string')
    return value
      .split(',')
      .map((email) => email.trim())
      .filter(Boolean)
  return []
}
export function createNoticeDraft(record?: NoticeRecord): NoticeDraft {
  return {
    name: record?.name ?? '',
    mail: noticeMail(record?.mail),
    work_weixin: record?.work_weixin ?? '',
    feishu: record?.feishu ?? '',
    dingding: record?.dingding ?? '',
  }
}
export function noticePayload(draft: NoticeDraft) {
  return {
    name: draft.name,
    mail: draft.mail.filter((email) => email !== ''),
    work_weixin: draft.work_weixin || null,
    feishu: draft.feishu || null,
    dingding: draft.dingding || null,
  }
}
