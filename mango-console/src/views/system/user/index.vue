<template>
  <TableBody ref="tableBody">
    <template #header>
      <TableHeader
        :show-filter="true"
        title="用户管理"
        @search="doRefresh"
        @reset-search="onResetSearch"
      >
        <template #search-content>
          <a-form layout="inline" :model="{}" @keyup.enter="doRefresh">
            <a-form-item v-for="item of conditionItems" :key="item.key" :label="item.label">
              <template v-if="item.type === 'input'">
                <a-input v-model="item.value" :placeholder="item.placeholder" @blur="doRefresh" />
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
              <!--                  <a-button type="primary" size="small" @click="onAddPage">新增</a-button>-->
            </div>
          </a-space>
        </template>
      </a-tabs>
      <a-table
        :bordered="false"
        :row-selection="{ selectedRowKeys, showCheckedAll }"
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
            :ellipsis="item.ellipsis"
            :tooltip="item.tooltip"
          >
            <template v-if="item.key === 'index'" #cell="{ record }">
              {{ record.id }}
            </template>
            <template v-else-if="item.key === 'role'" #cell="{ record }">
              {{ record.role === null ? '-' : record.role.name }}
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <a-space>
                <a-button type="text" size="mini" @click="onUpdate(record)">编辑</a-button>
                <a-button status="danger" type="text" size="mini" @click="onDelete(record)"
                  >删除</a-button
                >
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
  <ModalDialog ref="modalDialogRef" :title="userData.actionTitle" @confirm="onDataForm">
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
            <a-textarea
              v-model="item.value"
              :placeholder="item.placeholder"
              :auto-size="{ minRows: 3, maxRows: 5 }"
            />
          </template>
          <template v-else-if="item.type === 'input-tag'">
            <a-input-tag v-model="item.value" :placeholder="item.placeholder" allow-clear />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'role'">
            <a-select
              v-model="item.value"
              :placeholder="item.placeholder"
              :options="userData.allRole"
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
</template>

<script lang="ts" setup>
  import { usePagination, useRowKey, useRowSelection, useTable } from '@/hooks/table'
  import { ModalDialogType } from '@/types/components'
  import { Message, Modal } from '@arco-design/web-vue'
  import { onMounted, ref, nextTick, reactive } from 'vue'
  import { useProject } from '@/store/modules/get-project'
  import { fieldNames } from '@/setting'
  import { getFormItems } from '@/utils/datacleaning'
  import { conditionItems, formItems, tableColumns } from './config'
  import { deleteUserInfo, getUserInfo, postUserInfo, putUserInfo } from '@/api/user/user'
  import { getUserAllRole } from '@/api/user/role'

  const modalDialogRef = ref<ModalDialogType | null>(null)
  const pagination = usePagination(doRefresh)
  const { selectedRowKeys, onSelectionChange, showCheckedAll } = useRowSelection()
  const table = useTable()
  const rowKey = useRowKey('id')
  const project = useProject()
  const formModel = ref({})
  const userData = reactive({
    isAdd: false,
    updateId: 0,
    actionTitle: '新增',
    allRole: [],
  })

  function doRefresh() {
    let value = getFormItems(conditionItems)
    value['page'] = pagination.page
    value['pageSize'] = pagination.pageSize
    getUserInfo(value)
      .then((res) => {
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
      })
      .catch(console.log)
  }

  function getRole() {
    getUserAllRole()
      .then((res) => {
        userData.allRole = res.data
      })
      .catch(console.log)
  }

  function onResetSearch() {
    conditionItems.forEach((it) => {
      it.value = ''
    })
  }

  // function onAddPage() {
  //   userData.actionTitle = '添加用户'
  //   userData.isAdd = true
  //   modalDialogRef.value?.toggle()
  //   formItems.forEach((it) => {
  //     if (it.reset) {
  //       it.reset()
  //     } else {
  //       it.value = ''
  //     }
  //   })
  // }

  function onDelete(data: any) {
    Modal.confirm({
      title: '提示',
      content: '是否要删除此用户？',
      cancelText: '取消',
      okText: '删除',
      onOk: () => {
        deleteUserInfo(data.id)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      },
    })
  }

  function onUpdate(item: any) {
    userData.actionTitle = '编辑'
    userData.isAdd = false
    userData.updateId = item.id
    modalDialogRef.value?.toggle()
    nextTick(() => {
      formItems.forEach((it, index) => {
        if (it.key === 'password') {
          formItems.splice(index, 1)
          return
        }
        const propName = item[it.key]
        if (it.key === 'mailbox') {
          it.value = propName
        } else if (typeof propName === 'object' && propName !== null) {
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
      if (userData.isAdd) {
        postUserInfo(value)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      } else {
        value['id'] = userData.updateId
        putUserInfo(value)
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
      getRole()
    })
  })
</script>
