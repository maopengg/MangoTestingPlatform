<template>
  <div>
    <div class="main-container">
      <TableBody ref="tableBody">
        <template #header>
          <TableHeader :show-filter="true" title="数据库配置" @search="onSearch" @reset-search="onResetSearch">
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
                    <template v-if="item.type === 'date'">
                      <a-date-picker v-model="item.value.value" />
                    </template>
                    <template v-if="item.type === 'time'">
                      <a-time-picker v-model="item.value.value" value-format="HH:mm:ss" />
                    </template>
                    <template v-if="item.type === 'check-group'">
                      <a-checkbox-group v-model="item.value.value">
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
                <template v-else-if="item.key === 'project'" #cell="{ record }">
                  {{ record.project.name }}
                </template>
                <template v-else-if="item.key === 'test_obj'" #cell="{ record }">
                  {{ record.test_obj.name }}
                </template>
                <template v-else-if="item.key === 'password'" #cell="{ record }">
                  {{ record.password }}
                </template>
                <template v-else-if="item.key === 'environment'" #cell="{ record }">
                  <a-tag color="orangered" size="small" v-if="record.environment === 0">测试环境</a-tag>
                  <a-tag color="cyan" size="small" v-else-if="record.environment === 1">预发环境</a-tag>
                  <a-tag color="green" size="small" v-else-if="record.environment === 2">生产环境</a-tag>
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
              <template v-else-if="item.type === 'select' && item.key === 'project'">
                <a-select
                  v-model="item.value.value"
                  :placeholder="item.placeholder"
                  :options="project.data"
                  :field-names="fieldNames"
                  allow-clear
                  allow-search
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'test_obj'">
                <a-select
                  v-model="item.value.value"
                  :placeholder="item.placeholder"
                  :options="testObj.data"
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
import { getDatabase } from '@/api/url'
import { usePagination, useRowKey, useRowSelection, useTable, useTableColumn } from '@/hooks/table'
import { FormItem, ModalDialogType } from '@/types/components'
import { Input, Message, Modal } from '@arco-design/web-vue'
import { h, onMounted, ref, nextTick } from 'vue'
import { useProject } from '@/store/modules/get-project'
import { useTestObj } from '@/store/modules/get-test-obj'
import { fieldNames } from '@/setting'
import { getKeyByTitle, transformData } from '@/utils/datacleaning'

const project = useProject()
const testObj = useTestObj()
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
    key: 'project',
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
const formItems = [
  {
    label: '项目名称',
    key: 'project',
    value: ref(''),
    placeholder: '请选择项目名称',
    required: true,
    type: 'select',
    validator: function () {
      if (!this.value.value && this.value.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  },
  {
    label: '绑定环境',
    key: 'test_obj',
    value: ref(''),
    type: 'select',
    required: true,
    placeholder: '请选择对应环境',
    validator: function () {
      if (!this.value.value && this.value.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  },
  {
    label: '域名',
    key: 'host',
    value: ref(''),
    type: 'input',
    required: true,
    placeholder: '请输入数据库域名',
    validator: function () {
      if (!this.value.value && this.value.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  },
  {
    label: '端口',
    key: 'post',
    value: ref('3306'),
    type: 'input',
    required: true,
    placeholder: '请输入数据库端口',
    validator: function () {
      if (!this.value.value && this.value.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  },
  {
    label: '主库',
    key: 'name',
    value: ref(''),
    type: 'input',
    required: true,
    placeholder: '请输入主库名称',
    validator: function () {
      if (!this.value.value && this.value.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  },
  {
    label: '用户名',
    key: 'user',
    value: ref(''),
    type: 'input',
    required: true,
    placeholder: '请输入用户名',
    validator: function () {
      if (!this.value.value && this.value.value !== 0) {
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
    placeholder: '请输入密码',
    validator: function () {
      if (!this.value.value && this.value.value !== 0) {
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
const { onSelectionChange } = useRowSelection()
const table = useTable()
const rowKey = useRowKey('id')
const tableColumns = useTableColumn([
  table.indexColumn,
  {
    title: '项目名称',
    key: 'project',
    dataIndex: 'project',
    width: 100
  },
  {
    title: '对应环境',
    key: 'test_obj',
    dataIndex: 'test_obj',
    width: 150
  },
  {
    title: '域名',
    key: 'host',
    dataIndex: 'host',
    align: 'left'
  },
  {
    title: '端口',
    key: 'post',
    dataIndex: 'post'
  },
  {
    title: '主库',
    key: 'name',
    dataIndex: 'name'
  },
  {
    title: '用户名',
    key: 'user',
    dataIndex: 'user'
  },
  {
    title: '密码',
    key: 'password',
    dataIndex: 'password'
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
    url: getDatabase,
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
      url: getDatabase,
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
      url: getDatabase,
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
        url: getDatabase,
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
    if (addUpdate.value === 1) {
      addUpdate.value = 0
      post({
        url: getDatabase,
        data: () => {
          return {
            project: value.project,
            name: value.name,
            host: value.host,
            password: value.password,
            post: value.post,
            test_obj: value.test_obj,
            user: value.user
          }
        }
      })
        .then((res) => {
          Message.success(res.msg)
          doRefresh()
        })
        .catch(console.log)
    } else if (addUpdate.value === 0) {
      let projectId = value.project
      let testOb = value.test_obj
      if (typeof value.project === 'string') {
        projectId = getKeyByTitle(project.data, value.project)
        testOb = getKeyByTitle(testObj.data, value.test_obj)
      }
      addUpdate.value = 0
      value['id'] = updateId.value
      updateId.value = 0
      put({
        url: getDatabase,
        data: () => {
          return {
            id: value.id,
            project: projectId,
            name: value.name,
            host: value.host,
            password: value.password,
            post: value.post,
            test_obj: testOb,
            user: value.user
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

onMounted(doRefresh)
</script>
