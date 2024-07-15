<template>
  <div>
    <div class="main-container">
      <TableBody ref="tableBody">
        <template #header>
          <TableHeader
            :show-filter="true"
            title="项目产品配置"
            @search="doRefresh"
            @reset-search="onResetSearch"
          >
            <template #search-content>
              <a-form layout="inline" :model="{}" @keyup.enter="doRefresh">
                <a-form-item v-for="item of conditionItems" :key="item.key" :label="item.label">
                  <template v-if="item.type === 'input'">
                    <a-input
                      v-model="item.value"
                      :placeholder="item.placeholder"
                      @blur="doRefresh"
                    />
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
                  <a-button type="primary" size="small" @click="onAdd">新增</a-button>
                </div>
              </a-space>
            </template>
          </a-tabs>
          <a-table
            :bordered="false"
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
              >
                <template v-if="item.key === 'index'" #cell="{ record }">
                  {{ record.id }}
                </template>
                <template v-else-if="item.key === 'project'" #cell="{ record }">
                  {{ record.project.name }}
                </template>
                <template v-else-if="item.key === 'auto_type'" #cell="{ record }">
                  <a-tag color="orangered" size="small" v-if="record.auto_type === 0"
                    >界面自动化</a-tag
                  >
                  <a-tag color="cyan" size="small" v-else-if="record.auto_type === 1"
                    >接口自动化</a-tag
                  >
                  <a-tag color="green" size="small" v-else-if="record.auto_type === 2"
                    >性能自动化</a-tag
                  >
                </template>
                <template v-else-if="item.key === 'client_type'" #cell="{ record }">
                  <a-tag color="orangered" size="small" v-if="record.client_type === 0">WEB</a-tag>
                  <a-tag color="green" size="small" v-else-if="record.client_type === 1"
                    >PC桌面</a-tag
                  >
                  <template v-if="record.auto_type === 0">
                    <a-tag color="orangered" size="small" v-if="record.client_type === 2"
                      >安卓</a-tag
                    >
                    <a-tag color="cyan" size="small" v-else-if="record.client_type === 3"
                      >IOS</a-tag
                    > </template
                  ><template v-if="record.auto_type === 1">
                    <a-tag color="cyan" size="small" v-if="record.client_type === 2">APP</a-tag>
                    <a-tag color="green" size="small" v-else-if="record.client_type === 3"
                      >小程序</a-tag
                    >
                  </template>
                </template>

                <template v-else-if="item.key === 'actions'" #cell="{ record }">
                  <a-space>
                    <a-button type="text" size="mini" @click="onUpdate(record)">编辑</a-button>
                    <a-button type="text" size="mini" @click="onClick(record)">增加模块</a-button>
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
      <ModalDialog ref="modalDialogRef" :title="data.actionTitle" @confirm="onDataForm">
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
              <template v-else-if="item.type === 'select' && item.key === 'project'">
                <a-select
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="project.data"
                  :field-names="fieldNames"
                  value-key="key"
                  allow-clear
                  allow-search
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'auto_type'">
                <a-select
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="data.AutoTestNameList"
                  :field-names="fieldNames"
                  @change="getTypeList(item.value, item)"
                  value-key="key"
                  allow-clear
                  allow-search
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'client_type'">
                <a-select
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="data.typeList"
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
    </div>
  </div>
</template>

<script lang="ts" setup>
  import { usePagination, useRowKey, useRowSelection, useTable } from '@/hooks/table'
  import { ModalDialogType } from '@/types/components'
  import { Message, Modal } from '@arco-design/web-vue'
  import { onMounted, ref, nextTick, reactive } from 'vue'
  import { getFormItems } from '@/utils/datacleaning'
  import { useRouter } from 'vue-router'
  import { useProject } from '@/store/modules/get-project'
  import { fieldNames } from '@/setting'
  import { conditionItems, formItems, tableColumns } from './config'
  import { deleteUserProduct, getUserProduct, postUserProduct, putUserProduct } from '@/api/user'
  import { getSystemEnumAutotest, getSystemEnumEnd, getSystemEnumPlatform } from '@/api/system'

  const modalDialogRef = ref<ModalDialogType | null>(null)
  const pagination = usePagination(doRefresh)
  const { onSelectionChange } = useRowSelection()
  const table = useTable()
  const rowKey = useRowKey('id')
  const formModel = ref({})
  const router = useRouter()
  const project = useProject()

  const data = reactive({
    isAdd: false,
    updateId: 0,
    actionTitle: '添加项目',
    typeList: [],
    AutoTestNameList: [],
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
    getUserProduct(value)
      .then((res) => {
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
      })
      .catch(console.log)
  }

  function onAdd() {
    data.actionTitle = '添加项目'
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
      content: '是否要删除此产品？',
      cancelText: '取消',
      okText: '删除',
      onOk: () => {
        deleteUserProduct(data.id)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
            project.projectProductName()
          })
          .catch(console.log)
      },
    })
  }

  function onUpdate(item: any) {
    data.actionTitle = '编辑项目'
    data.isAdd = false
    data.updateId = item.id
    modalDialogRef.value?.toggle()
    getTypeList(item.auto_type, item)
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

  function onClick(record: any) {
    router.push({
      path: '/config/product/module',
      query: {
        id: record.id,
        name: record.name,
      },
    })
  }

  function onDataForm() {
    if (formItems.every((it) => (it.validator ? it.validator() : true))) {
      modalDialogRef.value?.toggle()
      let value = getFormItems(formItems)
      if (data.isAdd) {
        value['status'] = 1
        postUserProduct(value)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
            project.projectProductName()
          })
          .catch(console.log)
      } else {
        value['id'] = data.updateId
        putUserProduct(value)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
            project.projectProductName()
          })
          .catch(console.log)
      }
    }
  }
  function getAutoTestName() {
    getSystemEnumAutotest()
      .then((res) => {
        data.AutoTestNameList = res.data
      })
      .catch(console.log)
  }
  function getTypeList(autoTestType: number, item: any) {
    if (autoTestType === 0) {
      getSystemEnumPlatform()
        .then((res) => {
          data.typeList = res.data
        })
        .catch(console.log)
    } else if (autoTestType === 1) {
      getSystemEnumEnd()
        .then((res) => {
          data.typeList = res.data
        })
        .catch(console.log)
    } else {
      Message.warning('不支持选择自动化类型为性能，请重新选择！')
      item.value = ''
    }
  }
  onMounted(() => {
    nextTick(async () => {
      doRefresh()
      getAutoTestName()
    })
  })
</script>

<style></style>
