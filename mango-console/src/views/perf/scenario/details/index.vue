<template>
  <TableBody plain class="mango-detail-workbench-page mango-perf-page">
    <template #header>
      <TableHeader :title="`性能场景 / ${form.name || '配置'}`">
        <template #header-extra>
          <a-space>
            <a-button  status="success" size="small" :loading="executing" @click="openExecuteDialog"
              >执行场景</a-button
            >
            <a-button  size="small" :loading="scriptPreviewLoading" @click="openScriptPreview">预览 k6 脚本</a-button>
            <a-button size="small" :loading="validating" @click="validateConfig">校验配置</a-button>
            <a-button  type="primary" size="small" :loading="saving" @click="save">保存</a-button>
            <a-button class="mango-back-button" size="small" @click="router.back()">返回</a-button>
          </a-space>
        </template>
      </TableHeader>
    </template>
    <template #default>
      <a-spin :loading="loading" class="mango-perf-detail-spin">
        <div class="mango-perf-config-workbench">
          <div class="mango-perf-editor-grid">
            <main class="mango-perf-flow-column">
              <section class="mango-section-card mango-perf-flow-section">
                <div class="mango-section-title mango-perf-section-heading">
                  <div
                    ><span>Case 编排</span
                    ><small>一次 iteration 完整执行一次已发布 Case</small></div
                  >
                  <a-button size="small" :disabled="!sourceCase?.case_id" @click="caseDetailVisible = true"
                    >查看用例详情</a-button
                  >
                </div>
                <a-form layout="horizontal" :model="form" auto-label-width>
                  <a-form-item label="已发布 Case" required>
                    <a-select
                      v-model="form.source_case_release_id"
                      :options="caseOptions"
                      :loading="!loading && caseLoading"
                      allow-search
                      placeholder="请选择当前产品下已发布的API自动化 Case"
                      @change="selectCase"
                    />
                  </a-form-item>
                </a-form>
                <template v-if="sourceCase">
                  <a-alert v-if="!sourceCase.compatible" type="error"
                    >当前 Case 暂不兼容性能模式：{{
                      sourceCase.incompatible_reasons?.join('；')
                    }}</a-alert
                  >
                  <div v-else class="mango-perf-case-meta">
                    <a-tag size="small" color="green">已发布 {{ sourceCase.version_label }}</a-tag>
                    <span>{{ sourceCase.module_full_path }}</span
                    ><span>修订 #{{ sourceCase.revision_no }}</span>
                  </div>
                  <div class="mango-perf-step-list">
                    <article
                      v-for="(item, index) in sourceCase.steps || []"
                      :key="item.key"
                      class="mango-soft-panel mango-perf-step-item"
                    >
                      <div class="mango-perf-step-index">{{ index + 1 }}</div>
                      <div class="mango-perf-step-content">
                        <strong>{{ item.name }}</strong>
                        <div class="mango-perf-meta-row"
                          ><span>API #{{ item.api_info_id }}</span
                          ><span>提取 {{ item.extractor_count }}</span
                          ><span>检查 {{ item.check_count }}</span></div
                        >
                      </div>
                      <a-tag size="small">只读</a-tag>
                    </article>
                  </div>
                </template>
                <div v-else class="mango-perf-empty"
                  ><strong>请选择一个已发布 Case</strong
                  ><span>请求、变量、提取和断言均复用 Case 发布快照</span></div
                >
              </section>
            </main>

            <aside class="mango-perf-settings-column">
              <section class="mango-section-card mango-perf-settings-panel">
                <div class="mango-section-title mango-perf-section-heading"
                  ><div><span>场景设置</span><small>基本信息与执行器策略</small></div></div
                >
                <a-form
                  :model="form"
                  layout="horizontal"
                  :label-col-props="{ span: 7 }"
                  :wrapper-col-props="{ span: 17 }"
                >
                  <a-form-item label="场景名称" required
                    ><a-input v-model="form.name" :max-length="128"
                  /></a-form-item>
                  <a-form-item label="执行引擎"
                    ><a-select v-model="form.engine" :options="engineOptions" disabled
                  /></a-form-item>
                  <a-form-item label="执行器数"
                    ><a-input-number v-model="form.default_executor_count" :min="1" :max="100"
                  /></a-form-item>
                  <a-form-item label="失败策略"
                    ><a-select v-model="form.node_failure_policy" :options="failurePolicyOptions"
                  /></a-form-item>
                  <a-form-item label="最小就绪节点"
                    ><a-input-number
                      v-model="form.min_ready_nodes"
                      :min="1"
                      :max="form.default_executor_count || 100"
                      :disabled="form.node_failure_policy === 'strict'"
                  /></a-form-item>
                </a-form>
              </section>

              <section class="mango-section-card mango-perf-side-section">
                <div class="mango-section-title mango-perf-section-heading">
                  <div><span>负载配置</span><small>一次运行只使用这一套负载配置</small></div>
                  <a-button  size="mini" type="text" @click="openLoadConfig">编辑</a-button>
                </div>
                <div v-if="hasLoadConfig" class="mango-soft-panel mango-perf-load-summary">
                  <div class="mango-perf-load-name">
                    <span>压测方案</span>
                    <strong>{{ loadProfileLabel(loadConfig.profile) }}</strong>
                  </div>
                  <div class="mango-perf-load-metric">
                    <span>目标负载</span>
                    <strong>{{ formatLoadTarget(loadConfig) }}</strong>
                    <small>{{ formatLoadUnit(loadConfig) }}</small>
                  </div>
                  <div class="mango-perf-load-metric">
                    <span>{{ loadConfig.profile === 'fixed_iterations' ? '截止时间' : '持续时间' }}</span>
                    <strong>{{ loadConfig.duration_seconds || 0 }}</strong>
                    <small>秒</small>
                  </div>
                  <div class="mango-perf-load-metric">
                    <span>{{ loadConfig.profile === 'fixed_iterations' ? 'Case 执行次数' : '配置名称' }}</span>
                    <strong>{{ loadConfig.profile === 'fixed_iterations' ? loadConfig.total_iterations : loadConfig.name }}</strong>
                  </div>
                </div>
                <div v-else class="mango-perf-empty"
                  ><strong>尚未配置负载</strong><span>请设置持续时间和目标负载</span></div
                >
              </section>

              <section class="mango-section-card mango-perf-side-section">
                <div class="mango-section-title mango-perf-section-heading">
                  <div><span>性能目标</span><small>三个客户端指标 AND 判定</small></div>
                  <a-select
                    v-model="performanceGoalTemplate"
                    class="mango-perf-goal-template-select"
                    size="mini"
                    :options="performanceGoalTemplateOptions"
                    @change="applyPerformanceGoalTemplate"
                  />
                </div>
                <p class="mango-perf-goal-description">{{ performanceGoalDescription }}</p>
                <div class="mango-perf-goal-form">
                  <label class="mango-perf-goal-row"
                    ><span><strong>P95 响应时间</strong><small>95% 请求耗时上限</small></span
                    ><a-input-number
                      v-model="performanceGoal.p95_ms"
                      :min="1"
                      :precision="0"
                      @change="markPerformanceGoalCustom"
                      ><template #suffix>ms</template></a-input-number
                    ></label
                  >
                  <label class="mango-perf-goal-row"
                    ><span><strong>错误率</strong><small>失败请求比例上限</small></span
                    ><a-input-number
                      v-model="performanceGoal.error_rate_percent"
                      :min="0"
                      :max="100"
                      :precision="2"
                      @change="markPerformanceGoalCustom"
                      ><template #suffix>%</template></a-input-number
                    ></label
                  >
                  <label class="mango-perf-goal-row"
                    ><span><strong>负载达成率</strong><small>实际负载最低比例</small></span
                    ><a-input-number
                      v-model="performanceGoal.load_achievement_rate_percent"
                      :min="0"
                      :max="100"
                      :precision="2"
                      @change="markPerformanceGoalCustom"
                      ><template #suffix>%</template></a-input-number
                    ></label
                  >
                </div>
              </section>
            </aside>
          </div>
        </div>
      </a-spin>
    </template>
  </TableBody>

  <ModalDialog ref="loadDialogRef" title="编辑负载配置" :width="720" @confirm="commitLoadConfig">
    <template #content>
      <a-form ref="loadFormRef" :model="loadEditor.form" layout="horizontal" auto-label-width>
        <a-form-item field="profile" label="压测方案" required
          :rules="[{ required: true, message: '请选择压测方案' }]">
          <a-select v-model="loadEditor.form.profile" :options="loadProfileOptions" @change="selectLoadProfile" />
        </a-form-item>
        <a-alert type="info" class="mango-perf-profile-hint">{{ loadProfileHint }}</a-alert>
        <a-form-item
          field="name"
          label="配置名称"
          required
          :rules="[{ required: true, message: '请输入配置名称' }]"
          ><a-input v-model="loadEditor.form.name" placeholder="例如：短稳态负载"
        /></a-form-item>
        <a-form-item
          v-if="showFixedDuration"
          field="duration_seconds"
          :label="loadEditor.form.profile === 'fixed_iterations' ? '截止时间' : '持续时间'"
          required
          :rules="[{ required: true, message: '请输入持续时间' }]"
          ><a-input-number v-model="loadEditor.form.duration_seconds" :min="1"
            ><template #suffix>秒</template></a-input-number
          ></a-form-item
        >
        <a-form-item
          v-if="!isRateProfile"
          field="target_users"
          :label="loadEditor.form.profile === 'spike' ? '峰值并发' : '目标并发'"
          required
          :rules="[{ required: true, message: '请输入目标并发用户数' }]"
          ><a-input-number v-model="loadEditor.form.target_users" :min="1"
        /></a-form-item>
        <a-form-item v-if="loadEditor.form.profile === 'fixed_iterations'" field="total_iterations" label="Case 执行次数" required
          :rules="[{ required: true, message: '请输入 Case 执行次数' }]">
          <a-input-number v-model="loadEditor.form.total_iterations" :min="1" />
        </a-form-item>
        <template v-if="loadEditor.form.profile === 'staircase'">
          <a-form-item label="每阶增加并发" field="step_users" required :rules="[{ required: true, message: '请输入每阶增加并发' }]">
            <a-input-number v-model="loadEditor.form.step_users" :min="1" />
          </a-form-item>
          <a-form-item label="阶梯间隔" field="step_interval_seconds" required :rules="[{ required: true, message: '请输入阶梯间隔' }]">
            <a-input-number v-model="loadEditor.form.step_interval_seconds" :min="1"><template #suffix>秒/阶</template></a-input-number>
          </a-form-item>
          <a-form-item label="峰值保持"><a-input-number v-model="loadEditor.form.hold_seconds" :min="0"><template #suffix>秒</template></a-input-number></a-form-item>
        </template>
        <template v-if="loadEditor.form.profile === 'linear_ramp' || loadEditor.form.profile === 'spike'">
          <a-form-item label="起始并发" field="start_users" required :rules="[{ required: true, message: '请输入起始并发' }]">
            <a-input-number v-model="loadEditor.form.start_users" :min="loadEditor.form.profile === 'spike' ? 1 : 0" />
          </a-form-item>
          <a-form-item v-if="loadEditor.form.profile === 'spike'" label="基线时间" field="baseline_seconds" required :rules="[{ required: true, message: '请输入基线时间' }]">
            <a-input-number v-model="loadEditor.form.baseline_seconds" :min="1"><template #suffix>秒</template></a-input-number>
          </a-form-item>
          <a-form-item label="爬坡时间" field="ramp_seconds" required :rules="[{ required: true, message: '请输入爬坡时间' }]">
            <a-input-number v-model="loadEditor.form.ramp_seconds" :min="1"><template #suffix>秒</template></a-input-number>
          </a-form-item>
          <a-form-item label="峰值保持"><a-input-number v-model="loadEditor.form.hold_seconds" :min="0"><template #suffix>秒</template></a-input-number></a-form-item>
          <a-form-item v-if="loadEditor.form.profile === 'spike'" label="恢复时间" field="recovery_seconds" required :rules="[{ required: true, message: '请输入恢复时间' }]">
            <a-input-number v-model="loadEditor.form.recovery_seconds" :min="1"><template #suffix>秒</template></a-input-number>
          </a-form-item>
        </template>
        <template v-if="isRateProfile">
          <a-form-item
            field="target_rate"
            label="目标速率"
            required
            :rules="[{ required: true, message: '请输入目标速率' }]"
            ><a-input-number v-model="loadEditor.form.target_rate" :min="1"
          /></a-form-item>
          <a-form-item label="速率单位"
            ><a-select
              v-model="loadEditor.form.rate_time_unit"
              :options="[
                { label: 'Case 启动/秒', value: 'second' },
                { label: 'Case 启动/分钟', value: 'minute' },
              ]"
          /></a-form-item>
          <a-form-item label="预分配 VU"
            ><a-input-number v-model="loadEditor.form.preallocated_vus" :min="1"
          /></a-form-item>
          <a-form-item label="最大 VU"
            ><a-input-number v-model="loadEditor.form.max_vus" :min="1"
          /></a-form-item>
        </template>
        <a-form-item label="迭代间等待">
          <a-input-group>
            <a-input-number v-model="loadEditor.form.user_wait_min_ms" :min="0" :max="3600000" :precision="0" placeholder="最小 ms" />
            <span class="mango-perf-input-separator">至</span>
            <a-input-number v-model="loadEditor.form.user_wait_max_ms" :min="0" :max="3600000" :precision="0" placeholder="最大 ms" />
          </a-input-group>
        </a-form-item>
        <a-alert type="info" class="mango-perf-profile-hint">预计运行 {{ editedDuration }} 秒；执行器 {{ form.default_executor_count || 1 }} 个。定量任务按完整 Case 迭代计数，不等于 HTTP 请求数。</a-alert>
      </a-form>
    </template>
  </ModalDialog>

  <ModalDialog ref="executeDialogRef" title="执行性能场景" :width="680" @confirm="execute">
    <template #content>
      <a-form ref="executeFormRef" :model="executeForm" layout="horizontal" auto-label-width>
        <a-form-item
          field="test_env"
          label="测试环境"
          required
          :rules="[{ required: true, message: '请选择测试环境' }]"
          ><a-select
            v-model="executeForm.test_env"
            :options="enumStore.environment_type"
            :field-names="fieldNames"
            placeholder="请选择目标环境"
            @change="loadExecutorCandidates"
        /></a-form-item>
        <a-form-item
          field="selected_executor_fingerprints"
          label="执行器"
          required
          :rules="[
            {
              required: true,
              type: 'array',
              message: `请选择 ${form.default_executor_count || 1} 个执行器`,
            },
          ]"
          ><a-select
            v-model="executeForm.selected_executor_fingerprints"
            multiple
            allow-clear
            :loading="executorLoading"
            :options="executorOptions"
            :max-tag-count="3"
            :limit="Number(form.default_executor_count || 1)"
            placeholder="必须选择足量执行器后才能开始"
            @change="preflightSelectedExecutors"
        /></a-form-item>
        <a-alert
          v-if="executeForm.test_env !== null"
          :type="executorSelectionReady ? 'success' : 'warning'"
          class="mango-perf-executor-alert"
          >需要 {{ form.default_executor_count || 1 }} 个执行器，已选择
          {{ executeForm.selected_executor_fingerprints.length }} 个；每个节点至少需要
          {{ executorPreflight.required_per_node || 0 }}
          {{ String(executorPreflight.capacity_type || '').toUpperCase() }} 安全容量。</a-alert
        >
        <a-form-item label="请求记录">
          <a-space>
            <a-checkbox v-model="executeForm.capture_request">记录请求</a-checkbox>
            <a-checkbox v-model="executeForm.capture_response">记录响应</a-checkbox>
          </a-space>
        </a-form-item>
        <a-alert v-if="executeForm.capture_request || executeForm.capture_response" type="warning" class="mango-perf-profile-hint">
          每个执行器分别生成 CSV；单文件超过 100 MB 不上传。可能包含业务敏感数据，请按需开启。
        </a-alert>
        <a-form-item
          v-if="Number(executeForm.test_env) === 2"
          field="production_load_confirmed"
          label="生产风险确认"
          required
          :rules="[{ required: true, type: 'boolean', message: '请确认已获得生产环境发压授权' }]"
          ><a-checkbox v-model="executeForm.production_load_confirmed"
            >我确认已获得授权，并理解生产发压风险</a-checkbox
          ></a-form-item
        >
        <a-form-item field="remark" label="运行备注"
          ><a-textarea
            v-model="executeForm.remark"
            placeholder="本次执行目的、变更单号或关注点"
            :max-length="512"
            show-word-limit
        /></a-form-item>
      </a-form>
    </template>
  </ModalDialog>

  <BaseSidePanel
    :visible="scriptPreviewVisible"
    :title="`k6 脚本预览 / 场景版本 ${scriptPreview?.scenario_version || '-'}`"
    width="80vw"
    :show-footer="false"
    @update:visible="scriptPreviewVisible = $event"
    @cancel="scriptPreviewVisible = false"
  >
    <template #header-actions>
      <a-button v-if="scriptPreview" size="mini" @click="copyScriptPreview">复制当前内容</a-button>
    </template>
    <a-spin :loading="scriptPreviewLoading" class="mango-perf-script-preview">
      <template v-if="scriptPreview">
        <a-alert type="info" class="mango-perf-script-preview__notice">
          预览基于已保存的场景配置。执行器运行同一份脚本模板，场景快照通过环境变量注入；测试环境、分片、运行号和密钥在执行时才填入。快照按敏感字段规则脱敏，仍请勿对外分享。
        </a-alert>
        <div class="mango-perf-script-preview__meta">快照 SHA-256：{{ scriptPreview.snapshot_hash }}</div>
        <a-tabs v-model:active-key="scriptPreviewTab" class="mango-perf-script-preview__tabs">
          <a-tab-pane key="script" title="k6 脚本">
            <div class="mango-perf-script-preview__code">
              <CodeEditor :model-value="scriptPreview.script" language="javascript" readonly />
            </div>
          </a-tab-pane>
          <a-tab-pane key="snapshot" title="场景快照（脱敏）">
            <div class="mango-perf-script-preview__code">
              <CodeEditor :model-value="scriptPreview.snapshot" language="json" readonly />
            </div>
          </a-tab-pane>
        </a-tabs>
      </template>
    </a-spin>
  </BaseSidePanel>

  <BaseSidePanel
    :visible="caseDetailVisible"
    :title="`API 用例详情 / ${sourceCase?.name || ''}`"
    width="calc(92vw - 150px)"
    mode="page"
    @update:visible="caseDetailVisible = $event"
    @cancel="caseDetailVisible = false"
  >
    <ApiCaseDetails
      v-if="caseDetailVisible && sourceCase?.case_id"
      :key="sourceCase.case_id"
      embedded
      :case-id="sourceCase.case_id"
      :project-product-id="form.project_product?.id || form.project_product"
      @close="caseDetailVisible = false"
    />
  </BaseSidePanel>
</template>

<script setup lang="ts">
  import { Message, Modal } from '@arco-design/web-vue'
  import { computed, onMounted, reactive, ref } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import ModalDialog from '@/components/overlays/ModalDialog.vue'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import CodeEditor from '@/components/editors/CodeEditor.vue'
  import ApiCaseDetails from '@/views/apitest/case/details/index.vue'
  import {
    executePerfScenario,
    getPerfScenario,
    getPerfScenarioScriptPreview,
    getPerfScenarioSourceCases,
    preflightPerfScenario,
    savePerfScenarioConfiguration,
    validatePerfScenario,
  } from '@/api/perf'
  import { engineOptions, loadProfileOptions } from '../config'
  import {
    createDefaultPerformanceGoal,
    isRecommendedPerformanceGoal,
    performanceGoalTemplateOptions,
    performanceGoalFromApi,
    performanceGoalToPayload,
    type PerformanceGoalTemplateKey,
  } from './config'
  import { fieldNames } from '@/setting'
  import { useEnum } from '@/store/modules/get-enum'

  const route = useRoute()
  const router = useRouter()
  const id = String(route.query.id || '')
  const enumStore = useEnum()
  const loading = ref(false)
  const saving = ref(false)
  const validating = ref(false)
  const executing = ref(false)
  const caseLoading = ref(false)
  const executorLoading = ref(false)
  const form = reactive<any>({})
  const loadConfig = reactive<any>({})
  const sourceCase = ref<any>(null)
  const caseDetailVisible = ref(false)
  const scriptPreviewVisible = ref(false)
  const scriptPreviewLoading = ref(false)
  const scriptPreviewTab = ref('script')
  const scriptPreview = ref<{
    scenario_version: number
    snapshot_hash: string
    script: string
    snapshot: string
  } | null>(null)
  const caseItems = ref<any[]>([])
  const performanceGoal = reactive(createDefaultPerformanceGoal())
  const performanceGoalTemplate = ref<PerformanceGoalTemplateKey>('recommended')
  const loadDialogRef = ref<InstanceType<typeof ModalDialog> | null>(null)
  const loadFormRef = ref<any>(null)
  const loadEditor = reactive<any>({ form: {} })
  const isRateProfile = computed(() => ['constant_arrival_rate', 'constant_iteration_rate'].includes(loadEditor.form.profile))
  const showFixedDuration = computed(() => !['staircase', 'linear_ramp', 'spike'].includes(loadEditor.form.profile))
  const editedDuration = computed(() => {
    const value = loadEditor.form
    if (value.profile === 'staircase') return Math.ceil(Number(value.target_users || 0) / Math.max(1, Number(value.step_users || 1))) * Number(value.step_interval_seconds || 0) + Number(value.hold_seconds || 0)
    if (value.profile === 'linear_ramp') return Number(value.ramp_seconds || 0) + Number(value.hold_seconds || 0)
    if (value.profile === 'spike') return ['baseline_seconds', 'ramp_seconds', 'hold_seconds', 'recovery_seconds'].reduce((total, key) => total + Number(value[key] || 0), 0)
    return Number(value.duration_seconds || 0)
  })
  const loadProfileHint = computed(() => ({
    constant_concurrency: '固定人数持续运行指定时间；每个虚拟用户重复执行完整 Case。',
    fixed_iterations: '所有执行器合计完成指定次数的完整 Case；到截止时间仍未完成则本次运行不达标。',
    staircase: '从首阶开始，每隔指定秒数增加并发，最后可保持峰值。',
    linear_ramp: '从起始并发平滑升至目标并发，可在峰值保持一段时间。',
    spike: '先运行基线，再快速升至峰值，保持后恢复至基线。',
    soak: '固定并发长期运行，用于观察稳定性；最长 24 小时。',
    constant_arrival_rate: '按固定速率启动完整 Case；单个 Case 可以包含多个 HTTP 请求。',
    constant_iteration_rate: '按固定速率启动完整 Case；与到达率执行语义相同，保留独立模型供分类。',
  } as Record<string, string>)[loadEditor.form.profile] || '')
  const executeDialogRef = ref<InstanceType<typeof ModalDialog> | null>(null)
  const executeFormRef = ref<any>(null)
  const executorCandidates = ref<any[]>([])
  const executorPreflight = reactive<any>({})
  const executeForm = reactive<any>({
    test_env: null,
    selected_executor_fingerprints: [],
    remark: '',
    production_load_confirmed: false,
    capture_request: false,
    capture_response: false,
  })

  const failurePolicyOptions = [
    { label: '严格：全部节点就绪', value: 'strict' },
    { label: '满足最小节点后继续', value: 'continue' },
  ]
  const caseOptions = computed(() =>
    caseItems.value.map((item) => ({
      label: item.title,
      value: item.release_id,
      disabled: item.disabled,
    }))
  )
  const hasLoadConfig = computed(() => Number(loadConfig.duration_seconds || 0) > 0)
  function loadProfileLabel(profile: string) {
    return loadProfileOptions.find((item) => item.value === profile)?.label.split(' · ')[0] || '固定并发'
  }
  const performanceGoalDescription = computed(() =>
    performanceGoalTemplate.value === 'recommended'
      ? '系统推荐模板：三个客户端指标必须同时达标；仅用于结果判定，不会自动中止执行。'
      : '自定义目标：三个客户端指标按 AND 关系判定；不会自动中止执行。'
  )
  const executorOptions = computed(() =>
    executorCandidates.value.map((item) => ({
      value: item.fingerprint,
      label: `${item.executor_name || item.fingerprint} · 可用 ${item.available} ${String(
        executorPreflight.capacity_type || ''
      ).toUpperCase()}${item.calibrated ? ' · 已校准' : ' · 未校准'}`,
    }))
  )
  const executorSelectionReady = computed(
    () =>
      executeForm.selected_executor_fingerprints.length ===
        Number(form.default_executor_count || 1) && executorPreflight.can_run === true
  )

  async function loadCases() {
    caseLoading.value = true
    try {
      const response: any = await getPerfScenarioSourceCases(id)
      caseItems.value = response.data || []
      if (
        sourceCase.value &&
        !caseItems.value.some((item) => item.release_id === sourceCase.value.release_id)
      )
        caseItems.value.unshift(sourceCase.value)
    } finally {
      caseLoading.value = false
    }
  }
  async function load() {
    loading.value = true
    try {
      const response: any = await getPerfScenario(id)
      Object.assign(form, response.data)
      Object.keys(loadConfig).forEach((key) => delete loadConfig[key])
      Object.assign(loadConfig, response.data.load_config || {})
      sourceCase.value = response.data.source_case || null
      form.source_case_release_id ||= sourceCase.value?.release_id
      Object.assign(performanceGoal, performanceGoalFromApi(response.data.performance_goal))
      performanceGoalTemplate.value =
        response.data.performance_goal?.template_key === 'custom' ||
        !isRecommendedPerformanceGoal(performanceGoal)
          ? 'custom'
          : 'recommended'
      await loadCases()
    } finally {
      loading.value = false
    }
  }
  function selectCase(value: unknown) {
    sourceCase.value = caseItems.value.find((item) => item.release_id === Number(value)) || null
  }
  function formatLoadTarget(item: any) {
    return form.load_type === 'concurrency' ? item.target_users || 0 : item.target_rate || 0
  }
  function formatLoadUnit(item: any) {
    return form.load_type === 'concurrency'
      ? '并发用户'
      : item.rate_time_unit === 'minute'
      ? 'Case 启动/分钟'
      : 'Case 启动/秒'
  }
  async function openLoadConfig() {
    loadEditor.form = {
      name: '基础负载',
      profile: form.load_type === 'concurrency' ? 'constant_concurrency' : form.load_type === 'arrival_rate' ? 'constant_arrival_rate' : 'constant_iteration_rate',
      duration_seconds: 60,
      target_users: form.load_type === 'concurrency' ? 10 : null,
      target_rate: form.load_type === 'concurrency' ? null : 10,
      rate_time_unit: 'second',
      preallocated_vus: form.load_type === 'concurrency' ? null : 10,
      max_vus: form.load_type === 'concurrency' ? null : 100,
      ramp_type: 'linear',
      user_wait_min_ms: 0,
      user_wait_max_ms: 0,
      total_iterations: 10000,
      start_users: 1,
      step_users: 10,
      step_interval_seconds: 30,
      ramp_seconds: 30,
      hold_seconds: 30,
      baseline_seconds: 30,
      recovery_seconds: 30,
      ...loadConfig,
    }
    for (const [key, fallback] of Object.entries({ total_iterations: 10000, start_users: 1, step_users: 10, step_interval_seconds: 30, ramp_seconds: 30, hold_seconds: 30, baseline_seconds: 30, recovery_seconds: 30 })) {
      if (loadEditor.form[key] == null) loadEditor.form[key] = fallback
    }
    loadFormRef.value?.clearValidate?.()
    await loadDialogRef.value?.show()
  }
  async function commitLoadConfig() {
    const errors = await loadFormRef.value?.validate()
    if (errors) {
      loadDialogRef.value?.setConfirmLoading(false)
      return
    }
    if (isRateProfile.value && Number(loadEditor.form.max_vus) < Number(loadEditor.form.preallocated_vus)) {
      Message.warning('最大 VU 不能小于预分配 VU')
      loadDialogRef.value?.setConfirmLoading(false)
      return
    }
    if (Number(loadEditor.form.user_wait_min_ms || 0) > Number(loadEditor.form.user_wait_max_ms || 0)) {
      Message.warning('最大迭代等待不能小于最小值')
      loadDialogRef.value?.setConfirmLoading(false)
      return
    }
    if (!editedDuration.value || editedDuration.value > 86400) {
      Message.warning('总时长必须在 1 秒到 24 小时之间')
      loadDialogRef.value?.setConfirmLoading(false)
      return
    }
    if (!isRateProfile.value && Number(loadEditor.form.target_users) < Number(form.default_executor_count || 1)) {
      Message.warning('目标并发不能少于执行器数量')
      loadDialogRef.value?.setConfirmLoading(false)
      return
    }
    if (loadEditor.form.profile === 'fixed_iterations' && Number(loadEditor.form.total_iterations) < Number(loadEditor.form.target_users || 0)) {
      Message.warning('Case 执行次数不能少于目标并发用户数')
      loadDialogRef.value?.setConfirmLoading(false)
      return
    }
    if (loadEditor.form.profile === 'staircase' && (Number(loadEditor.form.step_users) < Number(form.default_executor_count || 1) || Math.ceil(Number(loadEditor.form.target_users) / Number(loadEditor.form.step_users)) > 99)) {
      Message.warning('每阶增加并发不能少于执行器数，且最多 99 阶')
      loadDialogRef.value?.setConfirmLoading(false)
      return
    }
    if (['linear_ramp', 'spike'].includes(loadEditor.form.profile) && Number(loadEditor.form.start_users) >= Number(loadEditor.form.target_users)) {
      Message.warning('起始并发必须小于目标并发')
      loadDialogRef.value?.setConfirmLoading(false)
      return
    }
    const value = { ...loadEditor.form, duration_seconds: editedDuration.value }
    form.load_type = isRateProfile.value ? (value.profile === 'constant_arrival_rate' ? 'arrival_rate' : 'iteration_rate') : 'concurrency'
    if (!isRateProfile.value) {
      value.target_rate = null
      value.rate_time_unit = null
      value.preallocated_vus = null
      value.max_vus = null
    } else value.target_users = null
    Object.keys(loadConfig).forEach((key) => delete loadConfig[key])
    Object.assign(loadConfig, value)
    await loadDialogRef.value?.close()
  }
  function selectLoadProfile(value: unknown) {
    const profile = String(value)
    const name = loadEditor.form.name
    const rate = ['constant_arrival_rate', 'constant_iteration_rate'].includes(profile)
    Object.assign(loadEditor.form, {
      name, profile, duration_seconds: 60, target_users: rate ? null : 10,
      target_rate: rate ? 10 : null, rate_time_unit: 'second',
      preallocated_vus: rate ? 10 : null, max_vus: rate ? 100 : null,
      total_iterations: 10000, start_users: 1, step_users: 10,
      step_interval_seconds: 30, ramp_seconds: 30, hold_seconds: 30,
      baseline_seconds: 30, recovery_seconds: 30,
    })
    loadFormRef.value?.clearValidate?.()
  }
  function applyPerformanceGoalTemplate(value: unknown) {
    if (value !== 'recommended' && value !== 'custom') return
    performanceGoalTemplate.value = value
    if (value === 'recommended') Object.assign(performanceGoal, createDefaultPerformanceGoal())
  }
  function markPerformanceGoalCustom() {
    performanceGoalTemplate.value = isRecommendedPerformanceGoal(performanceGoal)
      ? 'recommended'
      : 'custom'
  }
  function validateLocal() {
    if (!form.name?.trim()) return Message.warning('请输入场景名称'), false
    if (!sourceCase.value || !form.source_case_release_id)
      return Message.warning('请选择已发布的API自动化 Case'), false
    if (!sourceCase.value.compatible)
      return Message.warning('当前 Case 不兼容性能模式，请更换 Case'), false
    if (!hasLoadConfig.value) return Message.warning('请配置负载'), false
    if (Number(loadConfig.user_wait_min_ms || 0) > Number(loadConfig.user_wait_max_ms || 0))
      return Message.warning('最大迭代等待不能小于最小值'), false
    if (Number(performanceGoal.p95_ms) <= 0) return Message.warning('P95 响应时间必须大于 0'), false
    return true
  }
  async function save() {
    if (!validateLocal()) return false
    saving.value = true
    try {
      const response: any = await savePerfScenarioConfiguration(id, {
        version: form.version,
        source_case_release_id: form.source_case_release_id,
        base: {
          name: form.name,
          default_executor_count: form.default_executor_count,
          node_failure_policy: form.node_failure_policy,
          min_ready_nodes: form.min_ready_nodes,
        },
        load_config: { ...loadConfig },
        performance_goal: performanceGoalToPayload(performanceGoal, performanceGoalTemplate.value),
      })
      form.version = response.data.version
      Message.success('配置已保存')
      return true
    } finally {
      saving.value = false
    }
  }
  async function validateConfig() {
    validating.value = true
    try {
      if (!(await save())) return
      const response: any = await validatePerfScenario(id)
      Message.success(
        `校验通过：完整 Case 共 ${response.data.step_count} 个步骤，预计 ${response.data.duration_seconds} 秒`
      )
    } finally {
      validating.value = false
    }
  }
  async function openScriptPreview() {
    scriptPreviewVisible.value = true
    scriptPreviewLoading.value = true
    scriptPreviewTab.value = 'script'
    scriptPreview.value = null
    try {
      const response: any = await getPerfScenarioScriptPreview(id)
      scriptPreview.value = response.data
    } catch {
      scriptPreviewVisible.value = false
    } finally {
      scriptPreviewLoading.value = false
    }
  }
  async function copyScriptPreview() {
    if (!scriptPreview.value) return
    const value = scriptPreviewTab.value === 'snapshot' ? scriptPreview.value.snapshot : scriptPreview.value.script
    await navigator.clipboard.writeText(value)
    Message.success('已复制预览内容')
  }
  async function openExecuteDialog() {
    if (!validateLocal()) return
    Object.assign(executeForm, {
      test_env: null,
      selected_executor_fingerprints: [],
      remark: '',
      production_load_confirmed: false,
      capture_request: false,
      capture_response: false,
    })
    executorCandidates.value = []
    Object.keys(executorPreflight).forEach((key) => delete executorPreflight[key])
    executeFormRef.value?.clearValidate?.()
    await executeDialogRef.value?.show()
  }
  async function loadExecutorCandidates() {
    executeForm.selected_executor_fingerprints = []
    executorCandidates.value = []
    Object.keys(executorPreflight).forEach((key) => delete executorPreflight[key])
    if (executeForm.test_env === null || executeForm.test_env === undefined) return
    executorLoading.value = true
    try {
      const response: any = await preflightPerfScenario(id, {
        test_env: Number(executeForm.test_env),
        selected_executor_fingerprints: [],
      })
      Object.assign(executorPreflight, response.data || {})
      executorCandidates.value = response.data?.candidates || []
    } finally {
      executorLoading.value = false
    }
  }
  async function preflightSelectedExecutors() {
    if (!executeForm.selected_executor_fingerprints.length) {
      executorPreflight.can_run = false
      return
    }
    const response: any = await preflightPerfScenario(id, {
      test_env: Number(executeForm.test_env),
      selected_executor_fingerprints: executeForm.selected_executor_fingerprints,
    })
    Object.assign(executorPreflight, response.data || {})
  }
  async function execute() {
    const errors = await executeFormRef.value?.validate()
    if (errors || !executorSelectionReady.value) {
      if (!errors)
        Message.warning(`必须选择 ${form.default_executor_count || 1} 个容量充足的执行器`)
      executeDialogRef.value?.setConfirmLoading(false)
      return
    }
    executing.value = true
    try {
      if (!(await save())) return
      const response: any = await executePerfScenario(id, {
        test_env: Number(executeForm.test_env),
        remark: executeForm.remark,
        selected_executor_fingerprints: executeForm.selected_executor_fingerprints,
        production_load_confirmed: executeForm.production_load_confirmed,
        capture_request: executeForm.capture_request,
        capture_response: executeForm.capture_response,
      })
      await executeDialogRef.value?.close()
      router.push({ path: '/perf/run/details', query: { id: response.data.run_id } })
    } finally {
      executing.value = false
      executeDialogRef.value?.setConfirmLoading(false)
    }
  }
  onMounted(async () => {
    await load()
    if (String(route.query.execute || '') === '1') await openExecuteDialog()
  })
</script>

<style scoped lang="less">
  .mango-perf-profile-hint {
    margin-bottom: var(--m-page-gap);
  }
  .mango-perf-script-preview {
    display: block;
    min-height: 220px;
    padding: 0;
  }
  .mango-perf-script-preview__notice {
    margin-bottom: 12px;
  }
  .mango-perf-script-preview__meta {
    overflow: hidden;
    color: var(--m-muted);
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 12px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .mango-perf-script-preview__code {
    height: calc(100vh - 260px);
    min-height: 240px;
    overflow: hidden;
  }
  .mango-perf-script-preview__code :deep(.cm-editor) {
    height: 100%;
  }
  .mango-perf-detail-spin {
    display: block;
  }
  .mango-perf-config-workbench,
  .mango-perf-flow-column,
  .mango-perf-settings-column {
    display: grid;
    gap: var(--m-page-gap);
    min-width: 0;
  }
  .mango-perf-config-workbench {
    width: 100%;
    padding-bottom: var(--m-page-gap);
  }
  .mango-perf-editor-grid {
    display: grid;
    grid-template-columns: minmax(0, 2fr) minmax(460px, 1fr);
    align-items: start;
    gap: var(--m-page-gap);
    min-width: 0;
  }
  .mango-perf-flow-column > .mango-section-card,
  .mango-perf-settings-column > .mango-section-card {
    margin-top: 0;
    padding: var(--m-card-padding);
  }
  .mango-perf-section-heading {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .mango-perf-section-heading > div {
    display: flex;
    align-items: baseline;
    gap: 8px;
    min-width: 0;
  }
  .mango-perf-section-heading > div > span {
    color: var(--m-text);
    font-size: 15px;
    font-weight: 600;
  }
  .mango-perf-section-heading small,
  .mango-perf-goal-description {
    color: var(--m-muted);
    font-size: 12px;
    font-weight: 400;
  }
  .mango-perf-case-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 8px 14px;
    align-items: center;
    margin: 10px 0;
    color: var(--m-muted);
    font-size: 12px;
  }
  .mango-perf-step-list {
    display: grid;
    gap: 6px;
    margin-top: 10px;
  }
  .mango-perf-step-item {
    display: grid;
    grid-template-columns: 32px minmax(0, 1fr) auto;
    align-items: center;
    gap: 10px;
    padding: 11px 12px;
    border-color: transparent;
  }
  .mango-perf-step-index {
    display: flex;
    width: 28px;
    height: 28px;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    background: var(--m-primary-soft);
    color: var(--m-primary);
    font-size: 12px;
    font-weight: 700;
  }
  .mango-perf-step-content {
    min-width: 0;
  }
  .mango-perf-meta-row {
    display: flex;
    flex-wrap: wrap;
    gap: 4px 12px;
    margin-top: 4px;
    color: var(--m-muted);
    font-size: 12px;
  }
  .mango-perf-empty {
    color: var(--m-muted);
    font-size: 12px;
  }
  .mango-perf-empty {
    display: grid;
    min-height: 76px;
    place-content: center;
    gap: 5px;
    border: 1px dashed var(--m-border);
    border-radius: var(--m-radius-lg);
    text-align: center;
  }
  .mango-perf-empty strong {
    color: var(--m-text-2);
  }
  .mango-perf-load-summary {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    padding: 0;
    overflow: hidden;
  }
  .mango-perf-load-name,
  .mango-perf-load-metric {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    align-content: center;
    gap: 4px 6px;
    min-width: 0;
    min-height: 68px;
    padding: 10px 12px;
  }
  .mango-perf-load-metric {
    border-left: 1px solid var(--m-border);
  }
  .mango-perf-load-name {
    align-items: flex-start;
  }
  .mango-perf-load-name span,
  .mango-perf-load-metric span {
    flex-basis: 100%;
  }
  .mango-perf-load-metric:nth-child(3) {
    border-top: 1px solid var(--m-border);
    border-left: 0;
  }
  .mango-perf-load-metric:nth-child(4) {
    border-top: 1px solid var(--m-border);
  }
  .mango-perf-load-name span,
  .mango-perf-load-metric span,
  .mango-perf-load-metric small {
    color: var(--m-muted);
    font-size: 12px;
  }
  .mango-perf-load-name strong,
  .mango-perf-load-metric strong {
    overflow: hidden;
    max-width: 100%;
    color: var(--m-text);
    font-size: 15px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .mango-perf-load-metric strong {
    color: var(--m-primary);
    font-size: 18px;
  }
  .mango-perf-settings-panel :deep(.arco-form-item) {
    margin-bottom: 10px;
  }
  .mango-perf-settings-panel :deep(.arco-input-number),
  .mango-perf-settings-panel :deep(.arco-select) {
    width: 100%;
  }
  .mango-perf-input-separator {
    display: inline-flex;
    align-items: center;
    padding: 0 6px;
    border-block: 1px solid var(--m-border);
    color: var(--m-muted);
    font-size: 12px;
  }
  .mango-perf-goal-template-select {
    width: 144px;
  }
  .mango-perf-goal-description {
    margin: 0 0 10px;
    line-height: 18px;
  }
  .mango-perf-goal-form {
    overflow: hidden;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
  }
  .mango-perf-goal-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 128px;
    align-items: center;
    gap: 10px;
    padding: 11px 12px;
    background: var(--m-surface);
  }
  .mango-perf-goal-row + .mango-perf-goal-row {
    border-top: 1px solid var(--m-border);
  }
  .mango-perf-goal-row > span {
    display: grid;
    gap: 2px;
  }
  .mango-perf-goal-row small {
    color: var(--m-muted);
    font-size: 11px;
  }
  .mango-perf-goal-row :deep(.arco-input-number) {
    width: 100%;
  }
  .mango-perf-executor-alert {
    margin-bottom: var(--m-page-gap);
  }
  @container (max-width: 1199px) {
    .mango-perf-editor-grid {
      grid-template-columns: minmax(0, 1fr);
    }
    .mango-perf-section-heading small {
      display: none;
    }
  }
</style>
