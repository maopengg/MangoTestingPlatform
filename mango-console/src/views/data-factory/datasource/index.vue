<template>
  <TableBody content-flush>
    <template #header>
      <TableHeader title="数据工厂 / 数据库映射" @search="doRefresh" @reset-search="onResetSearch">
        <template #search-content>
          <a-form :model="{}" layout="inline" @keyup.enter="doRefresh">
            <a-form-item
              v-for="item of datasourceAliasConditionItems"
              :key="item.key"
              :label="item.label"
            >
              <template v-if="item.type === 'input'">
                <a-input
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  allow-clear
                  @blur="doRefresh"
                  @clear="doRefresh"
                />
              </template>
              <template v-else-if="item.type === 'cascader' && item.key === 'project_product'">
                <ProjectProductSelect
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  @change="doRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'db_type'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :field-names="enumFieldNames"
                  :options="enumStore.data_source_type"
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
          <div>
            <a-space>
              <a-button size="small" type="primary" @click="openAlias()" data-testid="qa-views-data-factory-datasource-button-新增逻辑源">新增逻辑源</a-button>
            </a-space></div
          >
        </template>
      </TableTabs>
      <a-table
        :scroll="{ x: 1100 }"
        :columns="datasourceAliasColumns"
        :data="aliasTable.dataList"
        :loading="aliasTable.tableLoading.value"
        :pagination="false"
        :row-key="'id'"
      >
        <template #columns>
          <a-table-column
            v-for="item of datasourceAliasColumns"
            :key="item.key"
            :align="item.align"
            :data-index="item.key"
            :fixed="item.fixed"
            :ellipsis="item.ellipsis"
            :tooltip="item.tooltip"
            :title="item.title"
            :width="item.width"
          >
            <template v-if="item.key === 'index'" #cell="{ record }">
              {{ record.id }}
            </template>
            <template v-else-if="item.key === 'project_product'" #cell="{ record }">
              {{ formatProjectProductPath(record?.project_product) }}
            </template>
            <template v-else-if="item.key === 'db_type'" #cell="{ record }">
              <a-tag :color="enumStore.colors[record.db_type]" size="small">
                {{ enumTitle(enumStore.data_source_type, record.db_type) }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'update_user'" #cell="{ record }">
              {{ record.update_user?.name || record.update_user?.username || '-' }}
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <MangoTableActions
                :actions="[
                  { label: '编辑', onClick: () => openAlias(record) },
                  {
                    label: '环境绑定',
                    loading: actionLoading === `binding-${record.id}`,
                    onClick: () => openBinding(record),
                  },
                  {
                    label: '删除',
                    danger: true,
                    loading: actionLoading === `alias-delete-${record.id}`,
                    onClick: () => removeAlias(record),
                  },
                ]"
              />
            </template>
          </a-table-column>
        </template>
      </a-table>
    </template>
    <template #footer><TableFooter :pagination="pagination" /></template>
  </TableBody>

  <a-modal
    v-model:visible="aliasVisible"
    :on-before-ok="saveAlias"
    :ok-loading="aliasSaving"
    :title="aliasForm.id ? '编辑逻辑数据库' : '新增逻辑数据库'"
    width="680px"
  >
    <a-form :model="aliasForm" layout="vertical">
      <a-form-item label="产品" required>
        <ProjectProductSelect v-model="aliasForm.project_product" />
      </a-form-item>
      <a-form-item label="名称" required><a-input v-model="aliasForm.name" /></a-form-item>
      <a-form-item label="数据库分类" required>
        <a-select
          v-model="aliasForm.source_category"
          :options="enumStore.data_source_category"
          :field-names="enumFieldNames"
          @change="onAliasCategoryChange"
        />
      </a-form-item>
      <a-form-item label="数据库类型" required>
        <a-select
          v-model="aliasForm.db_type"
          :options="aliasSourceTypeOptions"
          :field-names="enumFieldNames"
        />
      </a-form-item>
      <a-form-item label="描述"><a-textarea v-model="aliasForm.description" /></a-form-item>
    </a-form>
  </a-modal>

  <a-drawer
    v-model:visible="bindingVisible"
    :title="`${currentAlias?.name || ''} / 环境绑定`"
    width="900px"
  >
    <a-space class="datasource-toolbar">
      <a-button type="primary" @click="openBindingForm()" data-testid="qa-views-data-factory-datasource-button-新增绑定">新增绑定</a-button>
      <a-button :loading="bindingLoading" @click="loadBindings" data-testid="qa-views-data-factory-datasource-button-刷新">刷新</a-button>
    </a-space>
    <a-table
      :scroll="{ x: 1100 }"
      :columns="datasourceBindingColumns"
      :data="bindingRows"
      :loading="bindingLoading"
      :pagination="false"
      :row-key="'id'"
    >
      <template #columns>
        <a-table-column
          v-for="item of datasourceBindingColumns"
          :key="item.key"
          :align="item.align"
          :data-index="item.key"
          :ellipsis="item.ellipsis"
          :tooltip="item.tooltip"
          :title="item.title"
          :width="item.width"
        >
          <template v-if="item.key === 'index'" #cell="{ record }">
            {{ record.id }}
          </template>
          <template v-else-if="item.key === 'environment'" #cell="{ record }">
            <a-tag size="small">
              {{ enumTitle(enumStore.environment_type, record.environment) }}
            </a-tag>
          </template>
          <template v-else-if="item.key === 'data_source'" #cell="{ record }">
            {{ displayDataSource(record.data_source || record.database) }}
          </template>
          <template v-else-if="item.key === 'update_user'" #cell="{ record }">
            {{ record.update_user?.name || record.update_user?.username || '-' }}
          </template>
          <template v-else-if="item.key === 'db_c_status'" #cell="{ record }">
            {{ record.db_c_status === 1 ? '允许' : '禁止' }}
          </template>
          <template v-else-if="item.key === 'db_rud_status'" #cell="{ record }">
            {{ record.db_rud_status === 1 ? '允许' : '禁止' }}
          </template>
          <template v-else-if="item.key === 'actions'" #cell="{ record }">
            <MangoTableActions
              :actions="[
                { label: '编辑', onClick: () => openBindingForm(record) },
                {
                  label: '删除',
                  danger: true,
                  loading: actionLoading === `binding-delete-${record.id}`,
                  onClick: () => removeBinding(record),
                },
              ]"
            />
          </template>
        </a-table-column>
      </template>
    </a-table>
  </a-drawer>

  <a-modal
    v-model:visible="bindingFormVisible"
    :on-before-ok="saveBinding"
    :ok-loading="bindingSaving"
    :title="bindingForm.id ? '编辑绑定' : '新增绑定'"
    width="680px"
  >
    <a-form :model="bindingForm" layout="vertical">
      <a-form-item label="测试环境" required>
        <a-select
          v-model="bindingForm.environment"
          :options="enumStore.environment_type"
          :field-names="enumFieldNames"
          placeholder="请选择测试环境"
          allow-search
          value-key="key" data-testid="qa-views-data-factory-datasource-select-请选择测试环境"
        />
      </a-form-item>
      <a-form-item label="数据库配置" required>
        <a-select
          v-model="bindingForm.data_source"
          :options="dataSourceOptions"
          :field-names="{ value: 'id', label: 'display_name' }"
          :loading="databaseLoading"
          placeholder="请选择全局数据库配置"
          allow-search data-testid="qa-views-data-factory-datasource-select-请选择全局数据库配置"
        />
      </a-form-item>
      <a-form-item label="读取权限"
        ><a-switch v-model="bindingForm.allowQuery" size="small"
      /></a-form-item>
      <a-form-item label="写入权限">
        <a-switch
          v-model="bindingForm.allowWrite"
          :disabled="bindingForm.environment === 2"
          size="small"
        />
      </a-form-item>
      <DataSourceTargetFields v-model="bindingForm.target" :source-id="bindingForm.data_source"
        :source-type="dataSourceOptions.find(item => item.id === bindingForm.data_source)?.db_type ?? -1" />
      <a-form-item label="描述"><a-textarea v-model="bindingForm.description" /></a-form-item>
    </a-form>
  </a-modal>
</template>

<script lang="ts" setup>
  import DataSourceTargetFields from '@/components/forms/DataSourceTargetFields.vue'
  import {
    deleteDataFactoryDatasourceAlias,
    deleteDataFactoryDatasourceBinding,
    getDataFactoryDatasourceAlias,
    getDataFactoryDatasourceBinding,
    postDataFactoryDatasourceAlias,
    postDataFactoryDatasourceBinding,
    putDataFactoryDatasourceAlias,
    putDataFactoryDatasourceBinding,
  } from '@/api/data-factory'
  import { getSystemDataSource } from '@/api/system/data_source'
  import { usePagination, useTable } from '@/hooks/table'
  import { useEnum } from '@/store/modules/get-enum'
  import { getFormItems } from '@/utils/datacleaning'
  import { Message, Modal } from '@arco-design/web-vue'
  import { computed, onMounted, reactive, ref } from 'vue'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import TableTabs from '@/components/table/TableTabs.vue'
  import { formatProjectProductPath } from '@/utils/business-format'
  import {
    datasourceAliasColumns,
    datasourceAliasConditionItems,
    datasourceBindingColumns,
  } from './config'

  const aliasTable = useTable()
  const pagination = usePagination(doRefresh, () => aliasTable.tableLoading)
  const enumStore = useEnum()
  const enumFieldNames = { value: 'key', label: 'title' }
  const aliasVisible = ref(false)
  const bindingVisible = ref(false)
  const bindingFormVisible = ref(false)
  const aliasSaving = ref(false)
  const bindingSaving = ref(false)
  const bindingLoading = ref(false)
  const databaseLoading = ref(false)
  const actionLoading = ref('')
  const currentAlias = ref<any>(null)
  const bindingRows = ref<any[]>([])
  const dataSourceOptions = ref<any[]>([])
  const aliasForm = reactive<any>({})
  const bindingForm = reactive<any>({})
  const aliasSourceTypeOptions = computed(() =>
    (enumStore.data_source_type || []).filter((item: any) => {
      return enumStore.data_source_type_category[item.key] === aliasForm.source_category
    })
  )

  function enumTitle(options: any[] = [], value: any) {
    return options.find((it) => it.key === value)?.title || value
  }

  function displayDataSource(value: any) {
    if (!value || typeof value !== 'object') return value
    let technicalName = value.file_path || `${value.host}:${value.port}`
    if (value.db_type === 20) {
      const prefix = String(value.extra_config?.path_prefix || '').replace(/^\/+|\/+$/g, '')
      technicalName = `${value.host}:${value.port}${prefix ? `/${prefix}` : ''}`
    }
    const label = value.display_name || technicalName
    return label === technicalName ? label : `${label} · ${technicalName}`
  }

  function doRefresh() {
    aliasTable.tableLoading.value = true
    const query = getFormItems(datasourceAliasConditionItems)
    getDataFactoryDatasourceAlias({
      ...query,
      page: pagination.page,
      pageSize: pagination.pageSize,
    }).then((res) => {
      aliasTable.handleSuccess(res)
      pagination.setTotalSize((res as any).totalSize)
    })
  }

  function onResetSearch() {
    datasourceAliasConditionItems.forEach((it) => {
      it.value = it.multiple ? [] : ''
    })
    doRefresh()
  }

  function openAlias(record?: any) {
    Object.keys(aliasForm).forEach((key) => delete aliasForm[key])
    Object.assign(aliasForm, {
      id: record?.id,
      project_product: record?.project_product?.id || record?.project_product || null,
      name: record?.name || '',
      source_category: record?.source_category ?? 0,
      db_type: record?.db_type ?? 0,
      description: record?.description || '',
      status: record?.status ?? 1,
    })
    aliasVisible.value = true
  }

  function onAliasCategoryChange() {
    aliasForm.db_type = aliasSourceTypeOptions.value[0]?.key ?? null
  }

  async function saveAlias() {
    if (!aliasForm.project_product || !aliasForm.name || aliasForm.db_type == null) {
      Message.error('请先填写产品、名称和数据库类型')
      return false
    }
    const request = aliasForm.id ? putDataFactoryDatasourceAlias : postDataFactoryDatasourceAlias
    aliasSaving.value = true
    try {
      const res = await request({ ...aliasForm })
      Message.success(res.msg)
      doRefresh()
      return true
    } catch (error) {
      return false
    } finally {
      aliasSaving.value = false
    }
  }

  function removeAlias(record: any) {
    Modal.confirm({
      title: '删除逻辑源',
      content: `确认删除 ${record.name}？`,
      onBeforeOk: () => {
        actionLoading.value = `alias-delete-${record.id}`
        return deleteDataFactoryDatasourceAlias(record.id)
          .then(doRefresh)
          .finally(() => {
            actionLoading.value = ''
          })
      },
    })
  }

  function openBinding(alias: any) {
    currentAlias.value = alias
    bindingVisible.value = true
    actionLoading.value = `binding-${alias.id}`
    loadBindings().finally(() => {
      actionLoading.value = ''
    })
  }

  function loadBindings() {
    bindingLoading.value = true
    return getDataFactoryDatasourceBinding({ datasource_alias: currentAlias.value.id })
      .then((res) => {
        bindingRows.value = res.data || []
      })
      .finally(() => {
        bindingLoading.value = false
      })
  }

  function openBindingForm(record?: any) {
    Object.keys(bindingForm).forEach((key) => delete bindingForm[key])
    dataSourceOptions.value = []
    Object.assign(bindingForm, {
      id: record?.id,
      datasource_alias: currentAlias.value.id,
      environment: record?.environment ?? null,
      data_source: record?.data_source?.id || record?.database?.id || record?.database || null,
      target: { database_name: record?.database_name || '', schema_name: record?.schema_name || '', redis_db: record?.redis_db ?? null },
      allowQuery: record?.db_c_status === 1,
      allowWrite: record?.db_rud_status === 1,
      description: record?.description || '',
    })
    loadDataSourceOptions(bindingForm.data_source)
    bindingFormVisible.value = true
  }

  function loadDataSourceOptions(selectedDataSourceId?: any) {
    dataSourceOptions.value = []
    databaseLoading.value = true
    return getSystemDataSource({ page: 1, pageSize: 999 })
      .then((res) => {
        const dbType = currentAlias.value?.db_type
        const sourceCategory = currentAlias.value?.source_category
        dataSourceOptions.value = (res.data || []).filter((item: any) => {
          return (
            Number(item.source_category) === Number(sourceCategory) &&
            (dbType == null || Number(item.db_type) === Number(dbType))
          )
        })
        if (
          selectedDataSourceId &&
          !dataSourceOptions.value.some(
            (item: any) => String(item.id) === String(selectedDataSourceId)
          )
        ) {
          bindingForm.data_source = null
        }
      })
      .finally(() => {
        databaseLoading.value = false
      })
  }

  async function saveBinding() {
    if (bindingForm.environment == null || !bindingForm.data_source) {
      Message.error('请先选择测试环境和数据库配置')
      return false
    }
    if (bindingForm.environment === 2) bindingForm.allowWrite = false
    const request = bindingForm.id
      ? putDataFactoryDatasourceBinding
      : postDataFactoryDatasourceBinding
    bindingSaving.value = true
    try {
      const res = await request({
        id: bindingForm.id,
        datasource_alias: bindingForm.datasource_alias,
        environment: bindingForm.environment,
        data_source: bindingForm.data_source,
        ...bindingForm.target,
        description: bindingForm.description,
        db_c_status: bindingForm.allowQuery ? 1 : 0,
        db_rud_status: bindingForm.allowWrite ? 1 : 0,
      })
      Message.success(res.msg)
      loadBindings()
      return true
    } catch (error) {
      return false
    } finally {
      bindingSaving.value = false
    }
  }

  function removeBinding(record: any) {
    Modal.confirm({
      title: '删除绑定',
      content: '确认删除该环境绑定？',
      onBeforeOk: () => {
        actionLoading.value = `binding-delete-${record.id}`
        return deleteDataFactoryDatasourceBinding(record.id)
          .then(loadBindings)
          .finally(() => {
            actionLoading.value = ''
          })
      },
    })
  }

  onMounted(() => {
    enumStore.getEnum()
    doRefresh()
  })
</script>
<style scoped>
  .datasource-toolbar {
    margin-bottom: 12px;
  }
</style>
