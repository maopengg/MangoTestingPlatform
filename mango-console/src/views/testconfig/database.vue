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
                  {{ record.project?.name }}
                </template>
                <template v-else-if="item.key === 'test_obj'" #cell="{ record }">
                  {{ record.test_obj.name }}
                </template>
                <template v-else-if="item.key === 'password'" #cell="{ record }">
                  {{ record.password }}
                </template>
                <template v-else-if="item.key === 'status'" #cell="{ record }">
                  <a-switch
                    :default-checked="record.status === 1"
                    :beforeChange="(newValue) => onModifyStatus(newValue, record.id)"
                  />
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
      <ModalDialog ref="modalDialogRef" :title="database.actionTitle" @confirm="onDataForm">
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
              <template v-else-if="item.type === 'select' && item.key === 'project'">
                <a-select
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="project.data"
                  :field-names="fieldNames"
                  value-key="key"
                  allow-clear
                  allow-search
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'test_obj'">
                <a-select
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="testObj.data"
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
import { getDatabase, getDatabasePutStatus, getDatabaseQuery } from '@/api/url'
import { usePagination, useRowKey, useRowSelection, useTable, useTableColumn } from '@/hooks/table'
import { FormItem, ModalDialogType } from '@/types/components'
import { Input, Message, Modal } from '@arco-design/web-vue'
import { h, onMounted, ref, nextTick, reactive } from 'vue'
import { useProject } from '@/store/modules/get-project'
import { useTestObj } from '@/store/modules/get-test-obj'
import { fieldNames } from '@/setting'
import { getFormItems } from '@/utils/datacleaning'

const project = useProject()
const testObj = useTestObj()
const modalDialogRef = ref<ModalDialogType | null>(null)
const pagination = usePagination(doRefresh)
const { onSelectionChange } = useRowSelection()
const table = useTable()
const rowKey = useRowKey('id')
const formModel = ref({})
const database = reactive({
  actionTitle: '添加配置',
  isAdd: false,
  updateId: 0
})
const conditionItems: Array<FormItem> = reactive([
  {
    key: 'id',
    label: 'ID',
    type: 'input',
    placeholder: '请输入数据库ID',
    value: '',
    reset: function () {
      this.value = ''
    },
    render: (formItem: FormItem) => {
      return h(Input, {
        placeholder: '请输入数据库ID',
        modelValue: formItem.value,
        'onUpdate:modelValue': (value) => {
          formItem.value = value
        }
      })
    }
  },
  {
    key: 'name',
    label: '名称',
    type: 'input',
    placeholder: '请输入数据库名称',
    value: '',
    reset: function () {
      this.value = ''
    },
    render: (formItem: FormItem) => {
      return h(Input, {
        placeholder: '请输入数据库名称',
        modelValue: formItem.value,
        'onUpdate:modelValue': (value) => {
          formItem.value = value
        }
      })
    }
  },
  {
    key: 'project',
    label: '筛选项目',
    value: '',
    type: 'select',
    placeholder: '请选择项目',
    optionItems: project.data,
    reset: function () {}
  }
])
const formItems: FormItem[] = reactive([
  {
    label: '项目名称',
    key: 'project',
    value: '',
    placeholder: '请选择项目名称',
    required: true,
    type: 'select',
    validator: function () {
      if (!this.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  },
  {
    label: '绑定环境',
    key: 'test_obj',
    value: '',
    type: 'select',
    required: true,
    placeholder: '请选择对应环境',
    validator: function () {
      if (!this.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  },
  {
    label: '域名',
    key: 'host',
    value: '',
    type: 'input',
    required: true,
    placeholder: '请输入数据库域名',
    validator: function () {
      if (!this.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  },
  {
    label: '端口',
    key: 'post',
    value: '3306',
    type: 'input',
    required: true,
    placeholder: '请输入数据库端口',
    validator: function () {
      if (!this.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  },
  {
    label: '主库',
    key: 'name',
    value: '',
    type: 'input',
    required: true,
    placeholder: '请输入主库名称',
    validator: function () {
      if (!this.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  },
  {
    label: '用户名',
    key: 'user',
    value: '',
    type: 'input',
    required: true,
    placeholder: '请输入用户名',
    validator: function () {
      if (!this.value) {
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
    required: true,
    placeholder: '请输入密码',
    validator: function () {
      if (!this.value) {
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
    title: '项目名称',
    key: 'project',
    dataIndex: 'project',
    width: 100
  },
  {
    title: '对应环境',
    key: 'test_obj',
    dataIndex: 'test_obj'
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
    dataIndex: 'post',
    width: 70
  },
  {
    title: '主库',
    key: 'name',
    dataIndex: 'name',
    width: 130
  },
  {
    title: '用户名',
    key: 'user',
    dataIndex: 'user',
    width: 130
  },
  {
    title: '密码',
    key: 'password',
    dataIndex: 'password'
  },
  {
    title: '状态',
    key: 'status',
    dataIndex: 'status'
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
  let value = getFormItems(conditionItems)
  if (JSON.stringify(value) === '{}') {
    doRefresh()
    return
  }
  get({
    url: getDatabaseQuery,
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
  database.actionTitle = '添加测试对象的mysql配置'
  modalDialogRef.value?.toggle()
  database.isAdd = true
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
  database.actionTitle = '编辑配置'
  modalDialogRef.value?.toggle()
  database.isAdd = false
  database.updateId = item.id
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
    const value = getFormItems(formItems)
    if (database.isAdd) {
      post({
        url: getDatabase,
        data: () => {
          value['status'] = 0
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
        url: getDatabase,
        data: () => {
          value['id'] = database.updateId
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

const onModifyStatus = async (newValue: boolean, id: number) => {
  return new Promise<any>((resolve, reject) => {
    setTimeout(async () => {
      try {
        let value: any = false
        await put({
          url: getDatabasePutStatus,
          data: () => {
            return {
              id: id,
              status: newValue ? 1 : 0
            }
          }
        })
          .then((res) => {
            Message.success(res.msg)
            value = res.code === 200
          })
          .catch(reject)
        resolve(value)
      } catch (error) {
        reject(error)
      }
    }, 300)
  })
}
onMounted(doRefresh)
</script>
