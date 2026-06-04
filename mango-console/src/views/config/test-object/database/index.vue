<template>
  <TableBody ref="tableBody" class="mango-detail-workbench-page">
    <template #header>
      <div class="mango-detail-toolbar">
        <div class="mango-detail-heading">
          <div class="mango-detail-title">{{ datasourceDetailTitle }}</div>
          <div class="mango-detail-subtitle">维护当前测试对象下的真实数据库，并绑定到产品逻辑数据源</div>
        </div>
        <a-space class="mango-detail-actions" wrap>
          <a-button size="small" @click="doResetSearch">返回</a-button>
        </a-space>
      </div>
    </template>

    <template #default>
      <a-tabs v-model:active-key="activeTab" @change="onTabChange">
        <a-tab-pane key="database" title="真实数据库" />
        <template #extra>
          <a-space>
            <a-button size="small" type="primary" @click="onAdd">
              新增数据库
            </a-button>
          </a-space>
        </template>
      </a-tabs>

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
            <template v-else-if="item.key === 'host'" #cell="{ record }">
              {{ record.host }}
            </template>
            <template v-else-if="item.key === 'db_type'" #cell="{ record }">
              {{ getDatabaseTypeName(record.db_type) }}
            </template>
            <template v-else-if="item.key === 'port'" #cell="{ record }">
              {{ record.port }}
            </template>
            <template v-else-if="item.key === 'name'" #cell="{ record }">
              {{ record.name }}
            </template>
            <template v-else-if="item.key === 'datasource_alias'" #cell="{ record }">
              <a-space v-if="record.datasource_alias_names?.length" wrap>
                <a-tag v-for="name in record.datasource_alias_names" :key="name" size="small">
                  {{ name }}
                </a-tag>
              </a-space>
              <span v-else class="mango-muted-text">未绑定</span>
            </template>
            <template v-else-if="item.key === 'user'" #cell="{ record }">
              {{ record.user }}
            </template>
            <template v-else-if="item.key === 'password'" #cell="{ record }">
              {{ record.password }}
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <MangoTableActions
                :max-inline="3"
                :actions="[
                  {
                    label: '测试',
                    loading: testingDatabaseIds.includes(record.id),
                    onClick: () => onTestDatabase(record),
                  },
                  { label: '编辑', onClick: () => onUpdate(record) },
                  { label: '删除', danger: true, onClick: () => onDelete(record) },
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
          <template v-else-if="item.key === 'datasource_alias'">
            <a-select
              v-model="item.value"
              :options="datasourceAliasOptions"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              @change="onDatasourceAliasChange"
            />
          </template>
          <template v-else-if="item.key === 'db_type'">
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
        </a-form-item>
      </a-form>
    </template>
  </ModalDialog>

</template>

<script lang="ts" setup>
  import {
    deleteSystemDatabase,
    getSystemDatabase,
    getSystemDatabaseTest,
    postSystemDatabase,
    putSystemDatabase,
  } from '@/api/system/database'
  import {
    deleteDataFactoryDatasourceBinding,
    getDataFactoryDatasourceAlias,
    getDataFactoryDatasourceBinding,
    postDataFactoryDatasourceBinding,
  } from '@/api/data-factory'
  import { usePagination, useRowKey, useRowSelection, useTable } from '@/hooks/table'
  import { useEnum } from '@/store/modules/get-enum'
  import { usePageData } from '@/store/page-data'
  import { ModalDialogType } from '@/types/components'
  import { getFormItems } from '@/utils/datacleaning'
  import { Message, Modal } from '@arco-design/web-vue'
  import { computed, nextTick, onMounted, reactive, ref } from 'vue'
  import { useRoute } from 'vue-router'
  import { conditionItems, formItems, tableColumns } from './config'

  const route = useRoute()
  const pageData = usePageData()

  const enumStore = useEnum()
  const fieldNames = { value: 'key', label: 'title' }
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const pagination = usePagination(doRefresh)
  const { onSelectionChange } = useRowSelection()
  const table = useTable()
  const rowKey = useRowKey('id')
  const formModel = ref({})
  const activeTab = ref('database')
  const datasourceAliasOptions = ref<any[]>([])
  const datasourceBindings = ref<any[]>([])
  const testingDatabaseIds = ref<any[]>([])

  const datasourceDetailTitle = computed(() => {
    const id = pageData.record?.id || route.query.id || '-'
    const name = pageData.record?.name || route.query.name || '-'
    return `数据源配置 / ${id} / ${name}`
  })
  const testObjectId = computed(() => firstQueryValue(pageData.record?.id || route.query.id))
  const projectProductId = computed(() => {
    return firstQueryValue(
      pageData.record?.project_product?.id
        || pageData.record?.project_product
        || route.query.project_product,
    )
  })
  const data = reactive({
    actionTitle: '新增',
    isAdd: false,
    updateId: 0,
  })

  function firstQueryValue(value: any) {
    return Array.isArray(value) ? value[0] : value
  }

  function doRefresh() {
    const value = getFormItems(conditionItems)
    value['test_object_id'] = testObjectId.value
    value['page'] = pagination.page
    value['pageSize'] = pagination.pageSize
    Promise.all([
      getSystemDatabase(value),
      getDataFactoryDatasourceBinding({
        test_object: testObjectId.value,
        page: 1,
        pageSize: 999,
      }),
    ])
      .then(([databaseRes, bindingRes]) => {
        datasourceBindings.value = bindingRes.data || []
        refreshDatasourceAliasDisabled(data.isAdd ? undefined : data.updateId || undefined)
        table.handleSuccess({
          ...databaseRes,
          data: mergeDatabaseBindings(databaseRes.data || [], datasourceBindings.value),
        })
        pagination.setTotalSize((databaseRes as any).totalSize)
      })
      .catch(console.log)
  }

  function doResetSearch() {
    window.history.back()
  }

  function getDatabaseTypeName(value: number) {
    return enumStore.database_type?.find((item) => item.key === value)?.title || value
  }

  function mergeDatabaseBindings(databases: any[], bindings: any[]) {
    return databases.map((database: any) => {
      const databaseBindings = bindings.filter((binding: any) => {
        const databaseId = binding.database?.id || binding.database
        return String(databaseId) === String(database.id)
      })
      return {
        ...database,
        datasource_bindings: databaseBindings,
        datasource_alias_names: databaseBindings.map((binding: any) => {
          return binding.datasource_alias?.name || binding.datasource_alias
        }).filter(Boolean),
      }
    })
  }

  function getFormItem(key: string) {
    return formItems.find((it) => it.key === key)
  }

  function selectedDatasourceAlias(value: any) {
    return datasourceAliasOptions.value.find((item: any) => String(item.value) === String(value))
  }

  function findAliasBinding(datasourceAliasId: any) {
    return datasourceBindings.value.find((binding: any) => {
      const aliasId = binding.datasource_alias?.id || binding.datasource_alias
      return String(aliasId) === String(datasourceAliasId)
    })
  }

  function onDatasourceAliasChange(value: any) {
    const alias = selectedDatasourceAlias(value)
    const dbTypeItem = getFormItem('db_type')
    if (alias && dbTypeItem) {
      dbTypeItem.value = alias.db_type
    }
  }

  function loadDatasourceAliasOptions() {
    if (!projectProductId.value) {
      datasourceAliasOptions.value = []
      return Promise.resolve()
    }
    return getDataFactoryDatasourceAlias({
      project_product: projectProductId.value,
      status: 1,
      page: 1,
      pageSize: 999,
    }).then((res) => {
      datasourceAliasOptions.value = (res.data || []).map((item: any) => ({
        ...item,
        value: item.id,
        label: `${item.name}（${getDatabaseTypeName(item.db_type)}）`,
      }))
      refreshDatasourceAliasDisabled()
    })
  }

  function refreshDatasourceAliasDisabled(currentDatabaseId?: any) {
    datasourceAliasOptions.value = datasourceAliasOptions.value.map((item: any) => {
      const binding = findAliasBinding(item.id)
      const databaseId = binding?.database?.id || binding?.database
      const disabled = Boolean(
        binding
        && currentDatabaseId
        && String(databaseId) !== String(currentDatabaseId),
      ) || Boolean(binding && !currentDatabaseId)
      return {
        ...item,
        disabled,
        label: disabled
          ? `${item.name}（已绑定：${binding?.database?.name || databaseId}）`
          : `${item.name}（${getDatabaseTypeName(item.db_type)}）`,
      }
    })
  }

  function onTabChange(key: string | number) {
    activeTab.value = String(key)
  }

  function onAdd() {
    data.actionTitle = '新增'
    modalDialogRef.value?.toggle()
    data.isAdd = true
    refreshDatasourceAliasDisabled()
    formItems.forEach((it) => {
      if (it.reset) {
        it.reset()
      } else {
        it.value = ''
      }
    })
    const dbTypeItem = getFormItem('db_type')
    if (dbTypeItem) {
      dbTypeItem.value = 0
    }
  }

  function onDelete(record: any) {
    Modal.confirm({
      title: '提示',
      content: '是否要删除此数据库配置？已绑定的逻辑数据源关系会一并移除。',
      cancelText: '取消',
      okText: '删除',
      onBeforeOk: () => {
        const bindingIds = (record.datasource_bindings || []).map((binding: any) => binding.id)
        return Promise.all(bindingIds.map((id: any) => deleteDataFactoryDatasourceBinding(id)))
          .then(() => deleteSystemDatabase(record.id))
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

  function setDatabaseTesting(id: any, testing: boolean) {
    testingDatabaseIds.value = testing
      ? Array.from(new Set([...testingDatabaseIds.value, id]))
      : testingDatabaseIds.value.filter((item) => String(item) !== String(id))
  }

  function onTestDatabase(record: any) {
    if (!record?.id) {
      Message.error('请选择要测试的数据库')
      return
    }
    setDatabaseTesting(record.id, true)
    getSystemDatabaseTest({ id: record.id })
      .then((res) => {
        Message.success(res.msg)
      })
      .catch(console.log)
      .finally(() => {
        setDatabaseTesting(record.id, false)
      })
  }

  function onUpdate(item: any) {
    data.actionTitle = '编辑'
    modalDialogRef.value?.toggle()
    data.isAdd = false
    data.updateId = item.id
    refreshDatasourceAliasDisabled(item.id)
    nextTick(() => {
      formItems.forEach((it) => {
        if (it.key === 'datasource_alias') {
          const binding = item.datasource_bindings?.[0]
          it.value = binding?.datasource_alias?.id || binding?.datasource_alias || ''
        } else {
          const propName = item[it.key]
          if (typeof propName === 'object' && propName !== null) {
            it.value = propName.id
          } else {
            it.value = propName
          }
        }
      })
    })
  }

  async function syncDatasourceBinding(databaseId: any, datasourceAliasId: any, previousBindingId?: any) {
    await postDataFactoryDatasourceBinding({
      datasource_alias: datasourceAliasId,
      test_object: testObjectId.value,
      database: databaseId,
      status: 1,
    })
    if (previousBindingId) {
      const currentBinding = datasourceBindings.value.find((binding: any) => {
        return String(binding.id) === String(previousBindingId)
      })
      const previousAliasId = currentBinding?.datasource_alias?.id || currentBinding?.datasource_alias
      if (previousAliasId && String(previousAliasId) !== String(datasourceAliasId)) {
        await deleteDataFactoryDatasourceBinding(previousBindingId)
      }
    }
  }

  function validateDatasourceBindingForm(value: any, datasourceAliasId: any) {
    const alias = selectedDatasourceAlias(datasourceAliasId)
    if (!alias) {
      Message.error('请选择逻辑数据源')
      return false
    }
    if (Number(alias.db_type) !== Number(value.db_type)) {
      Message.error('逻辑数据源类型与数据库类型必须一致')
      return false
    }
    const binding = findAliasBinding(datasourceAliasId)
    const databaseId = binding?.database?.id || binding?.database
    if (binding && (!data.updateId || String(databaseId) !== String(data.updateId))) {
      Message.error('当前逻辑数据源已绑定其他真实数据库，一个逻辑数据源只能绑定一个真实数据库')
      return false
    }
    return true
  }

  function onDataForm() {
    if (formItems.every((it) => (it.validator ? it.validator() : true))) {
      const value = getFormItems(formItems)
      const datasourceAliasId = value.datasource_alias
      delete value.datasource_alias
      if (!validateDatasourceBindingForm(value, datasourceAliasId)) {
        modalDialogRef.value?.setConfirmLoading(false)
        return
      }
      if (data.isAdd) {
        value['test_object'] = testObjectId.value
        postSystemDatabase(value)
          .then(async (res) => {
            await syncDatasourceBinding(res.data?.id, datasourceAliasId)
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
        const currentDatabase = table.dataList.find((item: any) => String(item.id) === String(data.updateId))
        const previousBindingId = currentDatabase?.datasource_bindings?.[0]?.id
        putSystemDatabase(value)
          .then(async (res) => {
            await syncDatasourceBinding(data.updateId, datasourceAliasId, previousBindingId)
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

  onMounted(() => {
    enumStore.getEnum()
    loadDatasourceAliasOptions()
    doRefresh()
  })
</script>
