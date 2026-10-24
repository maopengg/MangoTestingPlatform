import { FormItem } from '@/types/components'
import { reactive, ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import { useTable, useTableColumn } from '@/hooks/table'

const table = useTable()
export const formItems: FormItem[] = reactive([
  {
    label: '项目/产品',
    key: 'project_product',
    value: ref(''),
    placeholder: '请选择项目名称',
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
    label: '仓库管理',
    key: 'repository',
    value: ref(''),
    placeholder: '请选择代码仓库',
    required: true,
    type: 'pytest-repository',
    validator: function () {
      if (!this.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '项目目录',
    key: 'file_name',
    value: ref(''),
    placeholder: '请选择项目在当前仓库中的目录',
    required: true,
    type: 'repository-directory',
    validator: function () {
      if (!this.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '名称',
    key: 'name',
    value: ref(''),
    placeholder: '请选择名称',
    required: true,
    type: 'input',
    validator: function () {
      if (!this.value && this.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '自动化类型',
    key: 'auto_type',
    value: ref(''),
    placeholder: '请选择自动化类型',
    required: true,
    type: 'select',
    validator: function () {
      if (!this.value && this.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '测试目录',
    key: 'test_dir',
    value: ref([]),
    placeholder: '请选择当前分支中测试文件所在的目录',
    required: true,
    type: 'cascader',
    multiple: true,
    validator: function () {
      if (!this.value || this.value.length === 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    },
  },
  {
    label: '配置文件',
    key: 'pytest_config_path',
    value: ref(''),
    placeholder: '例如 pytest.ini',
    required: false,
    type: 'input',
  },
])
export const tableColumns = useTableColumn([
  table.indexColumn,
  {
    title: '项目绑定',
    key: 'binding',
    dataIndex: 'binding',
    align: 'left',
    width: 260,
  },
  {
    title: '仓库 / 分支',
    key: 'repository',
    dataIndex: 'repository',
    width: 210,
  },
  {
    title: '自动化类型',
    key: 'auto_type',
    dataIndex: 'auto_type',
    width: 120,
  },
  {
    title: '测试目录',
    key: 'test_dir',
    dataIndex: 'test_dir',
    width: 260,
  },
  {
    title: '项目/产品',
    key: 'project_product',
    dataIndex: 'project_product',
    align: 'left',
    width: 180,
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 160,
  },
])
