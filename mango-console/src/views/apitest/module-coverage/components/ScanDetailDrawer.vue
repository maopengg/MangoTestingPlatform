<template>
  <a-drawer v-model:visible="visible" title="扫描详情" width="820px" unmount-on-close>
    <a-spin :loading="loading">
      <a-descriptions v-if="detail.id" :column="2" bordered size="small">
        <a-descriptions-item label="扫描ID">{{ detail.id }}</a-descriptions-item>
        <a-descriptions-item label="状态">{{
          labels[detail.status] || detail.status
        }}</a-descriptions-item>
        <a-descriptions-item label="扫描范围">{{
          labels[detail.scope_type] || '模块扫描'
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
        <a-descriptions-item label="扫描接口"
          >{{ validation.received_interface_count ?? 0 }} /
          {{ validation.expected_interface_count ?? '-' }}</a-descriptions-item
        >
        <a-descriptions-item label="扫描Case"
          >{{ validation.received_case_count ?? 0 }} /
          {{ validation.expected_case_count ?? '-' }}</a-descriptions-item
        >
        <a-descriptions-item label="链路完整">{{
          validation.resolved_interface_count ?? 0
        }}</a-descriptions-item>
        <a-descriptions-item label="尚未完成解析"
          >未分析/占位 {{ validation.placeholder_interface_count ?? 0 }} / Gap
          {{ validation.gap_interface_count ?? 0 }}</a-descriptions-item
        >
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
    </a-spin>
  </a-drawer>
</template>

<script lang="ts" setup>
  import { reactive, ref } from 'vue'
  import {
    getCoverageScanDetail,
    getCoverageScanUploadStatus,
    getCoverageScanValidation,
  } from '@/api/apitest/module-coverage'
  import { labels } from '../config'

  const visible = ref(false)
  const loading = ref(false)
  const detail = reactive<any>({})
  const validation = reactive<any>({})
  const uploadStatus = reactive<any>({})
  const scanId = ref<number>()
  const page = ref(1)
  const pageSize = 20

  async function loadUploadStatus() {
    if (!scanId.value) return
    Object.assign(
      uploadStatus,
      (await getCoverageScanUploadStatus(scanId.value, page.value, pageSize)).data || {}
    )
  }

  async function open(id: number) {
    scanId.value = id
    page.value = 1
    visible.value = true
    loading.value = true
    try {
      const [detailResponse, validationResponse, statusResponse] = await Promise.all([
        getCoverageScanDetail(id),
        getCoverageScanValidation(id),
        getCoverageScanUploadStatus(id, page.value, pageSize),
      ])
      Object.assign(detail, detailResponse.data || {})
      Object.assign(validation, validationResponse.data || {})
      Object.assign(uploadStatus, statusResponse.data || {})
    } finally {
      loading.value = false
    }
  }

  defineExpose({ open })
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
