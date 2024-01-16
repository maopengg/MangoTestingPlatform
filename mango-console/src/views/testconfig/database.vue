<template>
  <div>
    <div class="main-container">
      <TableBody ref="tableBody">
        <template #header>
          <TableHeader :show-filter="true" title="数据库配置" @search="doRefresh" @reset-search="onResetSearch">
            <template #search-content>
              <a-form layout="inline" :model="{}" @keyup.enter="doRefresh">
                <a-form-item v-for="item of conditionItems" :key="item.key" :label="item.label">
                  <template v-if="item.type === 'input'">
                    <a-input v-model="item.value" :placeholder="item.placeholder" @change="doRefresh" />
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
                      @change="doRefresh"
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
            :loading="table.tableLoading.value"
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
import { systemDatabase } from '@/api/url'
import { usePagination, useRowKey, useRowSelection, useTable, useTableColumn } from '@/hooks/table'
import { FormItem, ModalDialogType } from '@/types/components'
import { Message, Modal } from '@arco-design/web-vue'
import { onMounted, ref, nextTick, reactive } from 'vue'
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
    }
  },
  {
    key: 'project',
    label: '项目',
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
    key: 'port',
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
    width: 110
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
    key: 'port',
    dataIndex: 'port',
    width: 130
  },
  {
    title: '主库',
    key: 'name',
    dataIndex: 'name'
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
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 150
  }
])

function doRefresh() {
  get({
    url: systemDatabase,
    data: () => {
      let value = getFormItems(conditionItems)
      value['page'] = pagination.page
      value['pageSize'] = pagination.pageSize
      return value
    }
  })
    .then((res) => {
      table.handleSuccess(res)
      pagination.setTotalSize((res as any).totalSize)
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
        url: systemDatabase,
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
        url: systemDatabase,
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
        url: systemDatabase,
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

onMounted(doRefresh)
</script>
