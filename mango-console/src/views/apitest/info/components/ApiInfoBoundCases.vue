<template>
  <BaseSidePanel
    :visible="visible"
    :title="title"
    :width="1000"
    :show-footer="false"
    @update:visible="
      (value) => {
        if (!value) close()
      }
    "
    @cancel="close"
  >
    <div class="mango-bound-case-workbench">
      <div class="mango-bound-case-table">
        <a-table
          class="mango-native-scroll-table"
          :columns="boundCaseColumns"
          :data="rows"
          :loading="loading"
          :pagination="false"
          :bordered="false"
          :scroll="{ x: boundCaseScrollX, y: '100%' }"
          row-key="case_id"
          size="small"
        >
          <template #case_id="{ record }">
            <a-link @click="openCase(record)">{{ record.case_id }}</a-link>
          </template>
          <template #scenario_tags="{ record }">
            <ExecutionSceneTagGrid
              :values="record.scenario_tags"
              :options="enumStore.api_case_scenario_tag"
              :colors="enumStore.colors"
            />
          </template>
          <template #empty>
            <div class="mango-empty-state">
              {{ failed ? '' : (referenceMode ? '暂无引用用例' : '暂无绑定用例') }}
              <a-button v-if="failed" size="small" :loading="loading" @click="load">重试</a-button>
            </div>
          </template>
        </a-table>
      </div>
      <TableFooter class="mango-bound-case-footer" :pagination="pagination" :show-refresh="false" compact-pages />
    </div>
  </BaseSidePanel>
  <BaseSidePanel
    :visible="casePanel.visible"
    :title="`${domain.toUpperCase()} 用例详情${casePanel.name ? ` / ${casePanel.name}` : ''}`"
    width="calc(92vw - 150px)"
    mode="page"
    @update:visible="(value) => (casePanel.visible = value)"
    @cancel="casePanel.visible = false"
  >
    <component
      :is="domain === 'ui' ? UiCaseDetails : ApiCaseDetails"
      v-if="casePanel.visible && casePanel.id != null"
      :key="casePanel.id"
      embedded
      :case-id="casePanel.id"
      :project-product-id="casePanel.product"
      @close="casePanel.visible = false"
    />
  </BaseSidePanel>
</template>
<script setup lang="ts">
  import { reportLoadError } from '@/utils/load-error'
  import { computed, reactive, ref, onBeforeUnmount, onDeactivated, defineAsyncComponent, h, watch } from 'vue'
  import { usePagination } from '@/hooks/table'
  import useUserStore from '@/store/modules/user'
  import { useEnum } from '@/store/modules/get-enum'
  import { getApiInfoBoundCases } from '@/api/apitest/info'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import TableFooter from '@/components/table/TableFooter.vue'
  import ExecutionSceneTagGrid from '@/components/display/ExecutionSceneTagGrid.vue'
  import { boundCaseColumns, boundCaseScrollX } from '../config'
  import type { ApiInfoListRow, BoundApiCase, ApiEntityId } from '../types'
  const props = withDefaults(defineProps<{
    readCases?: (id: ApiEntityId, page: number, pageSize: number) => Promise<{data: BoundApiCase[]; totalSize?: number}>
    referenceMode?: boolean
    domain?: 'api' | 'ui'
  }>(), { referenceMode: false, domain: 'api' })
  const enumStore = useEnum()
  const UiCaseDetails = defineAsyncComponent({
    loader: () => import('@/views/uitest/case/details/index.vue'),
    loadingComponent: { render: () => h('div', '正在加载用例详情…') },
  })
  const ApiCaseDetails = defineAsyncComponent({
    loader: () => import('@/views/apitest/case/details/index.vue'),
    loadingComponent: { render: () => h('div', '正在加载用例详情…') },
  })
  const visible = ref(false),
    loading = ref(false),
    failed = ref(false),
    title = ref('绑定 Case')
  const pagination = usePagination(load, loading)
  const caseRows = ref<BoundApiCase[]>([])
  const rows = computed(() => props.readCases ? caseRows.value : caseRows.value.slice(
    (pagination.page - 1) * pagination.pageSize, pagination.page * pagination.pageSize
  ))
  const casePanel = reactive<{
    visible: boolean
    id: ApiEntityId | null
    name: string
    product: ApiEntityId | ''
  }>({ visible: false, id: null, name: '', product: '' })
  let target: ApiEntityId | null = null,
    request = 0,
    snapshotLoaded = false
  function close() {
    request++
    visible.value = false
    loading.value = false
    failed.value = false
    caseRows.value = []
    pagination.page = 1
    pagination.pageSize = 20
    pagination.setTotalSize(0)
    snapshotLoaded = false
    target = null
    casePanel.visible = false
  }
  async function open(record: Pick<ApiInfoListRow, 'id' | 'name'>) {
    close()
    target = record.id
    title.value = `${props.referenceMode ? '引用 Case' : '绑定 Case'} / ${record.name || record.id}`
    visible.value = true
    await load()
  }
  async function load() {
    if (target == null || !visible.value || (!props.readCases && snapshotLoaded)) {
      loading.value = false
      return
    }
    const current = ++request,
      id = target
    loading.value = true
    failed.value = false
    try {
      const response = props.readCases
        ? await props.readCases(id, pagination.page, pagination.pageSize)
        : await getApiInfoBoundCases(id)
      if (current !== request) return
      caseRows.value = response.data || []
      pagination.setTotalSize(props.readCases ? response.totalSize ?? caseRows.value.length : caseRows.value.length)
      snapshotLoaded = true
    } catch (loadFailure0) {
      if (current === request) (reportLoadError(loadFailure0, "加载失败，请重试", false), failed.value = true)
    } finally {
      if (current === request) loading.value = false
    }
  }
  const user = useUserStore()
  watch(() => [user.userId, user.roleId, user.token], close, { flush: 'sync' })
  function openCase(record: BoundApiCase) {
    if (record.case_id == null) return
    Object.assign(casePanel, {
      visible: true,
      id: record.case_id,
      name: record.case_name,
      product: record.project_product_id ?? '',
    })
  }
  onBeforeUnmount(close)
  onDeactivated(close)
  defineExpose({ open, close })
</script>
<style scoped>
  .mango-bound-case-workbench {
    height: 100%;
    min-height: 0;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    border-radius: var(--m-radius-lg);
    background: var(--m-surface);
  }
  .mango-bound-case-table {
    flex: 1;
    min-width: 0;
    min-height: 0;
    overflow: hidden;
  }
  .mango-bound-case-footer {
    flex: none;
    border-top: 1px solid var(--m-border);
  }
</style>
