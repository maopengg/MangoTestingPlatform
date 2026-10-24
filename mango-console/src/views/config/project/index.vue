<template>
  <TableBody ref="tableBody" content-flush>
    <template #header>
      <TableHeader
        :show-filter="true"
        title="项目配置"
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
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :field-names="fieldNames"
                  :options="item.key === 'update_user' ? item.optionItems : project.data"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
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
      <TableTabs>
        <template #extra>
          <a-space>
            <div>
              <a-button v-permission="'config.project:create'" size="small" type="primary" @click="onAdd" data-testid="qa-views-config-project-button-新增">新增</a-button>
            </div>
          </a-space>
        </template>
      </TableTabs>
      <a-table
        :scroll="{ x: 1100 }"
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
              <a-switch v-permission="'config.project:status'"
                :beforeChange="(newValue) => onModifyStatus(newValue, record.id, record.name)"
                :default-checked="record.status === 1"
              />
            </template>
            <template v-else-if="item.key === 'update_user'" #cell="{ record }">
              {{ record.update_user?.name || record.update_user?.username || '-' }}
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <MangoTableActions
                :actions="[
                  { permission: 'config.project:edit', label: '编辑', onClick: () => onUpdate(record) },
                  { permission: 'config.project:detail', label: '通知组', onClick: () => clickNotice(record) },
                  { permission: 'config.project:delete', label: '删除', danger: true, onClick: () => onDelete(record) },
                ]"
              />
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
          :class="[item.required ? 'mango-form-item__require' : 'mango-form-item__no_require']"
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
  import { usePageData } from '@/store/page-data'
  import { useRouter } from 'vue-router'
  import { getUserName } from '@/api/user/user'
  import { setUpdateUserOptions } from '@/utils/update-user'
  import TableTabs from '@/components/table/TableTabs.vue'

  const modalDialogRef = ref<ModalDialogType | null>(null)
  const pagination = usePagination(doRefresh, () => table.tableLoading)
  const { onSelectionChange } = useRowSelection()
  const table = useTable()
  const rowKey = useRowKey('id')
  const formModel = ref({})
  const project = useProject()
  const router = useRouter()

  const data = reactive({
    isAdd: false,
    updateId: 0,
    actionTitle: '新增',
  })

  function onResetSearch() {
    conditionItems.forEach((it) => {
      it.value = it.multiple ? [] : ''
    })
    doRefresh()
  }

  function doRefresh() {
    let value = getFormItems(conditionItems)
    if (value.update_user === null || value.update_user === '') {
      delete value.update_user
    }
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
        it.value = it.multiple ? [] : ''
      }
    })
  }

  function onDelete(record: any) {
    Modal.confirm({
      title: '提示',
      content: '是否要删除此项目？',
      cancelText: '取消',
      okText: '删除',
      onBeforeOk: () => {
        return deleteUserDepartmentList(record.id)
          .then((res) => {
            Message.success(res.msg)
            project.invalidateAllProductModuleTreeCache()
          })
          .catch(console.log)
          .finally(() => {
            doRefresh()
            project.getProject()
            project.projectProductName()
          })
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
      let value = getFormItems(formItems)
      if (data.isAdd) {
        value['status'] = 1
        postUserDepartmentList(value)
          .then((res) => {
            modalDialogRef.value?.toggle()
            Message.success(res.msg)
            doRefresh()
            project.getProject()
            project.projectProductName()
            project.invalidateAllProductModuleTreeCache()
          })
          .catch((error) => {
            console.log(error)
          })
          .finally(() => {
            modalDialogRef.value?.setConfirmLoading(false)
          })
      } else {
        value['id'] = data.updateId
        putUserDepartmentList(value)
          .then((res) => {
            modalDialogRef.value?.toggle()
            Message.success(res.msg)
            doRefresh()
            project.getProject()
            project.projectProductName()
            project.invalidateAllProductModuleTreeCache()
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
              project.invalidateAllProductModuleTreeCache()
            })
            .catch(reject)
          resolve(value)
        } catch (error) {
          reject(error)
        }
      }, 300)
    })
  }

  function clickNotice(record: any) {
    const pageData = usePageData()
    pageData.setRecord(record)
    router.push({
      path: '/config/project/notice',
      query: {
        id: record.id,
        name: record.name,
      },
    })
  }
  onMounted(() => {
    nextTick(async () => {
      getUserName().then((res) => setUpdateUserOptions(conditionItems, res.data || []))
      doRefresh()
    })
  })
</script>

<style></style>
