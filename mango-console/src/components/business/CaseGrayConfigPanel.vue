<template>
  <div class="mango-case-gray-panel">
    <div class="mango-case-gray-panel__filters">
      <a-form layout="inline" @keyup.enter="loadFeatures">
        <a-form-item label="项目/产品">
          <ProjectProductSelect v-model="query.projectProduct" @change="onSearchProjectProductChange" />
        </a-form-item>
        <a-form-item label="模块">
          <ProductModuleSelect
            v-model="query.module"
            :project-product-id="normalizeProductId(query.projectProduct)"
            :auto-clear="false"
            placeholder="请选择模块"
            @change="onSearch" data-testid="qa-components-business-casegrayconfigpanel-productmoduleselect-请选择模块"
          />
        </a-form-item>
        <a-form-item label="关键词">
          <a-input
            v-model="query.keyword"
            allow-clear
            placeholder="编号/名称/Key"
            @blur="onSearch"
            @clear="onSearch" data-testid="qa-components-business-casegrayconfigpanel-input-编号-名称-key"
          />
        </a-form-item>
      </a-form>
    </div>

    <div class="mango-case-gray-panel__table-wrap">
      <a-table
        :bordered="false"
        class="mango-case-gray-panel__table"
        :columns="columns"
        :data="tableFeatures"
        :loading="loading || saving"
        :pagination="false"
        :row-selection="{ selectedRowKeys, showCheckedAll: true, fixed: true, width: 48 }"
        :scroll="{ x: 1280 }"
        row-key="id"
        size="small"
        @selection-change="onSelectionChange"
      >
        <template #columns>
          <a-table-column v-for="item in columns" :key="item.key" v-bind="item">
            <template v-if="item.key === 'project_product'" #cell="{ record }">
              {{ formatProjectProductPath(record.project_product) }}
            </template>
            <template v-else-if="item.key === 'module'" #cell="{ record }">
              {{ record.module?.name || '-' }}
            </template>
            <template v-else-if="item.key === 'config_type'" #cell="{ record }">
              <a-tag size="small">{{ configTypeText(record.config_type) }}</a-tag>
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <MangoTableActions
                :actions="[
                  { label: '预览', loading: previewDrawer.loading && previewDrawer.record?.id === record.id, onClick: () => openPreviewDrawer(record) },
                ]"
              />
            </template>
          </a-table-column>
        </template>
      </a-table>
    </div>
    <div class="mango-case-gray-panel__pagination">
      <a-pagination
        v-model:current="pagination.page"
        v-model:page-size="pagination.pageSize"
        :page-size-options="[10, 20, 50, 100]"
        :total="unselectedFilteredFeatures.length"
        show-total
        show-page-size
        size="small"
      />
    </div>

    <BaseSidePanel
      :visible="previewDrawer.visible"
      :title="previewDrawer.title"
      :width="960"
      cancel-button-text="关闭"
      @update:visible="(value) => (previewDrawer.visible = value)"
      @cancel="previewDrawer.visible = false"
    >
      <template #default>
        <div class="mango-case-gray-preview">
          <section class="mango-case-gray-preview__readonly">
            <div class="mango-case-gray-preview__title">灰度配置</div>
            <a-descriptions :column="2" size="small" bordered>
              <a-descriptions-item label="灰度编号">{{ previewDrawer.record?.gray_code || '-' }}</a-descriptions-item>
              <a-descriptions-item label="灰度名称">{{ previewDrawer.record?.name || '-' }}</a-descriptions-item>
              <a-descriptions-item label="灰度Key">{{ previewDrawer.record?.feature_key || '-' }}</a-descriptions-item>
              <a-descriptions-item label="类型">{{ configTypeText(previewDrawer.record?.config_type) }}</a-descriptions-item>
              <a-descriptions-item label="项目/产品">{{ formatProjectProductPath(previewDrawer.record?.project_product) }}</a-descriptions-item>
              <a-descriptions-item label="模块">{{ previewDrawer.record?.module?.name || '-' }}</a-descriptions-item>
              <a-descriptions-item label="配置文件">{{ previewDrawer.record?.yaml_file?.file_path || '-' }}</a-descriptions-item>
              <a-descriptions-item label="业务数据库">{{ previewDrawer.record?.database?.name || '-' }}</a-descriptions-item>
            </a-descriptions>
            <div v-if="previewPathConfig.length" class="mango-case-gray-preview__paths">
              <div class="mango-case-gray-preview__sub-title">路径配置</div>
              <div v-for="(item, index) in previewPathConfig" :key="index" class="mango-case-gray-preview__path-row">
                <span>{{ item.path }}</span>
                <span>{{ item.value_type }}</span>
                <span>{{ item.original_value || '-' }}</span>
                <span>{{ item.value || '-' }}</span>
              </div>
            </div>
          </section>
          <a-form layout="inline" :model="previewDrawer">
            <a-form-item>
              <a-button size="small" type="primary" :loading="previewDrawer.loading" @click="generatePreview" data-testid="qa-components-business-casegrayconfigpanel-button-重新预览">
                重新预览
              </a-button>
            </a-form-item>
          </a-form>
          <div class="mango-case-gray-preview__summary">{{ previewDrawer.summary }}</div>
          <section class="mango-case-gray-preview__section">
            <div class="mango-case-gray-preview__title">原文</div>
            <CodeEditor
              v-model="previewDrawer.beforeText"
              readonly
              placeholder="暂无原文"
              :code-style="{ height: 'calc((100vh - 300px) / 2)' }"
            />
          </section>
          <section class="mango-case-gray-preview__section">
            <div class="mango-case-gray-preview__title">修改后</div>
            <CodeEditor
              v-model="previewDrawer.afterText"
              readonly
              placeholder="暂无修改内容"
              :code-style="{ height: 'calc((100vh - 300px) / 2)' }"
            />
          </section>
        </div>
      </template>
      <template #footer-buttons>
        <a-button @click="previewDrawer.visible = false" data-testid="qa-components-business-casegrayconfigpanel-button-关闭">关闭</a-button>
      </template>
    </BaseSidePanel>
  </div>
</template>

<script setup lang="ts">
  import { Message } from '@arco-design/web-vue'
  import { computed, onMounted, reactive, ref, watch } from 'vue'
  import {
    getGrayCaseConfig,
    getGrayFeature,
    postGrayFeaturePreview,
    postGrayCaseConfigReplaceScope,
  } from '@/api/gray'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import CodeEditor from '@/components/editors/CodeEditor.vue'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import { formatProjectProductPath, getOptionId } from '@/utils/business-format'

  const props = withDefaults(defineProps<{
    caseType: number
    scope: string
    apiCaseId?: number | string
    uiCaseId?: number | string
    apiCaseDetailedId?: number | string
    apiCaseDetailedParameterId?: number | string
    projectProductId?: number | string
    testEnv?: number | string
    autoLoad?: boolean
  }>(), {
    autoLoad: true,
  })

  const loading = ref(false)
  const saving = ref(false)
  const features = ref<any[]>([])
  const selectedFeatureMap = ref<Map<string, any>>(new Map())
  const selectedRowKeys = ref<Array<number | string>>([])
  const selectedFeatureIds = ref<Set<string>>(new Set())
  const query = reactive({
    keyword: '',
    projectProduct: undefined as number | string | undefined,
    module: undefined as number | string | undefined,
  })
  const pagination = reactive({
    page: 1,
    pageSize: 10,
  })
  const previewDrawer = reactive<any>({
    visible: false,
    title: '',
    record: null,
    action: 'enable',
    loading: false,
    hasPreview: false,
    beforeText: '',
    afterText: '',
    summary: '',
  })

  const columns = [
    { title: '灰度编号', key: 'gray_code', dataIndex: 'gray_code', width: 140, ellipsis: true, tooltip: true, align: 'left' },
    { title: '灰度名称', key: 'name', dataIndex: 'name', width: 200, ellipsis: true, tooltip: true, align: 'left' },
    { title: '灰度Key', key: 'feature_key', dataIndex: 'feature_key', width: 280, ellipsis: true, tooltip: true, align: 'left' },
    { title: '项目/产品', key: 'project_product', dataIndex: 'project_product', width: 210, align: 'left' },
    { title: '模块', key: 'module', dataIndex: 'module', width: 120, align: 'left' },
    { title: '类型', key: 'config_type', dataIndex: 'config_type', width: 90, align: 'center' },
    { title: '操作', key: 'actions', dataIndex: 'actions', width: 120, fixed: 'right', align: 'center' },
  ]
  const configTypeOptions = [
    { label: 'YAML', value: 1 },
    { label: 'SQL', value: 2 },
    { label: '函数代码', value: 3 },
  ]
  const previewPathConfig = computed(() => {
    const value = previewDrawer.record?.path_config
    return Array.isArray(value) ? value : []
  })

  const filteredFeatures = computed(() => {
    const keyword = String(query.keyword || '').trim().toLowerCase()
    return features.value.filter((item) => {
      const productId = normalizeProductId(query.projectProduct)
      if (productId && String(item.project_product?.id || item.project_product) !== String(productId)) return false
      if (query.module && String(item.module?.id) !== String(query.module)) return false
      if (!keyword) return true
      return [item.gray_code, item.name, item.feature_key]
        .some((value) => String(value || '').toLowerCase().includes(keyword))
    })
  })
  const selectedFeatures = computed(() => {
    const featureMap = new Map<string, any>()
    features.value.forEach((item) => featureMap.set(String(item.id), item))
    selectedFeatureMap.value.forEach((item, key) => featureMap.set(key, item))
    return Array.from(selectedFeatureIds.value)
      .map((id) => featureMap.get(String(id)))
      .filter(Boolean)
  })
  const unselectedFilteredFeatures = computed(() => {
    return filteredFeatures.value.filter((item) => !selectedFeatureIds.value.has(String(item.id)))
  })
  const pagedUnselectedFeatures = computed(() => {
    const start = (pagination.page - 1) * pagination.pageSize
    return unselectedFilteredFeatures.value.slice(start, start + pagination.pageSize)
  })
  const tableFeatures = computed(() => {
    return [...selectedFeatures.value, ...pagedUnselectedFeatures.value]
  })

  const scopePayload = computed(() => {
    const payload: any = {
      case_type: props.caseType,
      scope: props.scope,
    }
    if (props.apiCaseId) payload.api_case = props.apiCaseId
    if (props.uiCaseId) payload.ui_case = props.uiCaseId
    if (props.apiCaseDetailedId) payload.api_case_detailed = props.apiCaseDetailedId
    if (props.apiCaseDetailedParameterId) {
      payload.api_case_detailed_parameter = props.apiCaseDetailedParameterId
    }
    return payload
  })

  function normalizeProductId(value: any) {
    return getOptionId(value)
  }

  function configTypeText(value: any) {
    return configTypeOptions.find((item) => Number(item.value) === Number(value))?.label || '-'
  }

  async function loadFeatures() {
    const queryData: any = { status: 1, page: 1, pageSize: 10000 }
    const res = await getGrayFeature(queryData)
    features.value = res.data || []
    normalizeCurrentPage()
  }

  async function loadConfigs() {
    if (!props.caseType || !props.scope) return
    const res = await getGrayCaseConfig({ ...scopePayload.value, page: 1, pageSize: 10000 })
    const nextMap = new Map<string, any>()
    const ids = (res.data || [])
      .map((item: any) => {
        const feature = item.gray_feature
        const featureId = feature?.id || feature
        if (feature?.id) {
          nextMap.set(String(feature.id), feature)
        }
        return featureId
      })
      .filter((value: any) => value !== undefined && value !== null)
      .map((value: any) => String(value))
    selectedFeatureMap.value = nextMap
    selectedFeatureIds.value = new Set(ids)
    syncSelectedRowKeys()
  }

  async function loadAll() {
    loading.value = true
    try {
      await Promise.all([loadFeatures(), loadConfigs()])
      syncSelectedRowKeys()
    } finally {
      loading.value = false
    }
  }

  function syncSelectedRowKeys() {
    const featureMap = new Map<string, any>()
    features.value.forEach((item) => featureMap.set(String(item.id), item))
    selectedFeatureMap.value.forEach((item, key) => featureMap.set(key, item))
    selectedRowKeys.value = Array.from(selectedFeatureIds.value).map((id) => featureMap.get(String(id))?.id ?? id)
  }

  function onSearch() {
    pagination.page = 1
    normalizeCurrentPage()
    syncSelectedRowKeys()
  }

  function onSearchProjectProductChange() {
    query.module = undefined
    onSearch()
  }

  async function onSelectionChange(keys: Array<number | string>) {
    if (loading.value || saving.value) return
    const visibleIds = new Set(tableFeatures.value.map((item) => String(item.id)))
    const nextIds = new Set(
      Array.from(selectedFeatureIds.value).filter((item) => !visibleIds.has(String(item)))
    )
    const checkedKeys = keys || []
    checkedKeys.forEach((item) => nextIds.add(String(item)))
    selectedFeatureIds.value = nextIds
    syncSelectedRowKeys()
    await saveSelection()
  }

  function normalizeCurrentPage() {
    const maxPage = Math.max(1, Math.ceil(unselectedFilteredFeatures.value.length / pagination.pageSize))
    if (pagination.page > maxPage) {
      pagination.page = maxPage
    }
  }

  async function saveSelection() {
    saving.value = true
    try {
      const nextSelectedFeatures = selectedFeatures.value
      await postGrayCaseConfigReplaceScope({
        scope: scopePayload.value,
        items: nextSelectedFeatures.map((item, index) => ({
          gray_feature: item.id,
          target_value: '',
          action: 'enable',
          restore_after_execute: true,
          wait_seconds: 0,
          sort: index,
          status: 1,
        })),
      })
      Message.success('灰度绑定已保存')
    } catch (error) {
      console.log(error)
      await loadConfigs()
      syncSelectedRowKeys()
    } finally {
      saving.value = false
    }
  }

  async function openPreviewDrawer(record: any) {
    previewDrawer.visible = true
    previewDrawer.record = record
    previewDrawer.title = `${record.name || '-'} 预览`
    previewDrawer.action = 'enable'
    previewDrawer.beforeText = ''
    previewDrawer.afterText = ''
    previewDrawer.summary = ''
    previewDrawer.hasPreview = false
    await generatePreview()
  }

  async function generatePreview() {
    const record = previewDrawer.record
    if (!record?.id) return
    previewDrawer.loading = true
    try {
      const res = await postGrayFeaturePreview(previewPayload())
      previewDrawer.beforeText = res.data?.before_text || JSON.stringify(res.data?.before_snapshot ?? {}, null, 2)
      previewDrawer.afterText = res.data?.after_text || JSON.stringify(res.data?.after_snapshot ?? {}, null, 2)
      previewDrawer.summary = [
        `Key：${res.data?.feature_key || record.feature_key || '-'}`,
        `解析值：${res.data?.resolved_target_value ?? '-'}`,
        res.data?.file_path || record.yaml_file?.file_path || record.database?.name || '',
      ].filter(Boolean).join(' / ')
      previewDrawer.hasPreview = true
    } finally {
      previewDrawer.loading = false
    }
  }

  function previewPayload() {
    return {
      feature_id: previewDrawer.record?.id,
      target_value: '',
      action: previewDrawer.action,
      variable_source: props.caseType === 2 ? 'ui' : 'api',
      variable_test_env: props.testEnv,
      path_config: previewDrawer.record?.path_config || [],
    }
  }

  watch(
    () => [
      props.caseType,
      props.scope,
      props.apiCaseId,
      props.uiCaseId,
      props.apiCaseDetailedId,
      props.apiCaseDetailedParameterId,
      props.projectProductId,
    ],
    () => {
      if (props.autoLoad) loadAll()
    }
  )

  watch(
    () => props.projectProductId,
    (value) => {
      query.projectProduct = normalizeProductId(value) as any
    },
    { immediate: true }
  )

  watch(
    () => [pagination.pageSize, unselectedFilteredFeatures.value.length],
    () => normalizeCurrentPage()
  )

  onMounted(() => {
    if (props.autoLoad) loadAll()
  })

  defineExpose({ loadAll })
</script>

<style scoped>
  .mango-case-gray-panel {
    display: flex;
    flex-direction: column;
    gap: var(--m-page-gap);
    padding-top: var(--m-page-gap);
  }

  .mango-case-gray-panel__filters {
    display: block;
    padding-bottom: 0;
  }

  .mango-case-gray-panel__filters :deep(.arco-form-layout-inline) {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-start;
    width: 100%;
    gap: var(--m-page-gap);
  }

  .mango-case-gray-panel__filters :deep(.arco-form-item) {
    flex: 1 1 230px;
    min-width: 0;
    margin: 0;
  }

  .mango-case-gray-panel__filters :deep(.arco-form-item-label-col) {
    flex: none;
  }

  .mango-case-gray-panel__filters :deep(.arco-form-item-wrapper) {
    flex: 1 1 0;
    min-width: 0;
  }

  .mango-case-gray-panel__filters :deep(.arco-select),
  .mango-case-gray-panel__filters :deep(.arco-cascader),
  .mango-case-gray-panel__filters :deep(.arco-input-wrapper) {
    width: 100%;
    min-width: 0;
  }

  .mango-case-gray-panel__table-wrap {
    margin-top: 4px;
  }

  .mango-case-gray-panel__pagination {
    display: flex;
    justify-content: flex-end;
  }

  .mango-case-gray-preview {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .mango-case-gray-preview__readonly {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .mango-case-gray-preview__title {
    color: var(--m-text);
    font-size: 13px;
    font-weight: 600;
    line-height: 22px;
  }

  .mango-case-gray-preview__sub-title {
    color: var(--m-text-2);
    font-size: 12px;
    line-height: 20px;
  }

  .mango-case-gray-preview__paths {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .mango-case-gray-preview__path-row {
    display: grid;
    grid-template-columns: minmax(160px, 1.4fr) 88px minmax(120px, 1fr) minmax(160px, 1.2fr);
    gap: 8px;
    align-items: center;
    min-height: 32px;
    padding: 0 8px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-sm);
    color: var(--m-text-2);
    font-size: 12px;
  }

  .mango-case-gray-preview__summary {
    color: var(--m-text-2);
    font-size: 12px;
    line-height: 20px;
  }

  .mango-case-gray-preview__section {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
</style>
