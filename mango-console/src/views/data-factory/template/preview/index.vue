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
          <a-button  size="small" type="primary" :loading="saving" @click="saveTemplateConfig" data-testid="qa-views-data-factory-template-preview-button-保存字段配置">
            保存字段配置
          </a-button>
          <a-button size="small" @click="postUpdateVisible = true">
            配置插入后回写
            <a-badge :count="templateForm.post_insert_updates?.length || 0" :max-count="99" />
          </a-button>
          <a-button
            size="small"
            :disabled="!templateForm.entity"
            :loading="entityRuleLoading"
            @click="openRootEntityRules"
            data-testid="qa-views-data-factory-template-preview-button-查看实体规则"
          >
            查看实体规则
          </a-button>
          <a-button  size="small" :loading="syncLoading" @click="confirmSyncTemplateFields" data-testid="qa-views-data-factory-template-preview-button-同步实体规则">
            同步实体规则
          </a-button>
          <a-button
            size="small"
            status="success"
            :disabled="!templateForm.id || previewLoading"
            :loading="debugLoading"
            @click="debugRun" data-testid="qa-views-data-factory-template-preview-button-调试运行"
          >
            调试运行
          </a-button>
          <VariableReferencePanel />
          <a-button class="mango-back-button" size="small" @click="goBack" data-testid="qa-views-data-factory-template-preview-button-返回">返回</a-button>
        </a-space>
      </div>
    </template>

    <template #default>
      <mango-panel-spin
        :loading="initialPageLoading"
        class="preview-spin mango-workbench-scroll-x scene-config-workbench-scroll"
        tip="模板配置加载中..."
      >
        <div v-if="templateForm.entity" class="scene-config-workbench">
          <mango-panel-spin :loading="scenePanelLoading" class="scene-items-spin" tip="编排数据加载中...">
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
                <a-button size="small" type="primary" long @click="addSceneItem" data-testid="qa-views-data-factory-template-preview-button-添加关联模板"
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
                  role="button"
                  tabindex="0"
                  :aria-pressed="activeSceneNodeKey === 'root'"
                  @keydown.enter="activeSceneNodeKey = 'root'"
                  @keydown.space.prevent="activeSceneNodeKey = 'root'"
                >
                  <div class="scene-root-label">主模板</div>
                  <div class="scene-root-name" :title="templateForm.name || pageRecord?.name">{{
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
                      :options="sceneSelectOptions"
                      :loading="sceneOptionsLoading"
                      :filter-option="false"
                      :field-names="{ value: 'id', label: 'name' }"
                      allow-search
                      allow-clear
                      placeholder="选择关联模板"
                      @popup-visible-change="(visible) => visible && loadSceneTemplateOptions('', 1)"
                      @search="(keyword) => loadSceneTemplateOptions(keyword, 1)"
                      @dropdown-reach-bottom="loadMoreSceneTemplateOptions"
                      @change="() => onSceneItemTemplateChange(item)" data-testid="qa-views-data-factory-template-preview-select-选择关联模板"
                    >
                      <template #footer v-if="sceneOptionsFailed">
                        <a-button type="text" size="small" :loading="sceneOptionsLoading" @click="loadSceneTemplateOptions(sceneOptionsKeyword, sceneOptionsPage)">加载失败，点击重试</a-button>
                      </template>
                    </a-select>
                    <a-input
                      v-model="item.name"
                      placeholder="关联名称"
                      @blur="() => onSceneItemNameBlur(item)" data-testid="qa-views-data-factory-template-preview-input-关联名称"
                    />
                    <div class="scene-item-footer">
                      <span class="scene-item-hint">共享主场景上下文</span>
                      <a-button
                        size="mini"
                        status="danger"
                        type="text"
                        @click="removeSceneItem(index)" data-testid="qa-views-data-factory-template-preview-button-移除"
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
          </mango-panel-spin>
          <section class="scene-preview-panel">
            <DataFactoryDependencyPreview
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
              :flow-loading="previewLoading"
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
        @click="debugCleanup" data-testid="qa-views-data-factory-template-preview-button-清理调试数据"
        >清理调试数据</a-button
      >
    </a-space>
  </a-modal>

  <a-modal
    v-model:visible="entityRuleVisible"
    :title="`${entityRuleRecord?.name || ''} 字段规则`"
    width="1180px"
    :footer="false"
  >
    <div class="entity-rule-toolbar">
      <a-tag color="arcoblue">当前表：{{ entityRuleRecord?.table_name || '-' }}</a-tag>
    </div>
    <div class="mango-entity-rule-table-region">
    <a-table
      class="mango-native-scroll-table"
      size="small"
      :columns="entityRuleColumns"
      :data="entityRuleRows"
      :loading="entityRuleLoading"
      :pagination="false"
      :scroll="{ x: entityRuleTableScrollWidth, y: '100%' }"
      row-key="id"
    >
      <template #columns>
        <a-table-column
          v-for="item of entityRuleColumns"
          :key="item.key"
          :align="item.align"
          :data-index="item.key"
          :fixed="item.fixed"
          :ellipsis="item.ellipsis"
          :tooltip="item.tooltip"
          :title="item.title"
          :width="item.width"
        >
          <template v-if="item.key === 'generator_type'" #cell="{ record }">
            <a-select
              :model-value="generatorTypeTitle(record.generator_type)"
              :options="[generatorTypeTitle(record.generator_type)]"
              disabled
              :title="generatorTypeTitle(record.generator_type)"
              :aria-label="`${record.name} 生成方式（只读）`"
            />
          </template>
          <template v-else-if="item.key === 'generator_config'" #cell="{ record }">
            <a-tooltip :content="getGeneratorDisplay(record).text">
              <a-select
                v-if="getGeneratorDisplay(record).enum"
                :model-value="getGeneratorDisplay(record).text"
                :options="[getGeneratorDisplay(record).text]"
                disabled
                :aria-label="`${record.name} 枚举配置（只读）`"
              />
              <a-input
                v-else
                :model-value="getGeneratorDisplay(record).text"
                readonly
                :disabled="getGeneratorDisplay(record).automatic"
                :aria-label="`${record.name} 生成配置（只读）`"
              />
            </a-tooltip>
          </template>
          <template
            v-else-if="['nullable', 'primary_key', 'autoincrement', 'db_type', 'platform_type'].includes(item.key)"
            #cell="{ record }"
          >
            <DataFactoryFieldTag :record="record" :field="item.key" />
          </template>
        </a-table-column>
      </template>
    </a-table>
    </div>
  </a-modal>

  <a-modal
    v-model:visible="postUpdateVisible"
    title="插入后回写"
    width="920px"
    :footer="false"
  >
    <a-alert type="info" class="post-update-alert">
      适用于两张表互相引用的场景。全部数据创建完成后，系统会把来源记录的真实字段值写入目标记录，并且只更新本次执行创建的那一条数据。
    </a-alert>
    <div class="post-update-list">
      <section
        v-for="(item, index) in templateForm.post_insert_updates || []"
        :key="`${item.target_node}-${item.target_field}-${index}`"
        class="post-update-rule"
      >
        <header class="post-update-rule-header">
          <div>
            <span class="post-update-rule-title">回写规则 {{ index + 1 }}</span>
            <span class="post-update-rule-summary">{{ getPostUpdateSummary(item) }}</span>
          </div>
          <a-button  size="mini" type="text" status="danger" @click="removePostInsertUpdate(index)">
            删除规则
          </a-button>
        </header>

        <div class="post-update-mapping">
          <div class="post-update-side post-update-source">
            <div class="post-update-side-title">取值来源</div>
            <label class="post-update-field">
              <span>来源节点</span>
              <a-select
                v-model="item.source_node"
                :options="sceneNodeOptions"
                placeholder="选择已创建的数据节点"
                allow-search
                @change="handlePostUpdateSourceNodeChange(item)"
              />
            </label>
            <label class="post-update-field">
              <span>来源字段</span>
              <a-select
                v-model="item.source_field"
                :options="getPostUpdateSourceFieldOptions(item)"
                placeholder="选择要取出的字段"
                allow-search
                @change="handlePostUpdateFieldChange(item)"
              />
            </label>
          </div>

          <div class="post-update-direction" aria-hidden="true">
            <span>写入</span>
            <strong>→</strong>
          </div>

          <div class="post-update-side post-update-target">
            <div class="post-update-side-title">写入目标</div>
            <label class="post-update-field">
              <span>目标节点</span>
              <a-select
                v-model="item.target_node"
                :options="sceneNodeOptions"
                placeholder="选择要更新的数据节点"
                allow-search
                @change="handlePostUpdateTargetNodeChange(item)"
              />
            </label>
            <label class="post-update-field">
              <span>目标字段</span>
              <a-select
                v-model="item.target_field"
                :options="getPostUpdateTargetFieldOptions(item.target_node)"
                placeholder="仅显示可安全回写字段"
                allow-search
                @change="handlePostUpdateFieldChange(item)"
              />
            </label>
          </div>
        </div>

        <a-alert
          :type="getPostUpdateValidation(item, index).type"
          class="post-update-validation"
        >
          {{ getPostUpdateValidation(item, index).message }}
        </a-alert>

        <details class="post-update-advanced">
          <summary>高级设置与执行详情</summary>
          <div class="post-update-advanced-content">
            <label class="post-update-order-field">
              <span>执行顺序</span>
              <a-input-number v-model="item.sort" :min="0" placeholder="数字越小越先执行" />
            </label>
            <div class="post-update-order-tip">存在多条回写规则时，数字越小越先执行。</div>
            <div
              v-if="previewResult.post_insert_updates?.[index]?.valid"
              class="post-update-sql"
            >
              {{ previewResult.post_insert_updates[index].sql_template }}
            </div>
          </div>
        </details>
      </section>
      <div v-if="!templateForm.post_insert_updates?.length" class="mango-empty-state">
        <div>暂未配置回写规则</div>
        <div class="post-update-empty-tip">例如：评分创建后，将评分 ID 写入状态表的当前评分结果字段。</div>
      </div>
    </div>
    <a-space>
      <a-button size="small" type="primary" @click="addPostInsertUpdate">添加回写规则</a-button>
      <a-button size="small" :loading="previewLoading" @click="loadPreview">检查全部规则</a-button>
    </a-space>
  </a-modal>
</template>

<script lang="ts" setup>
  import DataFactoryDependencyPreview from '@/components/DataFactory/DataFactoryDependencyPreview.vue'
  import DataFactoryFieldTag from '@/components/display/DataFactoryFieldTag.vue'
  import JsonDisplay from '@/components/display/JsonDisplay.vue'
  import VariableReferencePanel from '@/components/business/VariableReferencePanel.vue'
  import {
    getDataFactoryField,
    getDataFactoryEntity,
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
  import { entityRuleColumns, entityRuleTableScrollWidth } from './config'
  import { getGeneratorDisplay } from './generatorDisplay'

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
  const entityRuleLoading = ref(false)
  const entityRuleVisible = ref(false)
  const postUpdateVisible = ref(false)
  const entityRuleRecord = ref<any>(null)
  const entityRuleRows = ref<any[]>([])
  const sceneAutoSaving = ref(false)
  const sceneAutoSaveStatus = ref<'idle' | 'saving' | 'saved' | 'error'>('idle')
  const sceneSavedItemOverrides = ref<Record<string, Record<string, any>>>({})
  const savedFieldConfigSignature = ref('')
  const fieldRows = ref<any[]>([])
  const sceneTemplateOptions = ref<any[]>([])
  const sceneOptionsKeyword = ref('')
  const sceneOptionsPage = ref(0)
  const sceneOptionsHasMore = ref(false)
  const sceneOptionsFailed = ref(false)
  let sceneOptionsRequest = 0
  const sceneSelectOptions = computed(() => {
    const selected = (templateForm.items || []).map((item: any) => item.child_template_detail).filter(Boolean)
    return [...new Map([...selected, ...sceneTemplateOptions.value].map((item: any) => [String(item.id), item])).values()]
  })
  const itemFieldsMap = ref<Record<string, any[]>>({})
  const dependencyTemplateOptions = ref<Record<string, any[]>>({})
  const draggingSceneItemKey = ref('')
  const activeSceneNodeKey = ref('root')
  const templateForm = reactive<any>({
    id: null,
    field_overrides: {},
    output_config: [],
    post_insert_updates: [],
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
  const sceneNodeOptions = computed(() => [
    {
      label: `主模板：${templateForm.name || '-'}${
        previewResult.value?.entity?.table_name
          ? `｜${previewResult.value.entity.table_name}`
          : ''
      }`,
      value: 'root',
    },
    ...(templateForm.items || [])
      .filter((item: any) => item.child_template && (item.id || item.name))
      .map((item: any) => ({
        label: `关联模板：${item.name || getSceneTemplateName(item.child_template)}${
          item.child_template_detail?.entity?.table_name
            ? `｜${item.child_template_detail.entity.table_name}`
            : ''
        }`,
        value: `item:${item.id || item.name}`,
      })),
  ])
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
      !firstPreviewReady.value ||
      !editableFieldsReady.value
  )

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

  function resetTemplateForm(record: any) {
    Object.keys(templateForm).forEach((key) => delete templateForm[key])
    Object.assign(templateForm, {
      id: record?.id || templateId.value,
      project_product: record?.project_product?.id || record?.project_product || null,
      module: record?.module?.id || record?.module || null,
      entity: record?.entity?.id || record?.entity || null,
      name: record?.name || '',
      description: record?.description || '',
      cleanup_strategy: record?.cleanup_strategy ?? 1,
      is_default: record?.is_default || false,
      config_status: record?.config_status ?? 0,
      status: record?.status || 1,
      field_overrides: previewContext.value.overrides || record?.field_overrides || {},
      output_config: previewContext.value.output_config || record?.output_config || [],
      post_insert_updates: record?.post_insert_updates || [],
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
    return getDataFactoryTemplate({ id: templateId.value, page: 1, pageSize: 1 }, 30000)
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
    sceneOptionsRequest += 1
    sceneOptionsLoading.value = false
    sceneTemplateOptions.value = []
    sceneOptionsPage.value = 0
    sceneOptionsHasMore.value = false
    sceneOptionsFailed.value = false
    previewResult.value = {}
    dependencyTemplateOptions.value = {}
    itemFieldsMap.value = {}
    firstPreviewReady.value = false
    editableFieldsReady.value = false
    return loadTemplate()
      .then(() => Promise.all([loadPreview(), loadEditableFieldDefinitions()]))
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
    if (hasUnsavedFieldConfig()) {
      Message.warning('请先保存字段和插入后回写配置，再调试运行')
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
      post_insert_updates: templateForm.post_insert_updates || [],
      items: normalizeSceneItems(),
    })
      .then((res) => {
        if (Number(res.data?.config_status) === 0) {
          Message.warning('配置已保存，待校验后可执行；请在模板列表完成校验')
        } else {
          Message.success(res.msg)
        }
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
        templateForm.items = (templateForm.items || []).map((item: any) => ({
          ...item,
          field_overrides: {},
        }))
        snapshotSceneItemOverrides(templateForm.items || [])
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
      content: '同步后会清空当前场景模板字段覆盖，使用实体字段规则作为默认生成方式，确认继续？',
      okText: '确认同步',
      cancelText: '取消',
      onBeforeOk: () => syncTemplateFields(),
    })
  }

  function openRootEntityRules() {
    if (!templateForm.entity) {
      Message.warning('当前场景模板未绑定数据实体')
      return
    }
    entityRuleVisible.value = true
    entityRuleLoading.value = true
    entityRuleRecord.value = null
    entityRuleRows.value = []
    Promise.all([
      getDataFactoryEntity({ id: templateForm.entity, page: 1, pageSize: 1 }),
      getDataFactoryField({ entity: templateForm.entity }),
    ])
      .then(([entityRes, fieldRes]) => {
        entityRuleRecord.value = (entityRes.data || [])[0] || null
        entityRuleRows.value = fieldRes.data || []
        if (!entityRuleRecord.value) {
          Message.warning('数据实体不存在或已被删除')
        }
      })
      .finally(() => {
        entityRuleLoading.value = false
      })
  }

  function generatorTypeTitle(value: any) {
    return (
      (enumStore.data_factory_generator_type || []).find(
        (item: any) => Number(item.key) === Number(value)
      )?.title || value || '-'
    )
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

  function loadSceneTemplateOptions(keyword = '', page = 1) {
    if (!templateForm.project_product) {
      sceneTemplateOptions.value = []
      return Promise.resolve()
    }
    const requestId = ++sceneOptionsRequest
    const productId = templateForm.project_product
    sceneOptionsKeyword.value = keyword
    sceneOptionsPage.value = page
    sceneOptionsFailed.value = false
    sceneOptionsLoading.value = true
    return getDataFactoryTemplate({
      project_product: productId,
      ...(keyword.trim() ? { name: keyword.trim() } : {}),
      page,
      pageSize: 30,
    }, 30000)
      .then((res) => {
        if (requestId !== sceneOptionsRequest) return
        const rows = res.data || []
        const candidates = rows.filter(
          (item: any) => String(item.id) !== String(templateForm.id)
        )
        sceneTemplateOptions.value = page === 1 ? candidates : [...sceneTemplateOptions.value, ...candidates]
        sceneOptionsHasMore.value = page * 30 < res.totalSize
      })
      .catch(() => {
        if (requestId !== sceneOptionsRequest) return
        sceneOptionsFailed.value = true
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
      post_insert_updates: templateForm.post_insert_updates || [],
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
      sceneSelectOptions.value.find((item: any) => String(item.id) === String(templateId))
        ?.name || ''
    )
  }

  function getSceneTemplateEntity(templateId: any) {
    const template = sceneSelectOptions.value.find(
      (item: any) => String(item.id) === String(templateId)
    )
    return template?.entity?.id || template?.entity
  }

  function getSceneItemByNode(node: string) {
    if (!node || node === 'root') {
      return null
    }
    const reference = String(node).replace(/^item:/, '')
    return (templateForm.items || []).find(
      (item: any) => String(item.id) === reference || String(item.name) === reference
    )
  }

  function getPostUpdateNodeFields(node: string) {
    if (!node) {
      return []
    }
    if (node === 'root') {
      return fieldRows.value || []
    }
    const sceneItem = getSceneItemByNode(node)
    return sceneItem ? itemFieldsMap.value[getSceneItemKey(sceneItem)] || [] : []
  }

  function getPostUpdateNodeOverrides(node: string) {
    if (!node || node === 'root') {
      return templateForm.field_overrides || {}
    }
    const sceneItem = getSceneItemByNode(node)
    return {
      ...(sceneItem?.child_template_detail?.field_overrides || {}),
      ...(sceneItem?.field_overrides || {}),
    }
  }

  function getEffectiveGeneratorType(node: string, field: any) {
    return getPostUpdateNodeOverrides(node)?.[field.name]?.generator_type ?? field.generator_type
  }

  function getPostUpdateField(node: string, fieldName: string) {
    return getPostUpdateNodeFields(node).find((field: any) => field.name === fieldName)
  }

  function formatPostUpdateFieldOption(node: string, field: any) {
    const tags = []
    if (field.primary_key) tags.push('主键')
    if (field.autoincrement) tags.push('自增')
    if (field.nullable) tags.push('可空')
    if (getEffectiveGeneratorType(node, field) === 0) tags.push('已跳过')
    if (field.platform_type) tags.push(field.platform_type)
    const businessName = field.label && field.label !== field.name ? `${field.label}｜` : ''
    return `${businessName}${field.name}${tags.length ? ` · ${tags.join(' · ')}` : ''}`
  }

  function getPostUpdateTargetFieldOptions(node: string) {
    return getPostUpdateNodeFields(node)
      .filter(
        (field: any) =>
          field.nullable &&
          !field.primary_key &&
          getEffectiveGeneratorType(node, field) === 0
      )
      .map((field: any) => ({
        label: formatPostUpdateFieldOption(node, field),
        value: field.name,
      }))
  }

  function getPostUpdateSourceFieldOptions(item: any) {
    const targetField = getPostUpdateField(item.target_node, item.target_field)
    return getPostUpdateNodeFields(item.source_node)
      .filter(
        (field: any) => !targetField || field.platform_type === targetField.platform_type
      )
      .map((field: any) => ({
        label: formatPostUpdateFieldOption(item.source_node, field),
        value: field.name,
      }))
  }

  function getPostUpdateNodeLabel(node: string) {
    return sceneNodeOptions.value.find((option: any) => option.value === node)?.label || '未选择节点'
  }

  function getPostUpdateFieldLabel(node: string, fieldName: string) {
    const field = getPostUpdateField(node, fieldName)
    if (!field) return fieldName || '未选择字段'
    return field.label && field.label !== field.name
      ? `${field.label}（${field.name}）`
      : field.name
  }

  function getPostUpdateSummary(item: any) {
    if (!item.source_node || !item.source_field || !item.target_node || !item.target_field) {
      return '请选择取值来源和写入目标'
    }
    return `将 ${getPostUpdateNodeLabel(item.source_node)} 的 ${getPostUpdateFieldLabel(
      item.source_node,
      item.source_field
    )} 写入 ${getPostUpdateNodeLabel(item.target_node)} 的 ${getPostUpdateFieldLabel(
      item.target_node,
      item.target_field
    )}`
  }

  function clearPostUpdatePreview() {
    previewResult.value = {
      ...previewResult.value,
      post_insert_updates: [],
    }
  }

  function selectOnlyPostUpdateOption(item: any, key: string, options: any[]) {
    if (!options.some((option: any) => option.value === item[key])) {
      item[key] = options.length === 1 ? options[0].value : ''
    }
  }

  function handlePostUpdateSourceNodeChange(item: any) {
    selectOnlyPostUpdateOption(item, 'source_field', getPostUpdateSourceFieldOptions(item))
    clearPostUpdatePreview()
  }

  function handlePostUpdateTargetNodeChange(item: any) {
    selectOnlyPostUpdateOption(
      item,
      'target_field',
      getPostUpdateTargetFieldOptions(item.target_node)
    )
    selectOnlyPostUpdateOption(item, 'source_field', getPostUpdateSourceFieldOptions(item))
    clearPostUpdatePreview()
  }

  function handlePostUpdateFieldChange(item: any) {
    selectOnlyPostUpdateOption(item, 'source_field', getPostUpdateSourceFieldOptions(item))
    clearPostUpdatePreview()
  }

  function getPostUpdateValidation(item: any, index: number) {
    if (!item.source_node || !item.source_field || !item.target_node || !item.target_field) {
      return { type: 'warning', message: '请完整选择来源节点、来源字段、目标节点和目标字段。' }
    }
    const targetField = getPostUpdateField(item.target_node, item.target_field)
    const sourceField = getPostUpdateField(item.source_node, item.source_field)
    if (!targetField || !sourceField) {
      return { type: 'error', message: '所选字段已不存在，请重新选择。' }
    }
    if (
      !targetField.nullable ||
      targetField.primary_key ||
      getEffectiveGeneratorType(item.target_node, targetField) !== 0
    ) {
      return {
        type: 'error',
        message: '目标字段必须可空、不能是主键，并且需要在字段规则中配置为“跳过”。',
      }
    }
    if (sourceField.platform_type !== targetField.platform_type) {
      return {
        type: 'error',
        message: `字段类型不一致：来源为 ${sourceField.platform_type}，目标为 ${targetField.platform_type}。`,
      }
    }
    const checkedResult = previewResult.value.post_insert_updates?.[index]
    if (checkedResult?.valid === false) {
      return { type: 'error', message: checkedResult.message || '后端检查未通过，请调整配置。' }
    }
    if (checkedResult?.valid) {
      return { type: 'success', message: '检查通过，将按本次 execution 生成的目标主键安全回写。' }
    }
    return { type: 'info', message: '配置完整，请点击“检查全部规则”确认可执行 SQL。' }
  }

  function addPostInsertUpdate() {
    const item = {
      target_node: 'root',
      target_field: '',
      source_node: sceneNodeOptions.value[1]?.value || '',
      source_field: '',
      sort: (templateForm.post_insert_updates?.length || 0) * 10,
    }
    templateForm.post_insert_updates = [...(templateForm.post_insert_updates || []), item]
    handlePostUpdateTargetNodeChange(item)
    handlePostUpdateSourceNodeChange(item)
  }

  function removePostInsertUpdate(index: number) {
    templateForm.post_insert_updates.splice(index, 1)
    loadPreview()
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
    item.child_template_detail = sceneSelectOptions.value.find((option: any) => String(option.id) === String(item.child_template)) || null
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
  .template-preview-page :deep(> .arco-card-body) {
    display: flex;
    flex-direction: column;
    min-height: 0;
  }

  .preview-spin {
    display: block;
    box-sizing: border-box;
    width: 100%;
    height: 100%;
    min-height: 0;
    padding-top: var(--m-page-gap);
  }

  .entity-rule-toolbar {
    margin-bottom: var(--m-page-gap);
  }

  .mango-entity-rule-table-region {
    height: min(460px, 65vh);
    min-width: 0;
    min-height: 0;
    overflow: hidden;
  }

  .post-update-alert {
    margin-bottom: var(--m-page-gap);
  }

  .post-update-list {
    display: flex;
    flex-direction: column;
    margin-bottom: var(--m-page-gap);
    gap: 10px;
  }

  .post-update-rule {
    min-width: 0;
    padding: 12px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface-soft);
  }

  .post-update-rule-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    min-width: 0;
    margin-bottom: 10px;
    gap: 12px;
  }

  .post-update-rule-header > div {
    display: flex;
    flex: 1;
    align-items: baseline;
    min-width: 0;
    gap: 10px;
  }

  .post-update-rule-title {
    flex: none;
    color: var(--m-text);
    font-weight: 600;
  }

  .post-update-rule-summary {
    overflow: hidden;
    color: var(--m-muted);
    font-size: 12px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .post-update-mapping {
    display: grid;
    align-items: stretch;
    min-width: 0;
    gap: 10px;
    grid-template-columns: minmax(0, 1fr) 54px minmax(0, 1fr);
  }

  .post-update-side {
    display: grid;
    min-width: 0;
    padding: 10px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-sm);
    background: var(--m-surface);
    gap: 8px;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  }

  .post-update-side-title {
    color: var(--m-text);
    font-weight: 600;
    grid-column: 1 / -1;
  }

  .post-update-source .post-update-side-title {
    color: var(--m-warning);
  }

  .post-update-target .post-update-side-title {
    color: var(--m-primary);
  }

  .post-update-field,
  .post-update-order-field {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 4px;
  }

  .post-update-field > span,
  .post-update-order-field > span {
    color: var(--m-text-2);
    font-size: 12px;
  }

  .post-update-field :deep(.arco-select-view),
  .post-update-order-field :deep(.arco-input-wrapper) {
    width: 100%;
  }

  .post-update-direction {
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--m-muted);
    flex-direction: column;
    font-size: 12px;
    gap: 2px;
  }

  .post-update-direction strong {
    color: var(--m-warning);
    font-size: 22px;
    font-weight: 500;
    line-height: 1;
  }

  .post-update-validation {
    margin-top: 10px;
  }

  .post-update-advanced {
    margin-top: 8px;
    color: var(--m-text-2);
    font-size: 12px;
  }

  .post-update-advanced summary {
    width: fit-content;
    color: var(--m-primary);
    cursor: pointer;
    user-select: none;
  }

  .post-update-advanced-content {
    display: grid;
    align-items: end;
    margin-top: 8px;
    padding: 10px;
    border-radius: var(--m-radius-sm);
    background: var(--m-surface);
    gap: 8px 12px;
    grid-template-columns: 160px minmax(0, 1fr);
  }

  .post-update-order-tip {
    padding-bottom: 7px;
    color: var(--m-muted);
  }

  .post-update-sql {
    overflow-x: auto;
    padding: 8px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-sm);
    background: var(--m-code-bg);
    color: var(--m-code-text);
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    grid-column: 1 / -1;
    white-space: nowrap;
  }

  .post-update-empty-tip {
    margin-top: 4px;
    color: var(--m-muted);
    font-size: 12px;
  }

  @media (max-width: 900px) {
    .post-update-mapping {
      grid-template-columns: minmax(0, 1fr);
    }

    .post-update-direction strong {
      transform: rotate(90deg);
    }
  }

  .scene-config-workbench {
    display: grid;
    height: 100%;
    min-height: 0;
    gap: var(--m-page-gap);
    grid-template-columns: 300px minmax(0, 1fr);
  }

  .scene-config-workbench-scroll {
    --mango-workbench-min-width: 980px;
  }

  .scene-config-workbench-scroll .scene-config-workbench {
    min-width: var(--mango-workbench-min-width);
  }

  .scene-items-spin {
    display: block;
    height: 100%;
    min-height: 0;
  }

  .scene-items-spin :deep(> .mango-panel-spin__content) {
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
    box-sizing: border-box;
    padding: var(--m-card-padding);
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
  }

  .scene-items-header {
    display: flex;
    align-items: flex-start;
    flex-direction: column;
    justify-content: flex-start;
    gap: var(--m-page-gap);
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
    margin-top: var(--m-page-gap);
    padding-right: 2px;
    padding-bottom: 2px;
    gap: var(--m-page-gap);
  }

  .scene-item-card {
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

  .scene-root-card {
    flex-shrink: 0;
    padding: var(--m-card-padding);
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

  .scene-root-card:focus-visible {
    outline: 2px solid var(--m-primary);
    outline-offset: 2px;
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

  .preview-spin :deep(> .mango-panel-spin__content) {
    height: 100%;
    min-height: 0;
  }
</style>
