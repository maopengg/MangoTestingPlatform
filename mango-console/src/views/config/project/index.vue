<template>
  <TableBody ref="tableBody">
    <template #header>
      <TableHeader
        :show-filter="true"
        title="项目管理"
        @search="doRefresh"
        @reset-search="onResetSearch"
      >
        <template #search-content>
          <a-form :model="{}" layout="inline" @keyup.enter="doRefresh">
            <a-form-item v-for="item of conditionItems" :key="item.key" :label="item.label">
              <template v-if="item.type === 'input'">
                <a-input v-model="item.value" :placeholder="item.placeholder" @blur="doRefresh" />
              </template>
              <template v-else-if="item.type === 'select'">
                <a-select
                  v-model="item.value"
                  :field-names="fieldNames"
                  :options="project.data"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  style="width: 150px"
                  value-key="key"
                  @change="doRefresh"
                />
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
            <template v-else-if="item.key === 'status'" #cell="{ record }">
              <a-switch
                :beforeChange="(newValue) => onModifyStatus(newValue, record.id, record.name)"
                :default-checked="record.status === 1"
              />
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <a-space>
                <a-button size="mini" type="text" @click="onUpdate(record)">编辑</a-button>
                <a-button size="mini" status="danger" type="text" @click="onDelete(record)"
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
        </a-form-item>
      </a-form>
    </template>
  </ModalDialog>
</template>

<script lang="ts" setup>
  import { usePagination, useRowKey, useRowSelection, useTable } from '@/hooks/table'
  import { ModalDialogType } from '@/types/components'
  import { Message, Modal } from '@arco-design/web-vue'
  import { nextTick, onMounted, reactive, ref } from 'vue'
  import { getFormItems } from '@/utils/datacleaning'
  import { useProject } from '@/store/modules/get-project'
  import { fieldNames } from '@/setting'
  import { conditionItems, formItems, tableColumns } from './config'
  import {
    deleteUserDepartmentList,
    getUserDepartmentList,
    postUserDepartmentList,
    putUserDepartmentList,
  } from '@/api/system/project'

  const modalDialogRef = ref<ModalDialogType | null>(null)
  const pagination = usePagination(doRefresh)
  const { onSelectionChange } = useRowSelection()
  const table = useTable()
  const rowKey = useRowKey('id')
  const formModel = ref({})
  const project = useProject()

  const data = reactive({
    isAdd: false,
    updateId: 0,
    actionTitle: '新增',
  })

  function onResetSearch() {
    conditionItems.forEach((it) => {
      it.value = ''
    })
  }

  function doRefresh() {
    let value = getFormItems(conditionItems)
    value['page'] = pagination.page
    value['pageSize'] = pagination.pageSize
    getUserDepartmentList(value)
      .then((res) => {
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
      })
      .catch(console.log)
  }

  function onAdd() {
    data.actionTitle = '新增'
    data.isAdd = true
    modalDialogRef.value?.toggle()
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
      content: '是否要删除此项目？',
      cancelText: '取消',
      okText: '删除',
      onOk: () => {
        deleteUserDepartmentList(data.id)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
            project.getProject()
          })
          .catch(console.log)
      },
    })
  }

  function onUpdate(item: any) {
    data.actionTitle = '编辑'
    data.isAdd = false
    data.updateId = item.id
    modalDialogRef.value?.toggle()
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
      if (data.isAdd) {
        value['status'] = 1
        postUserDepartmentList(value)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
            project.getProject()
          })
          .catch(console.log)
      } else {
        value['id'] = data.updateId
        putUserDepartmentList(value)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
            project.getProject()
          })
          .catch(console.log)
      }
    }
  }

  const onModifyStatus = async (newValue: boolean, id: number, name: string) => {
    return new Promise<any>((resolve, reject) => {
      setTimeout(async () => {
        try {
          let value: any = false
          await putUserDepartmentList({
            id: id,
            name: name,
            status: newValue ? 1 : 0,
          })
            .then((res) => {
              Message.success(res.msg)
              value = res.code === 200
              project.getProject()
            })
            .catch(reject)
          resolve(value)
        } catch (error) {
          reject(error)
        }
      }, 300)
    })
  }

  onMounted(() => {
    nextTick(async () => {
      doRefresh()
    })
  })
</script>

<style></style>
