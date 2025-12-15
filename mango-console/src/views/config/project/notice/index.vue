<template>
  <TableBody ref="tableBody">
    <template #header>
      <a-card title="通知组配置" :bordered="false">
        <template #extra>
          <a-space>
            <a-button  size="small" status="warning" @click="doResetSearch">返回</a-button>
          </a-space>
        </template>
      </a-card>
    </template>

    <template #default>
      <a-tabs>
        <template #extra>
          <a-space>
            <div>
              <a-button size="small" type="primary" @click="onAdd">新增</a-button>
            </div>
          </a-space>
        </template>
      </a-tabs>
      <a-table
        :bordered="false"
        :columns="tableColumns"
        :data="table.dataList"
        :loading="table.tableLoading.value"
        :pagination="false"
        :rowKey="rowKey"
        :scroll="{ x: false }"
        @selection-change="onSelectionChange"
      >
        <template #columns>
          <a-table-column
            v-for="item of tableColumns"
            :key="item.key"
            :align="item.align"
            :data-index="item.key"
            :ellipsis="item.ellipsis"
            :fixed="item.fixed"
            :title="item.title"
            :tooltip="item.tooltip"
            :width="item.width"
          >
            <template v-if="item.key === 'index'" #cell="{ record }">
              {{ record.id }}
            </template>

            <template v-else-if="item.key === 'users'" #cell="{ record }">
              {{ Array.isArray(record.users) && record.users.length > 0 ? (typeof record.users[0] === 'object' && record.users[0] !== null ? record.users.map(u => u.username).join('，') : record.users.join('，')) : '' }}
            </template>

            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <a-space>
                <a-button size="mini" type="text" class="custom-mini-btn" @click="onTest(record)"
                  >测试
                </a-button>
                <a-button size="mini" type="text" class="custom-mini-btn" @click="onUpdate(record)"
                  >编辑
                </a-button>
                <a-button
                  size="mini"
                  status="danger"
                  type="text"
                  class="custom-mini-btn"
                  @click="onDelete(record)"
                  >删除
                </a-button>
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
  <ModalDialog ref="modalDialogRef" :title="data.actionTitle" @confirm="onDataForm">
    <template #content>
      <a-form :model="formModel">
        <a-form-item
          v-for="item of formItems"
          :key="item.key"
          :class="[item.required ? 'form-item__require' : 'form-item__no_require']"
          :label="item.label"
        >
          <template v-if="item.type === 'input'">
            <a-input v-model="item.value" :placeholder="item.placeholder" />
          </template>
          <template v-else-if="item.type === 'textarea'">
            <a-textarea
              v-model="item.value"
              :auto-size="{ minRows: 2, maxRows: 3 }"
              :placeholder="item.placeholder"
            />
          </template>

          <template v-else-if="item.type === 'select'">
            <a-select
              v-model="item.value"
              :placeholder="item.placeholder"
              :scrollbar="true"
              multiple
            >
              <a-option 
                v-for="user of data.userList" 
                :key="user.key" 
                :value="user.key"
              >
                {{ user.title }}
              </a-option>
            </a-select>
          </template>
        </a-form-item>
      </a-form>
    </template>
  </ModalDialog>
</template>

<script lang="ts" setup>
  import { usePagination, useRowKey, useRowSelection, useTable } from '@/hooks/table'
  import { ModalDialogType } from '@/types/components'
  import { Message, Modal } from '@arco-design/web-vue'
  import { onMounted, ref, nextTick, reactive } from 'vue'
  import { getFormItems } from '@/utils/datacleaning'
  import { formItems, tableColumns } from './config'
  import {
    deleteSystemNotice,
    getSystemNotice,
    getSystemNoticeTest,
    postSystemNotice,
    putSystemNotice,
  } from '@/api/system/notice_group'
  import { getUserName } from '@/api/user/user'
  import { useRoute } from 'vue-router'

  const route = useRoute()

  const modalDialogRef = ref<ModalDialogType | null>(null)
  const pagination = usePagination(doRefresh)
  const { onSelectionChange } = useRowSelection()
  const table = useTable()
  const rowKey = useRowKey('id')
  const formModel = ref({})

  const data: any = reactive({
    isAdd: false,
    updateId: 0,
    actionTitle: '新增',
    userList: [],
  })
  function doResetSearch() {
    window.history.back()
  }
  function doRefresh() {
    let value = {}
    value['project'] = route.query.id
    value['page'] = pagination.page
    value['pageSize'] = pagination.pageSize
    getSystemNotice(value)
      .then((res) => {
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
      })
      .catch(console.log)
  }

  function onAdd() {
    data.actionTitle = '添加'
    modalDialogRef.value?.toggle()
    data.isAdd = true
    formItems.forEach((it: any) => {
      if (it.reset) {
        it.reset()
      } else {
        it.value = ''
      }
    })
  }

  function onDelete(record: any) {
    Modal.confirm({
      title: '提示',
      content: '是否要删除此配置？',
      cancelText: '取消',
      okText: '删除',
      onOk: () => {
        deleteSystemNotice(record.id)
          .then((res) => {
            Message.success(res.msg)
          })
          .catch(console.log)
          .finally(() => {
            doRefresh()
          })
      },
    })
  }

  function onUpdate(item: any) {
    data.actionTitle = '编辑'
    modalDialogRef.value?.toggle()
    data.isAdd = false
    data.updateId = item.id
    nextTick(() => {
      formItems.forEach((it: any) => {
        const propName = item[it.key]
        // 特殊处理 users 字段，提取用户 ID 数组
        if (it.key === 'users' && Array.isArray(propName)) {
          if (propName.length > 0 && typeof propName[0] === 'object' && propName[0] !== null) {
            // 如果是用户对象数组，提取 id
            it.value = propName.map(user => user.id)
          } else {
            // 如果是 ID 数组或其他情况，直接赋值
            it.value = propName
          }
        } else if (typeof propName === 'object' && propName !== null) {
          it.value = propName.id
        } else if (item.type === 0) {
          it.value = JSON.parse(propName)
        } else {
          it.value = propName
        }
      })
    })
  }

  function onDataForm() {
    if (formItems.every((it: any) => (it.validator ? it.validator() : true))) {
      let value = getFormItems(formItems)
      if (data.isAdd) {
        value['project'] = route.query.id
        postSystemNotice(value)
          .then((res) => {
            modalDialogRef.value?.toggle()
            Message.success(res.msg)
            doRefresh()
          })
          .catch((error) => {
            console.log(error)
          })
          .finally(() => {
            modalDialogRef.value?.setConfirmLoading(false)
          })
      } else {
        value['id'] = data.updateId
        putSystemNotice(value)
          .then((res) => {
            modalDialogRef.value?.toggle()
            Message.success(res.msg)
            doRefresh()
          })
          .catch((error) => {
            console.log(error)
          })
          .finally(() => {
            modalDialogRef.value?.setConfirmLoading(false)
          })
      }
    } else {
      modalDialogRef.value?.setConfirmLoading(false)
    }
  }

  function getNickName() {
    getUserName()
      .then((res) => {
        data.userList = res.data
      })
      .catch(console.log)
  }

  function onTest(record: any) {
    getSystemNoticeTest(record.id)
      .then((res) => {
        Message.success(res.msg)
      })
      .catch(console.log)
  }

  onMounted(() => {
    nextTick(async () => {
      doRefresh()
      getNickName()
    })
  })
  onMounted(doRefresh)
</script>

<style lang="less" scoped>
</style>