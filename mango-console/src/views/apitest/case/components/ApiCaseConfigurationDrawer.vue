<template>
  <BaseSidePanel
    :visible="visible"
    :title="title"
    :width="1100"
    :show-footer="false"
    @update:visible="onVisibilityChange"
  >
    <div class="mango-case-configuration">
      <TableHeader
        :title="`SQL ${summary?.sql_count ?? 0} · 数据工厂 ${summary?.data_factory_count ?? 0}`"
        :show-search-actions="false"
      />
      <div class="mango-case-configuration__hint">{{
        summary
          ? `当前展示：${
              summary.publication_status === 'published'
                ? '已发布版本'
                : summary.publication_status === 'prepublished'
                ? '预发布修订'
                : '未发布（编辑态）'
            }。引用模板规则以当前模板为准，展开行可查看配置。`
          : '正在读取用例当前发布状态对应的执行配置…'
      }}</div>
      <template v-if="failed"><a-button size="small" :loading="loading" @click="load">重新加载</a-button></template>
      <a-table
        class="mango-native-scroll-table mango-case-configuration__table"
        row-key="rowKey"
        :data="rows"
        :columns="columns"
        :loading="loading"
        :pagination="false"
        :bordered="false"
        :expandable="{}"
        :scroll="{ x: 1000, y: '100%' }"
      >
        <template #kind="{ record }">
          <a-tag size="small" :color="record.kind === 'sql' ? 'orange' : 'blue'">{{
            record.kind === 'sql' ? 'SQL' : '数据工厂'
          }}</a-tag>
        </template>
        <template #content="{ record }">{{ contentPreview(record) }}</template>
        <template #enabled="{ record }">
          <span v-if="record.enabled === null">—</span>
          <a-tag v-else size="small" :color="record.enabled ? 'green' : 'gray'">{{
            record.enabled ? '启用' : '停用'
          }}</a-tag>
        </template>
        <template #expand-row="{ record }">
          <DataFactoryCaseConfigPanel
            v-if="record.kind === 'data_factory'"
            readonly
            :source-type="Number(record.configuration.source_type)"
            :configs="[factoryConfig(record.configuration)]"
          />
          <JsonDisplay v-else :data="record.configuration" :show-drawer-button="false" />
        </template>
        <template #empty
          ><div class="mango-empty-state">{{
            failed ? '' : '暂无 SQL 或数据工厂配置'
          }}</div></template
        >
      </a-table>
      <TableFooter :pagination="pagination" :show-refresh="false" />
    </div>
  </BaseSidePanel>
</template>

<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { computed, defineAsyncComponent, h, ref, onBeforeUnmount, onDeactivated } from 'vue'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import TableHeader from '@/components/table/TableHeader.vue'
  import TableFooter from '@/components/table/TableFooter.vue'
  import JsonDisplay from '@/components/display/JsonDisplay.vue'
  import { usePagination } from '@/hooks/table'
  import { useLatestRequest } from '@/hooks/use-latest-request'
  import { configurationColumns as columns } from '../config'
  import { cloneLosslessJson } from '@/utils/lossless-json'
  import { getApiCaseConfigurationDetails } from '@/api/apitest/case'

  import MangoPanelSpin from '@/components/feedback/MangoPanelSpin.vue'
  import type { ApiCaseConfigurationDetails, ApiCaseConfigurationItem } from '@/types/api-test/case'

  const DataFactoryCaseConfigPanel = defineAsyncComponent({
    loader: () => import('@/components/DataFactory/CaseConfigPanel.vue'),
    delay: 0,
    loadingComponent: {
      render: () => h(MangoPanelSpin, { loading: true }, () => '正在加载数据工厂配置…'),
    },
    errorComponent: {
      render: () => null,
    },
    onError(error, _retry, fail) { reportLoadError(error, '组件加载失败，请收起后重试'); fail() },
  })
  function factoryConfig(config: Record<string, unknown>) {
    return {
      ...config,
      template: {
        id: config.template_id ?? config.template,
        name: config.template__name ?? `模板 #${config.template_id ?? config.template}`,
        cleanup_strategy: config.template__cleanup_strategy,
        entity: {
          name: config.template__entity__name,
          table_name: config.template__entity__table_name,
        },
      },
    }
  }
  const visible = ref(false)
  const loading = ref(false)
  const failed = ref(false)
  const caseId = ref(0)
  const snapshot = ref<ApiCaseConfigurationDetails | null>(null)
  const title = ref('执行配置')
  const summary = ref<ApiCaseConfigurationDetails | null>(null)
  const rows = computed(() => {
    const items = snapshot.value
      ? snapshot.value.items.slice(
          (pagination.page - 1) * pagination.pageSize,
          pagination.page * pagination.pageSize
        )
      : summary.value?.items ?? []
    return items.map((item, index) => ({ ...item, rowKey: index }))
  })
  const { beginRequest, isLatestRequest, invalidateRequests } = useLatestRequest()
  const pagination = usePagination(load, loading)
  function contentPreview(item: ApiCaseConfigurationItem) {
    const config = item.configuration
    return String(
      config.value ??
        config.actual ??
        config['template__name'] ??
        config.name ??
        config['说明'] ??
        '—'
    )
  }

  function onVisibilityChange(nextVisible: boolean) {
    visible.value = nextVisible
    if (!nextVisible) {
      invalidateRequests()
      loading.value = false
      summary.value = null
      snapshot.value = null
    }
  }

  async function load() {
    if (snapshot.value) return
    const request = beginRequest()
    failed.value = false
    loading.value = true
    summary.value = null
    try {
      const res = await getApiCaseConfigurationDetails(
        caseId.value,
        pagination.page,
        pagination.pageSize
      )
      if (!isLatestRequest(request)) return
      summary.value = res.data as ApiCaseConfigurationDetails
      pagination.setTotalSize((res as any).totalSize)
    } catch (loadFailure0) {
      if (isLatestRequest(request)) (reportLoadError(loadFailure0, "加载失败，请重试", false), failed.value = true)
    } finally {
      if (isLatestRequest(request)) loading.value = false
    }
  }

  function open(id: number, name: string) {
    snapshot.value = null
    caseId.value = id
    title.value = `执行配置 / #${id} / ${name}`
    pagination.page = 1
    pagination.setTotalSize(0)
    visible.value = true
    void load()
  }

  function openSnapshot(details: ApiCaseConfigurationDetails) {
    invalidateRequests()
    loading.value = false
    failed.value = false
    snapshot.value = cloneLosslessJson(details)
    summary.value = snapshot.value
    title.value = `执行配置 / #${details.id} / ${details.name}`
    pagination.page = 1
    pagination.setTotalSize(details.items.length)
    visible.value = true
  }

  function close() {
    onVisibilityChange(false)
  }
  onBeforeUnmount(close)
  onDeactivated(close)
  defineExpose({ open, openSnapshot, close })
</script>

<style scoped>
  .mango-case-configuration {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
    gap: var(--m-page-gap);
  }
  .mango-case-configuration__hint {
    color: var(--m-muted);
  }
  .mango-case-configuration__table {
    flex: 1;
    min-height: 0;
  }
</style>
