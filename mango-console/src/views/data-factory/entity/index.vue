<template>
  <TableBody>
    <template #header>
      <a-card title="数据工厂 / 工厂实体" :bordered="false">
        <template #extra>
          <a-space>
            <a-button size="small" type="primary" @click="openEntity()">新增实体</a-button>
            <a-button size="small" @click="openBatchGenerate">批量生成</a-button>
          </a-space>
        </template>
      </a-card>
    </template>

    <template #default>
      <a-table
        :columns="entityTableColumns"
        :data="table.dataList"
        :loading="table.tableLoading.value"
        :pagination="false"
        :row-key="'id'"
      >
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
                <a-button :loading="actionLoading === `fields-${record.id}`" size="mini" type="text" @click="openFields(record)">字段规则</a-button>
                <a-dropdown trigger="hover">
                  <a-button size="mini" type="text">···</a-button>
                  <template #content>
                    <a-doption>
                      <a-button :loading="actionLoading === `switch-${record.id}`" size="mini" type="text" @click="switchEntity(record)">
                        {{ record.status === 1 ? '禁用' : '启用' }}
                      </a-button>
                    </a-doption>
                    <a-doption>
                      <a-button
                        :loading="actionLoading === `delete-${record.id}`"
                        size="mini"
                        status="danger"
                        type="text"
                        @click="removeEntity(record)"
                        >删除</a-button
                      >
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

  <a-drawer v-model:visible="batchVisible" title="批量生成工厂实体" width="50%">
    <a-form :model="batchForm" layout="vertical">
      <a-grid :cols="2" :col-gap="16">
        <a-grid-item>
          <a-form-item label="产品" required>
            <a-cascader
              v-model="batchForm.project_product"
              :options="projectInfo.projectProduct"
              allow-search
              allow-clear
            />
          </a-form-item>
        </a-grid-item>
        <a-grid-item>
          <a-form-item label="逻辑数据源" required>
            <a-select
              v-model="batchForm.datasource_alias"
              :field-names="{ value: 'id', label: 'name' }"
              :options="datasourceAliasOptions"
              allow-clear
              allow-search
            />
          </a-form-item>
        </a-grid-item>
      </a-grid>
      <a-space style="margin-bottom: 12px">
        <a-switch
          v-model="batchForm.sync_fields"
          checked-text="同步字段规则"
          unchecked-text="不同步字段"
        />
        <a-switch
          v-model="batchForm.skip_exists"
          checked-text="跳过已存在"
          unchecked-text="已存在报错"
        />
        <a-button :loading="batchLoading" type="primary" @click="loadBatchTables">加载表</a-button>
        <a-button :loading="batchGenerating" status="success" @click="batchGenerateEntities"
          >生成</a-button
        >
      </a-space>
    </a-form>
    <a-alert style="margin-bottom: 12px" type="info">
      当前使用顶部全局测试环境读取表结构。实体名称默认使用表注释，没有表注释时使用表名。
    </a-alert>
    <a-table
      :columns="batchEntityTableColumns"
      :data="batchRows"
      :loading="batchLoading || batchGenerating"
      :pagination="false"
      :row-key="'table_name'"
      :row-selection="batchRowSelection"
      :scroll="{ x: 900, y: 520 }"
      @selection-change="onBatchSelectionChange"
    >
      <template #columns>
        <a-table-column
          v-for="item of batchEntityTableColumns"
          :key="item.key"
          :data-index="item.key"
          :title="item.title"
          :width="item.width"
        >
          <template v-if="item.key === 'name'" #cell="{ record }">
            <a-input v-model="record.name" :disabled="record.disabled" />
          </template>
          <template v-else-if="item.key === 'status'" #cell="{ record }">
            <a-tag :color="getBatchStatusColor(record.status)">{{
              getBatchStatusText(record.status)
            }}</a-tag>
          </template>
        </a-table-column>
      </template>
    </a-table>
    <template #footer>
      <a-space>
        <a-button @click="batchVisible = false">关闭</a-button>
        <a-button :loading="batchLoading" @click="loadBatchTables">重新加载</a-button>
        <a-button :loading="batchGenerating" status="success" type="primary" @click="batchGenerateEntities">
          确认生成
        </a-button>
      </a-space>
    </template>
  </a-drawer>

  <a-modal
    v-model:visible="entityVisible"
    :on-before-ok="saveEntity"
    :ok-loading="entitySaving"
    :title="entityForm.id ? '编辑实体' : '新增实体'"
    width="760px"
  >
    <a-form :model="entityForm" layout="vertical">
      <a-grid :cols="2" :col-gap="16">
        <a-grid-item>
          <a-form-item label="产品" required>
            <a-cascader
              v-model="entityForm.project_product"
              :options="projectInfo.projectProduct"
              allow-search
              allow-clear
            />
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
        <a-grid-item
          ><a-form-item label="实体名称" required><a-input v-model="entityForm.name" /></a-form-item
        ></a-grid-item>
        <a-grid-item
          ><a-form-item label="主键字段"><a-input v-model="entityForm.primary_key" /></a-form-item
        ></a-grid-item>
        <a-grid-item
          ><a-form-item label="唯一字段"><a-input v-model="entityForm.unique_key" /></a-form-item
        ></a-grid-item>
        <a-grid-item
          ><a-form-item label="清理顺序"
            ><a-input-number v-model="entityForm.cleanup_order" style="width: 100%" /></a-form-item
        ></a-grid-item>
      </a-grid>
      <a-form-item label="同步字段规则">
        <a-switch v-model="syncFieldsAfterSave" checked-text="保存后同步" unchecked-text="不同步" />
      </a-form-item>
      <a-form-item label="描述"><a-textarea v-model="entityForm.description" /></a-form-item>
    </a-form>
  </a-modal>

  <a-modal
    v-model:visible="fieldVisible"
    :on-before-ok="saveFields"
    :ok-loading="fieldSaving"
    :title="`${currentEntity?.name || ''} 字段规则`"
    width="1180px"
  >
    <a-space style="margin-bottom: 12px">
      <a-tag color="arcoblue">当前表：{{ currentEntity?.table_name || '-' }}</a-tag>
      <a-button :loading="fieldSyncLoading" type="primary" @click="syncCurrentEntityFields">同步当前表字段</a-button>
      <a-button :loading="fieldPreviewLoading" @click="previewFieldValues">生成实际值</a-button>
      <a-switch v-model="replaceFields" checked-text="替换" unchecked-text="追加" />
    </a-space>
    <a-table
      :columns="fieldRuleColumns"
      :data="fieldRows"
      :pagination="false"
      :scroll="{ x: 1600, y: 460 }"
    >
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
            <a-select
              v-model="record.generator_type"
              :options="enumStore.data_factory_generator_type"
              :field-names="enumFieldNames"
            />
          </template>
          <template v-else-if="item.key === 'generator_config'" #cell="{ record }">
            <a-space
              v-if="record.generator_type === GENERATOR_TYPE_DEPENDENCY_FIELD"
              direction="vertical"
              fill
            >
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
              <a-tag :color="record.preview_valid ? 'green' : 'red'">{{
                formatPreviewValue(record.preview_value)
              }}</a-tag>
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
    postDataFactoryEntityBatchGenerate,
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
  import { computed, onMounted, reactive, ref } from 'vue'
  import { batchEntityTableColumns, entityTableColumns, fieldRuleColumns } from './config'

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
  const batchVisible = ref(false)
  const batchLoading = ref(false)
  const batchGenerating = ref(false)
  const fieldPreviewLoading = ref(false)
  const entitySaving = ref(false)
  const fieldSaving = ref(false)
  const fieldSyncLoading = ref(false)
  const actionLoading = ref('')
  const currentEntity = ref<any>(null)
  const fieldRows = ref<any[]>([])
  const batchRows = ref<any[]>([])
  const batchSelectedKeys = ref<any[]>([])
  const entityForm = reactive<any>({})
  const batchForm = reactive<any>({
    project_product: null,
    datasource_alias: null,
    sync_fields: true,
    skip_exists: true,
  })
  const batchRowSelection = computed(() => ({
    selectedRowKeys: batchSelectedKeys.value,
    showCheckedAll: true,
    getCheckboxProps: (record: any) => ({ disabled: record.disabled }),
  }))
  const GENERATOR_TYPE_SKIP = 0
  const GENERATOR_TYPE_FIXED = 1
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
      create_type: record?.create_type || 2,
      delete_type: record?.delete_type || 2,
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
    const projectProduct =
      record?.project_product?.id || record?.project_product || entityForm.project_product
    if (!projectProduct) {
      dependencyTemplateOptions.value = []
      entityNameMap.value = {}
      return Promise.resolve()
    }
    return Promise.all([
      getDataFactoryEntity({ project_product: projectProduct, page: 1, pageSize: 9999 }),
      getDataFactoryTemplate({ project_product: projectProduct, page: 1, pageSize: 9999 }),
    ]).then(([entityRes, templateRes]) => {
      entityNameMap.value = Object.fromEntries(
        (entityRes.data || []).map((entity: any) => [
          String(entity.id),
          entity.name || entity.table_name || entity.id,
        ])
      )
      dependencyTemplateOptions.value = (templateRes.data || []).map((it: any) => {
        const entityId = it.entity?.id || it.entity
        const entityName =
          it.entity?.name || entityNameMap.value[String(entityId)] || entityId || '未知实体'
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
    entityTableOptions.value = record?.table_name
      ? [{ label: record.table_name, value: record.table_name }]
      : []
    if (record?.datasource_alias && userStore.selected_environment != null) {
      loadEntityTables(record.datasource_alias?.id || record.datasource_alias)
    }
    entityVisible.value = true
  }

  function openBatchGenerate() {
    batchForm.project_product = entityForm.project_product || null
    batchForm.datasource_alias = null
    batchForm.sync_fields = true
    batchForm.skip_exists = true
    batchRows.value = []
    batchSelectedKeys.value = []
    batchVisible.value = true
  }

  async function saveEntity() {
    if (!entityForm.project_product) {
      Message.error('请选择产品')
      return false
    }
    if (!entityForm.datasource_alias) {
      Message.error('请选择逻辑数据源')
      return false
    }
    if (!entityForm.table_name) {
      Message.error('请选择表名')
      return false
    }
    if (!entityForm.name) {
      Message.error('请填写实体名称')
      return false
    }
    fillEntitySystemFields()
    const request = entityForm.id ? putDataFactoryEntity : postDataFactoryEntity
    entitySaving.value = true
    try {
      const res = await request({ ...entityForm })
      const entityId = res.data?.id || entityForm.id
      if (syncFieldsAfterSave.value && entityId) {
        await ensureEntityDiscoveredColumns()
        if (!entityDiscoveredColumns.value.length) {
          Message.warning('实体已保存，但没有发现可同步的字段，请进入字段规则手动同步')
          doRefresh()
          return true
        }
        await syncEntityFields(entityId)
        Message.success('实体和字段规则保存成功')
        doRefresh()
        return true
      }
      Message.success(res.msg)
      doRefresh()
      return true
    } catch (error) {
      return false
    } finally {
      entitySaving.value = false
    }
  }

  function onEntityDatasourceChange(value: any) {
    entityForm.table_name = ''
    entityForm.primary_key = 'id'
    entityForm.unique_key = ''
    entityDiscoveredColumns.value = []
    entityTableOptions.value = []
    if (value && userStore.selected_environment != null) {
      loadEntityTables(value)
    }
  }

  function loadEntityTables(datasourceAliasId: any) {
    if (!ensureSelectedEnvironment()) {
      return
    }
    const projectProduct =
      entityForm.project_product ||
      currentEntity.value?.project_product?.id ||
      currentEntity.value?.project_product
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

  function normalizeBatchTable(table: any, existsMap: Map<string, any>) {
    const name = typeof table === 'string' ? table : table.name || table.table || ''
    const comment = typeof table === 'string' ? '' : table.comment || table.table_comment || ''
    const existed = existsMap.get(name)
    return {
      table_name: name,
      table_comment: comment,
      name: existed?.name || comment || name,
      status: existed ? 'exists' : 'ready',
      message: existed ? `已存在实体：${existed.name}` : '可生成',
      disabled: Boolean(existed),
    }
  }

  function loadBatchTables() {
    if (!batchForm.project_product) {
      Message.error('请选择产品')
      return
    }
    if (!batchForm.datasource_alias) {
      Message.error('请选择逻辑数据源')
      return
    }
    if (!ensureSelectedEnvironment()) {
      return
    }
    batchLoading.value = true
    Promise.all([
      postDataFactoryDiscoverTables({
        datasource_alias_id: batchForm.datasource_alias,
        project_product: batchForm.project_product,
        test_env: userStore.selected_environment,
      }),
      getDataFactoryEntity({
        project_product: batchForm.project_product,
        datasource_alias: batchForm.datasource_alias,
        page: 1,
        pageSize: 9999,
      }),
    ])
      .then(([tableRes, entityRes]) => {
        const existsMap = new Map(
          (entityRes.data || []).map((entity: any) => [entity.table_name, entity])
        )
        batchRows.value = (tableRes.data || []).map((it: any) => normalizeBatchTable(it, existsMap))
        batchSelectedKeys.value = batchRows.value
          .filter((it) => !it.disabled)
          .map((it) => it.table_name)
        Message.success('表加载完成')
      })
      .finally(() => {
        batchLoading.value = false
      })
  }

  function onBatchSelectionChange(keys: any[]) {
    const disabledKeys = batchRows.value.filter((it) => it.disabled).map((it) => it.table_name)
    batchSelectedKeys.value = keys.filter((key) => !disabledKeys.includes(key))
  }

  function batchGenerateEntities() {
    const selectedRows = batchRows.value.filter(
      (it) => batchSelectedKeys.value.includes(it.table_name) && !it.disabled
    )
    if (!selectedRows.length) {
      Message.error('请至少选择一张可生成的表')
      return
    }
    const emptyNameRow = selectedRows.find((it) => !it.name)
    if (emptyNameRow) {
      Message.error(`表 ${emptyNameRow.table_name} 的实体名称不能为空`)
      return
    }
    batchGenerating.value = true
    postDataFactoryEntityBatchGenerate({
      project_product: batchForm.project_product,
      datasource_alias: batchForm.datasource_alias,
      test_env: userStore.selected_environment,
      sync_fields: batchForm.sync_fields,
      skip_exists: batchForm.skip_exists,
      tables: selectedRows.map((it) => ({
        table_name: it.table_name,
        name: it.name,
      })),
    })
      .then((res) => {
        const resultMap = new Map((res.data?.items || []).map((it: any) => [it.table_name, it]))
        batchRows.value = batchRows.value.map((row) => {
          const result = resultMap.get(row.table_name) as any
          if (!result) {
            return row
          }
          return {
            ...row,
            status: result.status,
            message: result.message,
            entity_id: result.entity_id,
            field_count: result.field_count,
            disabled: result.status === 'success' || result.status === 'skipped',
          }
        })
        batchSelectedKeys.value = batchRows.value
          .filter((it) => batchSelectedKeys.value.includes(it.table_name) && !it.disabled)
          .map((it) => it.table_name)
        Message.success(
          `生成完成：成功 ${res.data?.success || 0}，跳过 ${res.data?.skipped || 0}，失败 ${
            res.data?.failed || 0
          }`
        )
        batchVisible.value = false
        doRefresh()
      })
      .finally(() => {
        batchGenerating.value = false
      })
  }

  function getBatchStatusText(status: string) {
    const statusMap: Record<string, string> = {
      ready: '可生成',
      exists: '已存在',
      success: '成功',
      skipped: '跳过',
      failed: '失败',
    }
    return statusMap[status] || status || '-'
  }

  function getBatchStatusColor(status: string) {
    const colorMap: Record<string, string> = {
      ready: 'arcoblue',
      exists: 'gray',
      success: 'green',
      skipped: 'orange',
      failed: 'red',
    }
    return colorMap[status] || 'gray'
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
      const uniqueIndex = (schema.indexes || []).find(
        (item: any) => item.unique && item.column_names?.length === 1
      )
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
      const uniqueIndex = (schema.indexes || []).find(
        (item: any) => item.unique && item.column_names?.length === 1
      )
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
      onOk: () => {
        actionLoading.value = `delete-${record.id}`
        return deleteDataFactoryEntity(record.id)
          .then(() => doRefresh())
          .finally(() => {
            actionLoading.value = ''
          })
      },
    })
  }

  function switchEntity(record: any) {
    actionLoading.value = `switch-${record.id}`
    putDataFactoryEntityStatus({ id: record.id, status: record.status === 1 ? 0 : 1 })
      .then(() => doRefresh())
      .finally(() => {
        actionLoading.value = ''
      })
  }

  function openFields(record: any) {
    actionLoading.value = `fields-${record.id}`
    currentEntity.value = record
    Promise.all([
      loadDependencyTemplates(record),
      getDataFactoryField({ entity: record.id }).then((res) => {
        fieldRows.value = (res.data || []).map((it: any) => normalizeFieldRow(it))
      }),
    ])
      .then(() => {
        fieldVisible.value = true
      })
      .finally(() => {
        actionLoading.value = ''
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
    fieldSyncLoading.value = true
    postDataFactoryDiscoverTable({
      datasource_alias_id: currentEntity.value.datasource_alias,
      project_product:
        currentEntity.value.project_product?.id || currentEntity.value.project_product,
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
      Message.success('字段同步完成')
    }).finally(() => {
      fieldSyncLoading.value = false
    })
  }

  async function saveFields() {
    const fields = buildFieldPayload()
    if (!fields) {
      return false
    }
    fieldSaving.value = true
    try {
      const res = await postDataFactoryFieldBatchSave({
        entity_id: currentEntity.value.id,
        replace: replaceFields.value,
        fields,
      })
      Message.success(res.msg)
      return true
    } catch (error) {
      return false
    } finally {
      fieldSaving.value = false
    }
  }

  function buildFieldPayload() {
    return fieldRows.value.map((it) => {
      const generatorConfig = { ...(it.generator_config || {}) }
      if (!isReadonlyGeneratorConfig(it)) {
        const value = it.generator_config_value ?? ''
        if (it.generator_type === GENERATOR_TYPE_FIXED) {
          generatorConfig.value = value
        } else if (value === '') {
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
      generator_config_value: getGeneratorConfigValue({
        ...row,
        generator_config: generatorConfig,
      }),
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
    return dependencyTemplateOptions.value.filter(
      (item) => item.entity_id !== currentEntity.value?.id
    )
  }

  function refreshDependencyConfigValue(row: any) {
    row.generator_config_value = getGeneratorConfigValue(row)
    row.preview_value = undefined
    row.preview_message = ''
  }

  function isReadonlyGeneratorConfig(row: any) {
    return (
      row.generator_type === GENERATOR_TYPE_SKIP ||
      row.generator_type === GENERATOR_TYPE_DEPENDENCY_FIELD
    )
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
