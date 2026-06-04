<template>
  <TableBody class="template-preview-page mango-detail-workbench-page">
    <template #header>
      <div class="mango-detail-toolbar">
        <div class="mango-detail-heading">
          <div class="mango-detail-title">{{ previewTitle }}</div>
          <div class="mango-detail-subtitle">
            {{ canDebugText }}
          </div>
        </div>
        <a-space class="mango-detail-actions" wrap>
          <a-button size="small" type="primary" :loading="saving" @click="saveTemplateConfig">
            保存字段配置
          </a-button>
          <a-button size="small" :loading="syncLoading" @click="confirmSyncTemplateFields">
            同步实体规则
          </a-button>
          <a-button
            size="small"
            status="success"
            :disabled="!previewResult.can_debug_run"
            :loading="debugLoading"
            @click="debugRun"
          >
            调试运行
          </a-button>
          <a-button size="small" @click="goBack">返回</a-button>
        </a-space>
      </div>
    </template>

    <template #default>
      <a-spin
        :loading="initialPageLoading"
        class="preview-spin"
        tip="模板配置加载中..."
      >
        <div v-if="templateForm.entity" class="scene-config-workbench">
          <a-spin :loading="scenePanelLoading" class="scene-items-spin" tip="编排数据加载中...">
            <aside class="scene-items-card">
              <div class="scene-items-header">
                <div>
                  <div class="scene-items-title">场景编排</div>
                  <div class="scene-items-subtitle">点击模板查看局部依赖，拖动调整子模板创建顺序</div>
                </div>
                <a-tag
                  size="small"
                  :color="sceneAutoSaveMeta.color"
                  class="scene-save-status"
                  @click="retrySceneAutoSave"
                >
                  {{ sceneAutoSaveMeta.text }}
                </a-tag>
                <a-button size="small" type="primary" long @click="addSceneItem"
                  >添加关联模板</a-button
                >
              </div>
              <div class="scene-items-list">
                <div
                  :class="[
                    'scene-root-card',
                    { 'scene-item-card-active': activeSceneNodeKey === 'root' },
                  ]"
                  @click="activeSceneNodeKey = 'root'"
                >
                  <div class="scene-root-label">主模板</div>
                  <div class="scene-root-name">{{
                    templateForm.name || pageRecord?.name || '-'
                  }}</div>
                  <div class="scene-root-meta">场景入口，优先创建</div>
                </div>
                <div
                  v-for="(item, index) in templateForm.items || []"
                  :key="item._key || item.id || index"
                  :class="[
                    'scene-item-card',
                    { 'scene-item-card-active': activeSceneNodeKey === getSceneItemFocusKey(item) },
                    { 'scene-item-card-dragging': draggingSceneItemKey === getSceneItemKey(item) },
                  ]"
                  draggable="true"
                  @click="activeSceneNodeKey = getSceneItemFocusKey(item)"
                  @dragstart="onSceneItemDragStart(item)"
                  @dragover.prevent
                  @drop="onSceneItemDrop(item)"
                  @dragend="onSceneItemDragEnd"
                >
                  <div class="scene-item-drag" title="拖动排序">::</div>
                  <div class="scene-item-content">
                    <a-select
                      v-model="item.child_template"
                      :options="sceneTemplateOptions"
                      :field-names="{ value: 'id', label: 'name' }"
                      allow-search
                      allow-clear
                      placeholder="选择关联模板"
                      @change="() => onSceneItemTemplateChange(item)"
                    />
                    <a-input
                      v-model="item.name"
                      placeholder="关联名称"
                      @blur="() => onSceneItemNameBlur(item)"
                    />
                    <div class="scene-item-footer">
                      <span class="scene-item-hint">共享主场景上下文</span>
                      <a-button
                        size="mini"
                        status="danger"
                        type="text"
                        @click="removeSceneItem(index)"
                      >
                        移除
                      </a-button>
                    </div>
                  </div>
                </div>
                <div v-if="!templateForm.items?.length" class="mango-empty-state scene-empty">
                  暂未添加关联模板
                </div>
              </div>
            </aside>
          </a-spin>
          <section class="scene-preview-panel">
            <DataFactoryDependencyPreview
              :dependency-tree="previewResult.dependency_tree"
              :can-debug-run="previewResult.can_debug_run"
              :generator-options="enumStore.data_factory_generator_type"
              :root-fields="fieldRows"
              :editable-node-configs="editableNodeConfigs"
              v-model:field-overrides="templateForm.field_overrides"
              v-model:output-config="templateForm.output_config"
              :dependency-template-options="dependencyTemplateOptions"
              :load-dependency-template-options="loadDependencyTemplateOptions"
              :focus-node-key="activeSceneNodeKey"
              :flow-loading="previewLoading"
              :field-loading="fieldPanelLoading"
              editable-root
              field-table-scroll-y="calc(100vh - 320px)"
              @open-template="openDependencyTemplate"
              @update-node-field-overrides="updateSceneItemOverrides"
            />
          </section>
        </div>
        <div v-else class="mango-empty-state">场景模板未绑定实体</div>
      </a-spin>
    </template>
  </TableBody>

  <a-modal v-model:visible="debugVisible" title="调试结果" width="760px" :footer="false">
    <a-space v-if="debugResult" direction="vertical" fill>
      <a-alert v-if="debugResult.execution_no" type="success"
        >执行编号：{{ debugResult.execution_no }}</a-alert
      >
      <JsonDisplay :data="debugResult.context || debugResult" />
      <a-button
        v-if="debugResult.execution_id"
        :loading="debugCleanupLoading"
        status="danger"
        @click="debugCleanup"
        >清理调试数据</a-button
      >
    </a-space>
  </a-modal>
</template>

<script lang="ts" setup>
  import DataFactoryDependencyPreview from '@/components/DataFactory/DataFactoryDependencyPreview.vue'
  import JsonDisplay from '@/components/display/JsonDisplay.vue'
  import {
    getDataFactoryField,
    getDataFactoryTemplate,
    postDataFactoryTemplateDebugCleanup,
    postDataFactoryTemplateDebugRun,
    postDataFactoryTemplatePreview,
    postDataFactoryTemplateSyncFields,
    putDataFactoryTemplate,
  } from '@/api/data-factory'
  import { useEnum } from '@/store/modules/get-enum'
  import useUserStore from '@/store/modules/user'
  import { usePageData } from '@/store/page-data'
  import { Message, Modal } from '@arco-design/web-vue'
  import { computed, onMounted, reactive, ref, watch } from 'vue'
  import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'

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
  const previewResult = ref<any>({})
  const debugLoading = ref(false)
  const debugVisible = ref(false)
  const debugResult = ref<any>({})
  const debugCleanupLoading = ref(false)
  const saving = ref(false)
  const syncLoading = ref(false)
  const sceneAutoSaving = ref(false)
  const sceneAutoSaveStatus = ref<'idle' | 'saving' | 'saved' | 'error'>('idle')
  const sceneSavedItemOverrides = ref<Record<string, Record<string, any>>>({})
  const savedFieldConfigSignature = ref('')
  const fieldRows = ref<any[]>([])
  const sceneTemplateOptions = ref<any[]>([])
  const itemFieldsMap = ref<Record<string, any[]>>({})
  const dependencyTemplateOptions = ref<Record<string, any[]>>({})
  const draggingSceneItemKey = ref('')
  const activeSceneNodeKey = ref('root')
  const templateForm = reactive<any>({
    id: null,
    field_overrides: {},
    output_config: [],
    items: [],
  })
  const pageRecord = computed<any>(() => pageData.record || {})
  const previewContext = computed<any>(() => pageRecord.value?.preview_context || {})
  const templateId = computed(() => route.query.template_id || previewContext.value.template_id)
  const previewTitle = computed(() => {
    const id = templateForm.id || templateId.value || '-'
    const name = templateForm.name || pageRecord.value?.name || '-'
    return `场景模板配置 / ${id} / ${name}`
  })
  const editableNodeConfigs = computed(() => {
    const configs: Record<string, any> = {
      root: {
        fields: fieldRows.value,
        fieldOverrides: templateForm.field_overrides || {},
        outputConfig: templateForm.output_config || [],
      },
    }
    ;(templateForm.items || []).forEach((item: any) => {
      configs[`item:${getSceneItemKey(item)}`] = {
        fields: itemFieldsMap.value[getSceneItemKey(item)] || [],
        fieldOverrides: item.field_overrides || {},
        outputConfig: [],
      }
    })
    return configs
  })
  const canDebugText = computed(() => {
    if (!previewResult.value.dependency_tree) {
      return '维护字段覆盖配置，并查看依赖实体关系'
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
  const scenePanelLoading = computed(() => templateLoading.value || sceneOptionsLoading.value)
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
      !firstPreviewReady.value ||
      !editableFieldsReady.value
  )

  function buildPreviewPayload() {
    return {
      template_id: templateId.value,
      overrides: templateForm.field_overrides || {},
      output_config: templateForm.output_config,
      items: normalizeSceneItems(),
      test_env: route.query.test_env || userStore.selected_environment,
    }
  }

  function resetTemplateForm(record: any) {
    Object.keys(templateForm).forEach((key) => delete templateForm[key])
    Object.assign(templateForm, {
      id: record?.id || templateId.value,
      project_product: record?.project_product?.id || record?.project_product || null,
      module: record?.module?.id || record?.module || null,
      entity: record?.entity?.id || record?.entity || null,
      name: record?.name || '',
      description: record?.description || '',
      cleanup_strategy: record?.cleanup_strategy || 2,
      is_default: record?.is_default || false,
      config_status: record?.config_status ?? 0,
      status: record?.status || 1,
      field_overrides: previewContext.value.overrides || record?.field_overrides || {},
      output_config: previewContext.value.output_config || record?.output_config || [],
      items: normalizeLoadedItems(record?.items || []),
    })
    snapshotSceneItemOverrides(record?.items || [])
    snapshotFieldConfig()
  }

  function loadTemplate() {
    const cached =
      pageRecord.value?.id &&
      String(pageRecord.value.id) === String(templateId.value) &&
      pageRecord.value.project_product &&
      pageRecord.value.module &&
      pageRecord.value.entity &&
      Object.prototype.hasOwnProperty.call(pageRecord.value, 'field_overrides')
        ? pageRecord.value
        : null
    if (cached) {
      resetTemplateForm(cached)
      return Promise.resolve(cached)
    }
    templateLoading.value = true
    return getDataFactoryTemplate({ id: templateId.value, page: 1, pageSize: 1 })
      .then((res) => {
        const record = (res.data || [])[0]
        resetTemplateForm(record || {})
        return record
      })
      .finally(() => {
        templateLoading.value = false
      })
  }

  function reloadPageData() {
    previewResult.value = {}
    dependencyTemplateOptions.value = {}
    itemFieldsMap.value = {}
    firstPreviewReady.value = false
    editableFieldsReady.value = false
    return loadTemplate()
      .then(() => Promise.all([loadSceneTemplateOptions(), loadPreview()]))
      .then(loadEditableFieldDefinitions)
  }

  function loadEditableFieldDefinitions() {
    editableFieldsReady.value = false
    return Promise.all([loadTemplateFields(), loadSceneItemFields()]).finally(() => {
      editableFieldsReady.value = true
    })
  }

  function loadTemplateFields() {
    if (!templateForm.entity) {
      fieldRows.value = []
      return Promise.resolve()
    }
    fieldLoading.value = true
    return getDataFactoryField({ entity: templateForm.entity })
      .then((res) => {
        fieldRows.value = res.data || []
        return preloadDependencyTemplateOptions()
      })
      .finally(() => {
        fieldLoading.value = false
      })
  }

  function loadPreview() {
    if (!templateId.value) {
      Message.error('场景模板不存在，请返回后重试')
      firstPreviewReady.value = true
      return Promise.resolve()
    }
    previewLoading.value = true
    return postDataFactoryTemplatePreview(buildPreviewPayload())
      .then((res) => {
        previewResult.value = res.data || {}
      })
      .finally(() => {
        previewLoading.value = false
        firstPreviewReady.value = true
      })
  }

  function debugRun() {
    if (!previewResult.value.can_debug_run) {
      Message.warning('当前依赖链路还有字段未配置，暂不能调试运行')
      return
    }
    debugLoading.value = true
    postDataFactoryTemplateDebugRun({
      template_id: templateId.value,
      overrides: templateForm.field_overrides || {},
      test_env: route.query.test_env || userStore.selected_environment,
    })
      .then((res) => {
        debugResult.value = res.data || {}
        debugVisible.value = true
      })
      .finally(() => {
        debugLoading.value = false
      })
  }

  function saveTemplateConfig() {
    if (!templateForm.id) {
      Message.error('场景模板不存在，请返回后重试')
      return
    }
    saving.value = true
    putDataFactoryTemplate({
      id: templateForm.id,
      field_overrides: templateForm.field_overrides || {},
      output_config: templateForm.output_config || [],
      items: normalizeSceneItems(),
      test_env: route.query.test_env || userStore.selected_environment,
    })
      .then((res) => {
        Message.success(res.msg)
        resetTemplateForm(res.data || templateForm)
        snapshotFieldConfig()
        loadSceneItemFields().then(loadPreview)
      })
      .finally(() => {
        saving.value = false
      })
  }

  function syncTemplateFields() {
    if (!templateForm.id) {
      Message.error('场景模板不存在，请返回后重试')
      return
    }
    syncLoading.value = true
    return postDataFactoryTemplateSyncFields({
      id: templateForm.id,
      test_env: route.query.test_env || userStore.selected_environment,
    })
      .then((res) => {
        templateForm.field_overrides = res.data?.field_overrides || {}
        snapshotFieldConfig()
        Message.success(res.msg)
        return loadTemplateFields().then(loadPreview)
      })
      .finally(() => {
        syncLoading.value = false
      })
  }

  function confirmSyncTemplateFields() {
    if (!templateForm.id) {
      Message.error('场景模板不存在，请返回后重试')
      return
    }
    Modal.confirm({
      title: '同步实体规则',
      content: '同步后会使用当前实体字段规则覆盖场景模板字段配置，确认继续？',
      okText: '确认同步',
      cancelText: '取消',
      onBeforeOk: () => syncTemplateFields(),
    })
  }

  function loadDependencyTemplateOptions(row: any) {
    const dependencyEntityId = row.generator_config?.dependency_entity_id
    const projectProduct = templateForm.project_product
    if (!dependencyEntityId || !projectProduct) {
      return Promise.resolve()
    }
    const cacheKey = String(dependencyEntityId)
    if (dependencyTemplateOptions.value[cacheKey]) {
      return Promise.resolve()
    }
    return getDataFactoryTemplate({
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
    const tasks = fieldRows.value
      .filter((row: any) => row.generator_config?.dependency_entity_id)
      .map((row) => loadDependencyTemplateOptions(row))
    if (!tasks.length) {
      return Promise.resolve([])
    }
    dependencyTemplateLoading.value = true
    return Promise.all(tasks).finally(() => {
      dependencyTemplateLoading.value = false
    })
  }

  function loadSceneTemplateOptions() {
    if (!templateForm.project_product) {
      sceneTemplateOptions.value = []
      return Promise.resolve()
    }
    sceneOptionsLoading.value = true
    return getDataFactoryTemplate({
      project_product: templateForm.project_product,
      page: 1,
      pageSize: 9999,
    })
      .then((res) => {
        sceneTemplateOptions.value = (res.data || []).filter(
          (item: any) => String(item.id) !== String(templateForm.id)
        )
      })
      .finally(() => {
        sceneOptionsLoading.value = false
      })
  }

  function normalizeLoadedItems(items: any[]) {
    return (items || [])
      .map((item: any, index: number) => ({
        id: item.id,
        _key: item.id || `new-${Date.now()}-${index}`,
        child_template: item.child_template?.id || item.child_template || null,
        child_template_detail: item.child_template_detail,
        name: item.name || item.child_template_detail?.name || '',
        sort: item.sort ?? index * 10,
        field_overrides: item.field_overrides || {},
      }))
      .sort((left: any, right: any) => Number(left.sort || 0) - Number(right.sort || 0))
  }

  function normalizeSceneItems() {
    return (templateForm.items || [])
      .map((item: any, index: number) => ({
        id: typeof item.id === 'number' ? item.id : undefined,
        child_template: item.child_template,
        name: item.name || getSceneTemplateName(item.child_template) || `关联模板${index + 1}`,
        sort: index * 10,
        field_overrides: item.field_overrides || {},
      }))
      .filter((item: any) => item.child_template)
  }

  function normalizeSceneArrangementItems() {
    return (templateForm.items || [])
      .map((item: any, index: number) => {
        const key = getSceneItemKey(item)
        return {
          id: typeof item.id === 'number' ? item.id : undefined,
          child_template: item.child_template,
          name: item.name || getSceneTemplateName(item.child_template) || `关联模板${index + 1}`,
          sort: index * 10,
          field_overrides: sceneSavedItemOverrides.value[key] || {},
        }
      })
      .filter((item: any) => item.child_template)
  }

  function snapshotSceneItemOverrides(items: any[]) {
    const next: Record<string, Record<string, any>> = {}
    normalizeLoadedItems(items).forEach((item: any) => {
      next[getSceneItemKey(item)] = item.field_overrides || {}
    })
    sceneSavedItemOverrides.value = next
  }

  function buildFieldConfigSignature() {
    return JSON.stringify({
      field_overrides: templateForm.field_overrides || {},
      output_config: templateForm.output_config || [],
      item_field_overrides: (templateForm.items || [])
        .filter((item: any) => Object.keys(item.field_overrides || {}).length)
        .map((item: any) => ({
          key: item.id || item.child_template || item._key,
          field_overrides: item.field_overrides || {},
        })),
    })
  }

  function snapshotFieldConfig() {
    savedFieldConfigSignature.value = buildFieldConfigSignature()
  }

  function hasUnsavedFieldConfig() {
    return savedFieldConfigSignature.value && savedFieldConfigSignature.value !== buildFieldConfigSignature()
  }

  function getSceneItemKey(item: any) {
    return String(item.id || item._key || item.name)
  }

  function getSceneItemFocusKey(item: any) {
    return `item:${getSceneItemKey(item)}`
  }

  function getSceneTemplateName(templateId: any) {
    return (
      sceneTemplateOptions.value.find((item: any) => String(item.id) === String(templateId))
        ?.name || ''
    )
  }

  function getSceneTemplateEntity(templateId: any) {
    const template = sceneTemplateOptions.value.find(
      (item: any) => String(item.id) === String(templateId)
    )
    return template?.entity?.id || template?.entity
  }

  function addSceneItem() {
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
    const removedKey = getSceneItemFocusKey(templateForm.items[index])
    templateForm.items.splice(index, 1)
    if (activeSceneNodeKey.value === removedKey) {
      activeSceneNodeKey.value = 'root'
    }
    autoSaveSceneItems()
  }

  function reorderSceneItems(data: any[]) {
    templateForm.items = (data || []).map((item: any, index: number) => ({
      ...item,
      sort: index * 10,
    }))
    autoSaveSceneItems()
  }

  function onSceneItemDragStart(item: any) {
    draggingSceneItemKey.value = getSceneItemKey(item)
  }

  function onSceneItemDrop(targetItem: any) {
    const sourceKey = draggingSceneItemKey.value
    const targetKey = getSceneItemKey(targetItem)
    if (!sourceKey || sourceKey === targetKey) {
      return
    }
    const items = [...(templateForm.items || [])]
    const sourceIndex = items.findIndex((item: any) => getSceneItemKey(item) === sourceKey)
    const targetIndex = items.findIndex((item: any) => getSceneItemKey(item) === targetKey)
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

  function onSceneItemTemplateChange(item: any) {
    if (!item.name) {
      item.name = getSceneTemplateName(item.child_template)
    }
    item.field_overrides = item.field_overrides || {}
    autoSaveSceneItems()
  }

  function onSceneItemNameBlur(item: any) {
    if (!item.child_template) {
      return
    }
    autoSaveSceneItems()
  }

  function loadSceneItemFields() {
    sceneItemFieldsLoading.value = true
    const tasks = (templateForm.items || []).map((item: any) => {
      const entityId =
        getSceneTemplateEntity(item.child_template) ||
        item.child_template_detail?.entity?.id ||
        item.child_template_detail?.entity
      if (!entityId) {
        return Promise.resolve()
      }
      const key = getSceneItemKey(item)
      return getDataFactoryField({ entity: entityId }).then((res) => {
        itemFieldsMap.value = {
          ...itemFieldsMap.value,
          [key]: res.data || [],
        }
      })
    })
    return Promise.all(tasks).finally(() => {
      sceneItemFieldsLoading.value = false
    })
  }

  function updateSceneItemOverrides(key: string, value: Record<string, any>) {
    const itemKey = key.replace(/^item:/, '')
    const item = (templateForm.items || []).find((row: any) => getSceneItemKey(row) === itemKey)
    if (!item) {
      return
    }
    item.field_overrides = value
    loadPreview()
  }

  function mergeSavedSceneItems(savedItems: any[], keepFieldDirty = false) {
    const loadedItems = normalizeLoadedItems(savedItems)
    let validIndex = 0
    const previousActiveKey = activeSceneNodeKey.value
    templateForm.items = (templateForm.items || []).map((item: any) => {
      if (!item.child_template) {
        return item
      }
      const saved = loadedItems[validIndex]
      validIndex += 1
      if (!saved) {
        return item
      }
      const previousFocusKey = getSceneItemFocusKey(item)
      const nextItem = {
        ...saved,
        field_overrides: item.field_overrides || {},
      }
      if (previousActiveKey === previousFocusKey) {
        activeSceneNodeKey.value = getSceneItemFocusKey(nextItem)
      }
      return nextItem
    })
    snapshotSceneItemOverrides(savedItems)
    if (!keepFieldDirty) {
      snapshotFieldConfig()
    }
  }

  function autoSaveSceneItems() {
    if (!templateForm.id) {
      return Promise.resolve()
    }
    sceneAutoSaving.value = true
    sceneAutoSaveStatus.value = 'saving'
    const keepFieldDirty = hasUnsavedFieldConfig()
    return putDataFactoryTemplate({
      id: templateForm.id,
      items: normalizeSceneArrangementItems(),
      test_env: route.query.test_env || userStore.selected_environment,
    })
      .then((res) => {
        mergeSavedSceneItems(res.data?.items || [], keepFieldDirty)
        sceneAutoSaveStatus.value = 'saved'
        loadSceneItemFields().then(loadPreview).catch(() => undefined)
      })
      .catch(() => {
        sceneAutoSaveStatus.value = 'error'
      })
      .finally(() => {
        sceneAutoSaving.value = false
      })
  }

  function retrySceneAutoSave() {
    if (sceneAutoSaveStatus.value !== 'error') {
      return
    }
    autoSaveSceneItems()
  }

  function debugCleanup() {
    debugCleanupLoading.value = true
    postDataFactoryTemplateDebugCleanup({ execution_id: debugResult.value.execution_id })
      .then((res) => {
        Message.success(res.msg)
      })
      .finally(() => {
        debugCleanupLoading.value = false
      })
  }

  function openDependencyTemplate(node: any) {
    if (!node?.template_id) {
      return
    }
    pageData.setRecord({
      id: node.template_id,
      name: node.template_name,
      entity: node.entity_id,
    })
    router.push({
      path: '/data-factory/template/preview',
      query: {
        template_id: node.template_id,
        test_env: route.query.test_env || userStore.selected_environment,
      },
    })
  }

  function goBack() {
    window.history.back()
  }

  onMounted(() => {
    enumStore.getEnum()
    reloadPageData()
  })

  watch(
    () => route.query.template_id,
    () => {
      reloadPageData()
    }
  )

  onBeforeRouteLeave(() => {
    if (!hasUnsavedFieldConfig()) {
      return true
    }
    return window.confirm('当前字段配置尚未保存，确认离开吗？')
  })
</script>

<style scoped>
  .template-preview-page :deep(.arco-card-body) {
    display: flex;
    flex-direction: column;
    min-height: 0;
  }

  .preview-spin {
    display: block;
    width: 100%;
    height: calc(100vh - 178px);
    min-height: 0;
    padding-top: 12px;
  }

  .scene-config-workbench {
    display: grid;
    height: 100%;
    min-height: 0;
    gap: 12px;
    grid-template-columns: 300px minmax(0, 1fr);
  }

  .scene-items-spin {
    display: block;
    height: 100%;
    min-height: 0;
  }

  .scene-items-spin :deep(.arco-spin),
  .scene-items-spin :deep(.arco-spin-children) {
    height: 100%;
    min-height: 0;
  }

  .scene-items-card {
    display: flex;
    overflow: hidden;
    flex-direction: column;
    width: 100%;
    height: 100%;
    min-height: 0;
    padding: 12px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
  }

  .scene-items-header {
    display: flex;
    align-items: flex-start;
    flex-direction: column;
    justify-content: flex-start;
    gap: 12px;
  }

  .scene-items-title {
    color: var(--m-text);
    font-size: 15px;
    font-weight: 600;
    line-height: 22px;
  }

  .scene-items-subtitle {
    margin-top: 2px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .scene-items-list {
    display: flex;
    overflow: auto;
    flex-direction: column;
    flex: 1;
    min-height: 0;
    margin-top: 12px;
    padding-right: 2px;
    padding-bottom: 2px;
    gap: 10px;
  }

  .scene-item-card {
    display: grid;
    flex-shrink: 0;
    padding: 10px 10px 10px 8px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface-soft);
    cursor: grab;
    gap: 8px;
    grid-template-columns: 18px minmax(0, 1fr);
    transition: border-color 0.2s ease, background 0.2s ease, opacity 0.2s ease;
  }

  .scene-root-card {
    flex-shrink: 0;
    padding: 10px 12px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface-soft);
    cursor: pointer;
    transition: border-color 0.2s ease, background 0.2s ease;
  }

  .scene-root-card:hover,
  .scene-item-card:hover {
    border-color: color-mix(in srgb, var(--m-primary) 28%, var(--m-border));
    background: var(--m-surface);
  }

  .scene-item-card-active {
    border-color: var(--m-primary);
    background: color-mix(in srgb, var(--m-primary) 7%, var(--m-surface));
  }

  .scene-item-card-dragging {
    opacity: 0.55;
  }

  .scene-root-label,
  .scene-root-meta {
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .scene-root-name {
    overflow: hidden;
    margin-top: 4px;
    color: var(--m-text);
    font-size: 14px;
    font-weight: 600;
    line-height: 20px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .scene-root-meta {
    margin-top: 4px;
  }

  .scene-item-drag {
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

  .scene-item-content {
    min-width: 0;
  }

  .scene-item-content :deep(.arco-select),
  .scene-item-content :deep(.arco-input-wrapper) {
    width: 100%;
  }

  .scene-item-content :deep(.arco-input-wrapper) {
    margin-top: 8px;
  }

  .scene-item-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    margin-top: 8px;
  }

  .scene-item-hint {
    overflow: hidden;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .scene-preview-panel {
    min-width: 0;
    min-height: 0;
  }

  :deep(.preview-spin > .arco-spin) {
    height: 100%;
  }

  :deep(.preview-spin .arco-spin-children) {
    height: 100%;
  }

  @media (max-width: 1px) {
    .scene-config-workbench {
      grid-template-columns: 1fr;
    }

    .scene-items-header {
      flex-direction: column;
    }
  }
</style>
