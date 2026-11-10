<template>
  <div class="mango-functional-case-details mango-detail-workbench-page">
    <div class="mango-detail-toolbar">
      <div class="mango-detail-heading">
        <h1 class="mango-detail-title" :title="detail?.title"
          >功能用例详情 / {{ caseId ?? '-' }} / {{ detail?.title || '-' }}</h1
        >
      </div>
      <a-spin v-if="enumLoading" :size="scaleDensityPixels(12)" aria-label="加载状态选项" />
      <a-button
        class="mango-back-button"
        size="small"
        @click="router.back()"
        data-testid="qa-views-functional-test-case-details-button-返回"
        >返回</a-button
      >
    </div>
    <div class="mango-detail-workbench">
      <div v-if="caseId === null" class="mango-empty-state">请提供有效的用例 ID</div>
      <template v-else>


        <MangoPanelSpin :loading="loading" class="mango-functional-case-details__body">
          <div v-if="detail" class="mango-functional-case-details__grid">
            <section class="mango-section-card">
              <div class="mango-section-title"><h2>基础信息</h2></div>
              <a-descriptions :column="1" bordered size="small">
                <a-descriptions-item label="用例编号">{{
                  detail?.case_no || '-'
                }}</a-descriptions-item>
                <a-descriptions-item label="优先级">
                  <a-tag :color="enumColor(detail?.priority)" size="small">{{
                    enumTitle(enumStore.case_level, detail?.priority)
                  }}</a-tag>
                </a-descriptions-item>
                <a-descriptions-item label="前置条件"
                  ><span class="mango-functional-case-details__text">{{
                    detail.precondition || '-'
                  }}</span></a-descriptions-item
                >
                <a-descriptions-item label="测试场景"
                  ><span class="mango-functional-case-details__text">{{
                    detail.test_point || '-'
                  }}</span></a-descriptions-item
                >
                <a-descriptions-item label="测试数据"
                  ><span class="mango-functional-case-details__text">{{
                    detail.test_data || '-'
                  }}</span></a-descriptions-item
                >
                <a-descriptions-item label="备注"
                  ><span class="mango-functional-case-details__text">{{
                    detail.remark || '-'
                  }}</span></a-descriptions-item
                >
              </a-descriptions>
            </section>
            <section class="mango-section-card">
              <div class="mango-section-title"><h2>自动化绑定</h2></div>
              <a-table
                :bordered="false"
                :columns="bindingColumns"
                :data="detail?.bindings || []"
                :pagination="false"
                :row-key="'id'"
                :scroll="{ x: BINDING_SCROLL_X }"
                size="small"
              >
                <template #automation_type="{ record }">
                  <a-tag :color="enumColor(record.automation_type)" size="small">{{
                    enumTitle(enumStore.manual_test_automation_type, record.automation_type)
                  }}</a-tag>
                </template>
                <template #case_id="{ record }">{{ bindingCaseId(record) }}</template>
                <template #optimize_status="{ record }">
                  <a-tag :color="optimizeStatusColor(record.optimize_status)" size="small">{{
                    enumTitle(enumStore.manual_test_optimize_status, record.optimize_status)
                  }}</a-tag>
                </template>
              </a-table>
            </section>
            <section class="mango-section-card mango-functional-case-details__source">
              <div class="mango-section-title"><h2>来源与同步</h2></div>
              <a-descriptions :column="2" bordered size="small">
                <a-descriptions-item label="来源片段"
                  ><span class="mango-functional-case-details__text">{{
                    detail.source_text || '-'
                  }}</span></a-descriptions-item
                >
                <a-descriptions-item label="变更状态">
                  <a-tag :color="changeStatusColor(detail?.change_status)" size="small">{{
                    enumTitle(enumStore.manual_test_change_status, detail?.change_status)
                  }}</a-tag>
                </a-descriptions-item>
                <a-descriptions-item label="自动化影响">
                  <a-tag
                    :color="impactStatusColor(detail?.automation_impact_status)"
                    size="small"
                    >{{
                      enumTitle(
                        enumStore.manual_test_automation_impact_status,
                        detail?.automation_impact_status
                      )
                    }}</a-tag
                  >
                </a-descriptions-item>
              </a-descriptions>
            </section>
          </div>

        </MangoPanelSpin>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { scaleDensityPixels } from '@/hooks/useDisplayDensity'
  import { computed, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, watch } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import { useEnum } from '@/store/modules/get-enum'
  import useUserStore from '@/store/modules/user'
  import {
    getStatusTagColor,
    MANUAL_TEST_CHANGE_STATUS_COLORS,
    MANUAL_TEST_IMPACT_STATUS_COLORS,
    MANUAL_TEST_OPTIMIZE_STATUS_COLORS,
  } from '@/utils/status-color'
  import { getManualCaseDetail } from '@/api/functional-test'
  import type { ManualCaseDetail } from '@/api/functional-test/types'
  import MangoPanelSpin from '@/components/feedback/MangoPanelSpin.vue'
  import { bindingColumns, BINDING_SCROLL_X } from './config'
  import { bindingCaseId, caseDetailId, enumTitle } from './presentation'

  const route = useRoute(),
    router = useRouter(),
    user = useUserStore(),
    enumStore = useEnum()
  const caseId = computed(() => caseDetailId(route.query.id))
  const detail = ref<ManualCaseDetail | null>(null)
  const loading = ref(false),
    loadError = ref(false),
    enumLoading = ref(false),
    enumError = ref(false)
  const pagePath = route.path
  let active = true,
    generation = 0,
    detailRequest = 0,
    enumRequest = 0
  const isActive = () => active && route.path === pagePath
  const current = (value: number) => isActive() && generation === value

  function invalidate() {
    ++generation
    ++detailRequest
    ++enumRequest
    detail.value = null
    loading.value = false
    loadError.value = false
    enumLoading.value = false
    enumError.value = false
  }
  function start() {
    invalidate()
    if (!isActive() || caseId.value === null) return
    void loadDetail()
    void loadEnums()
  }
  function stop() {
    active = false
    invalidate()
  }
  async function loadDetail() {
    if (!isActive() || caseId.value === null) return false
    const request = ++detailRequest,
      context = generation,
      id = caseId.value
    loading.value = true
    loadError.value = false
    try {
      const response = await getManualCaseDetail(id)
      if (request !== detailRequest || !current(context)) return false
      detail.value = response.data
      return true
    } catch (loadFailure0) {
      if (request === detailRequest && current(context)) (reportLoadError(loadFailure0, "加载失败，请重试", false), loadError.value = true)
      return false
    } finally {
      if (request === detailRequest && current(context)) loading.value = false
    }
  }
  async function loadEnums() {
    if (!isActive() || caseId.value === null) return false
    const request = ++enumRequest,
      context = generation
    enumLoading.value = true
    enumError.value = false
    try {
      await enumStore.getEnum()
      return request === enumRequest && current(context)
    } catch (loadFailure1) {
      if (request === enumRequest && current(context)) (reportLoadError(loadFailure1, "加载失败，请重试", false), enumError.value = true)
      return false
    } finally {
      if (request === enumRequest && current(context)) enumLoading.value = false
    }
  }
  function enumColor(value: number | null | undefined) {
    return value == null ? undefined : enumStore.colors[Number(value)]
  }
  const optimizeStatusColor = (value: number) =>
    getStatusTagColor(MANUAL_TEST_OPTIMIZE_STATUS_COLORS, value)
  const changeStatusColor = (value: number) =>
    getStatusTagColor(MANUAL_TEST_CHANGE_STATUS_COLORS, value)
  const impactStatusColor = (value: number) =>
    getStatusTagColor(MANUAL_TEST_IMPACT_STATUS_COLORS, value)

  watch(
    () => [
      route.path,
      route.query.id,
      user.userId,
      user.roleId,
      user.token,
      user.selected_environment,
    ],
    start,
    { flush: 'sync' }
  )
  onMounted(start)
  onDeactivated(stop)
  onBeforeUnmount(stop)
  onActivated(() => {
    if (!active) {
      active = true
      start()
    }
  })
</script>

<style scoped>
  .mango-functional-case-details {
    min-width: 0;
    padding: var(--m-page-gap);
    background: var(--m-bg);
    color: var(--m-text);
  }
  .mango-functional-case-details h1 {
    margin: 0;
  }
  .mango-functional-case-details .mango-detail-workbench {
    display: grid;
    gap: var(--m-page-gap);
  }
  .mango-functional-case-details__body {
    width: 100%;
    min-width: 0;
  }
  .mango-functional-case-details__grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: var(--m-page-gap);
  }
  .mango-functional-case-details__grid > section {
    min-width: 0;
  }
  .mango-functional-case-details__source {
    grid-column: 1 / -1;
  }
  .mango-functional-case-details__text {
    white-space: pre-wrap;
    overflow-wrap: anywhere;
  }
</style>
