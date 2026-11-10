import type { FormItem } from '@/types/components'
import { enableMultiSelectSearch } from '@/utils/search-condition'
import { createIdSearchValue } from '@/utils/id-search'
import { reactive, ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import { useTableIndexColumn, useTableColumn } from '@/hooks/table'
import { createUpdateUserCondition, updateUserColumn } from '@/utils/update-user'

export const apiProtocolOptions = [
  { label: '标准HTTP', value: 'http' },
  { label: 'SSE事件流', value: 'sse' },
  { label: 'JSON-RPC', value: 'json_rpc' },
  { label: 'XML-RPC', value: 'xml_rpc' },
  { label: 'SOAP', value: 'soap' },
  { label: 'GraphQL', value: 'graphql' },
  { label: 'gRPC', value: 'grpc' },
  { label: 'Dubbo', value: 'dubbo' },
  { label: 'Thrift', value: 'thrift' },
  { label: 'MCP', value: 'mcp' },
  { label: 'WebSocket', value: 'websocket' },
]

export const apiProtocolCreateOptions = [
  { label: 'MCP', value: 'mcp' },
  { label: '标准HTTP', value: 'http' },
  { label: 'SSE事件流', value: 'sse' },
  { label: 'WebSocket', value: 'websocket' },
]

export const apiBodyTypeOptions = [
  { label: '无请求体', value: 'none' },
  { label: 'JSON', value: 'json' },
  { label: 'Form', value: 'form' },
  { label: 'Raw', value: 'raw' },
  { label: 'Multipart', value: 'multipart' },
]

export const apiProtocolTabOptions = [
  { label: '标准HTTP', value: 'http' },
  { label: 'SSE事件流', value: 'sse' },
  { label: 'gRPC', value: 'grpc' },
  { label: 'MCP', value: 'mcp' },
  { label: 'WebSocket', value: 'websocket' },
]

export function createConditionItems(): FormItem[] {
  const fields: Array<Omit<FormItem, 'disabled'>> = [
    {
      key: 'id',
      label: 'ID',
      type: 'input',
      placeholder: '请输入接口ID',
      value: createIdSearchValue(),
      reset: function () {
        this.value = ''
      },
    },

    {
      key: 'name',
      label: '接口名称',
      type: 'input',
      placeholder: '请输入接口名称',
      value: ref(''),
      reset: function () {
        this.value = ''
      },
    },
    {
      key: 'url',
      label: 'url',
      value: ref(''),
      type: 'input',
      placeholder: '请输入url',
      reset: function () {},
    },
    {
      key: 'project_product',
      label: '项目/产品',
      value: ref(''),
      type: 'cascader',
      placeholder: '请选择产品',
      optionItems: [],
      reset: function () {},
    },
    {
      key: 'module',
      label: '模块名称',
      value: ref(''),
      type: 'select',
      placeholder: '请选择模块名称',
      optionItems: [],
      reset: function () {},
    },
    {
      key: 'project_product__api_client_type',
      label: '端类型',
      value: ref(''),
      type: 'select',
      placeholder: '请选择端类型',
      optionItems: [],
      reset: function () {},
    },
    {
      key: 'method',
      label: '方法',
      value: ref(''),
      type: 'select',
      placeholder: '请选择方法',
      optionItems: [],
      reset: function () {},
    },
    {
      key: 'protocol_type',
      label: '协议',
      value: ref(''),
      type: 'select',
      placeholder: '请选择协议',
      optionItems: apiProtocolOptions,
      reset: function () {},
    },
    {
      key: 'status',
      label: '状态',
      value: ref(''),
      type: 'select',
      placeholder: '请选择状态',
      optionItems: [],
      reset: function () {},
    },
    createUpdateUserCondition(),
  ]
  return enableMultiSelectSearch(reactive(fields))
}
export function createFormItems(): FormItem[] {
  return [
    {
      label: '项目/产品',
      key: 'project_product',
      value: ref(''),
      placeholder: '请选择项目/产品',
      required: true,
      type: 'cascader',
      validator: function () {
        if (!this.value && this.value !== 0) {
          Message.error(this.placeholder || '')
          return false
        }
        return true
      },
    },
    {
      label: '模块名称',
      key: 'module',
      value: ref(''),
      type: 'select',
      required: true,
      placeholder: '请选择接口归属模块',
      validator: function () {
        if (!this.value && this.value !== 0) {
          Message.error(this.placeholder || '')
          return false
        }
        return true
      },
    },
    {
      label: '接口名称',
      key: 'name',
      value: ref(''),
      type: 'input',
      required: true,
      placeholder: '请输入接口名称',
      validator: function () {
        if (!this.value && this.value !== 0) {
          Message.error(this.placeholder || '')
          return false
        }
        return true
      },
    },
    {
      label: '接口路径',
      key: 'url',
      value: ref(''),
      type: 'input',
      required: true,
      placeholder: '请输入url后面的路径',
      validator: function () {
        if (!this.value && this.value !== 0) {
          Message.error(this.placeholder || '')
          return false
        }
        const value = String(this.value || '').trim()
        if (/^[a-z][a-z0-9+.-]*:\/\//i.test(value) || value.startsWith('//')) {
          Message.error('只允许输入url的路径部分，协议、域名和端口从测试配置-测试对象中读取！')
          return false
        }
        if (!value.startsWith('/')) {
          Message.error('url必须以 / 开头，只保存路径部分')
          return false
        }
        return true
      },
    },
    {
      label: '协议',
      key: 'protocol_type',
      value: ref('http'),
      type: 'select',
      required: true,
      placeholder: '请选择协议类型',
      optionItems: apiProtocolCreateOptions,
      reset: function () {
        this.value = 'http'
      },
      validator: function () {
        if (!this.value && this.value !== 0) {
          Message.error(this.placeholder || '')
          return false
        }
        return true
      },
    },
    {
      label: '请求方法',
      key: 'method',
      value: ref(''),
      type: 'select',
      required: true,
      placeholder: '请选择接口方法',
      validator: function () {
        if (!this.value && this.value !== 0) {
          Message.error(this.placeholder || '')
          return false
        }
        return true
      },
    },
    {
      label: '请求体类型',
      key: 'body_type',
      value: ref('none'),
      type: 'select',
      required: true,
      placeholder: '请选择请求体类型',
      optionItems: apiBodyTypeOptions,
      reset: function () {
        this.value = 'none'
      },
      validator: function () {
        if (!this.value) {
          Message.error(this.placeholder || '')
          return false
        }
        return true
      },
    },
  ]
}
export function createImportFormItems(): FormItem[] {
  return [
    {
      label: '项目/产品',
      key: 'project_product',
      value: ref(''),
      placeholder: '请选择项目/产品',
      required: true,
      type: 'cascader',
      validator: function () {
        if (!this.value && this.value !== 0) {
          Message.error(this.placeholder || '')
          return false
        }
        return true
      },
    },
    {
      label: '模块名称',
      key: 'module',
      value: ref(''),
      type: 'select',
      required: true,
      placeholder: '请选择接口归属模块',
      validator: function () {
        if (!this.value && this.value !== 0) {
          Message.error(this.placeholder || '')
          return false
        }
        return true
      },
    },
    {
      label: '接口名称',
      key: 'name',
      value: ref(''),
      type: 'input',
      required: true,
      placeholder: '请输入接口名称',
      validator: function () {
        if (!this.value && this.value !== 0) {
          Message.error(this.placeholder || '')
          return false
        }
        return true
      },
    },
    {
      label: 'curl',
      key: 'curl_command',
      value: ref(''),
      type: 'textarea',
      required: true,
      placeholder: '请输入复制的cURL（bash）',
      validator: function () {
        if (!this.value && this.value !== 0) {
          Message.error(this.placeholder || '')
          return false
        }
        if (!/^curl\s/.test(String(this.value).trim())) {
          Message.error('请输入有效的 cURL（bash）命令')
          return false
        }
        return true
      },
    },
  ]
}

export const tableColumns = useTableColumn([
  { ...useTableIndexColumn(), align: 'center' },
  {
    title: '接口名称',
    key: 'name',
    dataIndex: 'name',
    align: 'left',
    width: 300,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: 'url',
    key: 'url',
    dataIndex: 'url',
    align: 'left',
    width: 360,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '方法',
    key: 'method',
    dataIndex: 'method',
    width: 70,
  },
  {
    title: '协议',
    key: 'protocol_type',
    dataIndex: 'protocol_type',
    width: 70,
  },
  {
    title: '结果',
    key: 'status',
    dataIndex: 'status',
    width: 70,
  },
  {
    title: '发布状态',
    key: 'publication_status',
    dataIndex: 'publication_status',
    width: 110,
  },
  {
    title: '端类型',
    key: 'client',
    dataIndex: 'client',
    width: 80,
  },
  { ...updateUserColumn(), key: 'update_user' },
  {
    title: '更新时间',
    key: 'update_time',
    dataIndex: 'update_time',
    width: 180,
  },
  {
    title: '项目/产品',
    key: 'project_product',
    dataIndex: 'project_product',
    align: 'left',
    width: 140,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '模块',
    key: 'module',
    dataIndex: 'module',
    align: 'left',
    width: 240,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 160,
  },
])

export const protocolMethodValues: Record<string, number> = { mcp: 7, grpc: 8, websocket: 9 }
export const protocolMethodTitles: Record<string, string> = {
  mcp: 'MCP_CALL',
  grpc: 'GRPC_CALL',
  websocket: 'WEBSOCKET_CONNECT',
}
export const importTemplateFileName = '接口批量上传模版.xlsx'
export const boundCaseColumns = [
  { title: 'Case ID', slotName: 'case_id', width: 80, align: 'center' as const },
  { title: '用例名称', dataIndex: 'case_name', width: 190, ellipsis: true, tooltip: true },
  { title: '负责人', dataIndex: 'case_people_name', width: 100, ellipsis: true, tooltip: true },
  { title: '最新更新人', dataIndex: 'update_user_name', width: 110, ellipsis: true, tooltip: true },
  { title: '更新时间', dataIndex: 'update_time', width: 180 },
  {
    title: '操作',
    slotName: 'actions',
    fixed: 'right' as const,
    width: 160,
    align: 'center' as const,
  },
]
