<template>
  <TableBody content-flush>
    <template #header>
      <TableHeader
        title="灰度仓库"
        :show-filter="true"
        @search="onSearchRefresh"
        @reset-search="onReset"
      >
        <template #search-content>
          <a-form layout="inline" :model="query" @keyup.enter="onSearchRefresh">
            <a-form-item label="仓库名称">
              <a-input
                v-model="query.name"
                allow-clear
                placeholder="请输入仓库名称"
                @blur="onSearchRefresh"
                @clear="onSearchRefresh"
                data-testid="qa-views-gray-repository-input-请输入仓库名称"
              />
            </a-form-item>
            <a-form-item label="仓库地址">
              <a-input
                v-model="query.repo_url"
                allow-clear
                placeholder="请输入仓库地址"
                @blur="onSearchRefresh"
                @clear="onSearchRefresh"
                data-testid="qa-views-gray-repository-input-请输入仓库地址"
              />
            </a-form-item>
            <a-form-item label="平台">
              <a-select
                v-model="query.provider"
                multiple
                :max-tag-count="1"
                :options="providerOptions"
                allow-clear
                allow-search
                placeholder="请选择平台"
                @change="onSearchRefresh"
                data-testid="qa-views-gray-repository-select-请选择平台"
              />
            </a-form-item>
            <a-form-item label="测试环境">
              <a-select
                v-model="query.test_env"
                :field-names="{ value: 'key', label: 'title' }"
                :options="environmentOptions"
                :loading="enumLoading"
                allow-clear
                allow-search
                placeholder="请选择被测环境"
                @change="onSearchRefresh"
                data-testid="qa-views-gray-repository-select-请选择环境"
              />
            </a-form-item>
            <a-form-item label="分支">
              <a-input
                v-model="query.branch"
                allow-clear
                placeholder="请输入分支"
                @blur="onSearchRefresh"
                @clear="onSearchRefresh"
                data-testid="qa-views-gray-repository-input-请输入分支"
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
                data-testid="qa-views-gray-repository-select-请选择状态"
              />
            </a-form-item>
          </a-form>
        </template>
      </TableHeader>
    </template>

    <template #default>
      <TableTabs>
        <template #extra>
          <a-button
            size="small"
            type="primary"
            @click="onAdd"
            data-testid="qa-views-gray-repository-button-新增仓库"
          >
            新增仓库
          </a-button>
        </template>
      </TableTabs>
      
      <a-table
        :bordered="false"
        :columns="repositoryColumns"
        :data="rows"
        :loading="loading"
        :pagination="false"
        :scroll="{ x: grayPageConfig.scrollX }"
        row-key="id"
      >
        <template #columns>
          <a-table-column v-for="item in repositoryColumns" :key="item.key" v-bind="item">
            <template v-if="item.key === 'index'" #cell="{ record }">{{ record.id }}</template>
            <template v-else-if="item.key === 'provider'" #cell="{ record }">
              <a-tag :color="providerColor(record.provider)" size="small">{{
                providerText(record.provider)
              }}</a-tag>
            </template>
            <template v-else-if="item.key === 'config_dirs'" #cell="{ record }">
              <a-popover
                v-if="normalizeDirs(record.config_dirs).length"
                position="left"
                trigger="hover"
              >
                <a-tag size="small">已配置 {{ normalizeDirs(record.config_dirs).length }} 个</a-tag>
                <template #content>
                  <div class="mango-gray-config-dir-popover">
                    <div
                      v-for="dir of normalizeDirs(record.config_dirs)"
                      :key="dir"
                      class="mango-gray-config-dir-popover__item"
                    >
                      {{ dir }}
                    </div>
                  </div>
                </template>
              </a-popover>
              <span v-else>-</span>
            </template>
            <template v-else-if="item.key === 'test_env'" #cell="{ record }">
              <a-tag :color="environmentColor(record.test_env)" size="small">{{
                formatEnvironmentText(record.test_env)
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
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <MangoTableActions
                :actions="[
                  {
                    label: '测试',
                    disabled: interactionBlocked,
                    loading: actionLoading === `test-${record.id}`,
                    onClick: () => onTest(record),
                  },
                  {
                    label: '同步',
                    disabled: interactionBlocked,
                    loading: actionLoading === `sync-${record.id}`,
                    onClick: () => onSync(record),
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
    </template>

    <template #footer>
      <TableFooter :pagination="pagination" />
    </template>
  </TableBody>

  <RepositoryEditor
    ref="editorRef"
    :context-key="contextKey"
    :blocked="!!actionLoading"
    @visible="editorVisible = $event"
    @busy="editorSaving = $event"
    @saved="onSaved"
  />
</template>

<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import {
    computed,
    onActivated,
    onBeforeUnmount,
    onDeactivated,
    onMounted,
    reactive,
    ref,
    watch,
  } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { useRoute } from 'vue-router'
  import TableBody from '@/components/table/TableBody.vue'
  import TableHeader from '@/components/table/TableHeader.vue'
  import TableFooter from '@/components/table/TableFooter.vue'
  import TableTabs from '@/components/table/TableTabs.vue'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import RepositoryEditor from './components/RepositoryEditor.vue'
  import { useEnum } from '@/store/modules/get-enum'
  import useUserStore from '@/store/modules/user'
  import { usePagination } from '@/hooks/table'
  import { getGrayRepository } from '@/api/gray'
  import { enableStatusOptions, grayPageConfig, providerOptions } from './config'
  import {
    COMMON_ENV,
    createQuery,
    normalizeDirs,
    repositoryPage,
    requestParams,
    type EditorHandle,
    type RepositoryRow,
  } from './records'
  import { useRepositoryActions } from './composables/useRepositoryActions'

  const enumStore = useEnum(),
    user = useUserStore(),
    route = useRoute()
  const query = reactive(createQuery()),
    rows = ref<RepositoryRow[]>([]),
    loading = ref(false),
    loadError = ref('')
  const enumLoading = ref(false),
    enumError = ref(false),
    editorVisible = ref(false),
    editorSaving = ref(false),
    editorRef = ref<EditorHandle | null>(null)
  const pagination = usePagination(onSearch, loading)
  const scopeKey = computed(() =>
    JSON.stringify([
      route.fullPath,
      user.userId,
      user.roleId,
      user.token,
      user.selected_environment,
    ])
  )
  const contextKey = () => scopeKey.value
  const { actionLoading, onTest, onSync, onModifyStatus, onDelete } = useRepositoryActions({
    contextKey,
    blocked: () => editorVisible.value || editorSaving.value,
    applied: onSearch,
    statusApplied: (id, status) => {
      rows.value = rows.value.map((row) => (row.id === id ? { ...row, status } : row))
    },
  })
  const interactionBlocked = computed(
    () => !!actionLoading.value || editorVisible.value || editorSaving.value
  )
  const repositoryColumns = computed(() => grayPageConfig.columns)
  const environmentOptions = computed(() => [
    { key: COMMON_ENV, title: '环境通用' },
    ...(Array.isArray(enumStore.environment_type) ? enumStore.environment_type : []),
  ])
  let active = true,
    mounted = false,
    generation = 0,
    sequence = 0,
    enumSequence = 0
  function environmentIndex(value: number | string | null) {
    return enumStore.environment_type.findIndex((item) =>
      [item.key, item.title].some((key) => String(key) === String(value))
    )
  }
  function formatEnvironmentText(value: number | string | null) {
    if (value === null || value === '' || value === COMMON_ENV) return '环境通用'
    return enumStore.environment_type[environmentIndex(value)]?.title || String(value)
  }
  function environmentColor(value: number | string | null) {
    if (value === null || value === '' || value === COMMON_ENV) return 'gray'
    const index = environmentIndex(value)
    return (
      enumStore.colors?.[index >= 0 ? index + 1 : Number(value)] ||
      enumStore.colors?.[index] ||
      'gray'
    )
  }
  function providerText(value: string) {
    return providerOptions.find((item) => item.value === value)?.label || value || '-'
  }
  function providerColor(value: string) {
    const index = providerOptions.findIndex((item) => item.value === value)
    return enumStore.colors?.[index + 1] || enumStore.colors?.[index] || 'gray'
  }
  async function onSearch(): Promise<boolean> {
    if (!active) {
      loading.value = false
      return false
    }
    const request = ++sequence,
      version = generation,
      context = contextKey(),
      current = () =>
        active && request === sequence && version === generation && context === contextKey()
    loading.value = true
    loadError.value = ''
    try {
      const result = repositoryPage(
        await getGrayRepository(requestParams(query, pagination.page, pagination.pageSize))
      )
      if (!current()) return false
      const last = Math.max(1, Math.ceil(result.total / pagination.pageSize))
      if (pagination.page > last) {
        pagination.page = last
        return await onSearch()
      }
      rows.value = result.rows
      pagination.setTotalSize(result.total)
      return true
    } catch (loadFailure0) {
      if (current()) (reportLoadError(loadFailure0, "仓库列表读取失败，请重试查询", false), loadError.value = '仓库列表读取失败，请重试查询')
      return false
    } finally {
      if (current()) loading.value = false
    }
  }
  async function loadEnums() {
    if (!active) return
    const request = ++enumSequence,
      version = generation,
      current = () => active && request === enumSequence && version === generation
    enumLoading.value = true
    enumError.value = false
    try {
      await enumStore.getEnum()
    } catch (loadFailure1) {
      if (current()) (reportLoadError(loadFailure1, "加载失败，请重试", false), enumError.value = true)
    } finally {
      if (current()) enumLoading.value = false
    }
  }
  function onSearchRefresh() {
    pagination.page = 1
    return onSearch()
  }
  function onReset() {
    Object.assign(query, createQuery())
    return onSearchRefresh()
  }
  function onAdd() {
    if (active && !interactionBlocked.value) editorRef.value?.open()
  }
  function onEdit(record: RepositoryRow) {
    if (active && !interactionBlocked.value) editorRef.value?.open(record)
  }
  async function onSaved() {
    const version = generation
    const loaded = await onSearch()
    if (active && version === generation && !loaded)
      Message.error('仓库已保存，列表读取失败，请重试查询')
  }
  function invalidate() {
    ++generation
    ++sequence
    ++enumSequence
    rows.value = []
    loading.value = false
    loadError.value = ''
    enumLoading.value = false
    enumError.value = false
    pagination.setTotalSize(0)
  }
  function reload() {
    void onSearch()
    void loadEnums()
  }
  watch(
    contextKey,
    () => {
      invalidate()
      if (active && mounted) reload()
    },
    { flush: 'sync' }
  )
  onMounted(() => {
    mounted = true
    reload()
  })
  onDeactivated(() => {
    active = false
    invalidate()
  })
  onActivated(() => {
    if (!active) {
      active = true
      if (mounted) reload()
    }
  })
  onBeforeUnmount(() => {
    active = false
    invalidate()
  })
</script>

<style scoped lang="less">
  .mango-gray-config-dir-popover {
    display: flex;
    flex-direction: column;
    gap: 6px;
    max-width: 360px;
  }

  .mango-gray-config-dir-popover__item {
    color: var(--m-text-2);
    font-size: 12px;
    line-height: 18px;
    word-break: break-all;
  }
</style>
