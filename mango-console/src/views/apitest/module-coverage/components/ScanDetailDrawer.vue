<template>
  <a-drawer v-model:visible="visible" title="扫描详情" width="820px" unmount-on-close>
    <MangoPanelSpin :loading="detailLoading">
      <template v-if="detailFailed"><a-button :loading="detailLoading" size="small" @click="loadDetail">重新加载</a-button></template>
      <a-descriptions v-if="detail.id" :column="2" bordered size="small">
        <a-descriptions-item label="扫描ID">{{ detail.id }}</a-descriptions-item>
        <a-descriptions-item label="状态">{{
          labels[detail.status || ''] || detail.status
        }}</a-descriptions-item>
        <a-descriptions-item label="扫描范围">{{
          labels[detail.scope_type || ''] || '模块扫描'
        }}</a-descriptions-item>
        <a-descriptions-item label="目标接口">{{
          detail.target_interface ? `#${detail.target_interface}` : '-'
        }}</a-descriptions-item>
        <a-descriptions-item label="仓库/分支"
          >{{ detail.repository_name }} / {{ detail.branch }}</a-descriptions-item
        >
        <a-descriptions-item label="Commit">{{ detail.commit_sha }}</a-descriptions-item>
        <a-descriptions-item label="基线Commit" :span="2">{{
          detail.base_commit_sha || '-'
        }}</a-descriptions-item>
        <a-descriptions-item label="接口增删改"
          >+{{ detail.summary?.interface_created || 0 }} / ~{{
            detail.summary?.interface_updated || 0
          }}
          / -{{ detail.summary?.interface_removed || 0 }}</a-descriptions-item
        >
        <a-descriptions-item label="Case增删改"
          >+{{ detail.summary?.created || 0 }} / ~{{ detail.summary?.updated || 0 }} / -{{
            detail.summary?.removed || 0
          }}</a-descriptions-item
        >
      </a-descriptions>
    </MangoPanelSpin>
    <MangoPanelSpin :loading="validationLoading">
      <template v-if="validationFailed"><a-button :loading="validationLoading" size="small" @click="loadValidation"
          >重新加载</a-button></template>
      <a-descriptions :column="2" bordered size="small">
        <a-descriptions-item label="扫描接口"
          >{{ validation.received_interface_count ?? '—' }} /
          {{ validation.expected_interface_count ?? '-' }}</a-descriptions-item
        >
        <a-descriptions-item label="扫描Case"
          >{{ validation.received_case_count ?? '—' }} /
          {{ validation.expected_case_count ?? '-' }}</a-descriptions-item
        >
        <a-descriptions-item label="链路完整">{{
          validation.resolved_interface_count ?? '—'
        }}</a-descriptions-item>
        <a-descriptions-item label="尚未完成解析"
          >未分析/占位 {{ validation.placeholder_interface_count ?? '—' }} / Gap
          {{ validation.gap_interface_count ?? '—' }}</a-descriptions-item
        >
      </a-descriptions>
      <a-alert
        v-if="validation.blocking_errors?.length"
        type="error"
        class="mango-scan-detail__alert"
        >{{ validation.blocking_errors.join('；') }}</a-alert
      >
      <a-alert
        v-if="validation.gap_errors?.length"
        type="warning"
        class="mango-scan-detail__alert"
        >{{ validation.gap_errors.join('；') }}</a-alert
      >
      <a-list
        v-if="validation.unresolved_interfaces?.length"
        size="small"
        :data="validation.unresolved_interfaces"
        class="mango-scan-detail__list"
      >
        <template #header>
          链路异常（最多展示 {{ validation.unresolved_interface_sample_limit || 20 }} 条）
        </template>
        <template #item="{ item }">
          <a-list-item>
            <a-tag size="small" :color="item.status === 'placeholder' ? 'red' : 'orange'">
              {{ labels[item.status] || item.status }}
            </a-tag>
            <div class="mango-scan-detail__gap">
              <strong>{{ item.source_key }}</strong>
              <span>原因：{{ item.reason }}</span>
              <span v-if="item.next_action">下一步：{{ item.next_action }}</span>
              <span v-if="item.resumption_point">恢复点：{{ item.resumption_point }}</span>
            </div>
          </a-list-item>
        </template>
      </a-list>
    </MangoPanelSpin>
    <MangoPanelSpin :loading="uploadLoading">
      <template v-if="uploadFailed"><a-button :loading="uploadLoading" size="small" @click="loadUploadStatus"
          >重新加载</a-button></template>
      <a-list
        size="small"
        :data="uploadStatus.interface_items || []"
        class="mango-scan-detail__list"
      >
        <template #header>已接收接口</template>
        <template #item="{ item }"
          ><a-list-item>{{ item.source_key }} · {{ item.sync_action }}</a-list-item></template
        >
      </a-list>
      <a-list size="small" :data="uploadStatus.items || []" class="mango-scan-detail__list">
        <template #header>已接收 Case</template>
        <template #item="{ item }"
          ><a-list-item>{{ item.source_key }} · {{ item.sync_action }}</a-list-item></template
        >
      </a-list>
      <a-pagination
        v-if="uploadStatus.count > pageSize"
        v-model:current="page"
        :page-size="pageSize"
        :total="uploadStatus.count"
        size="small"
        class="mango-scan-detail__pagination"
        @change="loadUploadStatus"
      />
    </MangoPanelSpin>
  </a-drawer>
</template>

<script lang="ts" setup>
import { reportLoadError } from '@/utils/load-error'

  import { ref } from 'vue'
  import MangoPanelSpin from '@/components/feedback/MangoPanelSpin.vue'
  import {
    getCoverageScanDetail,
    getCoverageScanUploadStatus,
    getCoverageScanValidation,
  } from '@/api/apitest/module-coverage'
  import { labels } from '../config'
  import { useCoveragePanelScope } from '../composables/useCoveragePanelScope'
  import type { CoverageRecord, ScanValidation, ScanUploadStatus } from '../types'
  const visible = ref(false),
    detail = ref<CoverageRecord>({ id: 0 }),
    validation = ref<ScanValidation>({}),
    uploadStatus = ref<ScanUploadStatus>({})
  const detailLoading = ref(false),
    validationLoading = ref(false),
    uploadLoading = ref(false)
  const detailFailed = ref(false),
    validationFailed = ref(false),
    uploadFailed = ref(false)
  const scanId = ref<number>(),
    page = ref(1),
    pageSize = 20
  let session = 0,
    detailRequest = 0,
    validationRequest = 0,
    uploadRequest = 0
  const { begin, current, close } = useCoveragePanelScope(visible, () => {
    detailLoading.value = false
    validationLoading.value = false
    uploadLoading.value = false
    ++detailRequest
    ++validationRequest
    ++uploadRequest
  })
  async function loadDetail() {
    if (!visible.value || !scanId.value) return
    const token = session,
      request = ++detailRequest,
      id = scanId.value
    detailLoading.value = true
    detailFailed.value = false
    try {
      const response = await getCoverageScanDetail(id)
      if (current(token) && request === detailRequest) detail.value = response.data
    } catch (loadFailure0) {
      if (current(token) && request === detailRequest) (reportLoadError(loadFailure0, "加载失败，请重试", false), detailFailed.value = true)
    } finally {
      if (current(token) && request === detailRequest) detailLoading.value = false
    }
  }
  async function loadValidation() {
    if (!visible.value || !scanId.value) return
    const token = session,
      request = ++validationRequest,
      id = scanId.value
    validationLoading.value = true
    validationFailed.value = false
    try {
      const response = await getCoverageScanValidation(id)
      if (current(token) && request === validationRequest) validation.value = response.data || {}
    } catch (loadFailure1) {
      if (current(token) && request === validationRequest) (reportLoadError(loadFailure1, "加载失败，请重试", false), validationFailed.value = true)
    } finally {
      if (current(token) && request === validationRequest) validationLoading.value = false
    }
  }
  async function loadUploadStatus() {
    if (!visible.value || !scanId.value) return
    const token = session,
      request = ++uploadRequest,
      id = scanId.value,
      requestedPage = page.value
    uploadLoading.value = true
    uploadFailed.value = false
    try {
      const response = await getCoverageScanUploadStatus(id, requestedPage, pageSize)
      if (current(token) && request === uploadRequest) uploadStatus.value = response.data || {}
    } catch (loadFailure2) {
      if (current(token) && request === uploadRequest) (reportLoadError(loadFailure2, "加载失败，请重试", false), uploadFailed.value = true)
    } finally {
      if (current(token) && request === uploadRequest) uploadLoading.value = false
    }
  }
  function open(id: number) {
    session = begin()
    scanId.value = id
    page.value = 1
    detail.value = { id: 0 }
    validation.value = {}
    uploadStatus.value = {}
    visible.value = true
    return Promise.all([loadDetail(), loadValidation(), loadUploadStatus()])
  }
  defineExpose({ open, close })
</script>
<style lang="less" scoped>
  .mango-scan-detail__alert,
  .mango-scan-detail__list {
    margin-top: var(--m-page-gap);
  }
  .mango-scan-detail__pagination {
    display: flex;
    justify-content: flex-end;
    margin-top: var(--m-page-gap);
  }
  .mango-scan-detail__gap {
    display: inline-flex;
    flex-direction: column;
    gap: 2px;
    margin-left: 8px;
  }
</style>
