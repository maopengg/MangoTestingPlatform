<template>
  <div>
    <div class="main-container">
      <TableBody ref="tableBody">
        <template #header>
          <TableHeader :show-filter="true" title="用户管理" @search="onSearch" @reset-search="onResetSearch">
            <template #search-content>
              <a-form layout="inline" :model="{}">
                <a-form-item v-for="item of conditionItems" :key="item.key" :label="item.label">
                  <template v-if="item.render">
                    <FormRender :render="item.render" :formItem="item" />
                  </template>
                  <template v-else>
                    <template v-if="item.type === 'input'">
                      <a-input v-model="item.value" :placeholder="item.placeholder" />
                    </template>
                    <template v-else-if="item.type === 'select'">
                      <a-select
                        style="width: 150px"
                        v-model="item.value"
                        :placeholder="item.placeholder"
                        :options="project.data"
                        :field-names="fieldNames"
                        value-key="key"
                        allow-clear
                        allow-search
                      />
                    </template>
                    <template v-if="item.type === 'date'">
                      <a-date-picker v-model="item.value" />
                    </template>
                    <template v-if="item.type === 'time'">
                      <a-time-picker v-model="item.value" value-format="HH:mm:ss" />
                    </template>
                    <template v-if="item.type === 'check-group'">
                      <a-checkbox-group v-model="item.value">
                        <a-checkbox v-for="it of item.optionItems" :value="it.value" :key="it.value">
                          {{ item.label }}
                        </a-checkbox>
                      </a-checkbox-group>
                    </template>
                  </template>
                </a-form-item>
              </a-form>
            </template>
          </TableHeader>
        </template>

        <template #default>
          <a-tabs>
            <template #extra>
              <a-space>
                <div>
                  <a-button type="primary" size="small" @click="onAddPage">新增</a-button>
                </div>
              </a-space>
            </template>
          </a-tabs>
          <a-table
            :bordered="false"
            :row-selection="{ selectedRowKeys, showCheckedAll }"
            :loading="table.tableLoading"
            :data="table.dataList"
            :columns="tableColumns"
            :pagination="false"
            :rowKey="rowKey"
            @selection-change="onSelectionChange"
          >
            <template #columns>
              <a-table-column
                v-for="item of tableColumns"
                :key="item.key"
                :align="item.align"
                :title="item.title"
                :width="item.width"
                :data-index="item.key"
                :fixed="item.fixed"
              >
                <template v-if="item.key === 'index'" #cell="{ record }">
                  {{ record.id }}
                </template>
                <template v-else-if="item.key === 'role'" #cell="{ record }">
                  {{ record.role === null ? '-' : record.role.name }}
                </template>
                <template v-else-if="item.key === 'actions'" #cell="{ record }">
                  <a-space>
                    <a-button type="text" size="mini" @click="onUpdate(record)">编辑</a-button>
                    <a-button status="danger" type="text" size="mini" @click="onDelete(record)">删除</a-button>
                  </a-space>
                </template>
              </a-table-column>
            </template>
          </a-table>
        </template>
        <template #footer>
          <TableFooter :pagination="pagination" />
        </template>
      </TableBody>
      <ModalDialog ref="modalDialogRef" :title="userData.actionTitle" @confirm="onDataForm">
        <template #content>
          <a-form :model="formModel">
            <a-form-item
              :class="[item.required ? 'form-item__require' : 'form-item__no_require']"
              :label="item.label"
              v-for="item of formItems"
              :key="item.key"
            >
              <template v-if="item.type === 'input'">
                <a-input :placeholder="item.placeholder" v-model="item.value" />
              </template>
              <template v-else-if="item.type === 'textarea'">
                <a-textarea v-model="item.value" :placeholder="item.placeholder" :auto-size="{ minRows: 3, maxRows: 5 }" />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'role'">
                <a-select
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="userData.allRole"
                  :field-names="fieldNames"
                  value-key="key"
                  allow-clear
                  allow-search
                />
              </template>
            </a-form-item>
          </a-form>
        </template>
      </ModalDialog>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { get, post, put, deleted } from '@/api/http'
import { getAllRole, getUserList } from '@/api/url'
import { usePagination, useRowKey, useRowSelection, useTable, useTableColumn } from '@/hooks/table'
import { FormItem, ModalDialogType } from '@/types/components'
import { Input, Message, Modal } from '@arco-design/web-vue'
import { h, onMounted, ref, nextTick, reactive } from 'vue'
import { useProject } from '@/store/modules/get-project'
import { fieldNames } from '@/setting'
import { getFormItems } from '@/utils/datacleaning'
const modalDialogRef = ref<ModalDialogType | null>(null)
const pagination = usePagination(doRefresh)
const { selectedRowKeys, onSelectionChange, showCheckedAll } = useRowSelection()
const table = useTable()
const rowKey = useRowKey('id')
const project = useProject()
const formModel = ref({})
const userData = reactive({
  isAdd: false,
  updateId: 0,
  actionTitle: '添加用户',
  allRole: []
})
const conditionItems: Array<FormItem> = reactive([
  {
    key: 'id',
    label: 'ID',
    type: 'input',
    placeholder: '请输入用户ID',
    value: '',
    reset: function () {
      this.value = ''
    },
    render: (formItem: FormItem) => {
      return h(Input, {
        placeholder: '请输入用户ID',
        modelValue: formItem.value,
        'onUpdate:modelValue': (value) => {
          formItem.value = value
        }
      })
    }
  },
  {
    key: 'nickname',
    label: '名称',
    type: 'input',
    placeholder: '请输入用户名称',
    value: '',
    reset: function () {
      this.value = ''
    },
    render: (formItem: FormItem) => {
      return h(Input, {
        placeholder: '请输入用户名称',
        modelValue: formItem.value,
        'onUpdate:modelValue': (value) => {
          formItem.value = value
        }
      })
    }
  }
])
const formItems: FormItem[] = reactive([
  {
    label: '昵称',
    key: 'nickname',
    value: '',
    placeholder: '请输入用户昵称',
    required: true,
    type: 'input',
    validator: function () {
      if (!this.value && this.value !== '0') {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  },
  {
    label: '账号',
    key: 'username',
    value: '',
    type: 'input',
    required: true,
    placeholder: '请输入用户账号',
    validator: function () {
      if (!this.value && this.value !== '0') {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  },
  {
    label: '密码',
    key: 'password',
    value: '',
    type: 'input',
    required: false,
    placeholder: '请输入用户密码',
    validator: function () {
      // 判断value是否包含汉字
      const reg = new RegExp('[\\u4E00-\\u9FFF]+', 'g')
      if (reg.test(this.value)) {
        Message.error('不能输入汉字')
        return false
      }
      return true
    }
  },
  {
    label: '绑定角色',
    key: 'role',
    value: '',
    type: 'select',
    required: true,
    placeholder: '请选择用户角色',
    validator: function () {
      if (this.value === null && this.value === '') {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  },
  {
    label: '邮箱',
    key: 'mailbox',
    value: '',
    type: 'input',
    required: true,
    placeholder: '请输入邮箱',
    validator: function () {
      if (!this.value && this.value !== '0') {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  }
])
const tableColumns = useTableColumn([
  table.indexColumn,
  {
    title: '昵称',
    key: 'nickname',
    dataIndex: 'nickname',
    width: 150
  },
  {
    title: '账号',
    key: 'username',
    dataIndex: 'username',
    align: 'left'
  },
  {
    title: '角色',
    key: 'role',
    dataIndex: 'role'
  },
  {
    title: '最近登录时间',
    key: 'last_login_time',
    dataIndex: 'last_login_time'
  },
  {
    title: '登录IP',
    key: 'ip',
    dataIndex: 'ip'
  },
  {
    title: '邮箱',
    key: 'mailbox',
    dataIndex: 'mailbox'
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 150
  }
])
function doRefresh() {
  get({
    url: getUserList,
    data: () => {
      return {
        page: pagination.page,
        pageSize: pagination.pageSize
      }
    }
  })
    .then((res) => {
      table.handleSuccess(res)
      pagination.setTotalSize((res as any).totalSize)
    })
    .catch(console.log)
}
function getRole() {
  get({
    url: getAllRole
  })
    .then((res) => {
      userData.allRole = res.data
    })
    .catch(console.log)
}

function onSearch() {
  let value = getFormItems(conditionItems)
  if (JSON.stringify(value) === '{}') {
    doRefresh()
    return
  }
  get({
    url: getUserList,
    data: () => {
      value['page'] = pagination.page
      value['pageSize'] = pagination.pageSize
      return value
    }
  })
    .then((res) => {
      table.handleSuccess(res)
      pagination.setTotalSize(res.totalSize || 10)
      Message.success(res.msg)
    })
    .catch(console.log)
}

function onResetSearch() {
  conditionItems.forEach((it) => {
    it.value = ''
  })
}
function onAddPage() {
  userData.actionTitle = '添加用户'
  userData.isAdd = true
  modalDialogRef.value?.toggle()
  formItems.forEach((it) => {
    if (it.reset) {
      it.reset()
    } else {
      it.value = ''
    }
  })
}

function onDelete(data: any) {
  Modal.confirm({
    title: '提示',
    content: '是否要删除此页面？',
    cancelText: '取消',
    okText: '删除',
    onOk: () => {
      deleted({
        url: getUserList,
        data: () => {
          return {
            id: '[' + data.id + ']'
          }
        }
      })
        .then((res) => {
          Message.success(res.msg)
          doRefresh()
        })
        .catch(console.log)
    }
  })
}

function onUpdate(item: any) {
  userData.actionTitle = '编辑用户'
  userData.isAdd = false
  userData.updateId = item.id
  modalDialogRef.value?.toggle()
  nextTick(() => {
    formItems.forEach((it) => {
      const propName = item[it.key]
      if (typeof propName === 'object' && propName !== null) {
        it.value = propName.id
      } else {
        it.value = propName
      }
    })
  })
}

function onDataForm() {
  if (formItems.every((it) => (it.validator ? it.validator() : true))) {
    modalDialogRef.value?.toggle()
    let value = getFormItems(formItems)
    if (userData.isAdd) {
      post({
        url: getUserList,
        data: () => {
          return value
        }
      })
        .then((res) => {
          Message.success(res.msg)
          doRefresh()
        })
        .catch(console.log)
    } else {
      put({
        url: getUserList,
        data: () => {
          value['id'] = userData.updateId
          return value
        }
      })
        .then((res) => {
          Message.success(res.msg)
          doRefresh()
        })
        .catch(console.log)
    }
  }
}

onMounted(() => {
  nextTick(async () => {
    doRefresh()
    getRole()
  })
})
</script>
