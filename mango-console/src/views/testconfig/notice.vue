<template>
  <div>
    <div class="main-container">
      <TableBody ref="tableBody">
        <template #header>
          <TableHeader :show-filter="true" title="自动化通知配置" @search="onSearch" @reset-search="onResetSearch">
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
                    <!--                    <template v-if="item.type === 'date'">-->
                    <!--                      <a-date-picker v-model="item.value.value" />-->
                    <!--                    </template>-->
                    <!--                    <template v-if="item.type === 'time'">-->
                    <!--                      <a-time-picker v-model="item.value.value" value-format="HH:mm:ss" />-->
                    <!--                    </template>-->
                    <!--                    <template v-if="item.type === 'check-group'">-->
                    <!--                      <a-checkbox-group v-model="item.value.value">-->
                    <!--                        <a-checkbox v-for="it of item.optionItems" :value="it.value" :key="it.value">-->
                    <!--                          {{ item.label }}-->
                    <!--                        </a-checkbox>-->
                    <!--                      </a-checkbox-group>-->
                    <!--                    </template>-->
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
                <template v-else-if="item.key === 'team'" #cell="{ record }">
                  {{ record.team.name }}
                </template>
                <template v-else-if="item.key === 'name'" #cell="{ record }">
                  <a-tag color="orangered" size="small" v-if="record.name === '邮箱'">{{ record.name }}</a-tag>
                  <a-tag color="cyan" size="small" v-else-if="record.name === '企微群'">{{ record.name }}</a-tag>
                  <a-tag color="cyan" size="small" v-else-if="record.name === '钉钉'">{{ record.name }}</a-tag>
                </template>
                <template v-else-if="item.key === 'state'" #cell="{ record }">
                  <a-tag color="green" size="small" v-if="record.state === 1">启用</a-tag>
                  <a-tag color="orangered" size="small" v-else-if="record.state === 0">未启用</a-tag>
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
                <a-textarea v-model="item.value.value" :placeholder="item.placeholder" :auto-size="{ minRows: 5, maxRows: 9 }" />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'team'">
                <a-select
                  v-model="item.value.value"
                  :placeholder="item.placeholder"
                  :options="project.data"
                  :field-names="fieldNames"
                  allow-clear
                  allow-search
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'name'">
                <a-select
                  v-model="item.value.value"
                  :placeholder="item.placeholder"
                  :options="project.data"
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
import { getNoticeConfig } from '@/api/url'
import { usePagination, useRowKey, useRowSelection, useTable, useTableColumn } from '@/hooks/table'
import { FormItem, ModalDialogType } from '@/types/components'
import { Input, Message, Modal } from '@arco-design/web-vue'
import { h, onMounted, ref, nextTick } from 'vue'
import { useProject } from '@/store/modules/get-project'
import { fieldNames } from '@/setting'

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
const formItems = [
  {
    label: '项目名称',
    key: 'team',
    value: ref(''),
    placeholder: '请选择项目名称',
    required: true,
    type: 'select'
  },
  {
    label: '通知类型',
    key: 'name',
    value: ref(''),
    type: 'select',
    required: true,
    placeholder: '请选择通知类型'
  },
  {
    label: '配置详情',
    key: 'config',
    value: ref(''),
    type: 'textarea',
    required: true,
    placeholder: '请输入配置详情'
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
    key: 'team',
    dataIndex: 'team',
    width: 100
  },
  {
    title: '通知类型',
    key: 'name',
    dataIndex: 'name',
    width: 150
  },
  {
    title: '配置详情',
    key: 'config',
    dataIndex: 'config',
    align: 'left'
  },
  {
    title: '状态',
    key: 'state',
    dataIndex: 'state',
    width: 80
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
    url: getNoticeConfig,
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
      url: getNoticeConfig,
      data: () => {
        return {
          page: pagination.page,
          pageSize: pagination.pageSize
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
      url: getNoticeConfig,
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
        url: getNoticeConfig,
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
    let value: { [key: string]: string } = {}
    formItems.forEach((it) => {
      value[it.key] = it.value.value
    })
    console.log(value)
    if (addUpdate.value === 1) {
      addUpdate.value = 0
      post({
        url: getNoticeConfig,
        data: () => {
          return {
            project: value.project,
            type: value.type,
            config: value.config,
            state: 0
          }
        }
      })
        .then((res) => {
          Message.success(res.msg)
          doRefresh()
        })
        .catch(console.log)
    } else if (addUpdate.value === 0) {
      addUpdate.value = 0
      value['id'] = updateId.value
      updateId.value = 0
      put({
        url: getNoticeConfig,
        data: () => {
          return {
            id: value.id,
            project: value.project,
            type: value.type,
            config: value.config,
            state: 0
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
