<template>
  <div>
    <div class="main-container">
      <TableBody ref="tableBody">
        <template #header>
          <TableHeader :show-filter="true" title="Api自动化用例管理" @search="onSearch" @reset-search="onResetSearch">
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
                    <template v-if="item.type === 'select'">
                      <a-select v-model="item.value.value" style="width: 150px" :placeholder="item.placeholder">
                        <a-option v-for="optionItem of item.optionItems" :key="optionItem.value" :value="optionItem.title">
                          {{ optionItem.title }}
                        </a-option>
                      </a-select>
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
          <a-tabs @tab-click="(key) => switchType(key)" default-active-key="1">
            <template #extra>
              <a-space v-if="caseType === '0'">
                <a-button type="primary" size="small" @click="onBatchUpload">批量上传</a-button>
                <a-button status="success" size="small" @click="onConcurrency">批量执行</a-button>
                <a-button status="warning" size="small" @click="setCase('测试用例')">设为调试</a-button>
                <a-button status="danger" size="small" @click="onDeleteItems">批量删除</a-button>
              </a-space>
              <a-space v-else-if="caseType === '1'">
                <a-button type="primary" size="small" @click="onAddPage">新增</a-button>
                <a-button status="warning" size="small" @click="setCase('定时任务')">调试完成</a-button>
                <a-button status="danger" size="small" @click="onDeleteItems">批量删除</a-button>
              </a-space>
              <a-space v-else-if="caseType === '2'">
                <a-button status="success" size="small" @click="onConcurrency">批量执行</a-button>
              </a-space>
              <a-space v-else />
            </template>
            <a-tab-pane key="0" title="本期接口" />
            <a-tab-pane key="1" title="调试接口" />
            <a-tab-pane key="2" title="调试完成" />
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
                :ellipsis="item.ellipsis"
                :tooltip="item.tooltip"
              >
                <template v-if="item.key === 'index'" #cell="{ record }">
                  {{ record.id }}
                </template>
                <template v-else-if="item.key === 'team'" #cell="{ record }"> 应用组</template>
                <template v-else-if="item.key === 'client'" #cell="{ record }">
                  <a-tag color="orangered" size="small" v-if="record.client === 0">WEB</a-tag>
                  <a-tag color="orange" size="small" v-else-if="record.client === 1">APP</a-tag>
                  <a-tag color="blue" size="small" v-else-if="record.client === 2">MINI</a-tag>
                </template>
                <template v-else-if="item.key === 'method'" #cell="{ record }">
                  <a-tag color="orangered" size="small" v-if="record.method === 0">GET</a-tag>
                  <a-tag color="orange" size="small" v-else-if="record.method === 1">POST</a-tag>
                  <a-tag color="blue" size="small" v-else-if="record.method === 2">PUT</a-tag>
                  <a-tag color="green" size="small" v-else-if="record.method === 3">DELETE</a-tag>
                </template>
                <template v-else-if="item.key === 'rely'" #cell="{ record }">
                  <a-tag color="blue" size="small" v-if="record.rely != null">已设置</a-tag>
                  <a-tag color="orange" size="small" v-else-if="record.rely === null">未设置</a-tag>
                </template>
                <template v-else-if="item.key === 'ass'" #cell="{ record }">
                  <a-tag color="green" size="small" v-if="record.ass != null">已设置</a-tag>
                  <a-tag color="red" size="small" v-else-if="record.ass === null">未设置</a-tag>
                </template>
                <template v-else-if="item.key === 'state'" #cell="{ record }">
                  <a-tag color="green" size="small" v-if="record.state === 1">通过</a-tag>
                  <a-tag color="red" size="small" v-else-if="record.state === 2">失败</a-tag>
                  <a-tag color="gray" size="small" v-else>未测试</a-tag>
                </template>
                <template v-else-if="item.key === 'actions'" #cell="{ record }">
                  <a-space v-if="caseType === '0'">
                    <a-button type="text" size="mini" @click="onRunCase(record)">执行</a-button>
                    <a-button type="text" size="mini" @click="onAssertion(record)">编辑/断言</a-button>
                    <a-button status="danger" type="text" size="mini" @click="onDelete(record)">删除</a-button>
                  </a-space>
                  <a-space v-else-if="caseType === '1'">
                    <a-button type="text" size="mini" @click="onRunCase(record)">执行</a-button>
                    <a-button type="text" size="mini" @click="onAssertion(record)">编辑/断言</a-button>
                    <a-button status="danger" type="text" size="mini" @click="onDelete(record)">删除</a-button>
                  </a-space>
                  <a-space v-else-if="caseType === '2'">
                    <a-button type="text" size="mini" @click="onRunCase(record)">执行</a-button>
                    <a-button type="text" size="mini" @click="onAssertion(record)">编辑/断言</a-button>
                    <a-button type="text" size="mini" @click="setCaseGroup(record)">设为用例组</a-button>
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
              <template v-else-if="item.type === 'tree-select'">
                <a-tree-select
                  v-model="item.value.value"
                  style="width: 100%"
                  :dropdown-style="{ maxHeight: '400px', overflow: 'auto' }"
                  :placeholder="item.placeholder"
                  allow-clear
                  :data="treeData"
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
// import {Search} from '@/components/ListSearch.vue'
import { get, post, put, deleted } from '@/api/http'
import { ApiCase, getAllItems, ApiCaseSynchronous, ApiRun } from '@/api/url'
import { usePagination, useRowKey, useRowSelection, useTable, useTableColumn } from '@/hooks/table'
import { FormItem, ModalDialogType } from '@/types/components'
import { Input, Message, Modal } from '@arco-design/web-vue'
import { defineComponent, h, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useTestObj } from '@/store/modules/get-test-obj'

interface TreeItem {
  title: string
  key: string
  children?: TreeItem[]
}

const conditionItems: Array<FormItem> = [
  {
    key: 'name',
    label: '用例名称',
    type: 'input',
    placeholder: '请输入用例名称',
    value: ref(''),
    reset: function () {
      this.value.value = ''
    },
    render: (formItem: FormItem) => {
      return h(Input, {
        placeholder: '请输入用例名称',
        modelValue: formItem.value.value,
        'onUpdate:modelValue': (value) => {
          formItem.value.value = value
        }
      })
    }
  },
  {
    key: 'caseid',
    label: '用例ID',
    type: 'input',
    placeholder: '请输入用例ID',
    value: ref(''),
    reset: function () {
      this.value.value = ''
    },
    render: (formItem: FormItem) => {
      return h(Input, {
        placeholder: '请输入用例ID',
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
const formItems = [
  {
    label: '项目名称',
    key: 'team',
    value: ref(''),
    placeholder: '请选择项目名称',
    required: true,
    type: 'tree-select'
  },
  {
    label: '用例名称',
    key: 'name',
    value: ref(''),
    type: 'input',
    required: true,
    placeholder: '请输入页面名称'
  }
] as FormItem[]

const testObj = useTestObj()
const actionTitle = ref('添加页面')
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
    title: '用例名称',
    key: 'name',
    dataIndex: 'name',
    width: 150
  },
  {
    title: '客户端',
    key: 'client',
    dataIndex: 'client',
    width: 80
  },
  {
    title: '方法',
    key: 'method',
    dataIndex: 'method',
    width: 80
  },
  {
    title: '请求体',
    key: 'body',
    dataIndex: 'body',
    align: 'left',
    ellipsis: true,
    tooltip: true
  },
  {
    title: '依赖',
    key: 'rely',
    dataIndex: 'rely',
    width: 80
  },
  {
    title: '断言',
    key: 'ass',
    dataIndex: 'ass',
    width: 80
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
    width: 250
  }
])
const caseType: any = ref('1')

function switchType(key: any) {
  caseType.value = key
  doRefresh()
}

const formModel = ref({})

function doRefresh() {
  get({
    url: ApiCase,
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
      url: ApiCase,
      data: () => {
        return {
          page: pagination.page,
          pageSize: pagination.pageSize,
          project: data.project,
          type: caseType.value
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
      url: ApiCase,
      data: () => {
        return {
          id: data.caseid,
          name: data.name,
          type: caseType.value
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
  actionTitle.value = '新建接口'
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

function onBatchUpload() {
  get({
    url: ApiCaseSynchronous,
    data: () => {
      return {
        team_id: '1',
        host: 'http://172.16.90.93:9999'
      }
    }
  })
    .then((res) => {
      doRefresh()
      Message.success(res.msg)
    })
    .catch(console.log)
}

function onDelete(data: any) {
  Modal.confirm({
    title: '提示',
    content: '是否要删除此页面？',
    cancelText: '取消',
    okText: '删除',
    onOk: () => {
      deleted({
        url: ApiCase,
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
        url: ApiCase,
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

// function onUpdate(item: any) {
//   actionTitle.value = '编辑页面'
//   modalDialogRef.value?.toggle()
//   addUpdate.value = 0
//   updateId.value = item.id
//   nextTick(() => {
//     formItems.forEach((it) => {
//       const key = it.key
//       const propName = item[key]
//       if (propName) {
//         it.value.value = propName
//       }
//     })
//   })
// }

function setCase(name: any) {
  if (selectedRowKeys.value.length === 0) {
    Message.error('请选择要设为' + name + '的数据')
    return
  }
  let type: any = 1
  if (name) {
    type = 5
  }
  Modal.confirm({
    title: '提示',
    content: '确定要把这些设为' + name + '的吗？',
    cancelText: '取消',
    okText: '确定',
    onOk: () => {
      put({
        url: ApiCase,
        data: () => {
          return {
            id: JSON.stringify(selectedRowKeys.value),
            type: type
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
        url: ApiCase,
        data: () => {
          return {
            project: value.project,
            name: value.name
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
        url: ApiCase,
        data: () => {
          return {
            id: value.id,
            project: value.project,
            name: value.name
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

// 获取所有项目
const treeData = ref<Array<TreeItem>>([])

function getItems() {
  get({
    url: getAllItems,
    data: {}
  })
    .then((res) => {
      for (let value of conditionItems) {
        if (value.key === 'project') {
          value.optionItems = res.data
        }
      }
      treeData.value = transformRoutes(res.data)
    })
    .catch(console.log)
}

function transformRoutes(routes: any[], parentPath = '/'): TreeItem[] {
  const list: TreeItem[] = []
  routes
    .filter((it) => it.hidden !== true && it.fullPath !== parentPath)
    .forEach((it) => {
      const searchItem: TreeItem = {
        // 可以控制是取id还是取名称
        key: it.title,
        title: it.title
      }
      if (it.children && it.children.length > 0) {
        searchItem.children = transformRoutes(it.children, it.fullPath)
      }
      list.push(searchItem)
    })
  return list
}

function onRunCase(record: any) {
  get({
    url: ApiRun,
    data: () => {
      return {
        case_id_list: '[' + record.id + ',]',
        test_obj: testObj.te
      }
    }
  })
    .then((res) => {
      Message.success(res.msg)
    })
    .catch(console.log)
}

const router = useRouter()

function onConcurrency() {
  Message.info('调用了并发按钮')
}

function setCaseGroup(record: any) {
  router.push({
    path: '/apitest/group',
    query: {
      id: record.id
    }
  })
}

function onAssertion(record: any) {
  console.log(record.project)
  router.push({
    path: '/apitest/details',
    query: {
      id: record.id,
      project: record.project
    }
  })
}

onMounted(doRefresh)
onMounted(getItems)
</script>

<style lang="less" scoped>
.avatar-container {
  position: relative;
  width: 30px;
  height: 30px;
  margin: 0 auto;
  vertical-align: middle;

  .avatar {
    width: 100%;
    height: 100%;
    border-radius: 50%;
  }

  .avatar-vip {
    border: 2px solid #cece1e;
  }

  .vip {
    position: absolute;
    top: 0;
    right: -9px;
    width: 15px;
    transform: rotate(60deg);
  }
}

.gender-container {
  .gender-icon {
    width: 20px;
  }
}
</style>
