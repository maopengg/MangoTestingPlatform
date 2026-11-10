<template>
  <TableBody plain class="mango-detail-workbench-page">
    <template #header>
      <TableHeader title="灰度开关" />
    </template>

    <template #default>
      <ProjectProductNavigationWorkbench
        ref="navigationCreateRef"
        contained-body
        :model-value="query.project_product"
        :module-value="query.module"
        :reset-key="sidebarResetKey"
        show-modules
        @filter-change="onNavigationFilterChange"
        @search="onSearchRefresh"
        @reset-search="onReset"
      >
        <template #search>
          <a-form layout="inline" :model="query" @keyup.enter="onSearchRefresh">
            <a-form-item label="配置类型">
              <a-select
                v-model="query.config_type"
                multiple
                :max-tag-count="1"
                :options="configTypeOptions"
                allow-clear
                placeholder="请选择类型"
                @change="onSearchRefresh"
                data-testid="qa-views-gray-feature-select-请选择类型"
              />
            </a-form-item>
            <a-form-item label="状态">
              <a-select
                v-model="query.status"
                multiple
                :max-tag-count="1"
                :options="enableStatusOptions"
                allow-clear
                placeholder="请选择状态"
                @change="onSearchRefresh"
                data-testid="qa-views-gray-feature-select-请选择状态"
              />
            </a-form-item>
            <a-form-item label="配置文件">
              <a-select
                v-model="query.yaml_file"
                multiple
                :max-tag-count="1"
                :options="yamlOptions"
                :loading="optionsLoading"
                allow-clear
                allow-search
                placeholder="请选择配置文件"
                @change="onSearchRefresh"
                data-testid="qa-views-gray-feature-select-请选择配置文件"
              />
            </a-form-item>
            <a-form-item label="灰度编号">
              <a-input
                v-model="query.gray_code"
                allow-clear
                placeholder="请输入灰度编号"
                @blur="onSearchRefresh"
                @clear="onSearchRefresh"
                data-testid="qa-views-gray-feature-input-请输入灰度编号"
              />
            </a-form-item>
            <a-form-item label="灰度名称">
              <a-input
                v-model="query.name"
                allow-clear
                placeholder="请输入灰度名称"
                @blur="onSearchRefresh"
                @clear="onSearchRefresh"
                data-testid="qa-views-gray-feature-input-请输入灰度名称"
              />
            </a-form-item>
            <a-form-item label="灰度Key">
              <a-input
                v-model="query.feature_key"
                allow-clear
                placeholder="请输入灰度Key"
                @blur="onSearchRefresh"
                @clear="onSearchRefresh"
                data-testid="qa-views-gray-feature-input-请输入灰度key"
              />
            </a-form-item>
          </a-form>
        </template>
        <template #toolbar>
          <a-button
            size="small"
            type="primary"
            @click="onAdd"
            data-testid="qa-views-gray-feature-button-新增灰度"
            >新增灰度</a-button
          >
        </template>
        
        <a-table
          class="mango-native-scroll-table"
          :bordered="false"
          :columns="featureColumns"
          :data="rows"
          :loading="listLoading"
          :pagination="false"
          :scroll="{ x: grayPageConfig.scrollX, y: '100%' }"
          row-key="id"
        >
          <template #columns>
            <a-table-column v-for="item in featureColumns" :key="item.key" v-bind="item">
              <template v-if="item.key === 'index'" #cell="{ record }">{{ record.id }}</template>
              <template v-else-if="item.key === 'config_type'" #cell="{ record }">
                <a-tag :color="configTypeColor(record.config_type)" size="small">{{
                  configTypeText(record.config_type)
                }}</a-tag>
              </template>
              <template v-else-if="item.key === 'status'" #cell="{ record }">
                <a-switch
                  :beforeChange="(newValue) => onModifyStatus(newValue, record.id)"
                  :model-value="record.status === 1"
                  :loading="actionLoading === `status-${record.id}`"
                  :disabled="interactionBlocked"
                />
              </template>
              <template v-else-if="item.key === 'project_product'" #cell="{ record }">
                {{ formatProjectProductPath(record.project_product) }}
              </template>
              <template v-else-if="item.key === 'module'" #cell="{ record }">
                {{ formatModulePath(record.module) }}
              </template>
              <template v-else-if="item.key === 'actions'" #cell="{ record }">
                <MangoTableActions
                  :actions="[
                    {
                      label: '预览/执行',
                      disabled: interactionBlocked,
                      onClick: () => onPreview(record),
                    },
                    { label: '编辑', disabled: interactionBlocked, onClick: () => onEdit(record) },
                    {
                      label: '删除',
                      danger: true,
                      disabled: interactionBlocked,
                      loading: actionLoading === `delete-${record.id}`,
                      onClick: () => onDelete(record),
                    },
                  ]"
                />
              </template>
            </a-table-column>
          </template>
        </a-table>
        <template #footer>
          <TableFooter :pagination="pagination" />
        </template>
      </ProjectProductNavigationWorkbench>
    </template>
  </TableBody>

  <FeatureEditor
    ref="editorRef"
    :context-key="featureContext"
    :blocked="!!actionLoading || previewVisible || previewBusy"
    @busy="editorSaving = $event"
    @visible="editorVisible = $event"
    @saved="onFeatureSaved"
  />

  <FeaturePreviewDrawer
    ref="previewRef"
    :context-key="featureContext"
    :blocked="!!actionLoading || editorSaving || editorVisible"
    :reload-list="onSearch"
    @visible="previewVisible = $event"
    @busy="previewBusy = $event"
  />
</template>

<script setup lang="ts">
  import { computed, onBeforeUnmount, onDeactivated, reactive, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import TableBody from '@/components/table/TableBody.vue'
  import TableHeader from '@/components/table/TableHeader.vue'
  import TableFooter from '@/components/table/TableFooter.vue'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import FeatureEditor from './components/FeatureEditor.vue'
  import type { EditorHandle, FeatureRecord } from './editor-form'
  import { useRoute } from 'vue-router'
  import useUserStore from '@/store/modules/user'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import { useEnum } from '@/store/modules/get-enum'
  import { formatModulePath, formatProjectProductPath } from '@/utils/business-format'
  import { createQuery, type FeatureRow } from './records'
  import FeaturePreviewDrawer from './components/FeaturePreviewDrawer.vue'
  import type { PreviewHandle } from './preview'
  import { useFeatureList } from './composables/useFeatureList'
  import { useFeatureMutations } from './composables/useFeatureMutations'
  import { configTypeOptions, enableStatusOptions, grayPageConfig } from './config'
  import type { NavigationCreateSource } from '@/utils/navigation-create-defaults'

  const navigationCreateRef = ref<NavigationCreateSource | null>(null)

  const enumStore = useEnum()
  const sidebarResetKey = ref(0)
  const editorRef = ref<EditorHandle | null>(null)
  const editorSaving = ref(false),
    editorVisible = ref(false)
  const user = useUserStore(),
    route = useRoute()
  const query = reactive(createQuery())
  const previewRef = ref<PreviewHandle | null>(null)
  const previewVisible = ref(false),
    previewBusy = ref(false)
  const featureColumns = computed(() => grayPageConfig.columns)
  const editorScopeKey = computed(() =>
    JSON.stringify([
      route.fullPath,
      user.userId,
      user.roleId,
      user.token,
      user.selected_environment,
      query.project_product,
      query.module,
    ])
  )
  const featureContext = () => editorScopeKey.value
  const {
    rows,
    loading: listLoading,
    error: listError,
    yamlOptions,
    optionsLoading,
    optionsError,
    pagination,
    search: onSearch,
    loadOptions,
  } = useFeatureList(query, () => editorScopeKey.value)
  const { actionLoading, onModifyStatus, onDelete } = useFeatureMutations({
    contextKey: () => editorScopeKey.value,
    blocked: () =>
      editorSaving.value || editorVisible.value || previewVisible.value || previewBusy.value,
    applied: onSearch,
    statusApplied: (id, status) => {
      rows.value = rows.value.map((row) => (row.id === id ? { ...row, status } : row))
    },
  })
  const interactionBlocked = computed(
    () =>
      !!actionLoading.value ||
      editorSaving.value ||
      editorVisible.value ||
      previewVisible.value ||
      previewBusy.value
  )
  let editorContextGeneration = 0
  watch(
    editorScopeKey,
    () => {
      ++editorContextGeneration
    },
    { flush: 'sync' }
  )
  onDeactivated(() => {
    ++editorContextGeneration
  })
  onBeforeUnmount(() => {
    ++editorContextGeneration
  })
  function onSearchRefresh() {
    pagination.page = 1
    onSearch()
  }

  function onNavigationFilterChange({
    projectProduct,
    module,
  }: {
    projectProduct: import('./editor-form').Selection
    module: import('./editor-form').Selection
  }) {
    query.project_product = projectProduct ?? null
    query.module = module ?? null
    onSearchRefresh()
  }

  function onReset() {
    Object.assign(query, createQuery())
    sidebarResetKey.value += 1
    onSearchRefresh()
  }

  function onAdd() {
    if (
      editorSaving.value ||
      editorVisible.value ||
      actionLoading.value ||
      previewVisible.value ||
      previewBusy.value
    )
      return
    editorRef.value?.open(undefined, navigationCreateRef.value?.getCreateDefaults())
  }
  function onEdit(record: FeatureRecord) {
    if (
      editorSaving.value ||
      editorVisible.value ||
      actionLoading.value ||
      previewVisible.value ||
      previewBusy.value
    )
      return
    editorRef.value?.open(record)
  }
  async function onFeatureSaved() {
    const version = editorContextGeneration
    const results = await Promise.allSettled([loadOptions(), onSearch()])
    if (
      version === editorContextGeneration &&
      results.some((result) => result.status === 'rejected' || !result.value)
    )
      Message.error('灰度开关已保存，列表读取失败，请重试查询')
  }

  function onPreview(record: FeatureRow) {
    if (interactionBlocked.value) return
    previewRef.value?.open(record)
  }

  function configTypeText(configType: number | string) {
    return configTypeOptions.find((item) => Number(item.value) === Number(configType))?.label || '-'
  }

  function configTypeColor(configType: number | string) {
    return enumStore.colors?.[Number(configType)] || 'gray'
  }
</script>
