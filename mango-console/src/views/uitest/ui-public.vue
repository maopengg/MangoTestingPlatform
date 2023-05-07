<template>
  <div>
    <div class="main-container">
      <TableBody ref="tableBody">
        <template #header>
          <TableHeader :show-filter="true" title="公共方法" @search="onSearch" @reset-search="onResetSearch">
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
          <a-tabs @tab-click="(key) => switchType(key)" default-active-key="0">
            <template #extra>
              <a-space>
                <a-button type="primary" size="small" @click="onAddPage">新增</a-button>
                <!--                <a-button status="danger" size="small" @click="onDeleteItems">批量删除</a-button>-->
              </a-space>
            </template>
            <a-tab-pane key="0" title="公共请求参数" />
            <a-tab-pane key="1" title="公共断言类型" />
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
                <template v-else-if="item.key === 'public_type'" #cell="{ record }">
                  <a-tag color="orangered" size="small" v-if="record.public_type === 0">自定义</a-tag>
                  <a-tag color="cyan" size="small" v-else-if="record.public_type === 1">SQL</a-tag>
                  <a-tag color="green" size="small" v-else-if="record.public_type === 2">请求头</a-tag>
                  <a-tag color="green" size="small" v-else-if="record.public_type === 3">预置数据</a-tag>
                </template>
                <template v-else-if="item.key === 'end'" #cell="{ record }">
                  <a-tag color="orangered" size="small" v-if="record.end === 0">web端</a-tag>
                  <a-tag color="orange" size="small" v-else-if="record.end === 1">小程序</a-tag>
                  <a-tag color="blue" size="small" v-else-if="record.end === 2">app</a-tag>
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
                <a-textarea v-model="item.value.value" :placeholder="item.placeholder" :auto-size="{ minRows: 3, maxRows: 5 }" />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'team'">
                <a-select v-model="item.value.value" :placeholder="item.placeholder">
                  <a-option v-for="optionItem of conditionItems[2].optionItems" :key="optionItem.value" :value="optionItem.title">
                    {{ optionItem.title }}
                  </a-option>
                </a-select>
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'end'">
                <a-select v-model="item.value.value" :placeholder="item.placeholder">
                  <a-option v-for="optionItem of selectValue.apiPublicEnd" :key="optionItem.value" :value="optionItem.title">
                    {{ optionItem.title }}
                  </a-option>
                </a-select>
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'public_type'">
                <a-select v-model="item.value.value" :placeholder="item.placeholder">
                  <a-option v-for="optionItem of selectValue.apiPublicPublic" :key="optionItem.value" :value="optionItem.title">
                    {{ optionItem.title }}
                  </a-option>
                </a-select>
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
import { ApiPublic, ApiPublicEnd, ApiPublicPublic } from '@/api/url'
import { usePagination, useRowKey, useRowSelection, useTable, useTableColumn } from '@/hooks/table'
import { FormItem, ModalDialogType } from '@/types/components'
import { Input, Message, Modal } from '@arco-design/web-vue'
import { h, onMounted, ref, nextTick, reactive } from 'vue'
import { useProject } from '@/store/modules/get-project'
import { fieldNames } from '@/setting'

const conditionItems: Array<FormItem> = [
  {
    key: 'executor_name',
    label: '项目负责人',
    type: 'input',
    placeholder: '请输入项目负责人',
    value: ref(''),
    reset: function () {
      this.value.value = ''
    },
    render: (formItem: FormItem) => {
      return h(Input, {
        placeholder: '请输入项目负责人',
        modelValue: formItem.value.value,
        'onUpdate:modelValue': (value) => {
          formItem.value.value = value
        }
      })
    }
  },
  {
    key: 'caseid',
    label: '项目ID',
    type: 'input',
    placeholder: '请输入项目ID',
    value: ref(''),
    reset: function () {
      this.value.value = ''
    },
    render: (formItem: FormItem) => {
      return h(Input, {
        placeholder: '请输入项目ID',
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
const project = useProject()
conditionItems[2].optionItems = project.data

const formItems = [
  {
    label: '项目名称',
    key: 'team',
    value: ref(''),
    placeholder: '请选择项目组',
    required: true,
    type: 'select',
    validator: function () {
      if (!this.value.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  },
  {
    label: '客户端',
    key: 'end',
    value: ref(''),
    type: 'select',
    required: true,
    placeholder: '请选择客户端',
    validator: function () {
      if (!this.value.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  },
  {
    label: '类型',
    key: 'public_type',
    value: ref(''),
    type: 'select',
    required: true,
    placeholder: '请选择对应类型，注意不同类型的加载顺序',
    validator: function () {
      if (!this.value.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  },
  {
    label: '名称',
    key: 'name',
    value: ref(''),
    type: 'input',
    required: true,
    placeholder: '请输入名称',
    validator: function () {
      if (!this.value.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  },
  {
    label: 'key',
    key: 'key',
    value: ref(''),
    type: 'input',
    required: true,
    placeholder: '请输入缓存的key',
    validator: function () {
      if (!this.value.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  },
  {
    label: 'value',
    key: 'value',
    value: ref(''),
    type: 'textarea',
    required: true,
    placeholder: '请根据规则输入value值',
    validator: function () {
      if (!this.value.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  }
] as FormItem[]

const actionTitle = ref('新增参数')
const modalDialogRef = ref<ModalDialogType | null>(null)
const pagination = usePagination(doRefresh)
const { selectedRowKeys, onSelectionChange, showCheckedAll } = useRowSelection()
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
    title: '客户端',
    key: 'end',
    dataIndex: 'end',
    width: 150
  },
  {
    title: '类型',
    key: 'public_type',
    dataIndex: 'public_type'
  },
  {
    title: '名称',
    key: 'name',
    dataIndex: 'name',
    width: 150
  },
  {
    title: 'key',
    key: 'key',
    dataIndex: 'key',
    width: 150
  },
  {
    title: 'value',
    key: 'value',
    dataIndex: 'value',
    align: 'left'
  },
  {
    title: '状态',
    key: 'state',
    dataIndex: 'state'
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
const caseType: any = ref('0')

function switchType(key: any) {
  caseType.value = key
  doRefresh()
}

function doRefresh() {
  get({
    url: ApiPublic,
    data: () => {
      return {
        page: pagination.page,
        pageSize: pagination.pageSize,
        type: caseType.value
      }
    }
  })
    .then((res) => {
      table.handleSuccess(res)
      pagination.setTotalSize((res as any).totalSize)
    })
    .catch(console.log)
}

const selectValue: any = reactive({
  apiPublicPublic: [],
  apiPublicEnd: []
})

function doPublic() {
  get({
    url: ApiPublicPublic
  })
    .then((res) => {
      selectValue.apiPublicPublic = res.data
    })
    .catch(console.log)
}

function doEnd() {
  get({
    url: ApiPublicEnd
  })
    .then((res) => {
      selectValue.apiPublicEnd = res.data
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
  if (JSON.stringify(data) === '{}') {
    doRefresh()
  } else if (data.project) {
    get({
      url: ApiPublic,
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
      url: ApiPublic,
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
  actionTitle.value = '新增参数'
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
        url: ApiPublic,
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
  actionTitle.value = '编辑参数'
  modalDialogRef.value?.toggle()
  addUpdate.value = 0
  updateId.value = item.id
  nextTick(() => {
    formItems.forEach((it) => {
      const key = it.key
      const propName = item[key]
      if (propName) {
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
    if (addUpdate.value === 1) {
      addUpdate.value = 0
      post({
        url: ApiPublic,
        data: () => {
          return {
            project: value.project,
            name: value.name,
            url: value.url,
            environment: value.environment,
            executor_name: value.executor_name
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
        url: ApiPublic,
        data: () => {
          return {
            id: value.id,
            project: value.project,
            name: value.name,
            url: value.url,
            environment: value.environment,
            executor_name: value.executor_name
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
    doPublic()
    doEnd()
  })
})
</script>
