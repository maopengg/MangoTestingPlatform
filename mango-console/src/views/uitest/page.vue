<template>
  <div>
    <div class="main-container">
      <TableBody ref="tableBody">
        <template #header>
          <TableHeader :show-filter="true" title="Ui元素页面对象" @search="onSearch" @reset-search="onResetSearch">
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
          <a-tabs @tab-click="(key) => switchType(key)">
            <template #extra>
              <a-space>
                <a-button type="primary" size="small" @click="onAddPage">新增</a-button>
                <a-button status="danger" size="small" @click="onDeleteItems">批量删除</a-button>
              </a-space>
            </template>
            <a-tab-pane key="0" title="Web页面对象" />
            <a-tab-pane key="1" title="Android页面对象" />
            <a-tab-pane key="2" title="IOS页面对象" />
            <a-tab-pane key="3" title="桌面页面对象" />
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
                <template v-else-if="item.key === 'project'" #cell="{ record }">
                  {{ record.project?.name }}
                </template>
                <template v-else-if="item.key === 'module_name'" #cell="{ record }">
                  {{ record.module_name?.name }}
                </template>
                <template v-else-if="item.key === 'actions'" #cell="{ record }">
                  <a-space>
                    <a-button type="text" size="mini" @click="onUpdate(record)">编辑</a-button>
                    <a-button type="text" size="mini" @click="onClick(record)">添加元素</a-button>
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
      <ModalDialog ref="modalDialogRef" :title="uiPageData.actionTitle" @confirm="onDataForm">
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
              <template v-else-if="item.type === 'select' && item.key === 'project'">
                <a-select
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="project.data"
                  :field-names="fieldNames"
                  @change="getProjectModule(item.value)"
                  value-key="key"
                  allow-clear
                  allow-search
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'module_name'">
                <a-select
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="uiPageData.moduleList"
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
import { getProjectModuleGetAll, uiPage, uiPageQuery } from '@/api/url'
import { usePagination, useRowKey, useRowSelection, useTable, useTableColumn } from '@/hooks/table'
import { FormItem, ModalDialogType } from '@/types/components'
import { Input, Message, Modal } from '@arco-design/web-vue'
import { h, onMounted, ref, nextTick, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useProject } from '@/store/modules/get-project'
import { getFormItems } from '@/utils/datacleaning'
import { fieldNames } from '@/setting'

const project = useProject()
const modalDialogRef = ref<ModalDialogType | null>(null)
const pagination = usePagination(doRefresh)
const { selectedRowKeys, onSelectionChange, showCheckedAll } = useRowSelection()
const table = useTable()
const rowKey = useRowKey('id')
const formModel = ref({})
const router = useRouter()

const uiPageData = reactive({
  isAdd: false,
  updateId: 0,
  actionTitle: '添加页面',
  pageType: 0,
  moduleList: []
})
const conditionItems: Array<FormItem> = reactive([
  {
    key: 'id',
    label: 'ID',
    type: 'input',
    placeholder: '请输入页面ID',
    value: '',
    reset: function () {
      this.value = ''
    },
    render: (formItem: FormItem) => {
      return h(Input, {
        placeholder: '请输入页面ID',
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
    placeholder: '请输入页面名称',
    value: '',
    reset: function () {
      this.value = ''
    },
    render: (formItem: FormItem) => {
      return h(Input, {
        placeholder: '请输入页面名称',
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
      if (!this.value && this.value !== '0') {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  },
  {
    label: '模块',
    key: 'module_name',
    value: '',
    placeholder: '请选择测试模块',
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
    label: '页面名称',
    key: 'name',
    value: '',
    type: 'input',
    required: true,
    placeholder: '请输入页面名称',
    validator: function () {
      if (!this.value && this.value !== '0') {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  },
  {
    label: '页面地址',
    key: 'url',
    value: '',
    type: 'input',
    required: true,
    placeholder: '请输入页面名称',
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
    title: '项目名称',
    key: 'project',
    dataIndex: 'project',
    width: 150
  },
  {
    title: '模块',
    key: 'module_name',
    dataIndex: 'module_name'
  },
  {
    title: '页面名称',
    key: 'name',
    dataIndex: 'name',
    width: 150
  },
  {
    title: '页面地址',
    key: 'url',
    dataIndex: 'url',
    align: 'left'
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 150
  }
])

function switchType(key: any) {
  uiPageData.pageType = key
  doRefresh()
}

function doRefresh() {
  get({
    url: uiPage,
    data: () => {
      return {
        page: pagination.page,
        pageSize: pagination.pageSize,
        type: uiPageData.pageType
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
  value['type'] = uiPageData.pageType
  get({
    url: uiPageQuery,
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
  uiPageData.actionTitle = '添加页面'
  uiPageData.isAdd = true
  modalDialogRef.value?.toggle()
  console.log(formItems)
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
        url: uiPage,
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

function onDeleteItems() {
  if (selectedRowKeys.value.length === 0) {
    Message.error('请选择要删除的数据')
    return
  }
  Modal.confirm({
    title: '提示',
    content: '确定要删除此数据吗？',
    cancelText: '取消',
    okText: '删除',
    onOk: () => {
      deleted({
        url: uiPage,
        data: () => {
          return {
            id: JSON.stringify(selectedRowKeys.value)
          }
        }
      })
        .then((res) => {
          Message.success(res.msg)
          selectedRowKeys.value = []
          doRefresh()
        })
        .catch(console.log)
    }
  })
}

function onUpdate(item: any) {
  uiPageData.actionTitle = '编辑页面'
  uiPageData.isAdd = false
  uiPageData.updateId = item.id
  modalDialogRef.value?.toggle()
  getProjectModule(item.project.id)

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
    value['type'] = uiPageData.pageType
    if (uiPageData.isAdd) {
      post({
        url: uiPage,
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
        url: uiPage,
        data: () => {
          value['id'] = uiPageData.updateId
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
function getProjectModule(projectId: number) {
  get({
    url: getProjectModuleGetAll,
    data: () => {
      return {
        project_id: projectId
      }
    }
  })
    .then((res) => {
      uiPageData.moduleList = res.data
    })
    .catch(console.log)
}
function onClick(record: any) {
  router.push({
    path: '/uitest/pageel',
    query: {
      id: record.id,
      name: record.name,
      project_id: record.project.id,
      project_name: record.project.name
    }
  })
}

onMounted(() => {
  nextTick(async () => {
    doRefresh()
  })
})
</script>
