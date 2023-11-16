<template>
  <div>
    <div class="main-container">
      <TableBody ref="tableBody" title="执行器列表">
        <template #header></template>

        <template #default>
          <a-tabs>
            <template #extra>
              <a-space>
                <div>
                  <!--                  <a-button type="primary" size="small" @click="onAddPage">新增</a-button>-->
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
                <template v-if="item.key === 'index'" :class="record" #cell="{ record }">
                  {{ record.id }}
                </template>
                <template v-else-if="item.key === 'actions'" #cell="{ record }">
                  <template v-if="record.username === 'admin'">
                    <a-space>
                      <a-button type="text" size="mini" @click="onUpdate(record)">领取</a-button>
                      <a-button status="danger" type="text" size="mini" @click="onDelete(record)" disabled>下线 </a-button>
                    </a-space>
                  </template>
                  <template v-if="record.username !== 'admin'">
                    <a-space>
                      <!--                      <a-button type="text" size="mini" @click="onUpdate(record)">领取</a-button>-->
                      <a-button status="danger" type="text" size="mini" @click="onDelete(record)" disabled>下线 </a-button>
                    </a-space>
                  </template>
                </template>
                <!--                <template v-else-if="item.key === 'actions' && record.username !== 'admin'" #cell="{ record }">-->
                <!--                  <a-space>-->
                <!--                    <a-button status="danger" type="text" size="mini" @click="onDelete(record)" disabled>删除</a-button>-->
                <!--                  </a-space>-->
                <!--                </template>-->
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
            </a-form-item>
          </a-form>
        </template>
      </ModalDialog>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { get, post, put, deleted } from '@/api/http'
import { SocketUserList } from '@/api/url'
import { usePagination, useRowKey, useRowSelection, useTable, useTableColumn } from '@/hooks/table'
import { FormItem, ModalDialogType } from '@/types/components'
import { Message, Modal } from '@arco-design/web-vue'
import { onMounted, ref, nextTick } from 'vue'

const formItems = [
  {
    label: '角色名称',
    key: 'name',
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
    label: '角色描述',
    key: 'description',
    value: ref(''),
    type: 'textarea',
    required: true,
    placeholder: '请输入橘色描述',
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
    title: '所有者',
    key: 'nickname',
    dataIndex: 'nickname'
  },
  {
    title: '账号',
    key: 'username',
    dataIndex: 'username'
  },
  {
    title: 'IP端口',
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
    url: SocketUserList,
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
        url: SocketUserList,
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
    if (addUpdate.value === 1) {
      addUpdate.value = 0
      post({
        url: SocketUserList,
        data: () => {
          return {
            description: value.description,
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
        url: SocketUserList,
        data: () => {
          return {
            id: value.id,
            description: value.description,
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

onMounted(() => {
  nextTick(async () => {
    doRefresh()
  })
})
</script>
