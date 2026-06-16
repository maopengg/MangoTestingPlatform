<template>
  <div class="mango-detail-workbench">
    <div class="mango-detail-toolbar">
      <a-space>
        <a-button @click="router.back()">返回</a-button>
        <strong>{{ detail?.title || '功能用例详情' }}</strong>
      </a-space>
      <a-space>
        <a-button type="primary" :loading="planLoading" @click="openPlanDialog">生成 API 自动化</a-button>
        <a-button disabled>生成 UI 自动化</a-button>
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
              <a-descriptions-item label="测试点">{{ detail?.test_point || '-' }}</a-descriptions-item>
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
                    <a-tag :color="statusColor(record.optimize_status)" size="small">{{ enumTitle(enumStore.manual_test_optimize_status, record.optimize_status) }}</a-tag>
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
                <a-tag :color="statusColor(detail?.change_status)" size="small">{{ enumTitle(enumStore.manual_test_change_status, detail?.change_status) }}</a-tag>
              </a-descriptions-item>
              <a-descriptions-item label="自动化影响">
                <a-tag :color="statusColor(detail?.automation_impact_status)" size="small">{{ enumTitle(enumStore.manual_test_automation_impact_status, detail?.automation_impact_status) }}</a-tag>
              </a-descriptions-item>
            </a-descriptions>
          </div>
        </a-grid-item>
      </a-grid>
    </a-spin>

    <a-modal
      v-model:visible="planDialogVisible"
      title="生成 API 自动化用例"
      width="720px"
      :confirm-loading="planLoading"
      @ok="makePlan"
    >
      <a-form :model="planForm" layout="vertical">
        <a-form-item label="角色提示词">
          <a-select
            v-model="planForm.ai_role"
            :options="aiRoleOptions"
            :field-names="fieldNames"
            placeholder="请选择角色提示词"
          />
        </a-form-item>
        <a-form-item label="技能">
          <a-select
            v-model="planForm.skill_id"
            :options="skillOptions"
            :field-names="fieldNames"
            :loading="aiOptionLoading"
            allow-clear
            placeholder="请选择 Skill"
          />
        </a-form-item>
        <a-form-item label="MCP 服务">
          <a-select
            v-model="planForm.mcp_server_ids"
            :options="mcpServerOptions"
            :field-names="fieldNames"
            :loading="aiOptionLoading"
            allow-clear
            multiple
            placeholder="请选择 MCP 服务"
          />
        </a-form-item>
        <a-form-item label="追问/补充要求">
          <a-textarea v-model="planForm.user_instruction" placeholder="补充本次 API 自动化生成要求" :auto-size="{ minRows: 2, maxRows: 4 }" />
        </a-form-item>
        <a-form-item label="携带上下文">
          <a-checkbox-group v-model="planForm.context_keys" direction="vertical">
            <a-checkbox :value="0">产品角色 / 需求文档</a-checkbox>
            <a-checkbox :value="1">开发角色 / 开发设计</a-checkbox>
            <a-checkbox :value="2">开发角色 / 接口文档</a-checkbox>
            <a-checkbox :value="3">开发角色 / 开发代码</a-checkbox>
            <a-checkbox :value="4">开发角色 / SQL语句</a-checkbox>
            <a-checkbox :value="5">测试角色 / 原始用例文档</a-checkbox>
          </a-checkbox-group>
        </a-form-item>
      </a-form>
    </a-modal>

  </div>
</template>

<script setup lang="ts">
  import { Message } from '@arco-design/web-vue'
  import { computed, onMounted, reactive, ref } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import { useEnum } from '@/store/modules/get-enum'
  import { getAiMcpServer, getAiSkill, postAiApiAutomationAgentStart } from '@/api/ai'
  import { getManualCaseDetail } from '@/api/functional-test'

  const route = useRoute()
  const router = useRouter()
  const enumStore = useEnum()
  const loading = ref(false)
  const planLoading = ref(false)
  const aiOptionLoading = ref(false)
  const planDialogVisible = ref(false)
  const detail = ref<any>(null)
  const aiSkills = ref<any[]>([])
  const mcpServers = ref<any[]>([])
  const fieldNames = { value: 'key', label: 'title' }
  const planForm = reactive<any>({
    context_keys: [0, 1, 2, 3, 4],
    ai_role: 'api_automation_expert',
    skill_id: null,
    mcp_server_ids: [],
    user_instruction: '',
  })
  const aiRoleOptions = [
    { key: 'business_test_expert', title: '业务测试专家' },
    { key: 'api_automation_expert', title: 'API自动化测试专家' },
  ]
  const skillOptions = computed(() =>
    aiSkills.value.filter((item) => item.status === 1 && item.skill_type === 1).map((item) => ({ key: item.id, title: item.name }))
  )
  const mcpServerOptions = computed(() =>
    mcpServers.value.filter((item) => item.status === 1).map((item) => ({ key: item.id, title: item.is_connected ? item.name : `${item.name}（未连接）` }))
  )
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
  function statusColor(value: any) {
    return enumStore.status_colors?.[Number(value)]
  }
  async function loadDetail() {
    loading.value = true
    try {
      const res = await getManualCaseDetail(Number(route.query.id))
      detail.value = res.data
    } finally {
      loading.value = false
    }
  }
  async function loadAiOptions() {
    aiOptionLoading.value = true
    try {
      const [skillRes, mcpRes] = await Promise.all([getAiSkill({ status: 1, page: 1, pageSize: 100 }), getAiMcpServer({})])
      aiSkills.value = skillRes.data || []
      mcpServers.value = mcpRes.data || []
      if (!planForm.skill_id && skillOptions.value.length) {
        planForm.skill_id = skillOptions.value[0].key
      }
      if (!planForm.mcp_server_ids?.length && mcpServerOptions.value.length) {
        const connected = mcpServers.value.find((item) => item.status === 1 && item.is_connected)
        planForm.mcp_server_ids = [connected?.id || mcpServerOptions.value[0].key]
      }
    } finally {
      aiOptionLoading.value = false
    }
  }
  async function openPlanDialog() {
    planForm.context_keys = [0, 1, 2, 3, 4]
    planForm.ai_role = 'api_automation_expert'
    planDialogVisible.value = true
    await loadAiOptions()
  }
  async function makePlan() {
    if (!planForm.ai_role) {
      Message.error('请选择角色提示词')
      return false
    }
    if (!planForm.skill_id) {
      Message.error('请选择技能')
      return false
    }
    if (!planForm.mcp_server_ids?.length) {
      Message.error('请选择 MCP 服务')
      return false
    }
    planLoading.value = true
    try {
      await postAiApiAutomationAgentStart({
        manual_case_id: detail.value.id,
        context_keys: planForm.context_keys,
        skill_id: planForm.skill_id,
        mcp_server_ids: planForm.mcp_server_ids,
        ai_role: planForm.ai_role,
        user_instruction: planForm.user_instruction,
      })
      planDialogVisible.value = false
      Message.success('已创建 API 自动化生成任务')
      return true
    } finally {
      planLoading.value = false
    }
  }
  onMounted(async () => {
    await enumStore.getEnum()
    loadDetail()
  })
</script>
