import type { NoticeDraft } from './types'
import { useTableIndexColumn, useTableColumn } from '@/hooks/table'
import { updateTimeColumn, updateUserColumn } from '@/utils/update-user'
type NoticeField = {
  label: string
  required: boolean
  placeholder: string
} & (
  | { key: 'name'; type: 'input' }
  | { key: 'mail'; type: 'input-tag' }
  | { key: Exclude<keyof NoticeDraft, 'name' | 'mail'>; type: 'textarea' }
)
export const noticeFields: NoticeField[] = [
  {
    key: 'name',
    label: '通知组名称',
    type: 'input',
    required: true,
    placeholder: '请输入通知组名称',
  },
  {
    key: 'mail',
    label: '邮箱联系人',
    type: 'input-tag',
    required: false,
    placeholder: '请输入邮箱，回车输入多个',
  },
  {
    key: 'work_weixin',
    label: '企微webhook',
    type: 'textarea',
    required: false,
    placeholder: '请输入企微webhook',
  },
  {
    key: 'feishu',
    label: '飞书webhook',
    type: 'textarea',
    required: false,
    placeholder: '请输入飞书webhook',
  },
  {
    key: 'dingding',
    label: '钉钉webhook',
    type: 'textarea',
    required: false,
    placeholder: '请输入钉钉webhook',
  },
]
export const tableColumns = useTableColumn([
  { ...useTableIndexColumn(), align: 'center' },
  {
    title: '通知组名称',
    key: 'name',
    dataIndex: 'name',
    ellipsis: true,
    tooltip: true,
    align: 'left',
    width: 150,
  },
  {
    title: '邮箱联系人',
    key: 'mail',
    dataIndex: 'mail',
    align: 'left',
    ellipsis: true,
    tooltip: true,
    width: 200,
  },
  {
    title: '企微webhook',
    key: 'work_weixin',
    dataIndex: 'work_weixin',
    align: 'left',
    ellipsis: true,
    tooltip: true,
    width: 150,
  },
  {
    title: '飞书webhook',
    key: 'feishu',
    dataIndex: 'feishu',
    align: 'left',
    ellipsis: true,
    tooltip: true,
    width: 150,
  },
  {
    title: '钉钉webhook（不可用）',
    key: 'dingding',
    dataIndex: 'dingding',
    align: 'left',
    ellipsis: true,
    tooltip: true,
    width: 150,
  },
  { ...updateUserColumn(), key: 'update_user' },
  { ...updateTimeColumn(), key: 'update_time' },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    width: 160,
    fixed: 'right',
    align: 'center',
  },
])
