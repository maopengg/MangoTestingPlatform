import {FormItem} from '@/types/components'
import {reactive, ref} from 'vue'
import {Message} from '@arco-design/web-vue'
import {useTable, useTableColumn} from '@/hooks/table'

const table = useTable()

export const formItems: FormItem[] = reactive([

    {
        label: '通知组名称',
        key: 'name',
        value: ref(''),
        type: 'input',
        required: true,
        placeholder: '请输入通知组名称',
        validator: function () {
            if (this.value.length === 0) {
                Message.error(this.placeholder || '')
                return false
            }
            return true
        },
    },
    {
        label: '邮箱联系人',
        key: 'mail',
        value: ref([]),
        type: 'input-tag',
        required: false,
        placeholder: '请输入邮箱，回车输入多个',
        validator: function () {
            return true
        },
    },
    {
        label: '企微webhook',
        key: 'work_weixin',
        value: ref(''),
        type: 'textarea',
        required: false,
        placeholder: '请输入企微webhook',
        validator: function () {
            return true
        },
    },
    {
        label: '飞书webhook',
        key: 'feishu',
        value: ref(''),
        type: 'textarea',
        required: false,
        placeholder: '请输入飞书webhook',
        validator: function () {
            return true
        },
    },
    {
        label: '钉钉webhook',
        key: 'dingding',
        value: ref(''),
        type: 'textarea',
        required: false,
        placeholder: '请输入钉钉webhook',
        validator: function () {
            return true
        },
    },
])

export const tableColumns = useTableColumn([
    table.indexColumn,
    {
        title: '通知组名称',
        key: 'name',
        dataIndex: 'name',
        align: 'left',
        width: 300,
    },
    {
        title: '邮箱联系人',
        key: 'mail',
        dataIndex: 'mail',
        align: 'left',
        ellipsis: true,
        tooltip: true,
        width: 120,
    },
    {
        title: '企微webhook',
        key: 'work_weixin',
        dataIndex: 'work_weixin',
        align: 'left',
        ellipsis: true,
        tooltip: true,
        width: 120,
    },
    {
        title: '飞书webhook',
        key: 'feishu',
        dataIndex: 'feishu',
        align: 'left',
        ellipsis: true,
        tooltip: true,
        width: 120,
    },
    {
        title: '钉钉webhook（不可用）',
        key: 'dingding',
        dataIndex: 'dingding',
        align: 'left',
        ellipsis: true,
        tooltip: true,
        width: 120,
    },
    {
        title: '操作',
        key: 'actions',
        dataIndex: 'actions',
        width: 120,
    },
])
