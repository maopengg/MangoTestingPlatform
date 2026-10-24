<template>
  <div class="mango-evaluation-item-browser">
    <section class="mango-evaluation-item-navigation">
      <div class="mango-section-title mango-evaluation-item-navigation__head"
        ><strong>评测条目</strong><span>{{ itemCount }} 条</span></div
      >
      <MangoPanelSpin :loading="itemsLoading && !items.length" class="mango-evaluation-items-spin">
        <div class="mango-evaluation-items-list mango-native-scrollbar">
          <div v-if="listError" class="mango-empty-state"
            >条目列表加载失败。<a-button
              size="small"
              :loading="itemsLoading"
              @click="loadItems(true)"
              >重试</a-button
            ></div
          >
          <div v-else-if="!items.length && !itemsLoading" class="mango-empty-state"
            >暂无条目结果</div
          >
          <button
            v-for="item in items"
            :key="item.id"
            type="button"
            class="mango-evaluation-item-option"
            :class="{ 'mango-evaluation-item-option--selected': selectedId === item.id }"
            :aria-pressed="selectedId === item.id"
            @click="selectItem(item.id)"
          >
            <span
              ><strong>{{ item.dataset_item_id }}</strong
              ><a-tag size="small" :color="statusColor(item.verdict)">{{
                enumTitle('evaluation_verdict', item.verdict)
              }}</a-tag></span
            >
            <small
              >第 {{ item.repeat_index }} 次 ·
              {{ item.score == null ? '暂无评分' : `${item.score} 分` }}</small
            >
          </button>
          <a-button
            v-if="hasMore"
            size="small"
            long
            :loading="itemsLoading"
            @click="loadItems(false)"
            >加载更多条目</a-button
          >
        </div>
      </MangoPanelSpin>
    </section>
    <MangoPanelSpin
      :loading="detailLoading || executionLoading"
      class="mango-evaluation-item-viewer"
    >
      <a-alert v-if="executionError" type="error"
        >执行快照加载失败，数据集版本信息暂不可用。<a-button
          size="small"
          :loading="executionLoading"
          @click="loadExecution"
          >重试</a-button
        ></a-alert
      >
      <template v-if="itemDetail">
        <section class="mango-evaluation-item-overview">
          <div class="mango-section-title"
            ><h3>{{ itemDetail.dataset_item_id }}</h3
            ><a-space
              ><a-tag size="small" :color="statusColor(itemDetail.verdict)">{{
                enumTitle('evaluation_verdict', itemDetail.verdict)
              }}</a-tag
              ><a-button size="small" :disabled="!execution" @click="snapshotVisible = true"
                >执行快照</a-button
              ></a-space
            ></div
          >
          <p
            >{{ execution?.execution_no }} ·
            {{ user.selected_environment_title || execution?.test_env }}</p
          >
          <a-descriptions :column="2" size="small">
            <a-descriptions-item label="调用状态"
              ><a-tag size="small" :color="statusColor(itemDetail.execution_status)">{{
                enumTitle('evaluation_item_execution_status', itemDetail.execution_status)
              }}</a-tag></a-descriptions-item
            >
            <a-descriptions-item label="评分状态"
              ><a-tag size="small" :color="statusColor(itemDetail.grade_status)">{{
                enumTitle('evaluation_grade_status', itemDetail.grade_status)
              }}</a-tag></a-descriptions-item
            >
            <a-descriptions-item label="得分">{{ itemDetail.score ?? '—' }}</a-descriptions-item>
            <a-descriptions-item label="尝试次数">{{
              itemDetail.attempts?.length ?? 0
            }}</a-descriptions-item>
            <a-descriptions-item label="耗时"
              >{{ itemDetail.details?.timing?.execution_ms ?? '—' }} ms</a-descriptions-item
            >
          </a-descriptions>
        </section>
        <a-alert v-if="itemDetail.details?.error_message" type="error">{{
          itemDetail.details.error_message
        }}</a-alert>
        <a-alert v-if="itemDetail.details?.cleanup_error" type="warning"
          >资源清理失败：{{ itemDetail.details.cleanup_error }}。已完成的评分结果保留。</a-alert
        >
        <ItemResultContent
          :item="itemDetail"
          :dataset="execution?.snapshot?.dataset"
          :dataset-name="
            Number(execution?.snapshot?.dataset?.id) === datasetId ? datasetName : undefined
          "
        />
      </template>
      <div v-else class="mango-empty-state"
        >{{ detailError ? '条目结果加载失败' : '请选择评测条目'
        }}<a-button v-if="detailError" size="small" @click="selectItem(selectedId!)"
          >重试</a-button
        ></div
      >
    </MangoPanelSpin>
    <EvaluationDrawer
      v-model:visible="snapshotVisible"
      title="执行快照（JSON）"
      :width="900"
      :footer="false"
      unmount-on-close
      ><JsonDisplay :data="execution?.snapshot" :show-drawer-button="false"
    /></EvaluationDrawer>
  </div>
</template>
<script setup lang="ts">
  import EvaluationDrawer from './EvaluationDrawer.vue'
  import { computed, onBeforeUnmount, ref, watch } from 'vue'
  import { getCaseExecution, getCaseExecutionItems, getCaseExecutionItem } from '@/api/evaluation'
  import useUserStore from '@/store/modules/user'
  import MangoPanelSpin from '@/components/feedback/MangoPanelSpin.vue'
  import ItemResultContent from './ItemResultContent.vue'
  import JsonDisplay from '@/components/display/JsonDisplay.vue'
  import { useEvaluationEnums } from './useEvaluationEnums'
  const props = defineProps<{
    caseId: number
    executionId: number
    initialItemId?: number
    datasetId?: number
    datasetName?: string
  }>()
  const user = useUserStore()
  const snapshotVisible = ref(false)
  const { title: enumTitle, color: statusColor } = useEvaluationEnums()
  const execution = ref<any>(),
    items = ref<any[]>([]),
    itemDetail = ref<any>(),
    selectedId = ref<number>()
  const itemCount = ref(0),
    page = ref(0),
    itemsLoading = ref(false),
    detailLoading = ref(false),
    detailError = ref(false),
    listError = ref(false),
    executionLoading = ref(false),
    executionError = ref(false)
  const hasMore = computed(() => page.value * 20 < itemCount.value)
  let generation = 0,
    detailRequest = 0,
    listRequest = 0
  async function loadExecution() {
    const scope = generation
    executionLoading.value = true
    executionError.value = false
    try {
      const response: any = await getCaseExecution(props.caseId, props.executionId)
      if (scope === generation) execution.value = response.data
    } catch {
      if (scope === generation) executionError.value = true
    } finally {
      if (scope === generation) executionLoading.value = false
    }
  }
  async function selectItem(id: number) {
    const request = ++detailRequest,
      scope = generation
    selectedId.value = id
    itemDetail.value = undefined
    detailLoading.value = true
    detailError.value = false
    try {
      const response: any = await getCaseExecutionItem(props.caseId, props.executionId, id)
      if (scope !== generation || request !== detailRequest) return
      itemDetail.value = response.data
      if (response.data && !items.value.some((item) => item.id === id))
        items.value.unshift(response.data)
    } catch {
      if (scope === generation && request === detailRequest) detailError.value = true
    } finally {
      if (scope === generation && request === detailRequest) detailLoading.value = false
    }
  }
  async function loadItems(reset = true) {
    if (itemsLoading.value && !reset) return
    const request = ++listRequest,
      scope = generation,
      nextPage = reset ? 1 : page.value + 1
    itemsLoading.value = true
    listError.value = false
    try {
      const response: any = await getCaseExecutionItems(props.caseId, props.executionId, {
        page: nextPage,
        pageSize: 20,
      })
      if (scope !== generation || request !== listRequest) return
      const rows = response.data?.items || []
      const merged = reset ? rows : [...items.value, ...rows]
      items.value = [...new Map(merged.map((item: any) => [item.id, item])).values()] as any[]
      itemCount.value = response.data?.count || 0
      page.value = nextPage
      const preferred = selectedId.value || props.initialItemId || rows[0]?.id
      if (reset && preferred) await selectItem(preferred)
    } catch {
      if (scope === generation && request === listRequest) listError.value = true
    } finally {
      if (scope === generation && request === listRequest) itemsLoading.value = false
    }
  }
  watch(
    () => [props.caseId, props.executionId, props.initialItemId, user.selected_environment],
    async () => {
      ++generation
      detailRequest++
      listRequest++
      items.value = []
      execution.value = undefined
      snapshotVisible.value = false
      itemDetail.value = undefined
      selectedId.value = undefined
      itemCount.value = 0
      page.value = 0
      detailLoading.value = false
      detailError.value = false
      itemsLoading.value = false
      if (!props.executionId) return
      await Promise.allSettled([loadExecution(), loadItems()])
    },
    { immediate: true }
  )
  onBeforeUnmount(() => {
    generation++
    detailRequest++
    listRequest++
  })
</script>
<style scoped>
  .mango-evaluation-item-browser {
    display: grid;
    grid-template-columns: 220px minmax(0, 1fr);
    gap: var(--m-page-gap);
    min-height: 0;
    height: 100%;
    min-width: 0;
  }
  .mango-evaluation-item-navigation {
    display: flex;
    flex-direction: column;
    min-height: 0;
    min-width: 0;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
    overflow: hidden;
  }
  .mango-evaluation-item-navigation__head {
    padding: 10px 12px;
    margin: 0;
    align-items: center;
    border-bottom: 1px solid var(--m-border);
    flex-wrap: wrap;
  }
  .mango-evaluation-item-navigation__head > span {
    color: var(--m-muted);
  }
  .mango-evaluation-items-spin {
    flex: 1;
    min-height: 0;
  }
  .mango-evaluation-items-spin :deep(> .mango-panel-spin__content) {
    height: 100%;
    min-height: 0;
  }
  .mango-evaluation-items-list {
    height: 100%;
    overflow-y: auto;
  }
  .mango-evaluation-item-option {
    display: flex;
    flex-direction: column;
    gap: var(--m-page-gap);
    width: 100%;
    padding: 12px;
    border: 0;
    border-bottom: 1px solid var(--m-border);
    color: var(--m-text);
    background: var(--m-surface);
    text-align: left;
    cursor: pointer;
  }
  .mango-evaluation-item-option > span {
    display: flex;
    justify-content: space-between;
    gap: var(--m-page-gap);
  }
  .mango-evaluation-item-option strong {
    overflow-wrap: anywhere;
  }
  .mango-evaluation-item-option small {
    color: var(--m-muted);
  }
  .mango-evaluation-item-option:hover,
  .mango-evaluation-item-option--selected {
    background: var(--m-primary-soft);
  }
  .mango-evaluation-item-option:focus-visible {
    outline: 2px solid var(--m-primary);
    outline-offset: -2px;
  }
  .mango-evaluation-item-viewer {
    min-width: 0;
    min-height: 0;
    height: 100%;
  }
  .mango-evaluation-item-viewer :deep(> .mango-panel-spin__content) {
    display: flex;
    flex-direction: column;
    gap: var(--m-page-gap);
    height: 100%;
    overflow-y: auto;
    min-width: 0;
  }
  .mango-evaluation-item-viewer :deep(> .mango-panel-spin__content > *) {
    flex-shrink: 0;
  }
  .mango-evaluation-item-overview {
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    padding: var(--m-card-padding);
    background: var(--m-surface);
  }
  .mango-evaluation-item-overview h3 {
    margin: 0;
    font-size: 16px;
  }
  .mango-evaluation-item-overview p {
    color: var(--m-muted);
    overflow-wrap: anywhere;
  }
  @container (max-width: 700px) {
    .mango-evaluation-item-browser {
      grid-template-columns: minmax(0, 1fr);
      grid-template-rows: minmax(120px, 25%) minmax(0, 1fr);
    }
  }
</style>
