<template>
  <TableBody ref="tableBody" class="mango-detail-workbench-page">
    <template #header>
      <div class="mango-detail-toolbar">
        <div class="mango-detail-heading">
          <div class="mango-detail-title">{{ datasourceDetailTitle }}</div>
          <div class="mango-detail-subtitle">维护当前产品下稳定的业务数据库名称，环境绑定在测试对象数据源中配置</div>
        </div>
        <a-space class="mango-detail-actions" wrap>
          <a-button size="small" type="primary" @click="onAdd">新增</a-button>
          <a-button size="small" @click="doResetSearch">返回</a-button>
        </a-space>
      </div>
    </template>

    <template #default>
      <a-table
        :scroll="{ x: 1100 }"
        :bordered="false"
        :columns="tableColumns"
        :data="table.dataList"
        :loading="table.tableLoading.value"
        :pagination="false"
        :row-key="rowKey"
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
            <template v-else-if="item.key === 'db_type'" #cell="{ record }">
              <a-tag :color="enumStore.colors[record.db_type]" size="small">
                {{ getDatabaseTypeName(record.db_type) }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'status'" #cell="{ record }">
              <a-switch
                :before-change="(newValue) => onModifyStatus(newValue, record)"
                :default-checked="record.status === 1"
              />
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <MangoTableActions
                :actions="[
                  { label: '编辑', onClick: () => onUpdate(record) },
                  { label: '删除', danger: true, onClick: () => onDelete(record) },
                ]"
              />
            </template>
          </a-table-column>
        </template>
      </a-table>
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
          <template v-else-if="item.type === 'select' && item.key === 'db_type'">
            <a-select
              v-model="item.value"
              :field-names="fieldNames"
              :options="enumStore.database_type"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              value-key="key"
            />
          </template>
          <template v-else-if="item.type === 'textarea'">
            <a-textarea
              v-model="item.value"
              :auto-size="{ minRows: 3, maxRows: 5 }"
              :placeholder="item.placeholder"
            />
          </template>
        </a-form-item>
      </a-form>
    </template>
  </ModalDialog>
</template>

<script lang="ts" setup>
  import {
    deleteDataFactoryDatasourceAlias,
    getDataFactoryDatasourceAlias,
    postDataFactoryDatasourceAlias,
    putDataFactoryDatasourceAlias,
  } from '@/api/data-factory'
  import { useRowKey, useTable } from '@/hooks/table'
  import { fieldNames } from '@/setting'
  import { useEnum } from '@/store/modules/get-enum'
  import { ModalDialogType } from '@/types/components'
  import { getFormItems } from '@/utils/datacleaning'
  import { Message, Modal } from '@arco-design/web-vue'
  import { computed, nextTick, onMounted, reactive, ref } from 'vue'
  import { useRoute } from 'vue-router'
  import { formItems, tableColumns } from './config'

  const route = useRoute()
  const enumStore = useEnum()
  const table = useTable()
  const rowKey = useRowKey('id')
  const formModel = ref({})
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const data = reactive({
    actionTitle: '新增',
    isAdd: true,
    updateId: 0,
  })

  const datasourceDetailTitle = computed(() => {
    const id = route.query.id || '-'
    const name = route.query.name || '-'
    return `产品逻辑数据源 / ${id} / ${name}`
  })

  function getDatabaseTypeName(value: number) {
    return enumStore.database_type?.find((item) => item.key === value)?.title || value
  }

  function doResetSearch() {
    window.history.back()
  }

  function doRefresh() {
    table.tableLoading.value = true
    getDataFactoryDatasourceAlias({
      project_product: route.query.id,
      page: 1,
      pageSize: 999,
    })
      .then((res) => {
        table.dataList = res.data || []
      })
      .finally(() => {
        table.tableLoading.value = false
      })
  }

  function onAdd() {
    data.actionTitle = '新增'
    data.isAdd = true
    modalDialogRef.value?.toggle()
    formItems.forEach((it) => {
      if (it.reset) {
        it.reset()
      } else if (it.key === 'db_type') {
        it.value = 0
      } else {
        it.value = ''
      }
    })
  }

  function onUpdate(record: any) {
    data.actionTitle = '编辑'
    data.isAdd = false
    data.updateId = record.id
    modalDialogRef.value?.toggle()
    nextTick(() => {
      formItems.forEach((it) => {
        it.value = record[it.key] ?? ''
      })
    })
  }

  function onDelete(record: any) {
    Modal.confirm({
      title: '删除产品逻辑源',
      content: `确认删除 ${record.name}？删除后会影响引用它的数据工厂实体、API SQL 和 UI SQL 配置。`,
      cancelText: '取消',
      okText: '删除',
      onBeforeOk: () => {
        return deleteDataFactoryDatasourceAlias(record.id)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      },
    })
  }

  function onDataForm() {
    if (formItems.every((it) => (it.validator ? it.validator() : true))) {
      const value = getFormItems(formItems)
      value.project_product = route.query.id
      value.status = 1
      const request = data.isAdd ? postDataFactoryDatasourceAlias : putDataFactoryDatasourceAlias
      if (!data.isAdd) {
        value.id = data.updateId
      }
      request(value)
        .then((res) => {
          modalDialogRef.value?.toggle()
          Message.success(res.msg)
          doRefresh()
        })
        .catch(console.log)
        .finally(() => {
          modalDialogRef.value?.setConfirmLoading(false)
        })
    } else {
      modalDialogRef.value?.setConfirmLoading(false)
    }
  }

  const onModifyStatus = async (newValue: boolean, record: any) => {
    return new Promise<any>((resolve, reject) => {
      putDataFactoryDatasourceAlias({
        id: record.id,
        project_product: record.project_product?.id || record.project_product || route.query.id,
        name: record.name,
        code: record.code,
        db_type: record.db_type,
        description: record.description || '',
        status: newValue ? 1 : 2,
      })
        .then((res) => {
          Message.success(res.msg)
          doRefresh()
          resolve(res.code === 200)
        })
        .catch(reject)
    })
  }

  onMounted(() => {
    enumStore.getEnum()
    doRefresh()
  })
</script>
