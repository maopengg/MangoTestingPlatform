<template>
  <TableBody>
    <template #header>
      <a-card title="数据工厂 / 工厂实体" :bordered="false">
        <template #extra>
          <a-space>
            <a-button size="small" type="primary" @click="openEntity()">新增实体</a-button>
          </a-space>
        </template>
      </a-card>
    </template>

    <template #default>
      <a-table :columns="entityTableColumns" :data="table.dataList" :loading="table.tableLoading.value" :pagination="false" :row-key="'id'">
        <template #columns>
          <a-table-column
            v-for="item of entityTableColumns"
            :key="item.key"
            :data-index="item.key"
            :fixed="item.fixed"
            :title="item.title"
            :width="item.width"
          >
            <template v-if="item.key === 'index'" #cell="{ record }">
              {{ record.id }}
            </template>
            <template v-else-if="item.key === 'status'" #cell="{ record }">
              <a-tag :color="record.status === 1 ? 'green' : 'gray'">
                {{ record.status === 1 ? '启用' : '禁用' }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <a-space wrap>
                <a-button size="mini" type="text" @click="openEntity(record)">编辑</a-button>
                <a-button size="mini" type="text" @click="openFields(record)">字段规则</a-button>
                <a-dropdown trigger="hover">
                  <a-button size="mini" type="text">···</a-button>
                  <template #content>
                    <a-doption>
                      <a-button size="mini" type="text" @click="switchEntity(record)">
                        {{ record.status === 1 ? '禁用' : '启用' }}
                      </a-button>
                    </a-doption>
                    <a-doption>
                      <a-button size="mini" status="danger" type="text" @click="removeEntity(record)">删除</a-button>
                    </a-doption>
                  </template>
                </a-dropdown>
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

  <a-modal v-model:visible="entityVisible" :title="entityForm.id ? '编辑实体' : '新增实体'" width="760px" @ok="saveEntity">
    <a-form :model="entityForm" layout="vertical">
      <a-grid :cols="2" :col-gap="16">
        <a-grid-item>
          <a-form-item label="产品" required>
            <a-cascader v-model="entityForm.project_product" :options="projectInfo.projectProduct" allow-search allow-clear />
          </a-form-item>
        </a-grid-item>
        <a-grid-item>
          <a-form-item label="逻辑数据源" required>
            <a-select
              v-model="entityForm.datasource_alias"
              :field-names="{ value: 'id', label: 'name' }"
              :options="datasourceAliasOptions"
              allow-clear
              allow-search
              @change="onEntityDatasourceChange"
            />
          </a-form-item>
        </a-grid-item>
        <a-grid-item>
          <a-form-item label="表名" required>
            <a-select
              v-model="entityForm.table_name"
              :loading="entityTableLoading"
              :options="entityTableOptions"
              allow-clear
              allow-search
              placeholder="选择逻辑源和环境后自动读取表"
              @change="onEntityTableChange"
            />
          </a-form-item>
        </a-grid-item>
        <a-grid-item><a-form-item label="实体名称" required><a-input v-model="entityForm.name" /></a-form-item></a-grid-item>
        <a-grid-item><a-form-item label="主键字段"><a-input v-model="entityForm.primary_key" /></a-form-item></a-grid-item>
        <a-grid-item><a-form-item label="唯一字段"><a-input v-model="entityForm.unique_key" /></a-form-item></a-grid-item>
        <a-grid-item><a-form-item label="清理顺序"><a-input-number v-model="entityForm.cleanup_order" style="width: 100%" /></a-form-item></a-grid-item>
      </a-grid>
      <a-form-item label="同步字段规则">
        <a-switch v-model="syncFieldsAfterSave" checked-text="保存后同步" unchecked-text="不同步" />
      </a-form-item>
      <a-form-item label="描述"><a-textarea v-model="entityForm.description" /></a-form-item>
    </a-form>
  </a-modal>

  <a-modal v-model:visible="fieldVisible" :title="`${currentEntity?.name || ''} 字段规则`" width="1180px" @ok="saveFields">
    <a-space style="margin-bottom: 12px">
      <a-tag color="arcoblue">当前表：{{ currentEntity?.table_name || '-' }}</a-tag>
      <a-button type="primary" @click="syncCurrentEntityFields">同步当前表字段</a-button>
      <a-button :loading="fieldPreviewLoading" @click="previewFieldValues">生成实际值</a-button>
      <a-switch v-model="replaceFields" checked-text="替换" unchecked-text="追加" />
    </a-space>
    <a-table :columns="fieldRuleColumns" :data="fieldRows" :pagination="false" :scroll="{ x: 1600, y: 460 }">
      <template #columns>
        <a-table-column
          v-for="item of fieldRuleColumns"
          :key="item.key"
          :data-index="item.key"
          :fixed="item.fixed"
          :title="item.title"
          :width="item.width"
        >
          <template v-if="item.key === 'label'" #cell="{ record }">
            <a-input v-model="record.label" />
          </template>
          <template v-else-if="item.key === 'nullable'" #cell="{ record }">
            <a-tag :color="record.nullable ? 'gray' : 'orange'">
              {{ record.nullable ? '可空' : '必填' }}
            </a-tag>
          </template>
          <template v-else-if="item.key === 'primary_key'" #cell="{ record }">
            <a-tag :color="record.primary_key ? 'arcoblue' : 'gray'">
              {{ record.primary_key ? '主键' : '普通' }}
            </a-tag>
          </template>
          <template v-else-if="item.key === 'autoincrement'" #cell="{ record }">
            <a-tag :color="record.autoincrement ? 'green' : 'gray'">
              {{ record.autoincrement ? '自增' : '非自增' }}
            </a-tag>
          </template>
          <template v-else-if="item.key === 'generator_type'" #cell="{ record }">
            <a-select v-model="record.generator_type" :options="enumStore.data_factory_generator_type" :field-names="enumFieldNames" />
          </template>
          <template v-else-if="item.key === 'generator_config'" #cell="{ record }">
            <a-space v-if="record.generator_type === GENERATOR_TYPE_DEPENDENCY_FIELD" direction="vertical" fill>
              <a-select
                v-model="record.generator_config.template_id"
                :options="getDependencyTemplateOptions(record)"
                allow-clear
                allow-search
                placeholder="请选择依赖模板"
                @change="refreshDependencyConfigValue(record)"
              />
              <a-input
                v-model="record.generator_config.field"
                placeholder="取值字段，例如 id"
                @input="refreshDependencyConfigValue(record)"
              />
            </a-space>
            <a-input
              v-else
              v-model="record.generator_config_value"
              :disabled="isReadonlyGeneratorConfig(record)"
              :placeholder="getGeneratorConfigPlaceholder(record)"
            />
          </template>
          <template v-else-if="item.key === 'preview_value'" #cell="{ record }">
            <a-tooltip v-if="record.preview_message" :content="record.preview_message">
              <a-tag :color="record.preview_valid ? 'green' : 'red'">{{ formatPreviewValue(record.preview_value) }}</a-tag>
            </a-tooltip>
            <span v-else>{{ formatPreviewValue(record.preview_value) }}</span>
          </template>
          <template v-else-if="item.key === 'sort'" #cell="{ record }">
            <a-input-number v-model="record.sort" />
          </template>
        </a-table-column>
      </template>
    </a-table>
  </a-modal>
</template>

<script lang="ts" setup>
  import {
    deleteDataFactoryEntity,
    getDataFactoryDatasourceAlias,
    getDataFactoryEntity,
    getDataFactoryField,
    getDataFactoryTemplate,
    postDataFactoryDiscoverTable,
    postDataFactoryDiscoverTables,
    postDataFactoryEntity,
    postDataFactoryFieldBatchSave,
    postDataFactoryFieldPreviewValues,
    putDataFactoryEntity,
    putDataFactoryEntityStatus,
  } from '@/api/data-factory'
  import { usePagination, useTable } from '@/hooks/table'
  import { useEnum } from '@/store/modules/get-enum'
  import { useProject } from '@/store/modules/get-project'
  import useUserStore from '@/store/modules/user'
  import { Message, Modal } from '@arco-design/web-vue'
  import { onMounted, reactive, ref } from 'vue'
  import { entityTableColumns, fieldRuleColumns } from './config'

  const table = useTable()
  const pagination = usePagination(doRefresh)
  const enumStore = useEnum()
  const projectInfo = useProject()
  const userStore = useUserStore()
  const enumFieldNames = { value: 'key', label: 'title' }
  const datasourceAliasOptions = ref<any[]>([])
  const dependencyTemplateOptions = ref<any[]>([])
  const entityNameMap = ref<Record<string, string>>({})
  const entityTableOptions = ref<any[]>([])
  const entityDiscoveredColumns = ref<any[]>([])
  const entityTableLoading = ref(false)
  const syncFieldsAfterSave = ref(true)
  const replaceFields = ref(true)
  const entityVisible = ref(false)
  const fieldVisible = ref(false)
  const fieldPreviewLoading = ref(false)
  const currentEntity = ref<any>(null)
  const fieldRows = ref<any[]>([])
  const entityForm = reactive<any>({})
  const GENERATOR_TYPE_SKIP = 0
  const GENERATOR_TYPE_DEPENDENCY_FIELD = 11

  function resetEntityForm(record?: any) {
    Object.keys(entityForm).forEach((key) => delete entityForm[key])
    Object.assign(entityForm, {
      id: record?.id,
      project_product: record?.project_product?.id || record?.project_product || null,
      datasource_alias: record?.datasource_alias?.id || record?.datasource_alias || null,
      name: record?.name || '',
      description: record?.description || '',
      table_name: record?.table_name || '',
      primary_key: record?.primary_key || 'id',
      unique_key: record?.unique_key || '',
      source_mode: record?.source_mode || 1,
      create_type: record?.create_type || 2,
      delete_type: record?.delete_type || 2,
      create_config: record?.create_config || {},
      delete_config: record?.delete_config || {},
      cleanup_order: record?.cleanup_order || 100,
      status: record?.status || 1,
    })
  }

  function doRefresh() {
    table.tableLoading.value = true
    getDataFactoryEntity({ page: pagination.page, pageSize: pagination.pageSize }).then((res) => {
      table.handleSuccess(res)
      pagination.setTotalSize((res as any).totalSize)
    })
  }

  function loadOptions() {
    getDataFactoryDatasourceAlias({}).then((res) => {
      datasourceAliasOptions.value = res.data || []
    })
  }

  function loadDependencyTemplates(record?: any) {
    const projectProduct = record?.project_product?.id || record?.project_product || entityForm.project_product
    if (!projectProduct) {
      dependencyTemplateOptions.value = []
      entityNameMap.value = {}
      return
    }
    Promise.all([
      getDataFactoryEntity({ project_product: projectProduct, page: 1, pageSize: 9999 }),
      getDataFactoryTemplate({ project_product: projectProduct, page: 1, pageSize: 9999 }),
    ]).then(([entityRes, templateRes]) => {
      entityNameMap.value = Object.fromEntries(
        (entityRes.data || []).map((entity: any) => [String(entity.id), entity.name || entity.table_name || entity.id])
      )
      dependencyTemplateOptions.value = (templateRes.data || []).map((it: any) => {
        const entityId = it.entity?.id || it.entity
        const entityName = it.entity?.name || entityNameMap.value[String(entityId)] || entityId || '未知实体'
        return {
          label: `${entityName} / ${it.name}`,
          value: it.id,
          entity_id: entityId,
          table_name: it.entity?.table_name,
          template: it,
        }
      })
    })
  }

  function openEntity(record?: any) {
    resetEntityForm(record)
    syncFieldsAfterSave.value = !record?.id
    entityDiscoveredColumns.value = []
    entityTableOptions.value = record?.table_name ? [{ label: record.table_name, value: record.table_name }] : []
    if (record?.datasource_alias && userStore.selected_environment) {
      loadEntityTables(record.datasource_alias?.id || record.datasource_alias)
    }
    entityVisible.value = true
  }

  function saveEntity() {
    if (!entityForm.project_product) {
      Message.error('请选择产品')
      return
    }
    if (!entityForm.datasource_alias) {
      Message.error('请选择逻辑数据源')
      return
    }
    if (!entityForm.table_name) {
      Message.error('请选择表名')
      return
    }
    if (!entityForm.name) {
      Message.error('请填写实体名称')
      return
    }
    fillEntitySystemFields()
    const request = entityForm.id ? putDataFactoryEntity : postDataFactoryEntity
    request({ ...entityForm }).then((res) => {
      const entityId = res.data?.id || entityForm.id
      if (syncFieldsAfterSave.value && entityId) {
        return ensureEntityDiscoveredColumns().then(() => {
          if (!entityDiscoveredColumns.value.length) {
            Message.warning('实体已保存，但没有发现可同步的字段，请进入字段规则手动同步')
            entityVisible.value = false
            doRefresh()
            return
          }
          return syncEntityFields(entityId).then(() => {
            Message.success('实体和字段规则保存成功')
            entityVisible.value = false
            doRefresh()
          })
        })
      }
      Message.success(res.msg)
      entityVisible.value = false
      doRefresh()
    })
  }

  function onEntityDatasourceChange(value: any) {
    entityForm.table_name = ''
    entityForm.primary_key = 'id'
    entityForm.unique_key = ''
    entityDiscoveredColumns.value = []
    entityTableOptions.value = []
    if (value && userStore.selected_environment) {
      loadEntityTables(value)
    }
  }

  function loadEntityTables(datasourceAliasId: any) {
    if (!ensureSelectedEnvironment()) {
      return
    }
    const projectProduct = entityForm.project_product || currentEntity.value?.project_product?.id || currentEntity.value?.project_product
    if (!projectProduct) {
      Message.error('请先选择产品')
      return
    }
    entityTableLoading.value = true
    postDataFactoryDiscoverTables({
      datasource_alias_id: datasourceAliasId,
      project_product: projectProduct,
      test_env: userStore.selected_environment,
    })
      .then((res) => {
        entityTableOptions.value = (res.data || []).map(normalizeTableOption)
      })
      .finally(() => {
        entityTableLoading.value = false
      })
  }

  function normalizeTableOption(table: any) {
    if (typeof table === 'string') {
      return { label: table, value: table, comment: '' }
    }
    const name = table.name || table.table || ''
    const comment = table.comment || table.table_comment || ''
    return {
      label: comment ? `${name} / ${comment}` : name,
      value: name,
      comment,
    }
  }

  function onEntityTableChange(tableName: string) {
    entityDiscoveredColumns.value = []
    if (!entityForm.datasource_alias || !tableName || !ensureSelectedEnvironment()) {
      return
    }
    postDataFactoryDiscoverTable({
      datasource_alias_id: entityForm.datasource_alias,
      project_product: entityForm.project_product,
      test_env: userStore.selected_environment,
      table_name: tableName,
    }).then((res) => {
      const schema = res.data || {}
      entityDiscoveredColumns.value = schema.columns || []
      entityForm.primary_key = schema.primary_keys?.[0] || entityForm.primary_key || 'id'
      const uniqueIndex = (schema.indexes || []).find((item: any) => item.unique && item.column_names?.length === 1)
      entityForm.unique_key = uniqueIndex?.column_names?.[0] || entityForm.unique_key || ''
      applyEntityNameSuggestion(tableName, schema.table_comment)
    })
  }

  function applyEntityNameSuggestion(tableName: string, tableComment?: string) {
    const selectedTable = entityTableOptions.value.find((item: any) => item.value === tableName)
    const suggestedName = tableComment || selectedTable?.comment || tableName
    if (!entityForm.id || !entityForm.name || entityForm.name === entityForm.table_name) {
      entityForm.name = suggestedName
    }
  }

  function fillEntitySystemFields() {
    // 保留方法入口，后续如有表级默认值可集中补齐。
  }

  function ensureEntityDiscoveredColumns() {
    if (entityDiscoveredColumns.value.length) {
      return Promise.resolve()
    }
    if (!entityForm.datasource_alias || !entityForm.table_name) {
      return Promise.resolve()
    }
    if (!ensureSelectedEnvironment()) {
      return Promise.resolve()
    }
    return postDataFactoryDiscoverTable({
      datasource_alias_id: entityForm.datasource_alias,
      project_product: entityForm.project_product,
      test_env: userStore.selected_environment,
      table_name: entityForm.table_name,
    }).then((res) => {
      const schema = res.data || {}
      entityDiscoveredColumns.value = schema.columns || []
      entityForm.primary_key = schema.primary_keys?.[0] || entityForm.primary_key || 'id'
      const uniqueIndex = (schema.indexes || []).find((item: any) => item.unique && item.column_names?.length === 1)
      entityForm.unique_key = uniqueIndex?.column_names?.[0] || entityForm.unique_key || ''
    })
  }

  function syncEntityFields(entityId: any) {
    const fields = entityDiscoveredColumns.value.map((it: any, index: number) => ({
      ...it,
      entity: entityId,
      generator_type: it.generator_type ?? it.recommend?.generator_type ?? 1,
      generator_config: it.generator_config || it.recommend?.generator_config || {},
      sort: index,
    }))
    return postDataFactoryFieldBatchSave({ entity_id: entityId, replace: true, fields })
  }

  function removeEntity(record: any) {
    Modal.confirm({
      title: '删除实体',
      content: `确认删除 ${record.name}？`,
      onOk: () => deleteDataFactoryEntity(record.id).then(() => doRefresh()),
    })
  }

  function switchEntity(record: any) {
    putDataFactoryEntityStatus({ id: record.id, status: record.status === 1 ? 0 : 1 }).then(() => doRefresh())
  }

  function openFields(record: any) {
    currentEntity.value = record
    fieldVisible.value = true
    loadDependencyTemplates(record)
    getDataFactoryField({ entity: record.id }).then((res) => {
      fieldRows.value = (res.data || []).map((it: any) => normalizeFieldRow(it))
    })
  }

  function syncCurrentEntityFields() {
    if (!currentEntity.value?.table_name) {
      Message.error('当前实体未绑定表名，请先编辑实体选择表')
      return
    }
    if (!currentEntity.value?.datasource_alias || !ensureSelectedEnvironment()) {
      Message.error('请先选择逻辑数据源和顶部测试环境')
      return
    }
    postDataFactoryDiscoverTable({
      datasource_alias_id: currentEntity.value.datasource_alias,
      project_product: currentEntity.value.project_product?.id || currentEntity.value.project_product,
      test_env: userStore.selected_environment,
      table_name: currentEntity.value.table_name,
    }).then((res) => {
      fieldRows.value = (res.data.columns || []).map((it: any, index: number) => ({
        ...normalizeFieldRow({
          ...it,
          entity: currentEntity.value.id,
          generator_type: it.generator_type ?? it.recommend?.generator_type ?? 1,
          generator_config: it.generator_config || it.recommend?.generator_config || {},
          sort: index,
        }),
      }))
    })
  }

  function saveFields() {
    const fields = buildFieldPayload()
    if (!fields) {
      return
    }
    postDataFactoryFieldBatchSave({ entity_id: currentEntity.value.id, replace: replaceFields.value, fields }).then((res) => {
      Message.success(res.msg)
      fieldVisible.value = false
    })
  }

  function buildFieldPayload() {
    return fieldRows.value.map((it) => {
      const generatorConfig = { ...(it.generator_config || {}) }
      if (!isReadonlyGeneratorConfig(it)) {
        const value = it.generator_config_value ?? ''
        if (value === '') {
          delete generatorConfig.value
        } else {
          generatorConfig.value = value
        }
      }
      return {
        ...it,
        generator_config: generatorConfig,
      }
    })
  }

  function previewFieldValues() {
    const fields = buildFieldPayload()
    if (!fields) {
      return
    }
    fieldPreviewLoading.value = true
    postDataFactoryFieldPreviewValues({ fields })
      .then((res) => {
        const previewMap = new Map((res.data?.fields || []).map((it: any) => [it.name, it]))
        fieldRows.value = fieldRows.value.map((row) => {
          const preview = previewMap.get(row.name) as any
          return {
            ...row,
            preview_value: preview?.value,
            preview_valid: preview?.valid ?? true,
            preview_message: preview?.message || '',
          }
        })
        Message.success('实际值生成完成')
      })
      .finally(() => {
        fieldPreviewLoading.value = false
      })
  }

  function formatPreviewValue(value: any) {
    if (value === undefined) {
      return 'null'
    }
    if (value === null) {
      return 'null'
    }
    if (typeof value === 'object') {
      return JSON.stringify(value)
    }
    return String(value)
  }

  function normalizeFieldRow(row: any) {
    const generatorConfig = row.generator_config || row.recommend?.generator_config || {}
    if (row.generator_type === GENERATOR_TYPE_DEPENDENCY_FIELD && !generatorConfig.field) {
      generatorConfig.field = 'id'
    }
    return {
      ...row,
      generator_config: generatorConfig,
      generator_config_value: getGeneratorConfigValue({ ...row, generator_config: generatorConfig }),
      preview_value: undefined,
      preview_valid: true,
      preview_message: '',
    }
  }

  function getGeneratorConfigValue(row: any) {
    const config = row.generator_config || {}
    if (config.value !== undefined && config.value !== null) {
      return String(config.value)
    }
    if (row.generator_type === GENERATOR_TYPE_SKIP) {
      return config.reason || '数据库生成'
    }
    if (row.generator_type === GENERATOR_TYPE_DEPENDENCY_FIELD) {
      const targetField = config.field || 'id'
      if (config.alias) {
        return `${config.alias}.${targetField}`
      }
      if (config.template_id) {
        return `template:${config.template_id}.${targetField}`
      }
      return `请选择依赖模板.${targetField}`
    }
    return ''
  }

  function getDependencyTemplateOptions(row: any) {
    return dependencyTemplateOptions.value.filter((item) => item.entity_id !== currentEntity.value?.id)
  }

  function refreshDependencyConfigValue(row: any) {
    row.generator_config_value = getGeneratorConfigValue(row)
    row.preview_value = undefined
    row.preview_message = ''
  }

  function isReadonlyGeneratorConfig(row: any) {
    return row.generator_type === GENERATOR_TYPE_SKIP || row.generator_type === GENERATOR_TYPE_DEPENDENCY_FIELD
  }

  function getGeneratorConfigPlaceholder(row: any) {
    if (row.generator_type === GENERATOR_TYPE_SKIP) {
      return '数据库生成'
    }
    if (row.generator_type === GENERATOR_TYPE_DEPENDENCY_FIELD) {
      return '请选择依赖模板.id'
    }
    return '填写 value，例如 ${{character_email()}}'
  }

  function ensureSelectedEnvironment() {
    if (userStore.selected_environment == null) {
      Message.error('请先在顶部选择测试环境')
      return false
    }
    return true
  }

  onMounted(() => {
    enumStore.getEnum()
    projectInfo.projectProductName()
    loadOptions()
    doRefresh()
  })
</script>
