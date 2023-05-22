<template>
  <div>
    <div class="main-container">
      <TableBody ref="tableBody">
        <template #header></template>

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
                <template v-else-if="item.key === 'user_id'" #cell="{ record }">
                  {{ record.user_id.nickname }}
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
              <template v-else-if="item.type === 'select' && item.key === 'user_id'">
                <a-select
                  v-model="item.value.value"
                  :placeholder="item.placeholder"
                  :options="uiConfigData.userList"
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
import { getNickname, uiConfig } from '@/api/url'
import { usePagination, useRowKey, useRowSelection, useTable, useTableColumn } from '@/hooks/table'
import { FormItem, ModalDialogType } from '@/types/components'
import { Message, Modal } from '@arco-design/web-vue'
import { onMounted, ref, nextTick, reactive } from 'vue'
import { fieldNames } from '@/setting'
import { getKeyByTitle, transformData } from '@/utils/datacleaning'

const formItems = [
  {
    label: '浏览器路径',
    key: 'browser_path',
    value: ref(''),
    type: 'textarea',
    required: true,
    placeholder: '请输入浏览器路径',
    validator: function () {
      if (!this.value.value && this.value.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  },
  {
    label: '浏览器端口',
    key: 'local_port',
    value: ref(''),
    placeholder: '请输入角色名称',
    required: true,
    type: 'input',
    validator: function () {
      if (!this.value.value && this.value.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  },
  {
    label: '安卓设备号',
    key: 'equipment',
    value: ref(''),
    placeholder: '请输入角色名称',
    required: true,
    type: 'input',
    validator: function () {
      if (!this.value.value && this.value.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  },
  {
    label: '所属用户',
    key: 'user_id',
    value: ref(''),
    type: 'select',
    required: true,
    placeholder: '请设置用例负责人',
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
    title: '浏览器类型',
    key: 'name',
    dataIndex: 'name'
  },
  {
    title: '浏览器地址',
    key: 'browser_path',
    dataIndex: 'browser_path',
    align: 'left'
  },
  {
    title: '浏览器端口',
    key: 'local_port',
    dataIndex: 'local_port'
  },
  {
    title: '安卓设备',
    key: 'equipment',
    dataIndex: 'equipment'
  },
  {
    title: '所属用户',
    key: 'user_id',
    dataIndex: 'user_id'
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
    url: uiConfig,
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
        url: uiConfig,
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
        url: uiConfig,
        data: () => {
          return {
            user_id: value.user_id,
            browser_path: value.browser_path,
            equipment: value.equipment,
            local_port: value.local_port
          }
        }
      })
        .then((res) => {
          Message.success(res.msg)
          doRefresh()
        })
        .catch(console.log)
    } else if (addUpdate.value === 0) {
      let userID = value.user_id
      if (typeof value.user_id === 'string') {
        userID = getKeyByTitle(uiConfigData.userList, value.user_id)
      }
      addUpdate.value = 0
      value['id'] = updateId.value
      updateId.value = 0
      put({
        url: uiConfig,
        data: () => {
          return {
            id: value.id,
            user_id: userID,
            browser_path: value.browser_path,
            equipment: value.equipment,
            local_port: value.local_port
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

const uiConfigData = reactive({
  userList: []
})

function getNickName() {
  get({
    url: getNickname,
    data: () => {
      return {}
    }
  })
    .then((res) => {
      uiConfigData.userList = res.data
    })
    .catch(console.log)
}

onMounted(() => {
  nextTick(async () => {
    doRefresh()
    getNickName()
  })
})
</script>
