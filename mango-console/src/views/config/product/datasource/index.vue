<template>
  <TableBody ref="tableBody" class="mango-detail-workbench-page">
    <template #header>
      <div class="mango-detail-toolbar">
        <div class="mango-detail-heading">
          <div class="mango-detail-title">{{ datasourceDetailTitle }}</div>
          <div class="mango-detail-subtitle">维护产品级逻辑数据库，并按环境绑定全局数据库配置</div>
        </div>
        <a-space v-if="!embedded" class="mango-detail-actions" wrap>
          <a-button
            class="mango-back-button"
            size="small"
            @click="doResetSearch"
            data-testid="qa-views-config-product-datasource-button-返回"
            >返回</a-button
          >
        </a-space>
      </div>
    </template>

    <template #default>
      <div class="mango-datasource-workbench-scroll">
        <div class="mango-datasource-workbench">
          <section class="mango-section-card mango-datasource-master">
            <div class="mango-section-title">
              <div class="mango-section-title__main">
                <h2>逻辑数据库</h2>
                <p>选择数据库后，在右侧维护对应的环境绑定关系</p>
              </div>
              <a-button v-permission="'config.product:create'"
                size="small"
                type="primary"
                @click="onAdd"
                data-testid="qa-views-config-product-datasource-button-新增"
                >新增</a-button
              >
            </div>

            <a-spin class="mango-datasource-card-loading mango-native-scrollbar" :loading="table.tableLoading.value">
              <div v-if="table.dataList.length" class="mango-datasource-card-list">
                <article
                  v-for="record in table.dataList"
                  :key="record.id"
                  class="mango-datasource-card"
                  :class="{
                    'mango-datasource-card--active':
                      String(record.id) === String(bindingPanel.datasourceId),
                  }"
                  :aria-selected="String(record.id) === String(bindingPanel.datasourceId)"
                  role="button"
                  tabindex="0"
                  @click="onSelectDatasource(record)"
                  @keydown.enter="onSelectDatasource(record)"
                  @keydown.space.prevent="onSelectDatasource(record)"
                >
                  <div class="mango-datasource-card__header">
                    <div class="mango-datasource-card__identity">
                      <span class="mango-datasource-card__name" :title="record.name">{{
                        record.name
                      }}</span>
                      <span class="mango-datasource-card__id mango-muted-text"
                        >ID {{ record.id }}</span
                      >
                    </div>
                    <span
                      :title="record.status === 1 ? '点击停用' : '点击启用'"
                      @click.stop
                      @keydown.stop
                    >
                      <a-switch v-permission="'config.product:status'"
                        :before-change="(checked) => onStatusChange(record, checked)"
                        :model-value="record.status === 1"
                      />
                    </span>
                  </div>
                  <div class="mango-datasource-card__tags">
                    <a-tag :color="enumStore.colors[record.source_category]" size="small">
                      {{ getDataSourceCategoryName(record.source_category) }}
                    </a-tag>
                    <a-tag :color="enumStore.colors[record.db_type]" size="small">
                      {{ getDatabaseTypeName(record.db_type) }}
                    </a-tag>
                  </div>
                  <p
                    v-if="record.description"
                    class="mango-datasource-card__description"
                    :title="record.description"
                  >
                    {{ record.description }}
                  </p>
                  <div class="mango-datasource-card__footer" @click.stop>
                    <MangoTableActions
                      :max-inline="3"
                      :actions="[
                        { permission: 'config.product:edit', label: '编辑', onClick: () => onUpdate(record) },
                        { permission: 'config.product:delete', label: '删除', danger: true, onClick: () => onDelete(record) },
                      ]"
                    />
                  </div>
                </article>
              </div>
              <a-empty v-else description="暂无逻辑数据库" />
            </a-spin>
          </section>

          <section class="mango-section-card mango-datasource-detail">
            <div class="mango-section-title mango-binding-title">
              <div class="mango-section-title__main">
                <h2>数据库绑定关系</h2>
                <p v-if="bindingPanel.datasourceId">
                  当前逻辑数据库：{{ bindingPanel.datasourceName }}，按测试环境绑定全局数据库配置
                </p>
                <p v-else>请先选择左侧逻辑数据库</p>
              </div>
              <a-space>
                <a-button v-permission="'config.product:query'"
                  size="small"
                  :disabled="!selectedDatasource"
                  @click="onOpenQueryDrawer(selectedDatasource)"
                >查询</a-button>
                <a-button v-permission="'config.product:create'"
                  size="small"
                  type="primary"
                  :disabled="!bindingPanel.datasourceId"
                  @click="onAddBinding"
                  data-testid="qa-views-config-product-datasource-button-新增绑定"
                >
                  新增绑定
                </a-button>
              </a-space>
            </div>

            <a-tabs v-model:active-key="detailTab" class="mango-datasource-detail-tabs">
              <a-tab-pane key="bindings" title="环境绑定">
                <div v-if="bindingPanel.datasourceId" class="mango-binding-table">
                  <a-table
                    :bordered="false"
                    :columns="bindingColumns"
                    :data="bindingPanel.bindings"
                    :loading="bindingPanel.loading"
                    :pagination="false"
                    :scroll="{ x: 1230 }"
                    row-key="id"
                    size="small"
                  >
                    <template #columns>
                      <a-table-column
                        v-for="item of bindingColumns"
                        :key="item.key"
                        :align="item.align"
                        :data-index="item.key"
                        :ellipsis="item.ellipsis"
                        :fixed="item.fixed"
                        :title="item.title"
                        :tooltip="item.tooltip"
                        :width="item.width"
                      >
                        <template v-if="item.key === 'environment'" #cell="{ record }">
                          <a-tag :color="enumStore.colors[record.environment]" size="small">
                            {{ getEnvironmentName(record) }}
                          </a-tag>
                        </template>
                        <template v-else-if="item.key === 'database_alias'" #cell="{ record }">
                          {{ bindingDataSource(record)?.display_name || '-' }}
                        </template>
                        <template v-else-if="item.key === 'data_source'" #cell="{ record }">
                          {{ dataSourceConnectionSummary(bindingDataSource(record)) }}
                        </template>
                        <template v-else-if="item.key === 'host'" #cell="{ record }">
                          {{ bindingDataSource(record)?.host || '-' }}
                        </template>
                        <template v-else-if="item.key === 'database_name'" #cell="{ record }">
                          {{ record.database_name || (record.redis_db != null ? `DB ${record.redis_db}` : '未选默认库') }}{{ record.schema_name ? ` / ${record.schema_name}` : '' }}
                        </template>
                        <template v-else-if="item.key === 'db_c_status'" #cell="{ record }">
                          <a-switch v-permission="'config.product:status'"
                            :before-change="
                              (checked) => onBindingPermissionChange(record, 'db_c_status', checked)
                            "
                            :model-value="record.db_c_status === 1"
                          />
                        </template>
                        <template v-else-if="item.key === 'db_rud_status'" #cell="{ record }">
                          <a-switch v-permission="'config.product:status'"
                            :before-change="
                              (checked) =>
                                onBindingPermissionChange(record, 'db_rud_status', checked)
                            "
                            :disabled="record.environment === 2 && record.db_rud_status !== 1"
                            :model-value="record.db_rud_status === 1"
                            :title="record.environment === 2 ? '生产环境禁止开启写入权限' : ''"
                          />
                        </template>
                        <template v-else-if="item.key === 'actions'" #cell="{ record }">
                          <MangoTableActions
                            :actions="[
                              { permission: 'config.product:edit',
                                label: '编辑',
                                onClick: () => onEditBinding(record),
                              },
                              { permission: 'config.product:delete',
                                label: '解绑',
                                danger: true,
                                onClick: () => onUnbindDatasource(record),
                              },
                            ]"
                          />
                        </template>
                      </a-table-column>
                    </template>
                  </a-table>
                </div>
                <a-empty v-else class="mango-binding-empty" description="请选择一个逻辑数据库" />
              </a-tab-pane>
              <a-tab-pane v-if="supportsDatasourceTables" key="tables" title="数据表">
                <ProductDataSourceTables
                  v-if="bindingPanel.datasourceId"
                  :alias-id="bindingPanel.datasourceId"
                  :product-id="String(productId || '')"
                  :bindings="bindingPanel.bindings"
                />
              </a-tab-pane>
            </a-tabs>
          </section>
        </div>
      </div>
    </template>
  </TableBody>

  <ModalDialog ref="modalDialogRef" :title="data.actionTitle" @confirm="onDataForm">
    <template #content>
      <a-form :model="aliasForm">
        <a-form-item class="mango-form-item__require" label="名称">
          <a-input
            v-model="aliasForm.name"
            placeholder="请输入逻辑数据库名称"
            data-testid="qa-views-config-product-datasource-input-请输入逻辑数据库名称"
          />
        </a-form-item>
        <a-form-item class="mango-form-item__require" label="数据库分类">
          <a-select
            v-model="aliasForm.sourceCategory"
            :field-names="fieldNames"
            :options="enumStore.data_source_category"
            placeholder="请选择数据库分类"
            value-key="key"
            @change="onAliasCategoryChange"
            data-testid="qa-views-config-product-datasource-select-请选择数据库分类"
          />
        </a-form-item>
        <a-form-item class="mango-form-item__require" label="数据库类型">
          <a-select
            v-model="aliasForm.dbType"
            :field-names="fieldNames"
            :options="aliasSourceTypeOptions"
            placeholder="请选择数据库类型"
            allow-clear
            allow-search
            value-key="key"
            data-testid="qa-views-config-product-datasource-select-请选择数据库类型"
          />
        </a-form-item>
        <a-form-item label="描述">
          <a-textarea
            v-model="aliasForm.description"
            :auto-size="{ minRows: 3, maxRows: 5 }"
            :max-length="50"
            placeholder="请输入描述"
            show-word-limit
            data-testid="qa-views-config-product-datasource-textarea-请输入描述"
          />
        </a-form-item>
      </a-form>
    </template>
  </ModalDialog>

  <a-drawer v-model:visible="queryDrawer.visible" :width="'50%'" :footer="false" unmount-on-close>
    <template #title> {{ queryDrawerTitle }} / {{ queryDrawer.datasourceName || '-' }} </template>
    <div class="mango-sql-query-drawer">
      <div class="mango-sql-query-editor">
        <div v-if="queryDrawer.sourceType === 20" class="mango-sql-query-meta">
          <span class="mango-sql-query-label">索引名称</span>
          <a-input
            v-model="queryDrawer.index"
            allow-clear
            placeholder="请输入索引名称，例如：order-*"
            data-testid="qa-views-config-product-datasource-input-请输入索引名称-例如-order"
          />
        </div>
        <div class="mango-datasource-query-field">
          <span class="mango-sql-query-label">{{ queryStatementLabel }}</span>
          <a-textarea
            v-model="queryDrawer.statement"
            :auto-size="{ minRows: 6, maxRows: 12 }"
            :placeholder="queryStatementPlaceholder"
          />
        </div>
        <div class="mango-sql-query-meta">
          <span class="mango-sql-query-label">测试环境</span>
          <a-select
            v-model="queryDrawer.testEnv"
            :field-names="fieldNames"
            :options="enumStore.environment_type"
            allow-clear
            allow-search
            placeholder="请选择测试环境"
            value-key="key"
            data-testid="qa-views-config-product-datasource-select-请选择测试环境"
          />
        </div>
        <div class="mango-sql-query-actions">
          <a-button
            size="small"
            @click="resetQueryInput"
            data-testid="qa-views-config-product-datasource-button-清空"
            >清空</a-button
          >
          <a-button v-permission="'config.product:query'"
            size="small"
            type="primary"
            :loading="queryDrawer.loading"
            @click="onQueryDatasource"
            data-testid="qa-views-config-product-datasource-button-查询"
          >
            查询
          </a-button>
        </div>
      </div>
      <div class="mango-sql-query-result">
        <div class="mango-sql-query-summary">
          <span>查询结果</span>
          <span class="mango-muted-text">结构化 JSON</span>
        </div>
        <a-spin class="mango-datasource-query-loading" :loading="queryDrawer.loading">
          <JsonDisplay
            v-if="queryDrawer.result !== null"
            :data="queryDrawer.result"
            :default-expanded="false"
            :show-drawer-button="false"
          />
          <a-empty v-else description="执行查询后将在这里展示结果" />
        </a-spin>
      </div>
    </div>
  </a-drawer>

  <ModalDialog
    ref="bindingEditorDialogRef"
    :title="bindingEditorTitle"
    width="560px"
    @confirm="onSaveBinding"
  >
    <template #content>
      <a-form :model="bindingEditor" class="mango-binding-editor-form">
        <a-form-item class="mango-form-item__require" label="测试环境">
          <a-select
            v-model="bindingEditor.environment"
            :field-names="fieldNames"
            :options="bindingEnvironmentOptions"
            :disabled="bindingEditor.isEdit"
            placeholder="请选择测试环境"
            value-key="key"
            data-testid="qa-views-config-product-datasource-select-请选择测试环境-2"
          />
        </a-form-item>
        <a-form-item class="mango-form-item__require" label="数据库配置">
          <a-select
            v-model="bindingEditor.dataSource"
            :options="dataSourceOptions"
            :loading="bindingEditor.optionsLoading"
            allow-search
            placeholder="请选择全局数据库配置"
            data-testid="qa-views-config-product-datasource-select-请选择全局数据库配置"
          />
        </a-form-item>
        <DataSourceTargetFields v-model="bindingEditor.target" :source-id="bindingEditor.dataSource"
          :source-type="dataSourceOptions.find(item => item.value === bindingEditor.dataSource)?.db_type ?? -1" />
        <a-form-item label="读取权限">
          <a-switch v-model="bindingEditor.allowQuery" />
        </a-form-item>
        <a-form-item label="写入权限">
          <a-switch
            v-model="bindingEditor.allowWrite"
            :disabled="bindingEditor.environment === 2"
          />
          <span v-if="bindingEditor.environment === 2" class="mango-muted-text">
            生产环境禁止开启写入权限
          </span>
        </a-form-item>
      </a-form>
    </template>
  </ModalDialog>
</template>

<script lang="ts" setup>
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
  import { postDataSourceExecution, queryLogicalDataSource } from '@/api/data-source-execution'
  import JsonDisplay from '@/components/display/JsonDisplay.vue'
  import { getSystemDataSource } from '@/api/system/data_source'
  import { useTable } from '@/hooks/table'
  import { fieldNames } from '@/setting'
  import { useEnum } from '@/store/modules/get-enum'
  import useUserStore from '@/store/modules/user'
  import { ModalDialogType } from '@/types/components'
  import { Message, Modal } from '@arco-design/web-vue'
  import { computed, onMounted, reactive, ref, watch } from 'vue'
  import { useRoute } from 'vue-router'
  import ProductDataSourceTables from './components/ProductDataSourceTables.vue'
  import DataSourceTargetFields from '@/components/forms/DataSourceTargetFields.vue'
  import { sortLogicalDatasources } from './config'

  const route = useRoute()
  const props = defineProps<{
    embedded?: boolean
    projectProductId?: string | number
    projectProductName?: string
    datasourceId?: string | number
  }>()
  const productId = computed(() => props.projectProductId ?? route.query.id)
  const productName = computed(() => props.projectProductName ?? route.query.name)
  const enumStore = useEnum()
  const userStore = useUserStore()
  const table = useTable()
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const bindingEditorDialogRef = ref<any>(null)
  const data = reactive({
    actionTitle: '新增',
    isAdd: true,
    updateId: 0,
  })
  const aliasForm = reactive({
    name: '',
    sourceCategory: 0,
    dbType: 0 as number | null,
    description: '',
    status: 1,
  })
  const queryDrawer = reactive({
    visible: false,
    loading: false,
    datasourceId: String(props.datasourceId || ''),
    datasourceName: '',
    sourceType: 0,
    testEnv: null as number | null,
    index: '',
    statement: '',
    result: null as any,
  })
  const bindingPanel = reactive({
    loading: false,
    datasourceId: '',
    datasourceName: '',
    bindings: [] as any[],
  })
  let bindingLoadVersion = 0
  const detailTab = ref('bindings')
  const selectedDatasource = ref<any>(null)
  const supportsDatasourceTables = computed(() => {
    const datasource = selectedDatasource.value
    if (datasource?.db_type == null) return false
    return [0, 1, 2, 3, 4, 20].includes(Number(datasource.db_type))
  })
  watch(supportsDatasourceTables, (supported) => {
    if (!supported) detailTab.value = 'bindings'
  }, { flush: 'sync' })
  const bindingEditor = reactive({
    isEdit: false,
    bindingId: null as number | null,
    optionsLoading: false,
    environment: null as number | null,
    dataSource: null as number | null,
    allowQuery: true,
    allowWrite: false,
    target: { database_name: '', schema_name: '', redis_db: null as number | null },
  })
  const dataSourceOptions = ref<any[]>([])
  const aliasCategory = computed(() => Number(aliasForm.sourceCategory))
  const aliasSourceTypeOptions = computed(() =>
    (enumStore.data_source_type || []).filter((item: any) => {
      return enumStore.data_source_type_category[item.key] === aliasCategory.value
    })
  )
  const bindingEditorTitle = computed(() =>
    bindingEditor.isEdit ? '编辑环境数据库绑定' : '绑定环境数据库'
  )
  const bindingEnvironmentOptions = computed(() => {
    const boundEnvironments = new Set(
      bindingPanel.bindings
        .map((item: any) => item.environment)
        .filter((value: any) => value !== null && value !== undefined)
        .map((value: any) => Number(value))
    )
    return (enumStore.environment_type || []).map((item: any) => {
      const disabled = !bindingEditor.isEdit && boundEnvironments.has(Number(item.key))
      return {
        ...item,
        disabled,
        title: disabled ? `${item.title}（已绑定）` : item.title,
      }
    })
  })

  const datasourceDetailTitle = computed(() => {
    const id = productId.value || '-'
    const name = productName.value || '-'
    return `产品逻辑数据库 / ${id} / ${name}`
  })
  const queryDrawerTitle = computed(() => {
    if (queryDrawer.sourceType === 10) return 'Redis查询'
    if (queryDrawer.sourceType === 20) return 'Elasticsearch查询'
    return 'SQL查询'
  })
  const queryStatementLabel = computed(() => {
    if (queryDrawer.sourceType === 10) return '查询命令'
    if (queryDrawer.sourceType === 20) return 'Query DSL'
    return '查询SQL'
  })
  const queryStatementPlaceholder = computed(() => {
    if (queryDrawer.sourceType === 10) return '请输入只读命令，例如：GET user:1 或 HGETALL user:1'
    if (queryDrawer.sourceType === 20) return '请输入 Elasticsearch Query DSL JSON'
    return '请输入查询SQL，例如：SELECT * FROM table_name LIMIT 20'
  })
  const bindingColumns = [
    {
      title: '测试环境',
      key: 'environment',
      dataIndex: 'environment',
      width: 160,
      ellipsis: true,
      tooltip: true,
      align: 'center',
    },
    {
      title: '数据库别名',
      key: 'database_alias',
      dataIndex: 'database_alias',
      width: 160,
      ellipsis: true,
      tooltip: true,
      align: 'left',
    },
    {
      title: '数据库配置',
      key: 'data_source',
      dataIndex: 'data_source',
      width: 180,
      ellipsis: true,
      tooltip: true,
      align: 'left',
    },
    {
      title: '域名',
      key: 'host',
      dataIndex: 'host',
      width: 220,
      ellipsis: true,
      tooltip: true,
      align: 'left',
    },
    {
      title: '主库',
      key: 'database_name',
      dataIndex: 'database_name',
      width: 180,
      ellipsis: true,
      tooltip: true,
      align: 'left',
    },
    {
      title: '读取权限',
      key: 'db_c_status',
      dataIndex: 'db_c_status',
      width: 100,
      align: 'center',
    },
    {
      title: '写入权限',
      key: 'db_rud_status',
      dataIndex: 'db_rud_status',
      width: 110,
      align: 'center',
    },
    {
      title: '操作',
      key: 'actions',
      dataIndex: 'actions',
      fixed: 'right',
      width: 120,
      align: 'center',
    },
  ]

  function getDatabaseTypeName(value: number) {
    return enumStore.data_source_type?.find((item) => item.key === value)?.title || value
  }

  function getDataSourceCategoryName(value: number) {
    return enumStore.data_source_category?.find((item) => item.key === value)?.title || value
  }

  function onAliasCategoryChange() {
    aliasForm.dbType = aliasSourceTypeOptions.value[0]?.key ?? null
  }

  function getEnvironmentName(record: any) {
    return (
      enumStore.environment_type?.find((item: any) => item.key === record.environment)?.title ||
      `环境${record.environment}`
    )
  }

  function bindingDataSource(record: any) {
    return record.data_source || record.database || null
  }

  function dataSourceDisplayLabel(dataSource: any) {
    return dataSource?.display_name || dataSourceTechnicalName(dataSource)
  }

  function dataSourceTechnicalName(dataSource: any) {
    if (!dataSource) return '-'
    if (dataSource.db_type === 2) return dataSource.file_path || '-'
    if (dataSource.db_type === 10) {
      return `${dataSource.host}:${dataSource.port}`
    }
    if (dataSource.db_type === 20) {
      const prefix = String(dataSource.extra_config?.path_prefix || '').replace(/^\/+|\/+$/g, '')
      return `${dataSource.host}:${dataSource.port}${prefix ? `/${prefix}` : ''}`
    }
    return `${dataSource.host}:${dataSource.port}`
  }

  function dataSourceConnectionSummary(dataSource: any) {
    if (!dataSource) return '-'
    return `${dataSourceTechnicalName(dataSource)} · ${getDatabaseTypeName(dataSource.db_type)}`
  }

  function dataSourceOptionLabel(dataSource: any) {
    return [
      dataSourceDisplayLabel(dataSource),
      dataSourceTechnicalName(dataSource) !== dataSourceDisplayLabel(dataSource)
        ? dataSourceTechnicalName(dataSource)
        : null,
      `${dataSource.host}:${dataSource.port}`,
    ]
      .filter(Boolean)
      .join(' · ')
  }

  function doResetSearch() {
    window.history.back()
  }

  function doRefresh() {
    table.tableLoading.value = true
    getDataFactoryDatasourceAlias({
      project_product: productId.value,
    })
      .then((res) => {
        const sortedRows = sortLogicalDatasources(res.data || [])
        table.dataList.splice(0, table.dataList.length, ...sortedRows)
        const selectedRecord =
          table.dataList.find((record: any) => {
            return String(record.id) === String(bindingPanel.datasourceId)
          }) || table.dataList[0]
        if (selectedRecord) {
          onSelectDatasource(selectedRecord, true)
        } else {
          bindingLoadVersion += 1
          bindingPanel.datasourceId = ''
          selectedDatasource.value = null
          bindingPanel.datasourceName = ''
          bindingPanel.bindings = []
          bindingPanel.loading = false
        }
      })
      .finally(() => {
        table.tableLoading.value = false
      })
  }

  function onAdd() {
    data.actionTitle = '新增'
    data.isAdd = true
    aliasForm.name = ''
    aliasForm.sourceCategory = 0
    aliasForm.dbType = 0
    aliasForm.description = ''
    aliasForm.status = 1
    modalDialogRef.value?.show()
  }

  function onUpdate(record: any) {
    data.actionTitle = '编辑'
    data.isAdd = false
    data.updateId = record.id
    aliasForm.name = record.name || ''
    aliasForm.sourceCategory = Number(record.source_category ?? 0)
    aliasForm.dbType = Number(record.db_type ?? 0)
    aliasForm.description = record.description || ''
    aliasForm.status = Number(record.status ?? 1)
    modalDialogRef.value?.show()
  }

  function onDelete(record: any) {
    Modal.confirm({
      title: '删除产品逻辑源',
      content: `确认删除 ${record.name}？删除后会影响引用它的数据实体、API SQL 和 UI SQL 配置。`,
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

  async function onStatusChange(record: any, checked: boolean) {
    try {
      const res = await putDataFactoryDatasourceAlias({
        id: record.id,
        project_product: record.project_product?.id || record.project_product || productId.value,
        name: record.name,
        source_category: record.source_category,
        db_type: record.db_type,
        description: record.description || null,
        status: checked ? 1 : 0,
      })
      record.status = checked ? 1 : 0
      Message.success(res.msg)
      return true
    } catch {
      return false
    }
  }

  function onOpenQueryDrawer(record: any) {
    queryDrawer.visible = true
    queryDrawer.datasourceId = record.id
    queryDrawer.datasourceName = record.name
    queryDrawer.sourceType = Number(record.db_type)
    queryDrawer.testEnv = userStore.selected_environment ?? null
    queryDrawer.index = ''
    queryDrawer.statement =
      queryDrawer.sourceType === 20
        ? '{\n  "query": {\n    "match_all": {}\n  },\n  "size": 20\n}'
        : ''
    queryDrawer.result = null
  }

  function resetQueryInput() {
    queryDrawer.index = ''
    queryDrawer.statement = ''
    queryDrawer.result = null
  }

  function onSelectDatasource(record: any, force = false) {
    if (!force && String(record.id) === String(bindingPanel.datasourceId)) return
    selectedDatasource.value = record
    bindingPanel.datasourceId = record.id
    bindingPanel.datasourceName = record.name
    bindingPanel.bindings = []
    loadDatasourceBindings()
  }

  function loadDatasourceBindings() {
    if (!bindingPanel.datasourceId) {
      return
    }
    const datasourceId = bindingPanel.datasourceId
    const loadVersion = ++bindingLoadVersion
    bindingPanel.loading = true
    getDataFactoryDatasourceBinding({
      datasource_alias: datasourceId,
      page: 1,
      pageSize: 999,
    })
      .then((res) => {
        if (loadVersion !== bindingLoadVersion) return
        bindingPanel.bindings = res.data || []
      })
      .finally(() => {
        if (loadVersion !== bindingLoadVersion) return
        bindingPanel.loading = false
      })
  }

  function onUnbindDatasource(record: any) {
    Modal.confirm({
      title: '解绑数据库',
      content: `确认解除「${bindingPanel.datasourceName}」在「${getEnvironmentName(
        record
      )}」与「${dataSourceDisplayLabel(bindingDataSource(record))}」的绑定关系？`,
      cancelText: '取消',
      okText: '解绑',
      onBeforeOk: () => {
        return deleteDataFactoryDatasourceBinding(record.id)
          .then((res) => {
            Message.success(res.msg)
            loadDatasourceBindings()
          })
          .catch(console.log)
      },
    })
  }

  async function onBindingPermissionChange(
    record: any,
    field: 'db_c_status' | 'db_rud_status',
    checked: boolean
  ) {
    try {
      const res = await putDataFactoryDatasourceBinding({
        id: record.id,
        [field]: checked ? 1 : 0,
      })
      record[field] = checked ? 1 : 0
      Message.success(res.msg)
      return true
    } catch {
      return false
    }
  }

  function onAddBinding() {
    const environmentOptions = bindingEnvironmentOptions.value
    const availableEnvironment = environmentOptions.some((item: any) => !item.disabled)
    if (environmentOptions.length && !availableEnvironment) {
      Message.warning('当前逻辑数据库已绑定全部测试环境，请编辑现有绑定')
      return
    }
    bindingEditor.isEdit = false
    bindingEditor.bindingId = null
    bindingEditor.environment = null
    bindingEditor.dataSource = null
    bindingEditor.target = { database_name: '', schema_name: '', redis_db: null }
    bindingEditor.allowQuery = true
    bindingEditor.allowWrite = false
    openBindingEditor()
  }

  function onEditBinding(record: any) {
    bindingEditor.isEdit = true
    bindingEditor.bindingId = Number(record.id)
    bindingEditor.environment = record.environment
    bindingEditor.dataSource = Number(bindingDataSource(record)?.id || record.database)
    bindingEditor.target = { database_name: record.database_name || '', schema_name: record.schema_name || '', redis_db: record.redis_db ?? null }
    bindingEditor.allowQuery = record.db_c_status === 1
    bindingEditor.allowWrite = record.db_rud_status === 1
    openBindingEditor()
  }

  function openBindingEditor() {
    dataSourceOptions.value = []
    bindingEditorDialogRef.value?.show()
    bindingEditor.optionsLoading = true
    getSystemDataSource({ page: 1, pageSize: 999 })
      .then((res) => {
        dataSourceOptions.value = (res.data || [])
          .filter((item: any) => {
            const alias = table.dataList.find(
              (row: any) => String(row.id) === String(bindingPanel.datasourceId)
            )
            return (
              item.source_category === alias?.source_category && item.db_type === alias?.db_type
            )
          })
          .map((item: any) => ({
            value: item.id,
            db_type: item.db_type,
            label: dataSourceOptionLabel(item),
          }))
      })
      .finally(() => {
        bindingEditor.optionsLoading = false
      })
  }

  async function onSaveBinding() {
    if ((!bindingEditor.isEdit && bindingEditor.environment == null) || !bindingEditor.dataSource) {
      Message.error('请选择测试环境和数据库配置')
      bindingEditorDialogRef.value?.setConfirmLoading(false)
      return
    }
    if (
      !bindingEditor.isEdit &&
      bindingPanel.bindings.some(
        (item: any) => Number(item.environment) === Number(bindingEditor.environment)
      )
    ) {
      Message.error('当前逻辑数据库已绑定该测试环境，请编辑现有绑定或先解绑')
      bindingEditorDialogRef.value?.setConfirmLoading(false)
      return
    }
    if (bindingEditor.environment === 2) bindingEditor.allowWrite = false
    try {
      const payload: Record<string, any> = {
        data_source: bindingEditor.dataSource,
        ...bindingEditor.target,
        db_c_status: bindingEditor.allowQuery ? 1 : 0,
        db_rud_status: bindingEditor.allowWrite ? 1 : 0,
      }
      const request = bindingEditor.isEdit
        ? putDataFactoryDatasourceBinding
        : postDataFactoryDatasourceBinding
      if (bindingEditor.isEdit) {
        payload.id = bindingEditor.bindingId
      } else {
        payload.datasource_alias = bindingPanel.datasourceId
        payload.environment = bindingEditor.environment
      }
      const res = await request(payload)
      Message.success(res.msg)
      loadDatasourceBindings()
      bindingEditorDialogRef.value?.close()
    } catch {
      return
    } finally {
      bindingEditorDialogRef.value?.setConfirmLoading(false)
    }
  }

  function onQueryDatasource() {
    const statement = queryDrawer.statement.trim()
    if (!statement) {
      Message.error(`请输入${queryStatementLabel.value}`)
      return
    }
    if (queryDrawer.testEnv == null) {
      Message.error('请选择测试环境')
      return
    }
    const requestData: Record<string, any> = {
      action: 'execute',
      datasource_alias_id: queryDrawer.datasourceId,
      project_product_id: productId.value,
      test_env: queryDrawer.testEnv,
    }
    if (queryDrawer.sourceType === 10) {
      requestData.operation_config = statement
    } else if (queryDrawer.sourceType === 20) {
      if (!queryDrawer.index.trim()) {
        Message.error('请输入索引名称')
        return
      }
      try {
        requestData.query = JSON.parse(statement)
      } catch {
        Message.error('Query DSL 必须是合法的JSON对象')
        return
      }
      if (
        !requestData.query ||
        Array.isArray(requestData.query) ||
        typeof requestData.query !== 'object'
      ) {
        Message.error('Query DSL 必须是JSON对象')
        return
      }
      requestData.operation_config = {
        index: queryDrawer.index.trim(),
        query: requestData.query,
      }
      delete requestData.query
    } else {
      requestData.operation_config = statement
    }
    const relational = [0, 1, 2].includes(queryDrawer.sourceType)
    queryDrawer.loading = true
    const request = relational ? queryLogicalDataSource({
      datasource_alias_id: queryDrawer.datasourceId,
      project_product_id: productId.value,
      test_env: queryDrawer.testEnv,
      sql: statement,
    }) : postDataSourceExecution(requestData)
    request
      .then((res) => {
        queryDrawer.result = res.data ?? {}
        Message.success(res.msg)
      })
      .catch(console.log)
      .finally(() => {
        queryDrawer.loading = false
      })
  }

  function onDataForm() {
    if (!aliasForm.name.trim()) {
      Message.error('请输入逻辑数据库名称')
      modalDialogRef.value?.setConfirmLoading(false)
      return
    }
    if (aliasForm.dbType == null) {
      Message.error('请选择数据库类型')
      modalDialogRef.value?.setConfirmLoading(false)
      return
    }
    if (aliasForm.description.length > 50) {
      Message.error('描述不能超过50字')
      modalDialogRef.value?.setConfirmLoading(false)
      return
    }
    const value: Record<string, any> = {
      project_product: productId.value,
      name: aliasForm.name.trim(),
      source_category: aliasForm.sourceCategory,
      db_type: aliasForm.dbType,
      description: aliasForm.description.trim() || null,
      status: aliasForm.status,
    }
    if (!data.isAdd) value.id = data.updateId
    const request = data.isAdd ? postDataFactoryDatasourceAlias : putDataFactoryDatasourceAlias
    request(value)
      .then((res) => {
        modalDialogRef.value?.close()
        Message.success(res.msg)
        doRefresh()
      })
      .catch(console.log)
      .finally(() => {
        modalDialogRef.value?.setConfirmLoading(false)
      })
  }

  onMounted(() => {
    enumStore.getEnum()
    doRefresh()
  })
</script>

<style scoped>
  .mango-datasource-workbench-scroll {
    height: calc(100% - var(--m-page-gap));
    min-height: 0;
    margin-top: var(--m-page-gap);
    overflow-x: auto;
    overflow-y: hidden;
  }

  .mango-datasource-workbench {
    display: grid;
    grid-template-columns: 320px minmax(720px, 1fr);
    gap: var(--m-page-gap);
    min-width: 1052px;
    height: 100%;
    min-height: 0;
    grid-template-rows: minmax(0, 1fr);
  }

  .mango-datasource-workbench > .mango-section-card + .mango-section-card {
    margin-top: 0;
  }

  .mango-datasource-master,
  .mango-datasource-detail {
    display: flex;
    min-width: 0;
    min-height: 0;
    flex-direction: column;
  }

  .mango-datasource-detail-tabs {
    display: flex;
    flex: 1;
    min-height: 0;
    flex-direction: column;

    :deep(.arco-tabs-nav) {
      flex-shrink: 0;
    }

    :deep(.arco-tabs-content) {
      flex: 1;
      min-height: 0;
      padding-top: 0;
      overflow-x: hidden;
      overflow-y: auto;
      overscroll-behavior-y: contain;
    }
  }

  .mango-datasource-card-loading {
    display: block;
    min-height: 0;
    flex: 1;
    overflow-x: hidden;
    overflow-y: auto;
    overscroll-behavior-y: contain;
    scrollbar-gutter: stable;
  }

  .mango-datasource-card-list {
    display: flex;
    flex-direction: column;
    gap: var(--m-page-gap);
  }

  .mango-datasource-card {
    position: relative;
    padding: var(--m-space-md);
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-lg);
    background: var(--m-surface);
    cursor: pointer;
    transition: border-color 0.16s ease, box-shadow 0.16s ease, background 0.16s ease;
  }

  .mango-datasource-card:hover,
  .mango-datasource-card:focus-visible {
    border-color: var(--m-primary-border);
    outline: none;
    box-shadow: var(--m-shadow-sm);
  }

  .mango-datasource-card--active {
    border-color: var(--m-primary);
    background: var(--m-primary-soft);
    box-shadow: inset 3px 0 0 var(--m-primary);
  }

  .mango-datasource-card__header,
  .mango-datasource-card__identity,
  .mango-datasource-card__tags,
  .mango-datasource-card__footer {
    display: flex;
    align-items: center;
  }

  .mango-datasource-card__header {
    justify-content: space-between;
    gap: var(--m-space-sm);
  }

  .mango-datasource-card__identity {
    min-width: 0;
    flex: 1;
    gap: var(--m-space-sm);
  }

  .mango-datasource-card__name {
    overflow: hidden;
    color: var(--m-text);
    font-size: var(--m-font-body);
    font-weight: 600;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-datasource-card__id {
    flex: none;
    font-size: var(--m-font-caption);
    white-space: nowrap;
  }

  .mango-datasource-card__tags {
    flex-wrap: wrap;
    gap: var(--m-space-xs);
    margin-top: var(--m-space-sm);
  }

  .mango-datasource-card__description {
    display: -webkit-box;
    margin: var(--m-space-sm) 0 0;
    overflow: hidden;
    color: var(--m-text-2);
    font-size: var(--m-font-caption);
    line-height: var(--m-line-caption);
    overflow-wrap: anywhere;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
  }

  .mango-datasource-card__footer {
    justify-content: flex-end;
    margin-top: var(--m-space-sm);
    padding-top: var(--m-space-xs);
    border-top: 1px solid var(--m-border);
  }

  .mango-binding-title {
    gap: var(--m-page-gap);
  }

  .mango-binding-table {
    min-height: 0;
    flex: 1;
    overflow: hidden;
  }

  .mango-binding-empty {
    display: flex;
    min-height: 240px;
    flex: 1;
    align-items: center;
    justify-content: center;
  }

  .mango-sql-query-drawer {
    display: flex;
    flex-direction: column;
    gap: var(--m-page-gap);
    height: 100%;
  }

  .mango-sql-query-editor {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .mango-datasource-query-field {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .mango-sql-query-actions {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
  }

  .mango-sql-query-meta {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .mango-sql-query-label {
    flex: none;
    color: var(--m-text);
    font-size: 13px;
  }

  .mango-sql-query-result {
    min-height: 0;
    flex: 1;
  }

  .mango-datasource-query-loading {
    display: block;
    min-height: 240px;
  }

  .mango-sql-query-summary {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
    color: var(--m-text);
    font-size: 13px;
  }

  @container (max-width: 1099px) {
    .mango-datasource-workbench {
      grid-template-columns: 300px minmax(700px, 1fr);
      min-width: 1012px;
    }
  }
</style>
