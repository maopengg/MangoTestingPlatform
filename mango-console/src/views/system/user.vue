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
                      <a-input v-model="item.value.value" :placeholder="item.placeholder" />
                    </template>
                    <template v-else-if="item.type === 'select'">
                      <a-select
                        style="width: 150px"
                        v-model="item.value.value"
                        :placeholder="item.placeholder"
                        :options="project.data"
                        :field-names="fieldNames"
                        allow-clear
                        allow-search
                      />
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
                <template v-else-if="item.key === 'department'" #cell="{ record }">
                  {{ record.department === null ? '-' : record.department.name }}
                </template>
                <template v-else-if="item.key === 'role'" #cell="{ record }">
                  {{ record.role.name }}
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
      <ModalDialog ref="modalDialogRef" :title="actionTitle" @confirm="onDataForm">
        <template #content>
          <a-form :model="formModel">
            <a-form-item
              :class="[item.required ? 'form-item__require' : 'form-item__no_require']"
              :label="item.label"
              v-for="item of formItems"
              :key="item.key"
            >
              <template v-if="item.type === 'input'">
                <a-input :placeholder="item.placeholder" v-model="item.value.value" />
              </template>
              <template v-else-if="item.type === 'textarea'">
                <a-textarea v-model="item.value.value" :placeholder="item.placeholder" :auto-size="{ minRows: 3, maxRows: 5 }" />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'department'">
                <a-select
                  v-model="item.value.value"
                  :placeholder="item.placeholder"
                  :options="project.data"
                  :field-names="fieldNames"
                  allow-clear
                  allow-search
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'role'">
                <a-select
                  v-model="item.value.value"
                  :placeholder="item.placeholder"
                  :options="allRole.value"
                  :field-names="fieldNames"
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
import { getKeyByTitle, transformData } from '@/utils/datacleaning'

const project = useProject()

const conditionItems: Array<FormItem> = [
  {
    key: 'name',
    label: '页面名称',
    type: 'input',
    placeholder: '请输入页面名称',
    value: ref(''),
    reset: function () {
      this.value.value = ''
    },
    render: (formItem: FormItem) => {
      return h(Input, {
        placeholder: '请输入页面名称',
        modelValue: formItem.value.value,
        'onUpdate:modelValue': (value) => {
          formItem.value.value = value
        }
      })
    }
  },
  {
    key: 'caseid',
    label: '页面ID',
    type: 'input',
    placeholder: '请输入页面ID',
    value: ref(''),
    reset: function () {
      this.value.value = ''
    },
    render: (formItem: FormItem) => {
      return h(Input, {
        placeholder: '请输入页面ID',
        modelValue: formItem.value.value,
        'onUpdate:modelValue': (value) => {
          formItem.value.value = value
        }
      })
    }
  },
  {
    key: 'team',
    label: '筛选项目',
    value: ref(),
    type: 'select',
    placeholder: '请选择项目',
    optionItems: [],
    reset: function () {
      this.value.value = undefined
    }
  }
]
conditionItems[2].optionItems = project.data
console.log(conditionItems[2].optionItems)
const formItems = [
  {
    label: '昵称',
    key: 'nickname',
    value: ref(''),
    placeholder: '请输入用户昵称',
    required: true,
    type: 'input',
    validator: function () {
      if (!this.value.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  },
  {
    label: '账号',
    key: 'username',
    value: ref(''),
    type: 'input',
    required: true,
    placeholder: '请输入用户账号',
    validator: function () {
      if (!this.value.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  },
  {
    label: '密码',
    key: 'password',
    value: ref(''),
    type: 'input',
    required: true,
    placeholder: '请输入用户密码',
    validator: function () {
      // 判断value是否为空
      if (!this.value.value) {
        Message.error(this.placeholder || '')
        return false
      }
      // 判断value是否包含汉字
      const reg = new RegExp('[\\u4E00-\\u9FFF]+', 'g')
      if (reg.test(this.value.value)) {
        Message.error('不能输入汉字')
        return false
      }
      return true
    }
  },
  {
    label: '归属项目组',
    key: 'department',
    value: ref(''),
    type: 'select',
    required: true,
    placeholder: '请选择角色项目组',
    validator: function () {
      if (!this.value.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  },
  {
    label: '绑定角色',
    key: 'role',
    value: ref(''),
    type: 'select',
    required: true,
    placeholder: '请选择用户角色，角色不同权限不同',
    validator: function () {
      if (!this.value.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  }
] as FormItem[]

const actionTitle = ref('添加页面')
const modalDialogRef = ref<ModalDialogType | null>(null)
const pagination = usePagination(doRefresh)
const { selectedRowKeys, onSelectionChange, showCheckedAll } = useRowSelection()
const table = useTable()
const rowKey = useRowKey('id')
const tableColumns = useTableColumn([
  table.indexColumn,
  {
    title: '昵称',
    key: 'nickname',
    dataIndex: 'nickname',
    width: 100
  },
  {
    title: '账号',
    key: 'username',
    dataIndex: 'username',
    align: 'left'
  },
  {
    title: '归属项目组',
    key: 'department',
    dataIndex: 'department',
    width: 150
  },
  {
    title: '角色',
    key: 'role',
    dataIndex: 'role'
  },
  {
    title: '登录时间',
    key: 'lastLoginTime',
    dataIndex: 'lastLoginTime'
  },
  {
    title: '登录IP',
    key: 'ip',
    dataIndex: 'ip'
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 150
  }
])

const formModel = ref({})

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

const allRole: any = reactive([])

function getRole() {
  get({
    url: getAllRole
  })
    .then((res) => {
      allRole.value = res.data
    })
    .catch(console.log)
}

function onSearch() {
  let data: { [key: string]: string } = {}
  conditionItems.forEach((it) => {
    if (it.value.value) {
      data[it.key] = it.value.value
    }
  })
  console.log(data)
  if (JSON.stringify(data) === '{}') {
    doRefresh()
  } else if (data.project) {
    get({
      url: getUserList,
      data: () => {
        return {
          page: pagination.page,
          pageSize: pagination.pageSize,
          executor_name: data.executor_name
        }
      }
    })
      .then((res) => {
        table.handleSuccess(res)
        pagination.setTotalSize(res.totalSize || 10)
        Message.success(res.msg)
      })
      .catch(console.log)
  } else if (data) {
    get({
      url: getUserList,
      data: () => {
        return {
          id: data.caseid,
          page: pagination.page,
          pageSize: pagination.pageSize,
          executor_name: data.executor_name
        }
      }
    })
      .then((res) => {
        table.handleSuccess(res)
        pagination.setTotalSize(res.totalSize || 10)
        Message.success(res.msg)
      })
      .catch(console.log)
  }
}

function onResetSearch() {
  conditionItems.forEach((it) => {
    it.reset ? it.reset() : (it.value.value = '')
  })
}

const addUpdate = ref(0)
const updateId: any = ref('')

function onAddPage() {
  actionTitle.value = '添加页面'
  modalDialogRef.value?.toggle()
  addUpdate.value = 1
  formItems.forEach((it) => {
    if (it.reset) {
      it.reset()
    } else {
      it.value.value = ''
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
  actionTitle.value = '编辑页面'
  modalDialogRef.value?.toggle()
  addUpdate.value = 0
  updateId.value = item.id
  nextTick(() => {
    formItems.forEach((it) => {
      const key = it.key
      const propName = item[key]
      if (typeof propName === 'object' && propName !== null) {
        it.value.value = propName.name
      } else {
        it.value.value = propName
      }
    })
  })
}

function onDataForm() {
  if (formItems.every((it) => (it.validator ? it.validator() : true))) {
    modalDialogRef.value?.toggle()
    let value = transformData(formItems)
    console.log(value)
    if (addUpdate.value === 1) {
      addUpdate.value = 0
      post({
        url: getUserList,
        data: () => {
          return {
            nickname: value.nickname,
            username: value.username,
            password: value.password,
            role: value.role,
            department: value.department
          }
        }
      })
        .then((res) => {
          Message.success(res.msg)
          doRefresh()
        })
        .catch(console.log)
    } else if (addUpdate.value === 0) {
      let teamId = value.team
      let roleId = value.role
      if (typeof value.team === 'string') {
        teamId = getKeyByTitle(project.data, value.team)
        roleId = getKeyByTitle(allRole.value, value.role)
      }
      addUpdate.value = 0
      value['id'] = updateId.value
      updateId.value = 0
      put({
        url: getUserList,
        data: () => {
          return {
            id: value.id,
            nickname: value.nickname,
            username: value.username,
            password: value.password,
            role: roleId,
            department: teamId
          }
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
