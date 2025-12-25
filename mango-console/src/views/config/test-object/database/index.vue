<template>
  <TableBody ref="tableBody">
    <template #header>
      <a-card title="数据库配置" :bordered="false">
        <template #extra>
          <a-space>
            <a-button size="small" status="warning" @click="doResetSearch">返回</a-button>
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
        @selection-change="onSelectionChange"
      >
        <template #columns>
          <a-table-column
            v-for="item of tableColumns"
            :key="item.key"
            :align="item.align"
            :data-index="item.key"
            :fixed="item.fixed"
            :title="item.title"
            :width="item.width"
          >
            <template v-if="item.key === 'index'" #cell="{ record }">
              {{ record.id }}
            </template>
            <template v-else-if="item.key === 'host'" #cell="{ record }">
              {{ record.host }}
            </template>
            <template v-else-if="item.key === 'port'" #cell="{ record }">
              {{ record.port }}
            </template>
            <template v-else-if="item.key === 'name'" #cell="{ record }">
              {{ record.name }}
            </template>
            <template v-else-if="item.key === 'user'" #cell="{ record }">
              {{ record.user }}
            </template>
            <template v-else-if="item.key === 'password'" #cell="{ record }">
              {{ record.password }}
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <a-space>
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
          <template v-else-if="item.type === 'cascader'">
            <a-cascader
              v-model="item.value"
              :options="projectInfo.projectProduct"
              :placeholder="item.placeholder"
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
  import { getFormItems } from '@/utils/datacleaning'
  import { conditionItems, formItems, tableColumns } from './config'
  import {
    deleteSystemDatabase,
    getSystemDatabase,
    postSystemDatabase,
    putSystemDatabase,
  } from '@/api/system/database'
  import { useRoute } from 'vue-router'

  const route = useRoute()

  const projectInfo = useProject()
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const pagination = usePagination(doRefresh)
  const { onSelectionChange } = useRowSelection()
  const table = useTable()
  const rowKey = useRowKey('id')
  const formModel = ref({})
  const data = reactive({
    actionTitle: '新增',
    isAdd: false,
    updateId: 0,
  })

  function doRefresh() {
    let value = getFormItems(conditionItems)
    value['test_object_id'] = route.query.id
    value['page'] = pagination.page
    value['pageSize'] = pagination.pageSize
    getSystemDatabase(value)
      .then((res) => {
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
      })
      .catch(console.log)
  }

  function doResetSearch() {
    window.history.back()
  }

  function onAdd() {
    data.actionTitle = '新增'
    modalDialogRef.value?.toggle()
    data.isAdd = true
    formItems.forEach((it) => {
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
        deleteSystemDatabase(record.id)
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
      const value = getFormItems(formItems)
      if (data.isAdd) {
        value['test_object'] = route.query.id
        postSystemDatabase(value)
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
        putSystemDatabase(value)
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

  onMounted(doRefresh)
</script>
