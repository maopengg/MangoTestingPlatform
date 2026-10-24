import { Message } from '@arco-design/web-vue'
import { Ref, VNode } from 'vue'

export interface HeaderCellStyle {
  backgroundColor?: string
  color: string
}

export interface TableConfig {
  dataList: Array<any>
  stripe: boolean
  border: boolean
  size: string
  headerCellStyle: HeaderCellStyle
  height: string | number
  tableLoading: boolean
}

export interface SelectOptionItem {
  label: string
  value: any
}

export interface TableSearchItem {
  key: string | number
  label: string
  value: any
  placeholder?: string
  associatedOption?: string
  onChange?: (value: any, associationItem: string) => void
  span?: number
}

export interface FormItem extends TableSearchItem {
  required?: boolean
  validator?: (value?: FormItem, message?: typeof Message) => boolean
  hidden?: boolean
  type?: string
  maxLength?: number
  min?: number
  rows?: number
  disabled?: Ref<boolean>
  optionItems?: Array<SelectOptionItem>
  /** 搜索下拉框是否允许选择多个值。 */
  multiple?: boolean
  /** 多选搜索使用集合查询，提交为 `key__in=value1,value2`。 */
  searchOperator?: 'in'
  path?: string
  reset?: (formItem?: FormItem) => void
  render?: (formItem: FormItem) => VNode
}

export interface LikeSearchModel {
  conditionItems: Array<TableSearchItem> | null
  extraParams?: (() => Record<string, any>) | Record<string, any>
}

export interface TablePropsType {
  title: string
  key: string
  sortIndex: number
  checked: boolean
}

// export type ModalDialogType = InstanceType<typeof ModalDialog>

export type ModalDialogType = InstanceType<
  typeof import('../components/overlays/ModalDialog.vue').default
>

// export type DataFormType = InstanceType<typeof import('../components/common/DataForm').default>

export type TableHeaderType = InstanceType<
  typeof import('../components/common/TableHeader.vue').default
>

export type TableFooterType = InstanceType<
  typeof import('../components/common/TableFooter.vue').default
>

// FlowChart 组件相关类型定义

export type Position = { x: number; y: number }
export type ConnectorPosition = 'top' | 'right' | 'bottom' | 'left'
export type Connector = { node_id: string; position: ConnectorPosition }

// 为了兼容性，保留原有的类型别名
export type UINode = {
  id: string
  position: Position
  type: number
  label: string
  config?: Record<any, any>
}
export type UIEdge = { id: string; source: Connector; target: Connector }

export interface UiStepControl {
  close_after_execution: boolean
  before_wait_seconds: number
  after_wait_seconds: number
  close_live_after_execution: boolean
}

export interface FlowData {
  nodes: UINode[]
  edges: UIEdge[]
}
