<template>
  <TableBody class="mango-template-preview-page mango-detail-workbench-page">
    <template #header>
      <div class="mango-detail-toolbar">
        <div class="mango-detail-heading">
          <div class="mango-detail-title">{{ previewTitle }}</div>
          <div class="mango-detail-subtitle"> {{ canDebugText }} </div>
        </div>
        <a-space class="mango-detail-actions" wrap>
          <a-button
            size="small"
            type="primary"
            :loading="saving"
            :disabled="writeBusy || templateLoading || templateForm.id === null"
            @click="saveTemplateConfig"
            data-testid="qa-views-data-factory-template-preview-button-保存字段配置"
          >
            保存字段配置
          </a-button>
          <a-button size="small" @click="postUpdatesRef?.open()">
            配置插入后回写
            <a-badge :count="templateForm.post_insert_updates?.length || 0" :max-count="99" />
          </a-button>
          <a-button
            size="small"
            :disabled="templateForm.id === null || writeBusy"
            @click="openCleanupResources"
          >
            关联ES清理
            <a-badge :count="templateForm.cleanup_resources?.length || 0" />
          </a-button>
          <a-button
            size="small"
            :disabled="templateForm.entity === null"
            @click="openRootEntityRules"
            data-testid="qa-views-data-factory-template-preview-button-查看实体规则"
          >
            查看实体规则
          </a-button>
          <a-button
            size="small"
            :loading="syncLoading"
            :disabled="writeBusy || templateLoading || templateForm.id === null"
            @click="confirmSyncTemplateFields"
            data-testid="qa-views-data-factory-template-preview-button-同步实体规则"
          >
            同步实体规则
          </a-button>
          <a-button
            size="small"
            status="success"
            :disabled="templateForm.id === null || previewLoading || writeBusy || templateLoading"
            :loading="debugLoading"
            @click="debugRun"
            data-testid="qa-views-data-factory-template-preview-button-调试运行"
          >
            调试运行
          </a-button>
          <VariableReferencePanel />
          <a-button
            class="mango-back-button"
            size="small"
            @click="goBack"
            data-testid="qa-views-data-factory-template-preview-button-返回"
            >返回</a-button
          >
        </a-space>
      </div>
    </template>

    <template #default>





      <mango-panel-spin
        :loading="initialPageLoading"
        class="mango-preview-spin mango-workbench-scroll-x mango-scene-config-workbench-scroll"
        tip="模板配置加载中..."
      >
        <div v-if="templateForm.entity !== null" class="mango-scene-config-workbench">
          <mango-panel-spin
            :loading="scenePanelLoading"
            class="mango-scene-items-spin"
            tip="编排数据加载中..."
          >
            <aside class="mango-scene-items-card">
              <div class="mango-scene-items-header">
                <div>
                  <div class="mango-scene-items-title">场景编排</div>
                  <div class="mango-scene-items-subtitle"
                    >点击模板查看局部依赖，拖动调整子模板创建顺序</div
                  >
                </div>
                <a-tag
                  size="small"
                  :color="sceneAutoSaveMeta.color"
                  class="mango-scene-save-status"
                  @click="retrySceneAutoSave"
                >
                  {{ sceneAutoSaveMeta.text }}
                </a-tag>
                <a-button
                  size="small"
                  type="primary"
                  long
                  @click="addSceneItem"
                  data-testid="qa-views-data-factory-template-preview-button-添加关联模板"
                  >添加关联模板</a-button
                >
              </div>
              <div class="mango-scene-items-list">
                <div
                  :class="[
                    'mango-scene-root-card',
                    { 'mango-scene-item-card-active': activeSceneNodeKey === 'root' },
                  ]"
                  @click="activeSceneNodeKey = 'root'"
                  role="button"
                  tabindex="0"
                  :aria-pressed="activeSceneNodeKey === 'root'"
                  @keydown.enter="activeSceneNodeKey = 'root'"
                  @keydown.space.prevent="activeSceneNodeKey = 'root'"
                >
                  <div class="mango-scene-root-label">主模板</div>
                  <div
                    class="mango-scene-root-name"
                    :title="templateForm.name || pageRecord?.name"
                    >{{ templateForm.name || pageRecord?.name || '-' }}</div
                  >
                  <div class="mango-scene-root-meta">场景入口，优先创建</div>
                </div>
                <div
                  v-for="(item, index) in templateForm.items || []"
                  :key="item._key || item.id || index"
                  :class="[
                    'mango-scene-item-card',
                    {
                      'mango-scene-item-card-active':
                        activeSceneNodeKey === getSceneItemFocusKey(item),
                    },
                    {
                      'mango-scene-item-card-dragging':
                        draggingSceneItemKey === getSceneItemKey(item),
                    },
                  ]"
                  :draggable="!sceneEditLocked"
                  @click="activeSceneNodeKey = getSceneItemFocusKey(item)"
                  @dragstart="onSceneItemDragStart(item)"
                  @dragover.prevent
                  @drop="onSceneItemDrop(item)"
                  @dragend="onSceneItemDragEnd"
                >
                  <div class="mango-scene-item-drag" title="拖动排序">::</div>
                  <div class="mango-scene-item-content">
                    <a-select
                      v-model="item.child_template"
                      :options="sceneSelectOptions"
                      :loading="sceneOptionsLoading"
                      :disabled="sceneEditLocked"
                      :filter-option="false"
                      :field-names="{ value: 'id', label: 'name' }"
                      allow-search
                      allow-clear
                      placeholder="选择关联模板"
                      @popup-visible-change="
                        (visible) => visible && loadSceneTemplateOptions('', 1)
                      "
                      @search="(keyword) => loadSceneTemplateOptions(keyword, 1)"
                      @dropdown-reach-bottom="loadMoreSceneTemplateOptions"
                      @change="() => onSceneItemTemplateChange(item)"
                      data-testid="qa-views-data-factory-template-preview-select-选择关联模板"
                    >
                      <template #footer v-if="sceneOptionsFailed">
                        <a-button
                          type="text"
                          size="small"
                          :loading="sceneOptionsLoading"
                          :disabled="sceneEditLocked"
                          @click="loadSceneTemplateOptions(sceneOptionsKeyword, sceneOptionsPage)"
                          >重试</a-button
                        >
                      </template>
                    </a-select>
                    <a-input
                      v-model="item.name"
                      :disabled="sceneEditLocked"
                      placeholder="关联名称"
                      @blur="() => onSceneItemNameBlur(item)"
                      data-testid="qa-views-data-factory-template-preview-input-关联名称"
                    />
                    <div class="mango-scene-item-footer">
                      <span class="mango-scene-item-hint">共享主场景上下文</span>
                      <a-button
                        size="mini"
                        status="danger"
                        type="text"
                        @click="removeSceneItem(index)"
                        data-testid="qa-views-data-factory-template-preview-button-移除"
                      >
                        移除
                      </a-button>
                    </div>
                  </div>
                </div>
                <div v-if="!templateForm.items?.length" class="mango-empty-state mango-scene-empty">
                  暂未添加关联模板
                </div>
              </div>
            </aside>
          </mango-panel-spin>
          <section class="mango-scene-preview-panel">
            <DataFactoryDependencyPreview
              :inert="sceneEditLocked ? '' : undefined"
              :dependency-tree="previewResult.dependency_tree"
              :post-insert-updates="previewResult.post_insert_updates || []"
              :can-debug-run="previewResult.can_debug_run"
              configuration-preview
              :generator-options="enumStore.data_factory_generator_type"
              :root-fields="fieldRows"
              :editable-node-configs="editableNodeConfigs"
              v-model:field-overrides="templateForm.field_overrides"
              v-model:output-config="templateForm.output_config"
              :dependency-template-options="dependencyTemplateOptions"
              :load-dependency-template-options="loadDependencyTemplateOptions"
              :focus-node-key="activeSceneNodeKey"
              :flow-loading="previewLoading || navigating"
              :field-loading="fieldPanelLoading"
              editable-root
              field-table-scroll-y="100%"
              @open-template="openDependencyTemplate"
              @update-node-field-overrides="updateSceneItemOverrides"
            />
          </section>
        </div>
        <div v-else class="mango-empty-state">场景模板未绑定实体</div>
      </mango-panel-spin>
    </template>
  </TableBody>

  <DebugResultDialog ref="debugRef" @busy-change="onDebugBusyChange" />

  <EntityRulesDialog ref="entityRulesRef" />

  <PostUpdatesDialog
    ref="postUpdatesRef"
    :nodes="postUpdateNodes"
    :model-value="templateForm.post_insert_updates"
    :checks="previewResult.post_insert_updates || []"
    :loading="previewLoading"
    :disabled="sceneEditLocked"
    @update:model-value="updatePostUpdates"
    @check="loadPreview"
  />
  <MangoJsonEditDrawer
    v-model:visible="cleanupResourceVisible"
    v-model="cleanupResourceJson"
    title="关联ES清理规则"
    :description="cleanupResourceDescription"
    :placeholder="cleanupResourceExample"
    :saving="cleanupResourceSaving"
    @save="saveCleanupResources"
  />
</template>

<script lang="ts" setup>
import { reportLoadError } from '@/utils/load-error'

  import DataFactoryDependencyPreview from '@/components/DataFactory/DataFactoryDependencyPreview.vue'
  import EntityRulesDialog from './components/EntityRulesDialog.vue'
  import type {
    EntityRulesHandle,
    TemplateRecord,
    TemplateDraft,
    SceneItem,
    TemplateSummary,
    Overrides,
    OutputItem,
    FieldRecord,
    PreviewResult,
    EditableNode,
    PostUpdate,
    PreviewNode,
    DebugHandle,
    JsonValue,
    PostUpdatesHandle,
    PostUpdateNode,
  } from './types'
  import { createDraft, clone, optionId, normalizeLoadedItems } from './form'
  import { useTemplateScope } from '../composables/useTemplateScope'
  import DebugResultDialog from './components/DebugResultDialog.vue'
  import PostUpdatesDialog from './components/PostUpdatesDialog.vue'
  import VariableReferencePanel from '@/components/business/VariableReferencePanel.vue'
  import MangoJsonEditDrawer from '@/components/editors/MangoJsonEditDrawer.vue'
  import {
    getDataFactoryField,
    getDataFactoryTemplate,
    postDataFactoryTemplatePreview,
    postDataFactoryTemplateSyncFields,
    putDataFactoryTemplate,
  } from '@/api/data-factory'
  import { useEnum } from '@/store/modules/get-enum'
  import useUserStore from '@/store/modules/user'
  import { usePageData } from '@/store/page-data'
  import { Message, Modal } from '@arco-design/web-vue'
  import { computed, onMounted, reactive, ref, watch, shallowRef, Ref } from 'vue'
  import { onBeforeRouteLeave, onBeforeRouteUpdate, useRoute, useRouter } from 'vue-router'
  import { cleanupResourceDescription, cleanupResourceExample } from './config'

  const route = useRoute()
  const router = useRouter()
  const enumStore = useEnum()
  const userStore = useUserStore()
  const pageData = usePageData()
  const templateLoading = ref(false)
  const fieldLoading = ref(false)
  const sceneOptionsLoading = ref(false)
  const sceneItemFieldsLoading = ref(false)
  const dependencyTemplateLoading = ref(false)
  const previewLoading = ref(false)
  const firstPreviewReady = ref(false)
  const editableFieldsReady = ref(false)
  const previewResult = shallowRef<PreviewResult>({})
  const debugLoading = ref(false)
  const navigating = ref(false)
  const debugRef = ref<DebugHandle | null>(null)
  const saving = ref(false)
  const syncLoading = ref(false)
  const entityRulesRef = ref<EntityRulesHandle | null>(null)
  const postUpdatesRef = ref<PostUpdatesHandle | null>(null)
  const cleanupResourceVisible = ref(false)
  const cleanupResourceJson = ref('[]')
  const cleanupResourceSaving = ref(false)
  const sceneAutoSaving = ref(false)
  const sceneAutoSaveStatus = ref<'idle' | 'saving' | 'saved' | 'error'>('idle')
  const sceneSavedItemOverrides = ref<Record<string, Overrides>>({})
  const savedFieldConfigSignature = ref('')
  const fieldRows: Ref<FieldRecord[]> = ref([])
  const sceneTemplateOptions = ref<TemplateSummary[]>([])
  const sceneOptionsKeyword = ref('')
  const sceneOptionsPage = ref(0)
  const sceneOptionsHasMore = ref(false)
  const sceneOptionsFailed = ref(false)
  let sceneOptionsRequest = 0
  const sceneSelectOptions = computed(() => {
    const selected = (templateForm.items || [])
      .map((item) => item.child_template_detail)
      .filter((item): item is TemplateSummary => item != null)
    return [
      ...new Map(
        [...selected, ...sceneTemplateOptions.value].map((item) => [String(item.id), item])
      ).values(),
    ]
  })
  const itemFieldsMap = ref<Record<string, FieldRecord[]>>({})
  const dependencyTemplateOptions = ref<
    Record<string, Array<{ label: string; value: string | number }>>
  >({})
  const draggingSceneItemKey = ref('')
  const activeSceneNodeKey = ref('root')
  const templateForm: TemplateDraft = reactive(createDraft())
  const pageRecord = computed<TemplateRecord | null>(() => pageData.record ?? null)
  const previewContext = computed(() => {
    const record = pageRecord.value
    const context = record?.preview_context
    const target = optionId(route.query.template_id)
    return context &&
      (target === null || String(target) === String(context.template_id ?? record?.id))
      ? context
      : {}
  })
  const templateId = computed(() =>
    optionId(route.query.template_id ?? previewContext.value.template_id)
  )
  const previewTitle = computed(() => {
    const id = templateForm.id ?? templateId.value ?? '-'
    const cachedName = String(pageRecord.value?.id) === String(id) ? pageRecord.value?.name : ''
    const name = templateForm.name || cachedName || '-'
    return `场景模板配置 / ${id} / ${name}`
  })
  const editableNodeConfigs = computed(() => {
    const configs: Record<string, EditableNode> = {
      root: {
        fields: fieldRows.value,
        fieldOverrides: templateForm.field_overrides || {},
        outputConfig: templateForm.output_config || [],
      },
    }
    ;(templateForm.items || []).forEach((item) => {
      configs[`item:${getSceneItemKey(item)}`] = {
        fields: itemFieldsMap.value[getSceneItemKey(item)] || [],
        fieldOverrides: item.field_overrides || {},
        outputConfig: [],
      }
    })
    return configs
  })
  const postUpdateNodes = computed<PostUpdateNode[]>(() => [
    {
      value: 'root',
      label: `主模板：${templateForm.name || '-'}`,
      fields: fieldRows.value,
      overrides: templateForm.field_overrides,
    },
    ...templateForm.items
      .filter((item) => item.child_template !== null && (item.id != null || item.name))
      .map((item) => ({
        value: `item:${item.id ?? item.name}`,
        label: `关联模板：${item.name || getSceneTemplateName(item.child_template)}`,
        fields: itemFieldsMap.value[getSceneItemKey(item)] || [],
        overrides: { ...item.child_template_detail?.field_overrides, ...item.field_overrides },
      })),
  ])
  function updatePostUpdates(rules: PostUpdate[]) {
    if (sceneEditLocked.value) return
    templateForm.post_insert_updates = clone(rules)
    previewResult.value = { ...previewResult.value, post_insert_updates: [] }
  }
  const canDebugText = computed(() => {
    if (!previewResult.value.dependency_tree) {
      return '维护字段覆盖配置，并查看依赖实体关系'
    }
    if (previewResult.value.preview_mode === 'configuration') {
      return '当前仅展示配置示例；调试运行时才校验环境和数据库权限'
    }
    return previewResult.value.can_debug_run
      ? '依赖链路完整，可以保存当前字段配置'
      : '依赖链路存在未配置字段，请在字段配置中补齐'
  })
  const initialPageLoading = computed(() => {
    return (
      (templateLoading.value || fieldLoading.value || previewLoading.value) &&
      !templateForm.entity &&
      !fieldRows.value.length &&
      !previewResult.value.dependency_tree
    )
  })
  const scenePanelLoading = computed(() => !initialPageLoading.value && templateLoading.value)
  const sceneAutoSaveMeta = computed(() => {
    if (sceneAutoSaving.value || sceneAutoSaveStatus.value === 'saving') {
      return { text: '保存中...', color: 'arcoblue' }
    }
    if (sceneAutoSaveStatus.value === 'error') {
      return { text: '保存失败，点击重试', color: 'red' }
    }
    if (sceneAutoSaveStatus.value === 'saved') {
      return { text: '已保存', color: 'green' }
    }
    return { text: '选择模板后自动保存', color: 'gray' }
  })
  const fieldPanelLoading = computed(
    () =>
      fieldLoading.value ||
      sceneItemFieldsLoading.value ||
      dependencyTemplateLoading.value ||
      previewLoading.value ||
      (!firstPreviewReady.value && !previewError.value) ||
      (!editableFieldsReady.value && !fieldsError.value)
  )

  const templateError = ref(false),
    fieldsError = ref(false),
    previewError = ref(false),
    dependencyError = ref(false),
    enumError = ref(false),
    enumLoading = ref(false)
  const writeBusy = computed(
    () =>
      saving.value ||
      syncLoading.value ||
      cleanupResourceSaving.value ||
      sceneAutoSaving.value ||
      debugLoading.value
  )
  const sceneEditLocked = computed(
    () =>
      saving.value ||
      syncLoading.value ||
      cleanupResourceSaving.value ||
      debugLoading.value ||
      templateLoading.value
  )
  let generation = 0,
    templateRequest = 0,
    fieldRequest = 0,
    previewRequest = 0,
    itemFieldsRequest = 0,
    dependencyRequest = 0,
    enumsRequest = 0
  let sceneSaveTask: Promise<boolean> | null = null
  let arrangementQueued = false
  let confirmation: ReturnType<typeof Modal.confirm> | null = null
  const scope = useTemplateScope(
    invalidate,
    () => {
      void reloadPageData()
    },
    false
  )
  const currentContext = () => ({ generation, version: scope.snapshot() })
  const isCurrent = (context: { generation: number; version: number }) =>
    context.generation === generation && scope.current(context.version)
  function invalidate() {
    ++generation
    ++templateRequest
    ++fieldRequest
    ++previewRequest
    ++itemFieldsRequest
    ++sceneOptionsRequest
    ++dependencyRequest
    ++enumsRequest
    arrangementQueued = false
    confirmation?.close()
    confirmation = null
    entityRulesRef.value?.close()
    debugRef.value?.close()
    cleanupResourceVisible.value = false
    postUpdatesRef.value?.close()
    Object.assign(templateForm, createDraft())
    fieldRows.value = []
    previewResult.value = {}
    sceneTemplateOptions.value = []
    itemFieldsMap.value = {}
    dependencyTemplateOptions.value = {}
    templateLoading.value = false
    fieldLoading.value = false
    sceneOptionsLoading.value = false
    sceneItemFieldsLoading.value = false
    dependencyTemplateLoading.value = false
    previewLoading.value = false
    enumLoading.value = false
    templateError.value = false
    fieldsError.value = false
    previewError.value = false
    dependencyError.value = false
    enumError.value = false
    sceneOptionsPage.value = 0
    sceneOptionsHasMore.value = false
    sceneOptionsFailed.value = false
    firstPreviewReady.value = false
    editableFieldsReady.value = false
    savedFieldConfigSignature.value = ''
    sceneSavedItemOverrides.value = {}
    sceneAutoSaveStatus.value = 'idle'
    activeSceneNodeKey.value = 'root'
  }
  async function loadEnums() {
    if (!scope.isActive()) return
    const context = currentContext(),
      request = ++enumsRequest
    enumLoading.value = true
    enumError.value = false
    try {
      await enumStore.getEnum()
    } catch (loadFailure0) {
      if (request === enumsRequest && isCurrent(context)) (reportLoadError(loadFailure0, "加载失败，请重试", false), enumError.value = true)
    } finally {
      if (request === enumsRequest) enumLoading.value = false
    }
  }
  function resumeArrangement() {
    if (arrangementQueued && !writeBusy.value && scope.isActive()) void autoSaveSceneItems()
  }
  function onDebugBusyChange(value: boolean) {
    debugLoading.value = value
    if (!value) resumeArrangement()
  }

  function buildPreviewPayload() {
    return {
      template_id: templateId.value,
      overrides: templateForm.field_overrides || {},
      output_config: templateForm.output_config,
      post_insert_updates: templateForm.post_insert_updates || [],
      items: normalizeSceneItems(),
      preview_mode: 'configuration',
    }
  }

  function resetTemplateForm(record: TemplateRecord | null) {
    const draft = createDraft(record, templateId.value)
    const context = previewContext.value
    if (String(record?.id) === String(templateId.value)) {
      if (context.overrides) draft.field_overrides = clone(context.overrides)
      if (context.output_config) draft.output_config = clone(context.output_config)
    }
    Object.assign(templateForm, draft)
    snapshotSceneItemOverrides(draft.items)
    snapshotFieldConfig()
  }

  async function loadTemplate(): Promise<boolean> {
    if (!scope.isActive() || templateId.value === null) {
      templateError.value = true
      return false
    }
    const context = currentContext(),
      request = ++templateRequest,
      id = templateId.value
    templateLoading.value = true
    templateError.value = false
    try {
      const response = await getDataFactoryTemplate({ id, page: 1, pageSize: 1 }, 30000)
      if (request !== templateRequest || !isCurrent(context)) return false
      const record: TemplateRecord | null = response.data?.[0] ?? null
      if (!record || String(record.id) !== String(id)) {
        templateError.value = true
        return false
      }
      resetTemplateForm(record)
      return true
    } catch (loadFailure1) {
      if (request === templateRequest && isCurrent(context)) (reportLoadError(loadFailure1, "加载失败，请重试", false), templateError.value = true)
      return false
    } finally {
      if (request === templateRequest) templateLoading.value = false
    }
  }

  async function reloadPageData() {
    if (!scope.isActive()) return
    invalidate()
    void loadEnums()
    const context = currentContext()
    if (!(await loadTemplate()) || !isCurrent(context)) return
    await Promise.all([loadPreview(), loadEditableFieldDefinitions()])
  }

  async function loadEditableFieldDefinitions() {
    if (!scope.isActive()) return
    const context = currentContext()
    editableFieldsReady.value = false
    fieldsError.value = false
    await Promise.all([loadTemplateFields(), loadSceneItemFields()])
    if (isCurrent(context)) editableFieldsReady.value = true
  }

  async function loadTemplateFields() {
    if (!scope.isActive()) return
    const request = ++fieldRequest,
      context = currentContext(),
      entity = templateForm.entity
    if (entity === null) {
      fieldRows.value = []
      return
    }
    fieldLoading.value = true
    fieldsError.value = false
    try {
      const response = await getDataFactoryField({ entity })
      if (request !== fieldRequest || !isCurrent(context)) return
      fieldRows.value = response.data || []
      await preloadDependencyTemplateOptions()
    } catch (loadFailure2) {
      if (request === fieldRequest && isCurrent(context)) (reportLoadError(loadFailure2, "加载失败，请重试", false), fieldsError.value = true)
    } finally {
      if (request === fieldRequest) fieldLoading.value = false
    }
  }

  async function loadPreview() {
    if (!scope.isActive()) return
    const request = ++previewRequest,
      context = currentContext()
    if (templateId.value === null) {
      previewError.value = true
      firstPreviewReady.value = true
      return
    }
    const payload = clone(buildPreviewPayload()),
      signature = JSON.stringify(payload)
    previewLoading.value = true
    previewError.value = false
    try {
      const response = await postDataFactoryTemplatePreview(payload)
      if (request === previewRequest && isCurrent(context)) {
        if (signature === JSON.stringify(buildPreviewPayload()))
          previewResult.value = response.data || {}
        else {
          void loadPreview()
          return
        }
      }
    } catch (loadFailure3) {
      if (request === previewRequest && isCurrent(context)) (reportLoadError(loadFailure3, "加载失败，请重试", false), previewError.value = true)
    } finally {
      if (request === previewRequest) {
        previewLoading.value = false
        firstPreviewReady.value = true
      }
    }
  }

  function debugRun() {
    if (!scope.isActive() || writeBusy.value || templateForm.id === null || templateLoading.value)
      return Promise.resolve(false)
    if (hasUnsavedFieldConfig() || sceneAutoSaveStatus.value === 'error' || arrangementQueued) {
      Message.warning('请先保存字段和插入后回写配置，再调试运行')
      return Promise.resolve(false)
    }
    return (
      debugRef.value?.run(
        templateForm.id,
        templateForm.field_overrides,
        optionId(route.query.test_env ?? userStore.selected_environment)
      ) ?? Promise.resolve(false)
    )
  }

  async function saveTemplateConfig(): Promise<boolean> {
    if (!scope.isActive() || writeBusy.value || templateForm.id === null || templateLoading.value)
      return false
    const context = currentContext(),
      signature = buildFieldConfigSignature(),
      arrangement = clone(templateForm.items)
    const payload = clone({
      id: templateForm.id,
      field_overrides: templateForm.field_overrides,
      output_config: templateForm.output_config,
      post_insert_updates: templateForm.post_insert_updates,
      items: normalizeSceneItems(),
    })
    saving.value = true
    try {
      const response = await putDataFactoryTemplate(payload)
      if (!isCurrent(context)) return false
      templateForm.config_status = response.data?.config_status ?? templateForm.config_status
      const unchanged = signature === buildFieldConfigSignature()
      mergeSavedSceneItems(response.data?.items ?? payload.items, arrangement)
      sceneAutoSaveStatus.value = 'saved'
      // A saved snapshot must not declare edits made during the request as saved.
      if (unchanged) snapshotFieldConfig()
      else savedFieldConfigSignature.value = signature
      snapshotSceneItemOverrides(response.data?.items ?? payload.items)
      if (Number(response.data?.config_status) === 0)
        Message.warning('配置已保存，待校验后可执行；请在模板列表完成校验')
      else Message.success(response.msg)
      await Promise.all([loadSceneItemFields(), loadPreview()])
      return true
    } catch {
      return false
    } finally {
      saving.value = false
      resumeArrangement()
    }
  }

  function openCleanupResources() {
    if (!scope.isActive() || writeBusy.value || templateForm.id === null) return
    cleanupResourceJson.value = JSON.stringify(templateForm.cleanup_resources, null, 2)
    cleanupResourceVisible.value = true
  }

  async function saveCleanupResources(value: string) {
    if (
      !scope.isActive() ||
      writeBusy.value ||
      !cleanupResourceVisible.value ||
      templateForm.id === null
    )
      return false
    let rules: JsonValue[]
    try {
      const parsed: unknown = JSON.parse(value)
      if (!Array.isArray(parsed)) throw Error('array-required')
      rules = parsed
    } catch {
      Message.error('请填写 JSON 数组，清空规则请使用 []')
      return false
    }
    const context = currentContext(),
      id = templateForm.id
    cleanupResourceSaving.value = true
    try {
      const response = await putDataFactoryTemplate({ id, cleanup_resources: rules })
      if (!isCurrent(context)) return false
      templateForm.cleanup_resources = clone(response.data?.cleanup_resources ?? rules)
      cleanupResourceVisible.value = false
      Message.success('关联ES清理规则已保存，仅对后续执行生效')
      return true
    } catch {
      return false
    } finally {
      cleanupResourceSaving.value = false
      resumeArrangement()
    }
  }

  async function syncTemplateFields(): Promise<boolean> {
    if (!scope.isActive() || writeBusy.value || templateForm.id === null || templateLoading.value)
      return false
    const context = currentContext(),
      signature = buildFieldConfigSignature()
    const payload = {
      id: templateForm.id,
      test_env: optionId(route.query.test_env ?? userStore.selected_environment),
    }
    syncLoading.value = true
    try {
      const response = await postDataFactoryTemplateSyncFields(payload)
      if (!isCurrent(context)) return false
      if (
        String(payload.test_env) !==
        String(optionId(route.query.test_env ?? userStore.selected_environment))
      ) {
        Message.warning('执行环境已变更，请重新同步实体规则')
        return false
      }
      if (signature === buildFieldConfigSignature()) {
        templateForm.field_overrides = clone(response.data?.field_overrides ?? {})
        templateForm.items = templateForm.items.map((item) => ({ ...item, field_overrides: {} }))
        snapshotSceneItemOverrides(templateForm.items)
        snapshotFieldConfig()
      }
      Message.success(response.msg)
      await Promise.all([loadTemplateFields(), loadPreview()])
      return true
    } catch {
      return false
    } finally {
      syncLoading.value = false
      resumeArrangement()
    }
  }

  function confirmSyncTemplateFields() {
    if (!scope.isActive() || confirmation || writeBusy.value || templateForm.id === null) return
    const context = currentContext()
    const dialog = Modal.confirm({
      title: '同步实体规则',
      content: '同步后会清空当前场景模板字段覆盖，使用实体字段规则作为默认生成方式，确认继续？',
      okText: '确认同步',
      cancelText: '取消',
      onBeforeOk: () => (isCurrent(context) ? syncTemplateFields() : Promise.resolve(false)),
      onClose() {
        if (confirmation === dialog) confirmation = null
      },
    })
    confirmation = dialog
  }

  function openRootEntityRules() {
    if (
      templateForm.entity === null ||
      templateForm.entity === undefined ||
      templateForm.entity === ''
    ) {
      Message.warning('当前场景模板未绑定数据实体')
      return
    }
    entityRulesRef.value?.open(templateForm.entity)
  }

  async function loadDependencyTemplateOptions(row: FieldRecord) {
    const entity = row.generator_config?.dependency_entity_id,
      product = templateForm.project_product
    if (!scope.isActive() || entity == null || product === null) return
    const key = String(entity),
      context = currentContext()
    if (dependencyTemplateOptions.value[key]) return
    try {
      const response = await getDataFactoryTemplate({
        project_product: product,
        entity,
        page: 1,
        pageSize: 9999,
      })
      if (!isCurrent(context)) return
      dependencyTemplateOptions.value = {
        ...dependencyTemplateOptions.value,
        [key]: (response.data || []).map((item: TemplateSummary) => ({
          label: item.name || String(item.id),
          value: item.id,
        })),
      }
    } catch (loadFailure4) {
      if (isCurrent(context)) (reportLoadError(loadFailure4, "加载失败，请重试", false), dependencyError.value = true)
    }
  }

  async function preloadDependencyTemplateOptions() {
    if (!scope.isActive()) return
    const request = ++dependencyRequest,
      context = currentContext()
    dependencyTemplateLoading.value = true
    dependencyError.value = false
    try {
      await Promise.all(
        fieldRows.value
          .filter((row) => row.generator_config?.dependency_entity_id != null)
          .map(loadDependencyTemplateOptions)
      )
    } finally {
      if (request === dependencyRequest && isCurrent(context))
        dependencyTemplateLoading.value = false
    }
  }

  function loadSceneTemplateOptions(keyword = '', page = 1) {
    if (!scope.isActive()) return Promise.resolve()
    if (templateForm.project_product === null) {
      sceneTemplateOptions.value = []
      return Promise.resolve()
    }
    const requestId = ++sceneOptionsRequest
    const context = currentContext()
    const productId = templateForm.project_product
    sceneOptionsKeyword.value = keyword
    sceneOptionsPage.value = page
    sceneOptionsFailed.value = false
    sceneOptionsLoading.value = true
    return getDataFactoryTemplate(
      {
        project_product: productId,
        ...(keyword.trim() ? { name: keyword.trim() } : {}),
        page,
        pageSize: 30,
      },
      30000
    )
      .then((res) => {
        if (requestId !== sceneOptionsRequest || !isCurrent(context)) return
        const rows = res.data || []
        const candidates = rows.filter((item) => String(item.id) !== String(templateForm.id))
        sceneTemplateOptions.value =
          page === 1 ? candidates : [...sceneTemplateOptions.value, ...candidates]
        sceneOptionsHasMore.value = page * 30 < res.totalSize
      })
      .catch((loadFailure5) => {
        if (requestId !== sceneOptionsRequest || !isCurrent(context)) return
        void (reportLoadError(loadFailure5, "加载失败，请重试", false), sceneOptionsFailed.value = true)
      })
      .finally(() => {
        if (requestId === sceneOptionsRequest) sceneOptionsLoading.value = false
      })
  }

  function loadMoreSceneTemplateOptions() {
    if (!sceneOptionsLoading.value && !sceneOptionsFailed.value && sceneOptionsHasMore.value) {
      return loadSceneTemplateOptions(sceneOptionsKeyword.value, sceneOptionsPage.value + 1)
    }
  }

  function normalizeSceneItems() {
    return (templateForm.items || [])
      .map((item: SceneItem, index: number) => ({
        id: typeof item.id === 'number' ? item.id : undefined,
        child_template: item.child_template,
        name: item.name || getSceneTemplateName(item.child_template) || `关联模板${index + 1}`,
        sort: index * 10,
        field_overrides: clone(item.field_overrides || {}),
      }))
      .filter((item) => item.child_template !== null)
  }

  function normalizeSceneArrangementItems() {
    return (templateForm.items || [])
      .map((item: SceneItem, index: number) => {
        const key = getSceneItemKey(item)
        return {
          id: typeof item.id === 'number' ? item.id : undefined,
          child_template: item.child_template,
          name: item.name || getSceneTemplateName(item.child_template) || `关联模板${index + 1}`,
          sort: index * 10,
          field_overrides: sceneSavedItemOverrides.value[key] || {},
        }
      })
      .filter((item) => item.child_template !== null)
  }

  function snapshotSceneItemOverrides(items: SceneItem[]) {
    const next: Record<string, Overrides> = {}
    normalizeLoadedItems(items).forEach((item) => {
      next[getSceneItemKey(item)] = item.field_overrides || {}
    })
    sceneSavedItemOverrides.value = next
  }

  function buildFieldConfigSignature() {
    return JSON.stringify({
      field_overrides: templateForm.field_overrides || {},
      output_config: templateForm.output_config || [],
      post_insert_updates: templateForm.post_insert_updates || [],
      item_field_overrides: (templateForm.items || [])
        .filter((item) => Object.keys(item.field_overrides || {}).length)
        .map((item) => ({
          key: item.id || item.child_template || item._key,
          field_overrides: clone(item.field_overrides || {}),
        })),
    })
  }

  function snapshotFieldConfig() {
    savedFieldConfigSignature.value = buildFieldConfigSignature()
  }

  function hasUnsavedFieldConfig() {
    return Boolean(
      savedFieldConfigSignature.value &&
        savedFieldConfigSignature.value !== buildFieldConfigSignature()
    )
  }

  function getSceneItemKey(item: SceneItem) {
    return String(item.id ?? item._key ?? item.name)
  }

  function getSceneItemFocusKey(item: SceneItem) {
    return `item:${getSceneItemKey(item)}`
  }

  function getSceneTemplateName(templateId: string | number | null) {
    return (
      sceneSelectOptions.value.find((item) => String(item.id) === String(templateId))?.name || ''
    )
  }

  function getSceneTemplateEntity(templateId: string | number | null) {
    const template = sceneSelectOptions.value.find((item) => String(item.id) === String(templateId))
    return optionId(template?.entity)
  }

  function addSceneItem() {
    if (sceneEditLocked.value) return
    const nextIndex = templateForm.items?.length || 0
    templateForm.items = [
      ...(templateForm.items || []),
      {
        id: null,
        _key: `new-${Date.now()}-${nextIndex}`,
        child_template: null,
        name: '',
        sort: nextIndex * 10,
        field_overrides: {},
      },
    ]
  }

  function removeSceneItem(index: number) {
    if (sceneEditLocked.value) return
    const removedKey = getSceneItemFocusKey(templateForm.items[index])
    templateForm.items.splice(index, 1)
    if (activeSceneNodeKey.value === removedKey) {
      activeSceneNodeKey.value = 'root'
    }
    autoSaveSceneItems()
  }

  function reorderSceneItems(data: SceneItem[]) {
    if (sceneEditLocked.value) return
    templateForm.items = (data || []).map((item: SceneItem, index: number) => ({
      ...item,
      sort: index * 10,
    }))
    autoSaveSceneItems()
  }

  function onSceneItemDragStart(item: SceneItem) {
    draggingSceneItemKey.value = getSceneItemKey(item)
  }

  function onSceneItemDrop(targetItem: SceneItem) {
    if (sceneEditLocked.value) return
    const sourceKey = draggingSceneItemKey.value
    const targetKey = getSceneItemKey(targetItem)
    if (!sourceKey || sourceKey === targetKey) {
      return
    }
    const items = [...(templateForm.items || [])]
    const sourceIndex = items.findIndex((item) => getSceneItemKey(item) === sourceKey)
    const targetIndex = items.findIndex((item) => getSceneItemKey(item) === targetKey)
    if (sourceIndex < 0 || targetIndex < 0) {
      return
    }
    const [sourceItem] = items.splice(sourceIndex, 1)
    items.splice(targetIndex, 0, sourceItem)
    reorderSceneItems(items)
  }

  function onSceneItemDragEnd() {
    draggingSceneItemKey.value = ''
  }

  function onSceneItemTemplateChange(item: SceneItem) {
    if (sceneEditLocked.value) return
    item.child_template_detail =
      sceneSelectOptions.value.find(
        (option) => String(option.id) === String(item.child_template)
      ) || null
    if (!item.name) {
      item.name = getSceneTemplateName(item.child_template)
    }
    item.field_overrides = item.field_overrides || {}
    autoSaveSceneItems()
  }

  function onSceneItemNameBlur(item: SceneItem) {
    if (sceneEditLocked.value) return
    if (item.child_template === null) {
      return
    }
    autoSaveSceneItems()
  }

  async function loadSceneItemFields() {
    if (!scope.isActive()) return
    const context = currentContext(),
      request = ++itemFieldsRequest,
      items = clone(templateForm.items)
    sceneItemFieldsLoading.value = true
    try {
      const entries = await Promise.all(
        items.map(async (item) => {
          const entity =
            getSceneTemplateEntity(item.child_template) ??
            optionId(item.child_template_detail?.entity)
          const fields = entity === null ? [] : (await getDataFactoryField({ entity })).data || []
          return [getSceneItemKey(item), fields] as const
        })
      )
      if (request === itemFieldsRequest && isCurrent(context))
        itemFieldsMap.value = Object.fromEntries(entries)
    } catch (loadFailure6) {
      if (request === itemFieldsRequest && isCurrent(context)) (reportLoadError(loadFailure6, "加载失败，请重试", false), fieldsError.value = true)
    } finally {
      if (request === itemFieldsRequest) sceneItemFieldsLoading.value = false
    }
  }

  function updateSceneItemOverrides(key: string, value: Overrides) {
    if (sceneEditLocked.value) return
    const itemKey = key.replace(/^item:/, '')
    const item = (templateForm.items || []).find((row) => getSceneItemKey(row) === itemKey)
    if (!item) {
      return
    }
    item.field_overrides = clone(value)
    loadPreview()
  }

  function mergeSavedSceneItems(savedItems: SceneItem[], sentItems: SceneItem[]) {
    const sent = sentItems.filter((item) => item.child_template !== null)
    savedItems.forEach((saved, index) => {
      const source = sent[index]
      if (!source) return
      const item = templateForm.items.find(
        (candidate) =>
          candidate._key === source._key && candidate.child_template === source.child_template
      )
      if (!item) return
      const previousFocus = getSceneItemFocusKey(item),
        previousKey = getSceneItemKey(item)
      item.id = saved.id ?? item.id
      item.child_template_detail = saved.child_template_detail
        ? clone(saved.child_template_detail)
        : item.child_template_detail
      const nextKey = getSceneItemKey(item)
      sceneSavedItemOverrides.value[nextKey] = clone(
        saved.field_overrides ?? source.field_overrides
      )
      if (previousKey !== nextKey) delete sceneSavedItemOverrides.value[previousKey]
      if (activeSceneNodeKey.value === previousFocus)
        activeSceneNodeKey.value = getSceneItemFocusKey(item)
    })
  }

  function autoSaveSceneItems(): Promise<boolean> {
    if (!scope.isActive() || templateForm.id === null || templateLoading.value)
      return Promise.resolve(false)
    arrangementQueued = true
    if (sceneSaveTask) return sceneSaveTask
    if (writeBusy.value) return Promise.resolve(false)
    const context = currentContext(),
      id = templateForm.id
    sceneAutoSaving.value = true
    sceneAutoSaveStatus.value = 'saving'
    sceneSaveTask = (async () => {
      try {
        while (arrangementQueued && isCurrent(context)) {
          arrangementQueued = false
          const items = clone(templateForm.items),
            fieldSignature = buildFieldConfigSignature(),
            wasDirty = hasUnsavedFieldConfig()
          const payload = clone({ id, items: normalizeSceneArrangementItems() })
          const response = await putDataFactoryTemplate(payload)
          if (!isCurrent(context)) return false
          const untouchedFields = fieldSignature === buildFieldConfigSignature()
          mergeSavedSceneItems(response.data?.items ?? payload.items, items)
          if (!wasDirty && untouchedFields) snapshotFieldConfig()
        }
        if (isCurrent(context)) {
          sceneAutoSaveStatus.value = 'saved'
          await Promise.all([loadSceneItemFields(), loadPreview()])
        }
        return true
      } catch {
        if (isCurrent(context)) {
          sceneAutoSaveStatus.value = 'error'
          arrangementQueued = false
        }
        return false
      } finally {
        sceneAutoSaving.value = false
        sceneSaveTask = null
        resumeArrangement()
      }
    })()
    return sceneSaveTask
  }

  function retrySceneAutoSave() {
    if (sceneAutoSaveStatus.value !== 'error') {
      return
    }
    autoSaveSceneItems()
  }

  async function openDependencyTemplate(node: PreviewNode) {
    if (!scope.isActive() || navigating.value || node.template_id == null || !confirmLeave())
      return false
    navigating.value = true
    pageData.setRecord({
      id: node.template_id,
      name: node.template_name,
      entity: node.entity_id,
    })
    try {
      await router.push({
        path: '/data-factory/template/preview',
        query: {
          template_id: node.template_id,
          test_env: route.query.test_env ?? userStore.selected_environment,
        },
      })
      return true
    } catch {
      return false
    } finally {
      navigating.value = false
    }
  }

  function goBack() {
    window.history.back()
  }

  onMounted(() => {
    void reloadPageData()
  })
  watch(
    () => route.query.template_id,
    () => {
      if (scope.isActive()) void reloadPageData()
    },
    { flush: 'sync' }
  )
  watch(
    () => [route.query.test_env, userStore.selected_environment],
    () => {
      confirmation?.close()
      confirmation = null
      debugRef.value?.close()
      entityRulesRef.value?.close()
    },
    { flush: 'sync' }
  )

  function confirmLeave() {
    if (!hasUnsavedFieldConfig() && !arrangementQueued && !sceneAutoSaving.value) {
      return true
    }
    return window.confirm('当前字段配置尚未保存，确认离开吗？')
  }
  onBeforeRouteLeave(confirmLeave)
  onBeforeRouteUpdate(
    (to) => String(to.query.template_id) === String(route.query.template_id) || confirmLeave()
  )
</script>

<style scoped>
  .mango-template-preview-page :deep(> .arco-card-body) {
    display: flex;
    flex-direction: column;
    min-height: 0;
  }

  .mango-preview-spin {
    display: block;
    box-sizing: border-box;
    width: 100%;
    height: 100%;
    min-height: 0;
    padding-top: var(--m-page-gap);
  }

  .mango-scene-config-workbench-scroll {
    --mango-workbench-min-width: 980px;
  }

  .mango-scene-config-workbench-scroll .mango-scene-config-workbench {
    min-width: var(--mango-workbench-min-width);
  }

  .mango-scene-items-spin {
    display: block;
    height: 100%;
    min-height: 0;
  }

  .mango-scene-items-spin :deep(> .mango-panel-spin__content) {
    height: 100%;
    min-height: 0;
  }

  .mango-scene-items-card {
    display: flex;
    overflow: hidden;
    flex-direction: column;
    width: 100%;
    height: 100%;
    min-height: 0;
    box-sizing: border-box;
    padding: var(--m-card-padding);
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
  }

  .mango-scene-items-header {
    display: flex;
    align-items: flex-start;
    flex-direction: column;
    justify-content: flex-start;
    gap: var(--m-page-gap);
  }

  .mango-scene-items-title {
    color: var(--m-text);
    font-size: 15px;
    font-weight: 600;
    line-height: 22px;
  }

  .mango-scene-items-subtitle {
    margin-top: 2px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .mango-scene-items-list {
    display: flex;
    overflow: auto;
    flex-direction: column;
    flex: 1;
    min-height: 0;
    margin-top: var(--m-page-gap);
    padding-right: 2px;
    padding-bottom: 2px;
    gap: var(--m-page-gap);
  }

  .mango-scene-item-card {
    display: grid;
    flex-shrink: 0;
    padding: var(--m-card-padding);
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface-soft);
    cursor: grab;
    gap: 8px;
    grid-template-columns: 18px minmax(0, 1fr);
    transition: border-color 0.2s ease, background 0.2s ease, opacity 0.2s ease;
  }

  .mango-scene-root-card {
    flex-shrink: 0;
    padding: var(--m-card-padding);
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface-soft);
    cursor: pointer;
    transition: border-color 0.2s ease, background 0.2s ease;
  }

  .mango-scene-root-card:hover,
  .mango-scene-item-card:hover {
    border-color: color-mix(in srgb, var(--m-primary) 28%, var(--m-border));
    background: var(--m-surface);
  }

  .mango-scene-root-card:focus-visible {
    outline: 2px solid var(--m-primary);
    outline-offset: 2px;
  }

  .mango-scene-item-card-active {
    border-color: var(--m-primary);
    background: color-mix(in srgb, var(--m-primary) 7%, var(--m-surface));
  }

  .mango-scene-item-card-dragging {
    opacity: 0.55;
  }

  .mango-scene-root-label,
  .mango-scene-root-meta {
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .mango-scene-root-name {
    overflow: hidden;
    margin-top: 4px;
    color: var(--m-text);
    font-size: 14px;
    font-weight: 600;
    line-height: 20px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-scene-root-meta {
    margin-top: 4px;
  }

  .mango-scene-item-drag {
    display: flex;
    align-self: stretch;
    align-items: center;
    justify-content: center;
    width: 18px;
    color: var(--m-muted);
    font-size: 14px;
    line-height: 1;
    user-select: none;
  }

  .mango-scene-item-content {
    min-width: 0;
  }

  .mango-scene-item-content :deep(.arco-select),
  .mango-scene-item-content :deep(.arco-input-wrapper) {
    width: 100%;
  }

  .mango-scene-item-content :deep(.arco-input-wrapper) {
    margin-top: 8px;
  }

  .mango-scene-item-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    margin-top: 8px;
  }

  .mango-scene-item-hint {
    overflow: hidden;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-scene-preview-panel {
    min-width: 0;
    min-height: 0;
  }

  .mango-preview-spin :deep(> .mango-panel-spin__content) {
    height: 100%;
    min-height: 0;
  }
</style>
