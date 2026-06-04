<template>
  <a-space direction="vertical" fill>
    <div v-if="showAddButton" class="mango-data-factory-case-config__toolbar">
      <a-button size="small" type="primary" @click="open()">增加</a-button>
    </div>
    <a-table
      :bordered="false"
      :columns="columns"
      :data="caseConfigList"
      :loading="loading"
      :pagination="false"
      :row-key="'id'"
      :draggable="{ type: 'handle', width: 40 }"
      :scroll="{ x: 900 }"
      size="small"
      @change="handleChange"
    >
      <template #columns>
        <a-table-column
          v-for="item of columns"
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
                  record.cleanup_strategy || record.template?.cleanup_strategy
                )
              }}
            </a-tag>
          </template>
          <template v-else-if="item.key === 'status'" #cell="{ record }">
            <a-switch
              :beforeChange="(newValue) => switchStatus(newValue, record)"
              :default-checked="record.status === 1"
            />
          </template>
          <template v-else-if="item.key === 'actions'" #cell="{ record }">
            <MangoTableActions
              :actions="[
                { label: '编辑/预览', onClick: () => open(record) },
                {
                  label: '删除',
                  danger: true,
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
    :title="form.id ? '编辑数据工厂配置' : '新增数据工厂配置'"
    width="min(1480px, 96vw)"
    :mask-closable="false"
    unmount-on-close
  >
    <div class="mango-data-factory-config-drawer">
      <a-form :model="form" layout="vertical" class="mango-data-factory-config-form">
        <div class="mango-section-card mango-data-factory-base-card">
          <a-form-item label="项目/产品" required>
            <ProjectProductSelect
              v-model="form.project_product"
              @change="onProjectProductChange"
            />
          </a-form-item>
          <a-form-item label="模块" required>
            <ProductModuleSelect
              v-model="form.module"
              :project-product-id="form.project_product"
              :auto-clear="false"
              @change="onModuleChange"
            />
          </a-form-item>
          <a-form-item label="数据名称" required>
            <a-input v-model="form.name" placeholder="例如：订单数据；用例中按“订单数据.id”取值" />
          </a-form-item>
          <a-form-item label="清理策略">
            <a-select
              v-model="form.cleanup_strategy"
              :options="cleanupStrategyOptions"
              :field-names="{ value: 'key', label: 'title' }"
              allow-clear
              placeholder="默认使用模板清理策略"
            />
          </a-form-item>
          <a-form-item label="状态">
            <a-switch
              :model-value="form.status === 1"
              @change="(value) => (form.status = value ? 1 : 0)"
            />
          </a-form-item>
        </div>

        <div class="mango-data-factory-template-workbench">
          <aside class="mango-template-selector mango-section-card">
            <div class="mango-section-title">
              <div>
                <h2>场景模板</h2>
                <p>按模板名、实体或表名搜索，选择后在右侧配置字段覆盖</p>
              </div>
              <a-tag size="small" color="arcoblue">{{ filteredTemplateList.length }}</a-tag>
            </div>
            <div v-if="currentTemplate" class="mango-template-current-card">
              <div class="mango-template-current-card__label">当前主模板</div>
              <div class="mango-template-current-card__name">{{ currentTemplate.name }}</div>
              <div class="mango-template-current-card__meta">
                {{ getTemplateEntityName(currentTemplate) }} / {{ getTemplateTableName(currentTemplate) }}
              </div>
              <div class="mango-template-current-card__foot">
                <span>{{ getTemplateItemCount(currentTemplate) }} 个关联模板</span>
                <span>{{ getTemplateCleanupText(currentTemplate) }}</span>
              </div>
              <a-button size="mini" type="text" class="mango-template-current-card__action" @click="clearSelectedTemplate">
                更换模板
              </a-button>
            </div>
            <a-input-search
              v-model="templateKeyword"
              allow-clear
              size="small"
              :placeholder="currentTemplate ? '搜索关联模板 / 实体 / 表名' : '搜索模板 / 实体 / 表名'"
            />
            <a-spin :loading="templateLoading" class="mango-template-list-spin">
              <div v-if="!form.project_product || !form.module" class="mango-empty-state mango-template-empty">
                请先选择项目/产品和模块
              </div>
              <template v-else-if="currentTemplate">
                <div v-if="!filteredTemplateItemList.length" class="mango-empty-state mango-template-empty">
                  当前主模板暂无关联模板
                </div>
                <div v-else class="mango-template-list">
                  <div
                    v-for="item in filteredTemplateItemList"
                    :key="getItemCaseKey(item)"
                    class="mango-template-option mango-template-option--relation"
                  >
                    <span class="mango-template-option__name">
                      {{ item.name || item.child_template_detail?.name || item.child_template }}
                    </span>
                    <span class="mango-template-option__meta">
                      {{ getTemplateEntityName(item.child_template_detail) }} /
                      {{ getTemplateTableName(item.child_template_detail) }}
                    </span>
                    <span class="mango-template-option__foot">
                      <span>{{ item.field || '关联模板' }}</span>
                      <span>{{ item.target_field || 'id' }}</span>
                    </span>
                  </div>
                </div>
              </template>
              <div v-else-if="!filteredTemplateList.length" class="mango-empty-state mango-template-empty">
                暂无可选场景模板
              </div>
              <div v-else class="mango-template-list">
                <button
                  v-for="template in filteredTemplateList"
                  :key="template.id"
                  type="button"
                  :class="[
                    'mango-template-option',
                    { 'mango-template-option--active': String(form.template) === String(template.id) },
                  ]"
                  @click="selectTemplate(template)"
                >
                  <span class="mango-template-option__name">{{ template.name }}</span>
                  <span class="mango-template-option__meta">
                    {{ getTemplateEntityName(template) }} / {{ getTemplateTableName(template) }}
                  </span>
                  <span class="mango-template-option__foot">
                    <span>{{ getTemplateItemCount(template) }} 个关联模板</span>
                    <span>{{ getTemplateCleanupText(template) }}</span>
                  </span>
                </button>
              </div>
            </a-spin>
          </aside>

          <section class="mango-template-editor">
            <div v-if="currentTemplate" class="mango-section-card mango-template-summary">
              <div>
                <div class="mango-template-summary__title">{{ currentTemplate.name }}</div>
                <div class="mango-template-summary__meta">
                  {{ getTemplateEntityName(currentTemplate) }} / {{ getTemplateTableName(currentTemplate) }}
                </div>
              </div>
              <a-space>
                <a-button
                  size="small"
                  type="primary"
                  :loading="previewLoading === 'form'"
                  :disabled="!form.template"
                  @click="openRelationPreview"
                >
                  预览整体流程
                </a-button>
                <a-tag size="small" color="arcoblue">{{ getTemplateItemCount(currentTemplate) }} 个关联模板</a-tag>
                <a-tag size="small">{{ getTemplateCleanupText(currentTemplate) }}</a-tag>
              </a-space>
            </div>
            <a-spin :loading="fieldLoading" class="mango-template-editor-spin">
              <a-space v-if="form.template" class="mango-template-field-stack" direction="vertical" fill>
                <section class="mango-section-card mango-case-config-field-card">
                  <div class="mango-section-title">
                    <div>
                      <h2>主模板字段</h2>
                      <p>配置主模板字段生成规则和输出字段</p>
                    </div>
                  </div>
                  <TemplateFieldConfigEditor
                    :field-overrides="mainCaseOverrides"
                    :output-config="templateOutputConfig"
                    :fields="fieldRows"
                    :generator-options="enumStore.data_factory_generator_type"
                    :dependency-template-options="dependencyTemplateOptions"
                    :load-dependency-template-options="loadDependencyTemplateOptions"
                    :preview-fields="previewResult.fields || []"
                    :loading="fieldLoading || previewLoading === 'form'"
                    :show-output="false"
                    show-preview
                    @update:field-overrides="updateMainCaseOverrides"
                    @update:output-config="updateTemplateOutputConfig"
                  />
                </section>
                <section
                  v-for="item in selectedTemplateItems"
                  :key="item.id"
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
                      <a-tag size="small">{{ itemFieldsMap[String(item.id)]?.length || 0 }} 个字段</a-tag>
                      <a-button size="mini" type="text" @click="toggleItemExpanded(item)">
                        {{ isItemExpanded(item) ? '收起' : '展开' }}
                      </a-button>
                    </a-space>
                  </div>
                  <template v-if="isItemExpanded(item)">
                    <TemplateFieldConfigEditor
                      :field-overrides="getItemCaseOverrides(item)"
                      :output-config="[]"
                      :fields="itemFieldsMap[String(item.id)] || []"
                      :generator-options="enumStore.data_factory_generator_type"
                      :dependency-template-options="dependencyTemplateOptions"
                      :load-dependency-template-options="loadDependencyTemplateOptions"
                      :preview-fields="getItemPreviewFields(item)"
                      :loading="fieldLoading || previewLoading === 'form'"
                      :show-output="false"
                      show-preview
                      @update:field-overrides="(value) => updateItemCaseOverrides(item, value)"
                    />
                  </template>
                  <div v-else class="mango-soft-panel mango-template-item-collapsed">
                    关联模板字段已收起。展开后可覆盖该模板在当前用例中的字段生成规则。
                  </div>
                </section>
              </a-space>
              <div v-else class="mango-empty-state mango-field-empty">请先选择场景模板</div>
            </a-spin>
          </section>
        </div>
      </a-form>
    </div>
    <template #footer>
      <a-space class="mango-data-factory-config-footer">
        <a-button @click="visible = false">取消</a-button>
        <a-button type="primary" :loading="saving" @click="save()">确定</a-button>
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
  import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import useUserStore from '@/store/modules/user'
  import { useEnum } from '@/store/modules/get-enum'
  import DataFactoryRelationFlow from '@/components/DataFactory/DataFactoryRelationFlow.vue'
  import TemplateFieldConfigEditor from '@/components/DataFactory/TemplateFieldConfigEditor.vue'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import {
    deleteDataFactoryCaseConfig,
    getDataFactoryCaseConfig,
    getDataFactoryField,
    getDataFactoryTemplate,
    postDataFactoryCaseConfig,
    postDataFactoryCaseConfigPreview,
    putDataFactoryCaseConfig,
    putDataFactoryCaseConfigSort,
  } from '@/api/data-factory'
  import type {
    DataFactoryFieldOverrides,
    DataFactoryFieldRule,
    DataFactoryOutputConfig,
  } from '@/types/data-factory'

  const props = withDefaults(
    defineProps<{
      caseId?: string | number | null
      projectProductId?: string | number | null
      sourceType: number
      showAddButton?: boolean
    }>(),
    {
      caseId: null,
      projectProductId: null,
      showAddButton: false,
    }
  )

  const enumStore = useEnum()
  const userStore = useUserStore()
  const TEMPLATE_USAGE_CASE = 1

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
      width: 170,
      align: 'center',
      fixed: 'right',
    },
  ]

  const caseConfigList = ref<any[]>([])
  const templateList = ref<any[]>([])
  const templateKeyword = ref('')
  const expandedTemplateItemKeys = ref<string[]>([])
  const fieldRows = ref<DataFactoryFieldRule[]>([])
  const itemFieldsMap = ref<Record<string, DataFactoryFieldRule[]>>({})
  const dependencyTemplateOptions = ref<Record<string, any[]>>({})
  const templateOutputConfig = ref<DataFactoryOutputConfig>([])
  const loading = ref(false)
  const templateLoading = ref(false)
  const fieldLoading = ref(false)
  const saving = ref(false)
  const visible = ref(false)
  const relationPreviewVisible = ref(false)
  const previewLoading = ref<any>(null)
  const deleteLoading = ref<number | null>(null)
  const previewResult = ref<any>({})
  const previewTimerId = ref<number>()

  const form = reactive<{
    id: number | null
    source_type: number
    source_id: string | number | null
    project_product: string | number | null
    module: string | number | null
    template: number | null
    name: string
    sort: number
    field_overrides: DataFactoryFieldOverrides
    cleanup_strategy: number | null
    status: number
    stage: number
  }>({
    id: null,
    source_type: props.sourceType,
    source_id: props.caseId,
    project_product: props.projectProductId,
    module: null,
    template: null,
    name: '',
    sort: 0,
    field_overrides: {},
    cleanup_strategy: null,
    status: 1,
    stage: 1,
  })

  const cleanupStrategyOptions = computed(() => [
    { key: null, title: '使用模板默认策略' },
    ...(enumStore.data_factory_cleanup_strategy || []),
  ])
  const currentTemplate = computed(() =>
    templateList.value.find((item) => String(item.id) === String(form.template))
  )
  const filteredTemplateList = computed(() => {
    const keyword = templateKeyword.value.trim().toLowerCase()
    if (!keyword) {
      return templateList.value
    }
    return templateList.value.filter((item) => {
      return [
        item.name,
        getTemplateEntityName(item),
        getTemplateTableName(item),
        item.description,
      ]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(keyword))
    })
  })
  const selectedTemplateItems = computed(() => currentTemplate.value?.items || [])
  const filteredTemplateItemList = computed(() => {
    const keyword = templateKeyword.value.trim().toLowerCase()
    if (!keyword) {
      return selectedTemplateItems.value
    }
    return selectedTemplateItems.value.filter((item: any) => {
      const template = item.child_template_detail || {}
      return [
        item.name,
        item.child_template,
        item.field,
        item.target_field,
        template.name,
        getTemplateEntityName(template),
        getTemplateTableName(template),
      ]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(keyword))
    })
  })
  const isSceneOverrideShape = computed(
    () =>
      Object.prototype.hasOwnProperty.call(form.field_overrides || {}, '__main__') ||
      Object.prototype.hasOwnProperty.call(form.field_overrides || {}, '__items__')
  )
  const mainCaseOverrides = computed(() =>
    isSceneOverrideShape.value ? form.field_overrides?.__main__ || {} : form.field_overrides || {}
  )

  function enumTitle(options: any[] = [], value: any) {
    return options.find((item) => item.key === value)?.title || value || '-'
  }

  function getTemplateEntityName(template: any) {
    return template?.entity?.name || template?.entity_name || template?.entity?.id || template?.entity || '-'
  }

  function getTemplateTableName(template: any) {
    return template?.entity?.table_name || template?.table_name || '-'
  }

  function getTemplateItemCount(template: any) {
    return template?.items?.length || 0
  }

  function getTemplateCleanupText(template: any) {
    return enumTitle(
      enumStore.data_factory_cleanup_strategy,
      template?.cleanup_strategy ?? form.cleanup_strategy
    )
  }

  function getOptionId(value: any) {
    if (Array.isArray(value)) {
      return value[value.length - 1] ?? null
    }
    return value?.id ?? value
  }

  function refresh() {
    if (!props.caseId || !props.sourceType) {
      caseConfigList.value = []
      return
    }
    loading.value = true
    getDataFactoryCaseConfig({ source_type: props.sourceType, source_id: props.caseId })
      .then((res) => {
        caseConfigList.value = res.data || []
      })
      .finally(() => {
        loading.value = false
      })
  }

  function handleChange(_data: any[]) {
    caseConfigList.value = _data.map((item, index) => ({
      ...item,
      sort: index,
    }))
    putDataFactoryCaseConfigSort({
      source_type: props.sourceType,
      case_sort_list: caseConfigList.value.map((item, index) => ({
        id: item.id,
        sort: index,
      })),
    })
      .then((res) => {
        Message.success(res.msg)
      })
      .catch(() => {
        refresh()
      })
  }

  function loadTemplates() {
    const projectProduct = getOptionId(form.project_product || props.projectProductId)
    const module = getOptionId(form.module)
    if (!projectProduct || !module) {
      templateList.value = []
      return Promise.resolve()
    }
    const query: any = {
      page: 1,
      pageSize: 9999,
      project_product: projectProduct,
      module,
    }
    templateLoading.value = true
    return getDataFactoryTemplate(query)
      .then((res) => {
        templateList.value = (res.data || []).filter((template: any) => {
          const usageScope = Number(template.usage_scope || TEMPLATE_USAGE_CASE)
          return usageScope === TEMPLATE_USAGE_CASE || String(template.id) === String(form.template)
        })
      })
      .finally(() => {
        templateLoading.value = false
      })
  }

  function resetForm(record: any = null) {
    const template = record?.template || {}
    form.id = record?.id || null
    form.source_type = props.sourceType
    form.source_id = props.caseId
    form.project_product =
      template?.project_product?.id || template?.project_product || props.projectProductId || null
    form.module = template?.module?.id || template?.module || null
    form.template = template?.id || record?.template || null
    form.name = record?.name || ''
    form.sort = record?.sort ?? caseConfigList.value.length
    form.field_overrides = record?.field_overrides || {}
    form.cleanup_strategy = record?.cleanup_strategy ?? null
    form.status = record?.status ?? 1
    form.stage = record?.stage || 1
    templateOutputConfig.value = record?.template?.output_config || []
    fieldRows.value = []
    itemFieldsMap.value = {}
    expandedTemplateItemKeys.value = []
    previewResult.value = {}
  }

  function open(record: any = null) {
    resetForm(record)
    templateKeyword.value = ''
    visible.value = true
    if (form.project_product && form.module) {
      loadTemplates().then(() => {
        if (form.template) {
          loadFields()
          scheduleCasePreview()
        }
      })
    } else {
      templateList.value = []
    }
  }

  function onProjectProductChange() {
    form.module = null
    form.template = null
    form.field_overrides = {}
    templateKeyword.value = ''
    templateOutputConfig.value = []
    templateList.value = []
    fieldRows.value = []
    itemFieldsMap.value = {}
    expandedTemplateItemKeys.value = []
    previewResult.value = {}
  }

  function onModuleChange() {
    form.template = null
    form.field_overrides = {}
    templateKeyword.value = ''
    templateOutputConfig.value = []
    fieldRows.value = []
    itemFieldsMap.value = {}
    expandedTemplateItemKeys.value = []
    previewResult.value = {}
    loadTemplates()
  }

  function selectTemplate(template: any) {
    if (String(form.template) === String(template?.id)) {
      return
    }
    form.template = template?.id || null
    onTemplateChange()
  }

  function clearSelectedTemplate() {
    form.template = null
    form.field_overrides = {}
    templateOutputConfig.value = []
    fieldRows.value = []
    itemFieldsMap.value = {}
    expandedTemplateItemKeys.value = []
    templateKeyword.value = ''
  }

  function onTemplateChange() {
    const template = templateList.value.find((item) => item.id === form.template)
    if (!form.name && template?.name) {
      form.name = template.name
    }
    templateOutputConfig.value = template?.output_config || []
    form.field_overrides = normalizeSceneOverrides(template?.field_overrides || {})
    itemFieldsMap.value = {}
    expandedTemplateItemKeys.value = []
    previewResult.value = {}
    loadFields()
    scheduleCasePreview()
  }

  function loadFields() {
    const template = templateList.value.find((item) => item.id === form.template)
    const entityId = template?.entity?.id || template?.entity
    if (!entityId) {
      fieldRows.value = []
      return
    }
    fieldLoading.value = true
    getDataFactoryField({ entity: entityId })
      .then((res) => {
        fieldRows.value = res.data || []
        preloadDependencyTemplateOptions()
        return loadItemFields()
      })
      .finally(() => {
        fieldLoading.value = false
      })
  }

  function loadDependencyTemplateOptions(row: DataFactoryFieldRule) {
    const dependencyEntityId = row.generator_config?.dependency_entity_id
    const projectProduct = getOptionId(form.project_product || props.projectProductId)
    if (!dependencyEntityId || !projectProduct) {
      return
    }
    const cacheKey = String(dependencyEntityId)
    if (dependencyTemplateOptions.value[cacheKey]) {
      return
    }
    getDataFactoryTemplate({
      project_product: projectProduct,
      entity: dependencyEntityId,
      page: 1,
      pageSize: 9999,
    }).then((res) => {
      dependencyTemplateOptions.value = {
        ...dependencyTemplateOptions.value,
        [cacheKey]: (res.data || []).map((template: any) => ({
          label: template.name,
          value: template.id,
        })),
      }
    })
  }

  function preloadDependencyTemplateOptions() {
    fieldRows.value
      .filter((row: any) => row.generator_config?.dependency_entity_id)
      .forEach((row) => loadDependencyTemplateOptions(row))
  }

  function normalizeSceneOverrides(overrides: any) {
    if (
      Object.prototype.hasOwnProperty.call(overrides || {}, '__main__') ||
      Object.prototype.hasOwnProperty.call(overrides || {}, '__items__')
    ) {
      return {
        __main__: overrides.__main__ || {},
        __items__: overrides.__items__ || {},
      }
    }
    return {
      __main__: overrides || {},
      __items__: {},
    }
  }

  function updateMainCaseOverrides(value: DataFactoryFieldOverrides) {
    form.field_overrides = {
      __main__: value,
      __items__: form.field_overrides?.__items__ || {},
    }
    scheduleCasePreview()
  }

  function updateTemplateOutputConfig(value: DataFactoryOutputConfig) {
    templateOutputConfig.value = value
  }

  function getItemCaseKey(item: any) {
    return String(item.id || item.name || item.child_template)
  }

  function getItemTemplateName(item: any) {
    return item.name || item.child_template_detail?.name || item.child_template || '-'
  }

  function isItemExpanded(item: any) {
    return expandedTemplateItemKeys.value.includes(getItemCaseKey(item))
  }

  function toggleItemExpanded(item: any) {
    const key = getItemCaseKey(item)
    expandedTemplateItemKeys.value = isItemExpanded(item)
      ? expandedTemplateItemKeys.value.filter((itemKey) => itemKey !== key)
      : [...expandedTemplateItemKeys.value, key]
  }

  function getItemCaseOverrides(item: any) {
    return form.field_overrides?.__items__?.[getItemCaseKey(item)] || {}
  }

  function updateItemCaseOverrides(item: any, value: DataFactoryFieldOverrides) {
    form.field_overrides = {
      __main__: mainCaseOverrides.value,
      __items__: {
        ...(form.field_overrides?.__items__ || {}),
        [getItemCaseKey(item)]: value,
      },
    }
    scheduleCasePreview()
  }

  function getItemPreviewFields(item: any) {
    const itemKey = getItemCaseKey(item)
    const itemPreview = (previewResult.value?.items || []).find((previewItem: any) =>
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

  function loadItemFields() {
    const tasks = selectedTemplateItems.value.map((item: any) => {
      const entityId = item.child_template_detail?.entity?.id || item.child_template_detail?.entity
      if (!entityId) {
        return Promise.resolve()
      }
      return getDataFactoryField({ entity: entityId }).then((res) => {
        itemFieldsMap.value = {
          ...itemFieldsMap.value,
          [String(item.id)]: res.data || [],
        }
      })
    })
    return Promise.all(tasks)
  }

  async function save() {
    if (!form.template) {
      Message.error('请选择场景模板')
      return false
    }
    if (!form.name) {
      Message.error('请填写数据名称')
      return false
    }
    if (!props.caseId) {
      Message.error('用例ID不能为空')
      return false
    }
    saving.value = true
    const payload = {
      id: form.id,
      source_type: props.sourceType,
      source_id: props.caseId,
      template: form.template,
      name: form.name,
      sort: form.sort,
      field_overrides: form.field_overrides,
      cleanup_strategy: (form.cleanup_strategy as any) === '' ? null : form.cleanup_strategy,
      status: form.status,
      stage: form.stage,
    }
    try {
      const res = payload.id
        ? await putDataFactoryCaseConfig(payload)
        : await postDataFactoryCaseConfig(payload)
      Message.success(res.msg)
      visible.value = false
      refresh()
      return true
    } catch (error) {
      return false
    } finally {
      saving.value = false
    }
  }

  function switchStatus(newValue: boolean, record: any) {
    return new Promise<boolean>((resolve, reject) => {
      putDataFactoryCaseConfig({
        id: record.id,
        source_type: props.sourceType,
        source_id: props.caseId,
        template: record.template?.id || record.template,
        name: record.name,
        sort: record.sort,
        field_overrides: record.field_overrides || {},
        cleanup_strategy: record.cleanup_strategy ?? null,
        status: newValue ? 1 : 0,
        stage: record.stage || 1,
      })
        .then((res) => {
          Message.success(res.msg)
          refresh()
          resolve(res.code === 200)
        })
        .catch(reject)
    })
  }

  function deleteConfig(record: any) {
    Modal.confirm({
      title: '提示',
      content: '确定要删除这个数据工厂配置吗？',
      cancelText: '取消',
      okText: '删除',
      onBeforeOk: () => {
        deleteLoading.value = record.id
        return deleteDataFactoryCaseConfig(record.id)
          .then((res) => {
            Message.success(res.msg)
            refresh()
          })
          .finally(() => {
            deleteLoading.value = null
          })
      },
    })
  }

  function scheduleCasePreview() {
    if (previewTimerId.value) {
      window.clearTimeout(previewTimerId.value)
    }
    previewTimerId.value = window.setTimeout(() => {
      loadCasePreview()
    }, 360)
  }

  function loadCasePreview() {
    const templateId = form.template
    if (!templateId) {
      previewResult.value = {}
      return
    }
    if (userStore.selected_environment == null) {
      previewResult.value = {}
      return
    }
    previewLoading.value = 'form'
    postDataFactoryCaseConfigPreview({
      source_type: props.sourceType,
      source_id: props.caseId,
      template_id: templateId,
      field_overrides: form.field_overrides || {},
      test_env: userStore.selected_environment,
    })
      .then((res) => {
        previewResult.value = res.data || {}
      })
      .finally(() => {
        previewLoading.value = null
      })
  }

  watch(
    () => [props.caseId, props.sourceType],
    () => {
      refresh()
    }
  )

  watch(
    () => props.projectProductId,
    () => {
      if (!visible.value) {
        return
      }
      form.project_product = props.projectProductId || null
      onProjectProductChange()
    }
  )

  onMounted(() => {
    refresh()
  })

  onBeforeUnmount(() => {
    if (previewTimerId.value) {
      window.clearTimeout(previewTimerId.value)
    }
  })

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

  .mango-data-factory-config-drawer {
    height: calc(100vh - 118px);
    min-height: 0;
  }

  .mango-data-factory-config-form {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
    gap: 12px;
  }

  .mango-data-factory-base-card {
    display: grid;
    padding: 12px;
    gap: 8px 12px;
    grid-template-columns: minmax(180px, 1.2fr) minmax(160px, 1fr) minmax(220px, 1.4fr) minmax(160px, 1fr) 80px;
  }

  .mango-data-factory-base-card :deep(.arco-form-item) {
    margin-bottom: 0;
  }

  .mango-data-factory-template-workbench {
    display: grid;
    flex: 1;
    min-height: 0;
    gap: 12px;
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
    padding: 12px;
    gap: 10px;
  }

  .mango-template-list-spin {
    display: block;
    flex: 1;
    min-height: 0;
  }

  .mango-template-list-spin :deep(.arco-spin),
  .mango-template-list-spin :deep(.arco-spin-children) {
    height: 100%;
    min-height: 0;
  }

  .mango-template-list {
    display: flex;
    overflow: auto;
    flex-direction: column;
    height: 100%;
    min-height: 0;
    padding-right: 2px;
    gap: 8px;
  }

  .mango-template-current-card {
    flex-shrink: 0;
    padding: 10px 11px;
    border: 1px solid var(--m-primary-border);
    border-radius: var(--m-radius-md);
    background: color-mix(in srgb, var(--m-primary) 7%, var(--m-surface));
    box-shadow: var(--m-form-focus-shadow);
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

  .mango-template-current-card__action {
    margin-top: 6px;
    padding: 0;
  }

  .mango-template-option {
    display: flex;
    align-items: stretch;
    flex-direction: column;
    width: 100%;
    padding: 10px 11px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface-soft);
    color: var(--m-text);
    cursor: pointer;
    gap: 5px;
    text-align: left;
    transition: border-color 0.2s ease, background 0.2s ease, box-shadow 0.2s ease;
  }

  .mango-template-option:hover {
    border-color: color-mix(in srgb, var(--m-primary) 28%, var(--m-border));
    background: var(--m-surface);
  }

  .mango-template-option--active {
    border-color: var(--m-primary);
    background: color-mix(in srgb, var(--m-primary) 7%, var(--m-surface));
    box-shadow: var(--m-form-focus-shadow);
  }

  .mango-template-option--relation {
    cursor: default;
  }

  .mango-template-option--relation:hover {
    border-color: var(--m-border);
    background: var(--m-surface-soft);
  }

  .mango-template-option__name,
  .mango-template-option__meta,
  .mango-template-option__foot {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-template-option__name {
    font-size: 13px;
    font-weight: 600;
    line-height: 19px;
  }

  .mango-template-option__meta,
  .mango-template-option__foot {
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .mango-template-option__foot {
    display: flex;
    justify-content: space-between;
    gap: 8px;
  }

  .mango-template-editor {
    display: flex;
    overflow: hidden;
    flex-direction: column;
    gap: 10px;
  }

  .mango-template-summary {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 11px 12px;
    gap: 12px;
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

  .mango-template-editor-spin :deep(.arco-spin),
  .mango-template-editor-spin :deep(.arco-spin-children) {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
  }

  .mango-template-editor-spin :deep(.arco-spin-children) {
    overflow: hidden;
  }

  .mango-template-field-stack {
    overflow-y: auto;
    flex: 1;
    height: 100%;
    min-height: 0;
    padding-right: 2px;
  }

  .mango-template-field-stack :deep(.arco-space-item) {
    flex-shrink: 0;
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
    padding-bottom: 12px;
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

  @media (max-width: 1px) {
    .mango-data-factory-base-card {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .mango-data-factory-template-workbench {
      grid-template-columns: 1fr;
    }

  }
</style>
