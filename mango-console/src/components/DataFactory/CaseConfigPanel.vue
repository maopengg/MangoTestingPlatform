<template>
  <a-space direction="vertical" fill>
    <div v-if="showAddButton && !readonly" class="mango-data-factory-case-config__toolbar">
      <a-button

        size="small"
        type="primary"
        :disabled="!!collectionPending"
        @click="open()"
        data-testid="qa-components-datafactory-caseconfigpanel-button-增加"
        >{{ local ? '选择模板' : '增加' }}</a-button
      >
    </div>
    <div v-if="collectionOperationError" class="mango-soft-panel" role="alert">{{ collectionOperationError }} <a-button v-if="collectionCanRetry" size="small" :loading="!!collectionPending" @click="retryCollectionOperation()">重试</a-button></div>
    <div v-if="collectionPending?.kind === 'sort'" class="mango-soft-panel" role="status"><a-spin :size="scaleDensityPixels(16)" /> 正在保存配置顺序…</div>
    <a-table
      :bordered="false"
      :columns="displayColumns"
      :data="caseConfigList"
      :loading="loading"
      :pagination="false"
      :row-key="'id'"
      :draggable="readonly || local || collectionPending ? undefined : { type: 'handle', width: 40 }"
      :scroll="{ x: readonly ? 1000 : 970 }"
      size="small"
      @change="handleChange"
    >
      <template #columns>
        <a-table-column
          v-for="item of displayColumns"
          :key="item.key"
          :data-index="item.key"
          :ellipsis="item.ellipsis"
          :tooltip="item.tooltip"
          :title="item.title"
          :width="item.width"
          :align="item.align"
          :fixed="item.fixed"
        >
          <template v-if="item.key === 'template'" #cell="{ record }">
            {{ record.template?.name }}
          </template>
          <template v-else-if="item.key === 'entity'" #cell="{ record }">
            {{ record.template?.entity?.name }}
          </template>
          <template v-else-if="item.key === 'table_name'" #cell="{ record }">
            {{ record.template?.entity?.table_name }}
          </template>
          <template v-else-if="item.key === 'cleanup_strategy'" #cell="{ record }">
            <a-tag :color="enumStore.colors[record.cleanup_strategy]" size="small">
              {{
                enumTitle(
                  enumStore.data_factory_cleanup_strategy,
                  record.cleanup_strategy ?? record.template?.cleanup_strategy
                )
              }}
            </a-tag>
          </template>
          <template v-else-if="item.key === 'status'" #cell="{ record }">
            <a-tag v-if="readonly" :color="record.status === 1 ? 'green' : 'gray'" size="small">{{ record.status === 1 ? '启用' : '停用' }}</a-tag>
            <a-switch
              v-else
              :beforeChange="(newValue) => switchStatus(newValue, record)"
              :model-value="record.status === 1"
              :loading="collectionPending?.kind === 'status' && String(collectionPending.recordId) === String(record.id)"
              :disabled="!!collectionPending || local"
            />
          </template>
          <template v-else-if="item.key === 'stage'" #cell="{ record }">
            {{ enumTitle(enumStore.data_factory_execution_stage, record.stage) }}
          </template>
          <template v-else-if="item.key === 'actions'" #cell="{ record }">
            <MangoTableActions
              :actions="[
    { label: readonly ? '查看/预览' : '编辑/预览', disabled: !!collectionPending, onClick: () => open(record) },
    {
        label: '删除',
        hidden: readonly,
        danger: true,
        disabled: !!collectionPending,
        loading: deleteLoading === record.id,
        onClick: () => deleteConfig(record),
    },
]"
            />
          </template>
        </a-table-column>
      </template>
    </a-table>
  </a-space>

  <a-drawer
    v-model:visible="visible"
    :title="readonly ? '查看数据工厂配置' : form.id !== null ? '编辑数据工厂配置' : '新增数据工厂配置'"
    width="min(1480px, 96vw)"
    body-class="mango-data-factory-config-body"
    unmount-on-close
  >
    <div class="mango-data-factory-config-drawer">
      <a-alert v-if="readonlyError" type="error">配置数据无效，请关闭后重新加载。</a-alert>
      <a-alert v-if="collectionOperationError && !readonly" type="error">{{ collectionOperationError }}</a-alert>
      <a-form
        :model="form"
        :disabled="readonly"
        layout="horizontal"
        :label-col-props="{ flex: 'none' }"
        :wrapper-col-props="{ flex: '1' }"
        class="mango-data-factory-config-form"
      >
        <div class="mango-section-card mango-data-factory-base-card">
          <a-form-item label="项目/产品" required>
            <ProjectProductSelect v-model="form.project_product" :disabled="readonly" @change="onProjectProductChange" />
          </a-form-item>
          <a-form-item label="逻辑数据库" required>
            <a-select
              v-model="form.datasource_alias"
              :disabled="readonly"
              :options="datasourceAliasOptions"
              :loading="editorPending.aliases"
              :field-names="{ value: 'id', label: 'name' }"
              allow-clear
              allow-search
              placeholder="请选择逻辑数据库"
              @change="onDatasourceAliasChange"
              data-testid="qa-components-datafactory-caseconfigpanel-select-请选择逻辑数据库"
            />
          </a-form-item>
          <a-form-item label="模块名称" required>
            <ProductModuleSelect
              v-model="form.module"
              :disabled="readonly"
              :project-product-id="form.project_product"
              :auto-clear="false"
              @change="onModuleChange"
            />
          </a-form-item>
          <a-form-item label="场景模板" required>
            <a-select
              v-model="form.template"
              :disabled="readonly"
              :options="templateSelectOptions"
              :loading="templateLoading"
              allow-clear
              allow-search
              placeholder="请选择场景模板"
              @change="onTemplateChange"
              data-testid="qa-components-datafactory-caseconfigpanel-select-请选择场景模板"
            />
          </a-form-item>
          <a-form-item v-if="!local" label="数据名称" required>
            <a-input
              v-model="form.name"
              :disabled="readonly"
              placeholder="例如：订单数据；用例中按“订单数据.id”取值"
              data-testid="qa-components-datafactory-caseconfigpanel-input-例如-订单数据-用例中按-订单数据-id-取值"
            />
          </a-form-item>
          <a-form-item v-if="!local" label="清理策略">
            <a-select
              v-model="form.cleanup_strategy"
              :disabled="readonly"
              :options="cleanupStrategyOptions"
              :field-names="{ value: 'key', label: 'title' }"
              allow-clear
              placeholder="默认使用模板清理策略"
              data-testid="qa-components-datafactory-caseconfigpanel-select-默认使用模板清理策略"
            />
          </a-form-item>
          <a-form-item v-if="!local" label="状态">
            <a-switch
              :model-value="form.status === 1"
              :disabled="readonly"
              @change="(value) => (form.status = value ? 1 : 0)"
            />
          </a-form-item>
        </div>

        <div class="mango-data-factory-template-workbench">
          <aside class="mango-template-selector mango-section-card">
            <div class="mango-section-title">
              <div>
                <h2>场景模板</h2>
                <p>查看主模板和关联子模板，点击后定位字段配置</p>
              </div>
              <a-tag size="small" color="arcoblue">{{ templateNavCount }}</a-tag>
            </div>
            <button
              v-if="currentTemplate"
              type="button"
              :class="[
                'mango-template-current-card',
                {
                  'mango-template-current-card--active':
                    activeTemplateSectionKey === MAIN_TEMPLATE_SECTION_KEY,
                },
              ]"
              @click="scrollToMainTemplate"
            >
              <div class="mango-template-current-card__label">主模板</div>
              <div class="mango-template-current-card__name">{{ currentTemplate.name }}</div>
              <div class="mango-template-current-card__meta">
                {{ getTemplateEntityName(currentTemplate) }} /
                {{ getTemplateTableName(currentTemplate) }}
              </div>
              <div class="mango-template-current-card__foot">
                <span>{{ getTemplateItemCount(currentTemplate) }} 个关联模板</span>
                <span>{{ getTemplateCleanupText(currentTemplate) }}</span>
              </div>
            </button>
            <div v-if="selectedTemplateItems.length" class="mango-template-child-list">
              <button
                v-for="item in selectedTemplateItems"
                :key="getItemCaseKey(item)"
                type="button"
                :class="[
                  'mango-template-child-card',
                  {
                    'mango-template-child-card--active':
                      activeTemplateSectionKey === getItemCaseKey(item),
                  },
                ]"
                @click="scrollToTemplateItem(item)"
              >
                <span>{{ getItemTemplateName(item) }}</span>
                <small>{{ getItemTemplateMeta(item) }}</small>
                <em>{{ itemFieldsMap[String(item.id)]?.length || 0 }} 字段</em>
              </button>
            </div>
            <mango-panel-spin
              v-if="templateLoading || !currentTemplate"
              :loading="templateLoading"
              :class="[
                'mango-template-list-spin',
                { 'mango-template-list-spin--fill': !currentTemplate },
              ]"
            >
              <div
                v-if="form.project_product == null || form.datasource_alias == null || form.module == null"
                class="mango-empty-state mango-template-empty"
              >
                请先选择项目/产品、逻辑数据库和模块名称
              </div>
              <div v-else-if="!templateList.length" class="mango-empty-state mango-template-empty">
                暂无可选场景模板
              </div>
              <div v-else-if="!currentTemplate" class="mango-empty-state mango-template-empty">
                请在上方筛选区选择场景模板
              </div>
            </mango-panel-spin>
          </aside>

          <section class="mango-template-editor">
            <div v-if="currentTemplate" class="mango-section-card mango-template-summary">
              <div>
                <div class="mango-template-summary__title">{{ currentTemplate.name }}</div>
                <div class="mango-template-summary__meta">
                  {{ getTemplateEntityName(currentTemplate) }} /
                  {{ getTemplateTableName(currentTemplate) }}
                </div>
              </div>
              <a-space>
                <a-button
                  size="small"
                  type="primary"
                  :loading="previewLoading === 'form'"
                  :disabled="form.template === null"
                  @click="openRelationPreview"
                  data-testid="qa-components-datafactory-caseconfigpanel-button-预览整体流程"
                >
                  预览整体流程
                </a-button>
                <a-tag size="small" color="arcoblue"
                  >{{ getTemplateItemCount(currentTemplate) }} 个关联模板</a-tag
                >
                <a-tag size="small">{{ getTemplateCleanupText(currentTemplate) }}</a-tag>
              </a-space>
            </div>
            <mango-panel-spin :loading="fieldLoading" class="mango-template-editor-spin">
              <div v-if="form.template !== null" class="mango-template-field-stack">
                <section
                  :id="getTemplateSectionDomId(MAIN_TEMPLATE_SECTION_KEY)"
                  class="mango-section-card mango-case-config-field-card"
                >
                  <div class="mango-section-title">
                    <div>
                      <h2>主模板字段</h2>
                      <p>配置主模板字段生成规则和输出字段</p>
                    </div>
                  </div>
                  <TemplateFieldConfigEditor
                    :readonly="readonly || local"
                    :show-config="!local"
                    :field-overrides="mainCaseOverrides"
                    :output-config="templateOutputConfig"
                    :fields="fieldRows"
                    :generator-options="enumStore.data_factory_generator_type"
                    :dependency-template-options="dependencyTemplateOptions"
                    :load-dependency-template-options="loadDependencyTemplateOptions"
                    :preview-fields="previewResult.fields || []"
                    :loading="!fieldLoading && previewLoading === 'form'"
                    :show-output="false"
                    show-preview
                    @update:field-overrides="updateMainCaseOverrides"
                    @update:output-config="updateTemplateOutputConfig"
                  />
                </section>
                <section
                  v-for="item in selectedTemplateItems"
                  :key="item.id"
                  :id="getTemplateSectionDomId(getItemCaseKey(item))"
                  :class="[
                    'mango-section-card',
                    'mango-case-config-field-card',
                    { 'mango-case-config-field-card--collapsed': !isItemExpanded(item) },
                  ]"
                >
                  <div class="mango-section-title">
                    <div>
                      <h2>关联模板 / {{ getItemTemplateName(item) }}</h2>
                      <p>配置该关联模板在当前用例中的字段生成规则</p>
                    </div>
                    <a-space>
                      <a-tag size="small"
                        >{{ itemFieldsMap[String(item.id)]?.length || 0 }} 个字段</a-tag
                      >
                      <a-button size="mini" type="text" @click="toggleItemExpanded(item)">
                        {{ isItemExpanded(item) ? '收起' : '展开' }}
                      </a-button>
                    </a-space>
                  </div>
                  <template v-if="isItemExpanded(item)">
                    <TemplateFieldConfigEditor
                      :readonly="readonly || local"
                      :show-config="!local"
                      :field-overrides="getItemCaseOverrides(item)"
                      :output-config="[]"
                      :fields="itemFieldsMap[String(item.id)] || []"
                      :generator-options="enumStore.data_factory_generator_type"
                      :dependency-template-options="dependencyTemplateOptions"
                      :load-dependency-template-options="loadDependencyTemplateOptions"
                      :preview-fields="getItemPreviewFields(item)"
                      :loading="!fieldLoading && previewLoading === 'form'"
                      :show-output="false"
                      show-preview
                      @update:field-overrides="(value) => updateItemCaseOverrides(item, value)"
                    />
                  </template>
                  <div v-else class="mango-soft-panel mango-template-item-collapsed">
                    关联模板字段已收起。展开后可覆盖该模板在当前用例中的字段生成规则。
                  </div>
                </section>
              </div>
              <div v-else class="mango-empty-state mango-field-empty">请先选择场景模板</div>
            </mango-panel-spin>
          </section>
        </div>
      </a-form>
    </div>
    <template #footer>
      <a-space class="mango-data-factory-config-footer">
        <a-button
          @click="visible = false"
          data-testid="qa-components-datafactory-caseconfigpanel-button-取消"
          >{{ readonly ? '关闭' : '取消' }}</a-button
        >
        <a-button
          v-if="!readonly"

          type="primary"
          :loading="saving"
          :disabled="!!collectionPending && !saving"
          @click="save()"
          data-testid="qa-components-datafactory-caseconfigpanel-button-确定"
          >确定</a-button
        >
      </a-space>
    </template>
  </a-drawer>

  <a-drawer
    v-model:visible="relationPreviewVisible"
    title="预览整体流程"
    width="76%"
    :footer="false"
    unmount-on-close
  >
    <div class="mango-data-factory-relation-drawer">
      <DataFactoryRelationFlow
        :dependency-tree="previewResult.dependency_tree"
        :flow-loading="previewLoading === 'form'"
        title="整体流程"
        subtitle="查看当前用例数据工厂配置将创建或复用的数据关系"
        height="calc(100vh - 110px)"
        :initial-max-zoom="0.82"
        show-download
        show-mini-map
        :download-name="`${form.name || '数据工厂'}-整体流程`"
      />
    </div>
  </a-drawer>
</template>

<script lang="ts" setup>
  import { scaleDensityPixels } from '@/hooks/useDisplayDensity'
  import { computed, nextTick, onBeforeUnmount, reactive, ref, watch } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import { reportLoadError } from '@/utils/load-error'
  import { useEnum } from '@/store/modules/get-enum'
  import { useCaseConfigCollection } from './composables/useCaseConfigCollection'
  import type { FactoryConfigId, FactoryConfigRecord, FactoryConfigSummary } from './case-config-record'
  import { factoryConfigId, factoryConfigObject } from './case-config-record'
  import { cloneLosslessJson } from '@/utils/lossless-json'
  import { emptyFactoryPreview, factorySceneOverrides, readFactoryEditorTemplates, readFactoryFields, readFactoryOverrides, readFactoryPreview, type FactoryEditorDraft, type FactoryEditorItem, type FactoryEditorPreview, type FactoryEditorTemplate, type FactoryPreviewField } from './case-config-editor'
  import type { FactoryConfigTemplate } from './case-config-record'
  import { factoryConfigResponse } from './case-config-record'

  import DataFactoryRelationFlow from '@/components/DataFactory/DataFactoryRelationFlow.vue'
  import TemplateFieldConfigEditor from '@/components/DataFactory/TemplateFieldConfigEditor.vue'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import {
    getDataFactoryDatasourceAlias,
    getDataFactoryField,
    getDataFactoryTemplate,
    postDataFactoryCaseConfigPreview,
  } from '@/api/data-factory'
  import type {
    DataFactoryAnyFieldOverrides,
    DataFactoryFieldOverrides,
    DataFactoryFieldRule,
    DataFactoryOutputConfig,
  } from '@/types/data-factory'

  const props = withDefaults(
    defineProps<{
      caseId?: string | number | null
      projectProductId?: string | number | null
      sourceType?: number
      local?: boolean
      showAddButton?: boolean
      readonly?: boolean
      configs?: unknown[]
    }>(),
    {
      caseId: null,
      local: false,
      projectProductId: null,
      showAddButton: false,
      readonly: false,
      configs: () => [],
    }
  )
  const emit = defineEmits<{
    (event: 'count-change', count: number): void
    (event: 'collection-state', state: FactoryConfigSummary): void
    (event: 'update:configs', configs: Array<{ id: string; name: string; template: FactoryEditorTemplate; field_overrides: DataFactoryAnyFieldOverrides }>): void
  }>()

  const enumStore = useEnum()

  const readonlyError = ref(false)
  let readonlyRequestVersion = 0
  const TEMPLATE_USAGE_CASE = 1
  const MAIN_TEMPLATE_SECTION_KEY = '__main__'
  const templateSectionDomPrefix = `mango-case-template-section-${Math.random()
    .toString(36)
    .slice(2)}`

  const columns = [
    {
      title: '数据名称',
      key: 'name',
      dataIndex: 'name',
      width: 200,
      align: 'left',
      ellipsis: true,
      tooltip: true,
    },
    {
      title: '场景模板',
      key: 'template',
      dataIndex: 'template',
      width: 200,
      align: 'left',
      ellipsis: true,
      tooltip: true,
    },
    {
      title: '基础实体',
      key: 'entity',
      dataIndex: 'entity',
      width: 100,
      align: 'left',
      ellipsis: true,
      tooltip: true,
    },
    {
      title: '表名',
      key: 'table_name',
      dataIndex: 'table_name',
      width: 100,
      align: 'left',
      ellipsis: true,
      tooltip: true,
    },
    { title: '清理策略', key: 'cleanup_strategy', dataIndex: 'cleanup_strategy', width: 120 },
    { title: '状态', key: 'status', dataIndex: 'status', width: 90, align: 'center' },
    {
      title: '操作',
      key: 'actions',
      dataIndex: 'actions',
      width: 160,
      align: 'center',
      fixed: 'right',
    },
  ]

  const displayColumns = computed(() => props.local ? columns.filter(item => !['name', 'cleanup_strategy', 'status'].includes(item.key)) : props.readonly ? [
    ...columns.filter(item => item.key !== 'actions'),
    { title: '执行阶段', key: 'stage', dataIndex: 'stage', width: 90, align: 'center' },
    { title: '执行顺序', key: 'sort', dataIndex: 'sort', width: 80, align: 'center' },
    columns.find(item => item.key === 'actions')!,
  ] : columns)
  const templateList = ref<FactoryEditorTemplate[]>([])
  const datasourceAliasOptions = ref<Array<{ id: FactoryConfigId; name: string }>>([])
  const expandedTemplateItemKeys = ref<string[]>([])
  const fieldRows = ref<FactoryPreviewField[]>([])
  const itemFieldsMap = ref<Record<string, FactoryPreviewField[]>>({})
  const dependencyTemplateOptions = ref<Record<string, Array<{ label: string; value: FactoryConfigId }>>>({})
  const templateOutputConfig = ref<DataFactoryOutputConfig>([])
  const visible = ref(false)
  const relationPreviewVisible = ref(false)
  type EditorResource = 'aliases' | 'templates' | 'fields' | 'dependencies' | 'preview'
  type EditorChannel = 'aliases' | 'templates' | 'selected-template' | 'fields' | 'preview' | `item:${string}` | `dependency:${string}`
  const editorPending = reactive<Record<EditorResource, boolean>>({ aliases: false, templates: false, fields: false, dependencies: false, preview: false })
  const templateLoading = computed({ get: () => editorPending.templates, set: (value: boolean) => { editorPending.templates = value } })
  const fieldLoading = computed({ get: () => editorPending.fields, set: (value: boolean) => { editorPending.fields = value } })
  const previewLoading = computed({ get: () => editorPending.preview ? 'form' : null, set: (value: 'form' | null) => { editorPending.preview = value !== null } })
  const editorFailures = ref<Array<{ key: EditorChannel; resource: EditorResource; message: string; retry: () => Promise<boolean> }>>([])
  const editorRequests = new Map<EditorChannel, number>(), editorActive = new Map<EditorResource, Set<EditorChannel>>()
  const previewResult = ref<FactoryEditorPreview>(emptyFactoryPreview())
  const previewTimerId = ref<number>()
  const activeTemplateSectionKey = ref(MAIN_TEMPLATE_SECTION_KEY)

  const form = reactive<FactoryEditorDraft>({
    id: null,
    source_type: props.sourceType,
    source_id: props.caseId,
    project_product: props.projectProductId,
    datasource_alias: null,
    module: null,
    template: null,
    name: '',
    sort: 0,
    field_overrides: {},
    cleanup_strategy: 1,
    status: 1,
    stage: 1,
  })
  let closeDeleteConfirmation: (() => void) | null = null
  const collection = useCaseConfigCollection({
    caseId: () => props.caseId, sourceType: () => props.sourceType, readonly: () => props.readonly, local: () => props.local, configs: () => props.configs,
    changed: state => { emit('collection-state', state); if (state.count !== null) emit('count-change', state.count) },
    invalidated: () => {
      invalidateEditorRequests()
      closeDeleteConfirmation?.(); closeDeleteConfirmation = null
      visible.value = false; relationPreviewVisible.value = false
      templateLoading.value = false; fieldLoading.value = false; previewLoading.value = null
      templateList.value = []; datasourceAliasOptions.value = []; fieldRows.value = []; itemFieldsMap.value = {}; dependencyTemplateOptions.value = {}; previewResult.value = emptyFactoryPreview()
      if (previewTimerId.value) window.clearTimeout(previewTimerId.value)
    },
  })
  const { rows: caseConfigList, loading, loadError: collectionLoadError, operationError: collectionOperationError, pending: collectionPending, load: refresh, retry: retryCollectionOperation, canRetry: collectionCanRetry } = collection
  const saving = computed(() => collectionPending.value?.kind === 'save')
  const deleteLoading = computed(() => collectionPending.value?.kind === 'delete' ? collectionPending.value.recordId : null)

  const cleanupStrategyOptions = computed(() => [
    { key: null, title: '使用模板默认策略' },
    ...(enumStore.data_factory_cleanup_strategy || []),
  ])
  const currentTemplate = computed(() =>
    templateList.value.find((item) => String(item.id) === String(form.template))
  )
  const templateSelectOptions = computed(() =>
    templateList.value.map((item) => ({
      label: `${item.name} / ${getTemplateEntityName(item)} / ${getTemplateTableName(item)}`,
      value: item.id,
    }))
  )
  const selectedTemplateItems = computed(() => currentTemplate.value?.items || [])
  const templateNavCount = computed(() =>
    currentTemplate.value ? 1 + selectedTemplateItems.value.length : 0
  )
  const mainCaseOverrides = computed(() => factorySceneOverrides(form.field_overrides).__main__)

  function enumTitle(options: unknown = [], value: unknown) {
    if (Array.isArray(options)) {
      const match = options.find(item => item && typeof item === 'object' && factoryConfigObject(item).key === value)
      if (match) { const title = factoryConfigObject(match).title; if (typeof title === 'string') return title }
    }
    return value == null || value === '' ? '-' : String(value)
  }
  function getTemplateEntityName(template: FactoryConfigTemplate | undefined | null) { return template?.entity?.name || (template?.entity?.id ?? '-') }
  function getTemplateTableName(template: FactoryConfigTemplate | undefined | null) { return template?.entity?.table_name || '-' }
  function getTemplateItemCount(template: FactoryEditorTemplate | undefined | null) { return template?.items.length ?? 0 }
  function getTemplateCleanupText(template: FactoryConfigTemplate | undefined | null) { return enumTitle(enumStore.data_factory_cleanup_strategy, template?.cleanup_strategy ?? form.cleanup_strategy) }

  function getOptionId(value: unknown): FactoryConfigId | null {
    if (Array.isArray(value)) return factoryConfigId(value[value.length - 1])
    return value && typeof value === 'object' ? factoryConfigId(factoryConfigObject(value).id) : factoryConfigId(value)
  }

  function handleChange(data: FactoryConfigRecord[]) {
    return collection.sort(data.map(item => item.id))
  }

  function invalidateEditorRequests() {
    readonlyRequestVersion++
    editorRequests.clear(); editorActive.clear(); editorFailures.value = []
    for (const key of Object.keys(editorPending) as EditorResource[]) editorPending[key] = false
    if (previewTimerId.value) window.clearTimeout(previewTimerId.value)
  }
  async function editorRead<T>(key: EditorChannel, resource: EditorResource, signature: () => string, request: () => Promise<T>, apply: (value: T) => void | Promise<void>): Promise<boolean> {
    const valid = collection.capture(), revision = readonlyRequestVersion, context = signature(), sequence = (editorRequests.get(key) ?? 0) + 1
    if (!valid() || !visible.value) return false
    editorRequests.set(key, sequence)
    const current = () => valid() && visible.value && revision === readonlyRequestVersion && context === signature() && editorRequests.get(key) === sequence
    const active = editorActive.get(resource) ?? new Set<EditorChannel>()
    active.add(key); editorActive.set(resource, active); editorPending[resource] = true
    editorFailures.value = editorFailures.value.filter(item => item.key !== key)
    try {
      const value = await request()
      if (!current()) return false
      await apply(value); return current()
    } catch (failure) {
      if (current()) {
        const names = { aliases: '逻辑数据库', templates: '场景模板', fields: '模板字段', dependencies: '依赖模板', preview: '配置预览' }
        reportLoadError(failure, `${names[resource]}加载失败，请重试`)
        editorFailures.value = [...editorFailures.value.filter(item => item.key !== key), { key, resource, message: `${names[resource]}加载失败，请重试`, retry: () => current() ? editorRead(key, resource, signature, request, apply) : Promise.resolve(false) }]
      }
      return false
    } finally {
      if (revision === readonlyRequestVersion && editorRequests.get(key) === sequence) {
        active.delete(key); editorPending[resource] = active.size > 0
      }
    }
  }
  function loadDatasourceAliases(projectProduct: unknown) {
    const projectProductId = getOptionId(projectProduct)
    if (projectProductId === null) { datasourceAliasOptions.value = []; return Promise.resolve(false) }
    return editorRead('aliases', 'aliases', () => JSON.stringify([getOptionId(form.project_product), props.projectProductId]),
      async () => {
        const values = factoryConfigResponse(await getDataFactoryDatasourceAlias({ project_product: projectProductId, status: 1, page: 1, pageSize: 9999 }))
        if (!Array.isArray(values)) throw Error('Invalid datasource aliases')
        return values.map(value => { const row = factoryConfigObject(value), id = factoryConfigId(row.id); if (id === null || typeof row.name !== 'string') throw Error('Invalid datasource alias'); return { id, name: row.name } })
      }, values => { datasourceAliasOptions.value = values })
  }
  function loadTemplates() {
    const projectProduct = getOptionId(form.project_product ?? props.projectProductId), datasourceAlias = getOptionId(form.datasource_alias), module = getOptionId(form.module)
    if (projectProduct === null || datasourceAlias === null || module === null) { templateList.value = []; return Promise.resolve(false) }
    return editorRead('templates', 'templates', () => JSON.stringify([form.project_product, form.datasource_alias, form.module]),
      async () => readFactoryEditorTemplates(factoryConfigResponse(await getDataFactoryTemplate({ page: 1, pageSize: 9999, project_product: projectProduct, entity__datasource_alias_id: datasourceAlias, module, usage_scope: TEMPLATE_USAGE_CASE }))),
      values => {
        const selected = templateList.value.find(item => String(item.id) === String(form.template))
        templateList.value = selected && !values.some(item => String(item.id) === String(selected.id)) ? [...values, selected] : values
      })
  }

  function resetForm(record: FactoryConfigRecord | null = null) {
    const template = record?.template ?? null
    form.id = record?.id ?? null
    form.source_type = props.sourceType
    form.source_id = record?.source_id ?? props.caseId
    form.project_product = getOptionId(template?.project_product) ?? props.projectProductId ?? null
    form.datasource_alias = getOptionId(template?.entity?.datasource_alias)
    form.module = getOptionId(template?.module)
    form.template = getOptionId(record?.template)
    form.name = props.local ? 'data' : record?.name || ''
    form.sort = record?.sort ?? caseConfigList.value.length
    form.field_overrides = readFactoryOverrides(record?.field_overrides)
    form.cleanup_strategy = record ? record.cleanup_strategy ?? null : 1
    form.status = record?.status ?? 1
    form.stage = record?.stage ?? 1
    templateOutputConfig.value = cloneLosslessJson(record?.template?.output_config ?? [])
    fieldRows.value = []
    itemFieldsMap.value = {}
    expandedTemplateItemKeys.value = []
    activeTemplateSectionKey.value = MAIN_TEMPLATE_SECTION_KEY
    previewResult.value = emptyFactoryPreview()
  }

  async function open(record: FactoryConfigRecord | null = null) {
    if (collectionPending.value || !collection.capture()()) return
    if (props.readonly) { if (record) await openReadonly(record); return }
    invalidateEditorRequests(); readonlyError.value = false
    try { resetForm(record) } catch { readonlyError.value = true; visible.value = true; return }
    visible.value = true
    const current = collection.capture(), revision = readonlyRequestVersion
    const valid = () => current() && visible.value && revision === readonlyRequestVersion
    const snapshot = record ? cloneLosslessJson(record) : null
    if (snapshot) {
      await loadSelectedTemplate(snapshot)
      if (!valid()) return
      if (props.local) return
    }
    await loadDatasourceAliases(form.project_product)
    if (valid() && form.project_product != null && form.datasource_alias !== null && form.module !== null) await loadTemplates()
  }

  function resetTemplateSelection() {
    dependencyTemplateOptions.value = {}
    form.template = null
    form.field_overrides = {}
    templateOutputConfig.value = []
    fieldRows.value = []
    itemFieldsMap.value = {}
    expandedTemplateItemKeys.value = []
    activeTemplateSectionKey.value = MAIN_TEMPLATE_SECTION_KEY
    previewResult.value = emptyFactoryPreview()
  }

  async function loadSelectedTemplate(record: FactoryConfigRecord): Promise<boolean> {
    const id = record.template?.id
    if (id == null) { readonlyError.value = true; return false }
    return editorRead('selected-template', 'templates', () => String(form.template),
      async () => {
        const values = readFactoryEditorTemplates(factoryConfigResponse(await getDataFactoryTemplate({ id, page: 1, pageSize: 1 })))
        const template = values.find(item => String(item.id) === String(id))
        if (!template) throw Error('Missing selected template')
        return template
      }, async template => {
        if (props.local || props.readonly) resetForm({ ...record, template })
        templateList.value = [...templateList.value.filter(item => String(item.id) !== String(id)), template]
        if (props.readonly) { const alias = template.entity?.datasource_alias; datasourceAliasOptions.value = alias?.id != null ? [{ id: alias.id, name: alias.name }] : [] }
        const current = collection.capture(), revision = readonlyRequestVersion
        await loadFields()
        if (current() && visible.value && revision === readonlyRequestVersion) await loadCasePreview()
      })
  }
  async function openReadonly(record: FactoryConfigRecord) {
    invalidateEditorRequests(); readonlyError.value = false
    try { resetForm(record) } catch { readonlyError.value = true; visible.value = true; return }
    visible.value = true
    const current = collection.capture(), revision = readonlyRequestVersion
    if (!await loadSelectedTemplate(cloneLosslessJson(record)) || !current() || !visible.value || revision !== readonlyRequestVersion) return
  }

  function onProjectProductChange() {
    invalidateEditorRequests()
    form.datasource_alias = null
    form.module = null
    resetTemplateSelection()
    datasourceAliasOptions.value = []
    templateList.value = []
    loadDatasourceAliases(form.project_product)
  }

  function onDatasourceAliasChange() {
    invalidateEditorRequests()
    resetTemplateSelection()
    templateList.value = []
    if (form.module !== null) {
      loadTemplates()
    }
  }

  function onModuleChange() {
    invalidateEditorRequests()
    resetTemplateSelection()
    loadTemplates()
  }

  function onTemplateChange() {
    invalidateEditorRequests()
    dependencyTemplateOptions.value = {}
    form.template = getOptionId(form.template)
    const template = templateList.value.find((item) => String(item.id) === String(form.template))
    if (!form.name && template?.name) {
      form.name = template.name
    }
    templateOutputConfig.value = template?.output_config || []
    form.field_overrides = normalizeSceneOverrides(template?.field_overrides || {})
    itemFieldsMap.value = {}
    expandedTemplateItemKeys.value = []
    previewResult.value = emptyFactoryPreview()
    loadFields()
    scheduleCasePreview()
  }

  async function loadFields() {
    const template = templateList.value.find(item => String(item.id) === String(form.template)), entityId = template?.entity?.id
    if (entityId == null) { fieldRows.value = []; return false }
    const results = await Promise.all([
      editorRead('fields', 'fields', () => JSON.stringify([form.template, currentTemplate.value?.entity?.id]), async () => readFactoryFields(factoryConfigResponse(await getDataFactoryField({ entity: entityId }))), values => { fieldRows.value = values; preloadDependencyTemplateOptions() }),
      loadItemFields(),
    ])
    return results.every(Boolean)
  }
  function dependencyEntityId(row: DataFactoryFieldRule) { const config = row.generator_config; return config && 'dependency_entity_id' in config ? factoryConfigId(config.dependency_entity_id) : null }
  function loadDependencyTemplateOptions(row: DataFactoryFieldRule) {
    const entityId = dependencyEntityId(row), projectProduct = getOptionId(form.project_product ?? props.projectProductId)
    if (entityId === null || projectProduct === null) return Promise.resolve(false)
    const cacheKey = String(entityId)
    if (dependencyTemplateOptions.value[cacheKey]) return Promise.resolve(true)
    return editorRead(`dependency:${cacheKey}`, 'dependencies', () => JSON.stringify([form.project_product, form.template]),
      async () => readFactoryEditorTemplates(factoryConfigResponse(await getDataFactoryTemplate({ project_product: projectProduct, entity: entityId, page: 1, pageSize: 9999 }))).map(template => ({ label: template.name, value: template.id })),
      values => { dependencyTemplateOptions.value = { ...dependencyTemplateOptions.value, [cacheKey]: values } })
  }
  function preloadDependencyTemplateOptions() { fieldRows.value.filter(row => dependencyEntityId(row) !== null).forEach(row => { void loadDependencyTemplateOptions(row) }) }

  function normalizeSceneOverrides(overrides: DataFactoryAnyFieldOverrides) { return factorySceneOverrides(overrides) }

  function updateMainCaseOverrides(value: DataFactoryFieldOverrides) {
    form.field_overrides = {
      __main__: value,
      __items__: factorySceneOverrides(form.field_overrides).__items__,
    }
    scheduleCasePreview()
  }

  function updateTemplateOutputConfig(value: DataFactoryOutputConfig) {
    templateOutputConfig.value = value
  }

  function getItemCaseKey(item: FactoryEditorItem) {
    return String(item.id ?? (item.name || item.child_template))
  }

  function getItemTemplateName(item: FactoryEditorItem) {
    return item.name || item.child_template_detail?.name || item.child_template || '-'
  }

  function getItemTemplateMeta(item: FactoryEditorItem) {
    const template = item.child_template_detail
    return `${getTemplateEntityName(template)} / ${getTemplateTableName(template)}`
  }

  function getTemplateSectionDomId(key: string) {
    return `${templateSectionDomPrefix}-${key}`
  }

  function scrollToTemplateSection(key: string) {
    activeTemplateSectionKey.value = key
    nextTick(() => {
      document.getElementById(getTemplateSectionDomId(key))?.scrollIntoView({
        behavior: 'smooth',
        block: 'start',
      })
    })
  }

  function scrollToMainTemplate() {
    scrollToTemplateSection(MAIN_TEMPLATE_SECTION_KEY)
  }

  function scrollToTemplateItem(item: FactoryEditorItem) {
    const key = getItemCaseKey(item)
    if (!expandedTemplateItemKeys.value.includes(key)) {
      expandedTemplateItemKeys.value = [...expandedTemplateItemKeys.value, key]
    }
    scrollToTemplateSection(key)
  }

  function isItemExpanded(item: FactoryEditorItem) {
    return expandedTemplateItemKeys.value.includes(getItemCaseKey(item))
  }

  function toggleItemExpanded(item: FactoryEditorItem) {
    const key = getItemCaseKey(item)
    expandedTemplateItemKeys.value = isItemExpanded(item)
      ? expandedTemplateItemKeys.value.filter((itemKey) => itemKey !== key)
      : [...expandedTemplateItemKeys.value, key]
  }

  function getItemCaseOverrides(item: FactoryEditorItem): DataFactoryFieldOverrides {
    return factorySceneOverrides(form.field_overrides).__items__[getItemCaseKey(item)] || {}
  }

  function updateItemCaseOverrides(item: FactoryEditorItem, value: DataFactoryFieldOverrides) {
    form.field_overrides = {
      __main__: mainCaseOverrides.value,
      __items__: {
        ...(factorySceneOverrides(form.field_overrides).__items__),
        [getItemCaseKey(item)]: value,
      },
    }
    scheduleCasePreview()
  }

  function getItemPreviewFields(item: FactoryEditorItem) {
    const itemKey = getItemCaseKey(item)
    const itemPreview = (previewResult.value?.items || []).find((previewItem) =>
      [previewItem.id, previewItem.name, previewItem.template?.id]
        .filter((value) => value !== undefined && value !== null && value !== '')
        .some((value) => String(value) === itemKey)
    )
    return itemPreview?.fields || []
  }

  function openRelationPreview() {
    relationPreviewVisible.value = true
    if (!previewResult.value?.dependency_tree) {
      loadCasePreview()
    }
  }

  async function loadItemFields() {
    const results = await Promise.all(selectedTemplateItems.value.map(item => {
      const entityId = item.child_template_detail?.entity?.id
      if (entityId == null) return Promise.resolve(true)
      const key = getItemCaseKey(item)
      return editorRead(`item:${key}`, 'fields', () => JSON.stringify([form.template, selectedTemplateItems.value.find(value => getItemCaseKey(value) === key)?.child_template_detail?.entity?.id]),
        async () => readFactoryFields(factoryConfigResponse(await getDataFactoryField({ entity: entityId }))), values => { itemFieldsMap.value = { ...itemFieldsMap.value, [String(item.id)]: values } })
    }))
    return results.every(Boolean)
  }

  async function save() {
    if (!visible.value || props.readonly || collectionPending.value || !collection.capture()()) return false
    if (form.template === null) { Message.error('请选择场景模板'); return false }
    if (!form.name) { Message.error('请填写数据名称'); return false }
    if (!props.local && factoryConfigId(props.caseId) === null) { Message.error('用例ID不能为空'); return false }
    if (props.local) {
      const template = currentTemplate.value
      if (!template) return false
      emit('update:configs', cloneLosslessJson([{ id: 'local', name: 'data', template, field_overrides: form.field_overrides }]))
      visible.value = false
      return true
    }
    const revision = readonlyRequestVersion
    const result = await collection.save({
      id: form.id, template: form.template, name: form.name, sort: form.sort,
      field_overrides: form.field_overrides,
      cleanup_strategy: form.cleanup_strategy === null ? null : form.cleanup_strategy,
      status: form.status, stage: form.stage,
    })
    if (result.accepted && result.current() && revision === readonlyRequestVersion && visible.value) visible.value = false
    return result.accepted && result.current()
  }

  function switchStatus(newValue: boolean, record: FactoryConfigRecord) {
    return collection.status(record.id, newValue)
  }

  function deleteConfig(record: FactoryConfigRecord) {
    const current = collection.capture(), id = record.id
    if (props.readonly || collectionPending.value || closeDeleteConfirmation || !current()) return
    let open = true
    const close = () => { if (!open) return; open = false; closeDeleteConfirmation = null; shell.close() }
    const shell = Modal.confirm({
      title: '提示', content: '确定要删除这个数据工厂配置吗？', cancelText: '取消', okText: '删除',
      onCancel: close,
      onBeforeOk: async () => {
        if (!open || !current()) { close(); return false }
        if (props.local) { emit('update:configs', []); close(); return true }
        const result = await collection.remove(id, current)
        if (result.accepted && result.current()) { close(); return true }
        return false
      },
    })
    closeDeleteConfirmation = close
  }

  function scheduleCasePreview() {
    if (!visible.value || !collection.capture()()) return
    const current = collection.capture(), revision = readonlyRequestVersion
    if (previewTimerId.value) {
      window.clearTimeout(previewTimerId.value)
    }
    previewTimerId.value = window.setTimeout(() => {
      if (current() && visible.value && revision === readonlyRequestVersion) void loadCasePreview()
    }, 360)
  }

  function loadCasePreview() {
    const templateId = form.template
    if (templateId === null) { previewResult.value = emptyFactoryPreview(); return Promise.resolve(false) }
    const payload = { source_type: props.sourceType, source_id: props.caseId, template_id: templateId, field_overrides: cloneLosslessJson(form.field_overrides), preview_mode: 'configuration' }
    return editorRead('preview', 'preview', () => JSON.stringify([form.template, form.field_overrides]),
      async () => readFactoryPreview(factoryConfigResponse(await postDataFactoryCaseConfigPreview(payload))), values => { previewResult.value = values })
  }

  watch(
    () => props.projectProductId,
    () => {
      if (!visible.value) {
        return
      }
      form.project_product = props.projectProductId ?? null
      onProjectProductChange()
    }
  )


  watch(visible, next => { if (!next) { invalidateEditorRequests(); relationPreviewVisible.value = false } }, { flush: 'sync' })
  onBeforeUnmount(() => invalidateEditorRequests())

  defineExpose({
    open,
    refresh,
  })
</script>

<style scoped>
  .mango-data-factory-case-config__toolbar {
    display: flex;
    justify-content: flex-end;
  }

  .full-width {
    width: 100%;
  }

  :global(.mango-data-factory-config-body) {
    display: flex;
    min-height: 0;
    padding: var(--m-page-gap);
    overflow: hidden;
  }

  .mango-data-factory-config-drawer {
    flex: 1;
    height: 100%;
    min-height: 0;
    min-width: 0;
    container-type: inline-size;
  }

  .mango-data-factory-config-form {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
    gap: var(--m-page-gap);
  }

  .mango-data-factory-base-card {
    display: grid;
    flex: none;
    padding: var(--m-card-padding);
    gap: var(--m-page-gap);
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  }

  .mango-data-factory-base-card :deep(.arco-form-item) {
    margin-bottom: 0;
  }

  .mango-data-factory-base-card :deep(.arco-form-item-label-col) {
    width: 100px;
    white-space: nowrap;
  }

  .mango-data-factory-base-card :deep(.arco-form-item-label) {
    white-space: nowrap;
  }

  .mango-data-factory-base-card :deep(.arco-form-item-wrapper-col) {
    min-width: 0;
  }

  .mango-template-current-card:focus-visible,
  .mango-template-child-card:focus-visible {
    outline: 1px solid var(--m-primary);
    outline-offset: 1px;
  }

  @media (prefers-reduced-motion: reduce) {
    .mango-template-current-card,
    .mango-template-child-card {
      transition: none;
    }
  }

  .mango-data-factory-template-workbench {
    display: grid;
    flex: 1;
    min-height: 0;
    gap: var(--m-page-gap);
    grid-template-columns: 330px minmax(0, 1fr);
  }

  .mango-template-selector,
  .mango-template-editor {
    min-height: 0;
  }

  .mango-template-selector {
    display: flex;
    overflow: hidden;
    flex-direction: column;
    padding: var(--m-card-padding);
    gap: var(--m-page-gap);
  }

  .mango-template-list-spin {
    display: block;
    flex: 0 0 auto;
    min-height: 0;
  }

  .mango-template-list-spin--fill {
    flex: 1;
  }

  .mango-template-list-spin :deep(> .mango-panel-spin__content) {
    height: 100%;
    min-height: 0;
  }

  .mango-template-current-card {
    appearance: none;
    display: block;
    width: 100%;
    flex-shrink: 0;
    cursor: pointer;
    padding: var(--m-card-padding);
    border: 1px solid var(--m-primary-border);
    border-radius: var(--m-radius-md);
    background: color-mix(in srgb, var(--m-primary) 7%, var(--m-surface));
    color: var(--m-text);
    box-shadow: none;
    font: inherit;
    text-align: left;
    transition: border-color var(--m-motion-duration-fast), background var(--m-motion-duration-fast);
  }

  .mango-template-current-card:hover,
  .mango-template-current-card--active {
    border-color: var(--m-primary);
    background: color-mix(in srgb, var(--m-primary) 10%, var(--m-surface));
  }

  .mango-template-current-card__label {
    margin-bottom: 4px;
    color: var(--m-primary);
    font-size: 12px;
    font-weight: 600;
    line-height: 18px;
  }

  .mango-template-current-card__name,
  .mango-template-current-card__meta,
  .mango-template-current-card__foot {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-template-current-card__name {
    color: var(--m-text);
    font-size: 13px;
    font-weight: 600;
    line-height: 19px;
  }

  .mango-template-current-card__meta,
  .mango-template-current-card__foot {
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .mango-template-current-card__foot {
    display: flex;
    justify-content: space-between;
    margin-top: 3px;
    gap: 8px;
  }

  .mango-template-child-list {
    display: flex;
    overflow: auto;
    flex: 1;
    flex-direction: column;
    min-height: 0;
    gap: var(--m-space-sm);
  }

  .mango-template-child-card {
    appearance: none;
    display: flex;
    width: 100%;
    cursor: pointer;
    flex-direction: column;
    padding: var(--m-space-sm) var(--m-card-padding);
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-sm);
    background: var(--m-surface);
    color: var(--m-text);
    font: inherit;
    gap: 1px;
    text-align: left;
    transition: border-color var(--m-motion-duration-fast), background var(--m-motion-duration-fast);
  }

  .mango-template-child-card:hover,
  .mango-template-child-card--active {
    border-color: var(--m-primary-border);
    background: color-mix(in srgb, var(--m-primary) 6%, var(--m-surface));
  }

  .mango-template-child-card span,
  .mango-template-child-card small,
  .mango-template-child-card em {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-template-child-card span {
    font-size: 13px;
    font-weight: 600;
    line-height: 19px;
  }

  .mango-template-child-card small,
  .mango-template-child-card em {
    color: var(--m-muted);
    font-size: 12px;
    font-style: normal;
    line-height: 18px;
  }

  .mango-template-editor {
    display: flex;
    overflow: hidden;
    flex-direction: column;
    gap: var(--m-page-gap);
  }

  .mango-template-summary {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex: none;
    flex-wrap: wrap;
    padding: var(--m-card-padding);
    gap: var(--m-page-gap);
    box-shadow: none;
  }

  .mango-template-summary__title {
    overflow: hidden;
    color: var(--m-text);
    font-size: 15px;
    font-weight: 600;
    line-height: 22px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-template-summary__meta {
    overflow: hidden;
    margin-top: 2px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-template-editor-spin {
    display: block;
    overflow: hidden;
    flex: 1;
    height: 100%;
    min-height: 0;
  }

  .mango-template-editor-spin :deep(> .mango-panel-spin__content) {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
  }

  .mango-template-editor-spin :deep(> .mango-panel-spin__content) {
    overflow: hidden;
  }

  .mango-template-field-stack {
    display: flex;
    flex-direction: column;
    gap: var(--m-page-gap);
    overflow-y: auto;
    flex: 1;
    height: 100%;
    min-height: 0;
    padding-right: 0;
  }

  .mango-template-field-stack > .mango-section-card + .mango-section-card {
    margin-top: 0;
  }

  .mango-template-empty {
    min-height: 160px;
  }

  .mango-data-factory-config-footer {
    width: 100%;
  }

  .mango-case-config-field-card {
    flex-shrink: 0;
    box-shadow: none;
  }

  .mango-case-config-field-card--collapsed {
    padding-bottom: var(--m-card-padding);
  }

  .mango-template-item-collapsed {
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .mango-field-empty {
    min-height: 96px;
  }

  .mango-data-factory-relation-drawer {
    height: calc(100vh - 110px);
    min-height: 0;
  }

  @container (max-width: 900px) {
    .mango-data-factory-template-workbench {
      grid-template-columns: 240px minmax(0, 1fr);
    }
  }
</style>
