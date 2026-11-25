<template>
  <a-popover
    v-model:popup-visible="visible"
    trigger="hover"
    position="left"
    @popup-visible-change="onVisibleChange"
  >
    <slot />
    <template #content>
      <div class="mango-case-version-results">
        <a-spin v-if="loading" tip="正在查询各发布状态、环境的结果" />
        <a-button v-else-if="failed" type="text" size="small" @click="loadResults">重新加载</a-button>
        <template v-else>
          <div v-for="item in items" :key="`${item.publication_status}:${item.test_env ?? 'none'}`" class="mango-case-version-results__row">
            <span>{{ item.label }}</span>
            <a-tag :color="enumStore.status_colors[item.status ?? 2]" size="small">
              {{ resultLabel(item) }}
            </a-tag>
            <span class="mango-case-version-results__environment">{{ environmentLabel(item) }}</span>
            <span v-if="item.started_at" class="mango-case-version-results__hint">
              {{ formatCaseResultTime(item.started_at) }}
            </span>
          </div>
          <span v-if="!items.length" class="mango-case-version-results__hint">暂无可查看的版本</span>
        </template>
      </div>
    </template>
  </a-popover>
</template>

<script setup lang="ts">
  import { onBeforeUnmount, onDeactivated, ref, watch } from 'vue'
  import { getApiCaseVersionResults, type ApiCaseVersionResult } from '@/api/apitest/case'
  import { useEnum } from '@/store/modules/get-enum'
  import useUserStore from '@/store/modules/user'
  import { reportLoadError } from '@/utils/load-error'
  import { formatCaseResultTime } from '../result-presentation'

  const props = defineProps<{ caseId: number; versionToken?: string }>()
  const enumStore = useEnum()
  const userStore = useUserStore()
  const visible = ref(false)
  const loading = ref(false)
  const failed = ref(false)
  const items = ref<ApiCaseVersionResult[]>([])
  let requestId = 0

  function reset() {
    requestId++
    visible.value = false
    loading.value = false
    failed.value = false
    items.value = []
  }
  async function loadResults() {
    if (!visible.value || loading.value) return
    const current = ++requestId
    const caseId = props.caseId
    loading.value = true
    failed.value = false
    items.value = []
    try {
      const response = await getApiCaseVersionResults(caseId)
      if (current !== requestId || !visible.value) return
      items.value = response.data || []
    } catch (error) {
      if (current !== requestId || !visible.value) return
      failed.value = true
      reportLoadError(error, '版本结果加载失败，请重试')
    } finally {
      if (current === requestId) loading.value = false
    }
  }
  function onVisibleChange(open: boolean) {
    visible.value = open
    if (open) void loadResults()
    else reset()
  }
  function resultLabel(item: ApiCaseVersionResult) {
    if (item.status == null || item.status === 2) return '待测试'
    if (item.status === 3 && item.phase === 'automatic_recovery')
      return enumStore.report_execution_phase[item.phase]?.title || '自动恢复中'
    return enumStore.task_status[item.status]?.title || '—'
  }
  function environmentLabel(item: ApiCaseVersionResult) {
    if (item.status == null) return '—'
    if (item.test_env == null) return '环境未记录'
    return enumStore.environment_type.find(option => String(option.key) === String(item.test_env))?.title
      || `环境 #${item.test_env}`
  }
  watch(() => [props.caseId, props.versionToken, userStore.userId,
    userStore.roleId, userStore.token], reset)
  onDeactivated(reset)
  onBeforeUnmount(reset)
</script>

<style scoped>
  .mango-case-version-results {
    display: flex;
    flex-direction: column;
    gap: var(--m-page-gap);
    max-width: min(720px, calc(100vw - 32px));
    max-height: min(480px, calc(100vh - 64px));
    overflow-y: auto;
  }
  .mango-case-version-results__row {
    display: grid;
    grid-template-columns: max-content max-content minmax(0, 1fr) max-content;
    align-items: center;
    gap: var(--m-page-gap);
    white-space: nowrap;
  }
  .mango-case-version-results__environment {
    white-space: normal;
    overflow-wrap: anywhere;
  }
  .mango-case-version-results__hint {
    color: var(--m-muted);
  }
</style>
