<template>
  <div class="mango-detail-workbench">
    <div class="mango-detail-toolbar">
      <a-space>
        <a-button class="mango-back-button" @click="router.back()" data-testid="qa-views-functional-test-case-details-button-返回">返回</a-button>
        <strong>{{ detail?.title || '功能用例详情' }}</strong>
      </a-space>
    </div>
    <a-spin :loading="loading">
      <a-grid :cols="2" :col-gap="12" :row-gap="12">
        <a-grid-item>
          <div class="mango-section-card">
            <div class="mango-section-title">基础信息</div>
            <a-descriptions :column="1" bordered size="small">
              <a-descriptions-item label="用例编号">{{ detail?.case_no || '-' }}</a-descriptions-item>
              <a-descriptions-item label="优先级">
                <a-tag :color="enumColor(detail?.priority)" size="small">{{ enumTitle(enumStore.case_level, detail?.priority) }}</a-tag>
              </a-descriptions-item>
              <a-descriptions-item label="前置条件">{{ detail?.precondition || '-' }}</a-descriptions-item>
              <a-descriptions-item label="测试场景">{{ detail?.test_point || '-' }}</a-descriptions-item>
              <a-descriptions-item label="测试数据">{{ detail?.test_data || '-' }}</a-descriptions-item>
              <a-descriptions-item label="备注">{{ detail?.remark || '-' }}</a-descriptions-item>
            </a-descriptions>
          </div>
        </a-grid-item>
        <a-grid-item>
          <div class="mango-section-card">
            <div class="mango-section-title">自动化绑定</div>
            <a-table
              :bordered="false"
              :columns="bindingColumns"
              :data="detail?.bindings || []"
              :pagination="false"
              :row-key="'id'"
              :scroll="{ x: 620 }"
            >
              <template #columns>
                <a-table-column v-for="item of bindingColumns" :key="item.key" v-bind="item">
                  <template v-if="item.key === 'automation_type'" #cell="{ record }">
                    <a-tag :color="enumColor(record.automation_type)" size="small">
                      {{ enumTitle(enumStore.manual_test_automation_type, record.automation_type) }}
                    </a-tag>
                  </template>
                  <template v-else-if="item.key === 'case_id'" #cell="{ record }">
                    {{ record.api_case_id || record.ui_case_id || record.automation_case_id }}
                  </template>
                  <template v-else-if="item.key === 'optimize_status'" #cell="{ record }">
                    <a-tag :color="optimizeStatusColor(record.optimize_status)" size="small">{{ enumTitle(enumStore.manual_test_optimize_status, record.optimize_status) }}</a-tag>
                  </template>
                </a-table-column>
              </template>
            </a-table>
          </div>
        </a-grid-item>
        <a-grid-item :span="2">
          <div class="mango-section-card">
            <div class="mango-section-title">来源与同步</div>
            <a-descriptions :column="2" bordered size="small">
              <a-descriptions-item label="来源片段">{{ detail?.source_text || '-' }}</a-descriptions-item>
              <a-descriptions-item label="变更状态">
                <a-tag :color="changeStatusColor(detail?.change_status)" size="small">{{ enumTitle(enumStore.manual_test_change_status, detail?.change_status) }}</a-tag>
              </a-descriptions-item>
              <a-descriptions-item label="自动化影响">
                <a-tag :color="impactStatusColor(detail?.automation_impact_status)" size="small">{{ enumTitle(enumStore.manual_test_automation_impact_status, detail?.automation_impact_status) }}</a-tag>
              </a-descriptions-item>
            </a-descriptions>
          </div>
        </a-grid-item>
      </a-grid>
    </a-spin>

  </div>
</template>

<script setup lang="ts">
  import { onMounted, ref } from 'vue'

  import { useRoute, useRouter } from 'vue-router'

  import { useEnum } from '@/store/modules/get-enum'

  import { getStatusTagColor, MANUAL_TEST_CHANGE_STATUS_COLORS, MANUAL_TEST_IMPACT_STATUS_COLORS, MANUAL_TEST_OPTIMIZE_STATUS_COLORS } from '@/utils/status-color'

  import { getManualCaseDetail } from '@/api/functional-test'

  const route = useRoute()

  const router = useRouter()

  const enumStore = useEnum()

  const loading = ref(false)

  const detail = ref<any>(null)

  const bindingColumns = [
    { title: '类型', key: 'automation_type', dataIndex: 'automation_type', width: 120 },
    { title: '用例 ID', key: 'case_id', dataIndex: 'automation_case_id', width: 110 },
    { title: '名称', key: 'automation_case_name', dataIndex: 'automation_case_name', ellipsis: true, tooltip: true },
    { title: '优化状态', key: 'optimize_status', dataIndex: 'optimize_status', width: 120 },
  ]

  function enumTitle(options: any[] = [], value: any) {
    return options.find((item) => item.key === value)?.title || value || '-'
  }

  function enumColor(value: any) {
    return enumStore.colors?.[Number(value)]
  }

  const optimizeStatusColor = (value: number) =>
    getStatusTagColor(MANUAL_TEST_OPTIMIZE_STATUS_COLORS, value)

  const changeStatusColor = (value: number) =>
    getStatusTagColor(MANUAL_TEST_CHANGE_STATUS_COLORS, value)

  const impactStatusColor = (value: number) =>
    getStatusTagColor(MANUAL_TEST_IMPACT_STATUS_COLORS, value)

  async function loadDetail() {
    loading.value = true
    try {
      const res = await getManualCaseDetail(Number(route.query.id))
      detail.value = res.data
    } finally {
      loading.value = false
    }
  }

  onMounted(async () => {
    await enumStore.getEnum()
    loadDetail()
  })
</script>
