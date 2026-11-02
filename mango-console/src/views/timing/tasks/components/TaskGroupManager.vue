<template>
  <div class="mango-task-group-manager">
    <a-table
      :data="rows"
      :loading="loading"
      :pagination="false"
      :bordered="false"
      :scroll="{ x: 2510 }"
      row-key="id"
    >
      <template #columns>
        <a-table-column title="ID" data-index="id" :width="80" align="center" />
        <a-table-column title="任务组名称" data-index="name" :width="180" ellipsis tooltip>
          <template #cell="{ record }">
            <a-link @click="emit('filter-tasks', record)">{{ record.name }}</a-link>
          </template>
        </a-table-column>
        <a-table-column title="子任务" :width="120" align="center">
          <template #cell="{ record }">
            {{ record.enabled_task_count }}/{{ record.module_count }} 启用
          </template>
        </a-table-column>
        <a-table-column title="最近执行质量" :width="290">
          <template #cell="{ record }">
            <TaskRecentResults
              :results="record.recent_results || []"
              @open="(index) => openGroupReport(record.recent_results[index])"
            />
          </template>
        </a-table-column>
        <a-table-column title="模块范围" :width="120" align="center">
          <template #cell="{ record }">{{ record.module_count }} 个模块</template>
        </a-table-column>
        <a-table-column title="定时器" :width="120" ellipsis tooltip>
          <template #cell="{ record }">
            <a-tooltip :content="record.timing_strategies.map((item) => item.name).join('、')">
              <span class="mango-task-group-manager__ellipsis">
                {{ record.timing_strategies.map((item) => item.name).join('、') || '-' }}
              </span>
            </a-tooltip>
          </template>
        </a-table-column>
        <a-table-column title="测试环境" :width="100">
          <template #cell="{ record }">
            <a-space :size="4" wrap>
              <a-tag
                v-for="value in record.test_envs"
                :key="value"
                :color="enumStore.colors[value]"
                size="small"
              >
                {{ optionTitle(enumStore.environment_type, value) }}
              </a-tag>
            </a-space>
          </template>
        </a-table-column>
        <a-table-column title="用例类型" :width="100">
          <template #cell="{ record }">
            <a-tag v-if="!record.case_types?.length" color="gray" size="small">全部类型</a-tag>
            <a-space v-else :size="4" wrap>
              <a-tag
                v-for="value in record.case_types"
                :key="value"
                :color="enumStore.colors[value]"
                size="small"
              >
                {{ optionTitle(enumStore.test_case_type, value) }}
              </a-tag>
            </a-space>
          </template>
        </a-table-column>
        <a-table-column title="执行场景" :width="180">
          <template #cell="{ record }">
            <ExecutionSceneTagGrid
              :values="record.execution_scenes"
              :options="enumStore.api_case_scenario_tag"
              :colors="enumStore.colors"
            />
          </template>
        </a-table-column>
        <a-table-column title="负责人" :width="90" align="center">
          <template #cell="{ record }">
            {{ record.case_people?.name || '-' }}
          </template>
        </a-table-column>
        <a-table-column title="是否开启" :width="90" align="center">
          <template #cell="{ record }">
            <a-switch
              :model-value="record.status === 1"
              :before-change="(value) => changeGroupSwitch(record, 'status', value)"
            />
          </template>
        </a-table-column>
        <a-table-column title="是否通知" :width="90" align="center">
          <template #cell="{ record }">
            <a-switch
              :model-value="record.is_notice === 1"
              :before-change="(value) => changeGroupSwitch(record, 'is_notice', value)"
            />
          </template>
        </a-table-column>
        <a-table-column title="失败通知" :width="90" align="center">
          <template #cell="{ record }">
            <a-switch
              :model-value="record.is_notice === 1 && record.fail_notice === 1"
              :disabled="record.is_notice !== 1"
              :before-change="(value) => changeGroupSwitch(record, 'fail_notice', value)"
            />
          </template>
        </a-table-column>
        <a-table-column title="通知组" :width="180" ellipsis tooltip>
          <template #cell="{ record }">{{ record.notice_group?.name || '-' }}</template>
        </a-table-column>
        <a-table-column title="更新人" data-index="update_user_name" :width="110" align="center" />
        <a-table-column title="更新时间" data-index="update_time" :width="180" align="center" />
        <a-table-column title="同步状态" :width="110" align="center">
          <template #cell="{ record }">
            <a-tag :color="syncColor(record.sync_status)" size="small">
              {{ syncText(record.sync_status) }}
            </a-tag>
          </template>
        </a-table-column>
        <a-table-column title="项目/产品" :width="140" ellipsis tooltip>
          <template #cell="{ record }">
            {{ formatProjectProductPath(record.project_product) }}
          </template>
        </a-table-column>
        <a-table-column title="操作" :width="160" fixed="right" align="center">
          <template #cell="{ record }">
            <MangoTableActions
              :actions="[
    {
        label: '触发',
        loading: triggeringIds.has(record.id),
        onClick: () => triggerGroup(record),
    },
    {
        label: '重发报告',
        loading: noticeLoadingIds.has(record.id) || (noticeSending && noticeGroup?.id === record.id),
        onClick: () => openResendNotice(record),
    },
    { label: '查看', onClick: () => openDetail(record) },
    { label: '导出离线 HTML', onClick: () => { offlineExport.sourceId = record.id; offlineExport.visible = true; } },
    { label: '编辑', onClick: () => openEdit(record) },
    { label: '删除', danger: true, onClick: () => deleteGroup(record) },
]"
            />
          </template>
        </a-table-column>
      </template>
    </a-table>
    <TableFooter :pagination="pagination" :show-refresh="false" />
  </div>

  <a-modal
    v-model:visible="noticeVisible"
    title="重新发送任务组汇总通知"
    :width="560"
    :mask-closable="false"
    :ok-loading="noticeSending"
    :cancel-button-props="{ disabled: noticeSending }"
    :closable="!noticeSending"
    ok-text="发送"
    @before-ok="confirmResendNotice"
  >
    <a-form :model="{}" layout="horizontal">
      <a-form-item label="任务组">{{ noticeGroup?.name }}</a-form-item>
      <a-form-item label="最近执行" required>
        <a-select
          v-model="noticeExecutionId"
          :options="noticeExecutions.map((item) => ({
            value: item.id,
            label: `${optionTitle(enumStore.environment_type, item.test_env)} · ${String(item.planned_at).replace('T', ' ').slice(0, 19)}`,
          }))"
          placeholder="请选择被测环境对应的最近一次执行"
        />
      </a-form-item>
      <a-form-item label="原通知组">
        {{ noticeExecutions.find((item) => item.id === noticeExecutionId)?.notice_group__name || '未配置' }}
      </a-form-item>
    </a-form>
    <a-alert>按所选批次全部子报告的当前结果发送到原通知组，不重新执行任务；全部通过也可发送。</a-alert>
  </a-modal>

  <a-modal
    v-model:visible="editorVisible"
    :title="editingId ? '编辑任务组' : '新增任务组'"
    width="min(760px, calc(100vw - 32px))"
    class="mango-task-group-editor-modal"
    body-class="mango-task-group-editor-body"
    :mask-closable="false"
  >
    <mango-panel-spin :loading="editorLoading" class="mango-task-group-editor__spin">
      <a-form :model="form" layout="horizontal" class="mango-task-group-editor">
        <div class="mango-task-group-editor__configuration">
        <section class="mango-task-group-editor__section">
          <header class="mango-task-group-editor__section-header">
            <div>
              <strong>基础信息</strong>
              <span>设置任务组名称及所属项目产品</span>
            </div>
          </header>
          <div class="mango-task-group-editor__grid">
            <a-form-item label="任务组名称" required>
              <a-input v-model="form.name" :max-length="64" placeholder="例如：WEB前端－测试回归" />
            </a-form-item>
            <a-form-item label="项目/产品" required>
              <ProjectProductSelect
                v-model="form.project_product_id"
                :disabled="editingId !== null"
                placeholder="请选择项目/产品"
                @change="onEditorProductChange"
              />
            </a-form-item>
            <a-form-item label="子任务名称模板" class="mango-task-group-editor__wide">
              <a-input
                v-model="form.task_name_template"
                disabled
                title="子任务名称由系统按任务组名称和模块完整路径自动生成"
              />
            </a-form-item>
          </div>
        </section>

        <section class="mango-task-group-editor__section">
          <header class="mango-task-group-editor__section-header">
            <div>
              <strong>公共执行规则</strong>
              <span>以下配置统一同步到组内全部模块任务</span>
            </div>
          </header>
          <div class="mango-task-group-editor__grid">
            <a-form-item label="定时策略" required>
              <a-select
                v-model="form.timing_strategies"
                multiple
                allow-search
                :max-tag-count="1"
                :field-names="fieldNames"
                :options="timingOptions"
                placeholder="请选择定时策略"
              />
            </a-form-item>
            <a-form-item label="测试环境" required>
              <a-select
                v-model="form.test_envs"
                multiple
                :max-tag-count="1"
                :field-names="fieldNames"
                :options="enumStore.environment_type"
                placeholder="请选择测试环境"
                @change="onEnvironmentChange"
              />
            </a-form-item>
            <a-form-item label="用例类型">
              <a-select
                v-model="form.case_types"
                multiple
                :max-tag-count="1"
                :field-names="fieldNames"
                :options="caseTypeOptions"
                placeholder="留空表示全部类型"
              />
            </a-form-item>
            <a-form-item label="执行场景" required>
              <a-select
                v-model="form.execution_scenes"
                multiple
                :max-tag-count="1"
                :field-names="fieldNames"
                :options="mutuallyExclusiveSceneOptions"
                placeholder="请选择执行场景"
              />
            </a-form-item>
            <a-form-item label="负责人" required>
              <a-select
                v-model="form.case_people"
                allow-search
                :field-names="fieldNames"
                :options="userOptions"
                placeholder="请选择负责人"
              />
            </a-form-item>
            <a-form-item label="是否开启">
              <a-switch v-model="form.status" :checked-value="1" :unchecked-value="0" />
            </a-form-item>
            <a-form-item label="发送通知">
              <a-switch v-model="form.is_notice" :checked-value="1" :unchecked-value="0" />
            </a-form-item>
            <a-form-item label="失败通知">
              <a-switch v-model="form.fail_notice" :checked-value="1" :unchecked-value="0" />
            </a-form-item>
            <a-form-item label="通知组">
              <a-select
                v-model="form.notice_group"
                allow-clear
                :options="noticeOptions"
                placeholder="可先选择，开启通知后生效"
              />
            </a-form-item>
            <a-form-item v-if="!editingId" label="报告保留策略">
              <a-select v-model="form.new_task_report_retention_policy" :field-names="fieldNames"
                :options="enumStore.report_retention_policy" />
            </a-form-item>
          </div>
        </section>

        </div>
        <section class="mango-task-group-editor__section mango-task-group-editor__modules">
          <header class="mango-task-group-editor__section-header">
            <div>
              <strong>拆分模块</strong>
              <span>每个选中模块生成一条“模块全量”定时任务</span>
            </div>
            <a-tag size="small">已选择 {{ form.module_ids.length }} 个</a-tag>
          </header>
          <div v-if="!form.project_product_id" class="mango-task-group-editor__module-empty">
            请先选择项目/产品，再选择需要拆分的模块
          </div>
          <div v-else class="mango-task-group-editor__tree">
            <a-tree
              v-model:expanded-keys="expandedModuleKeys"
              :checked-keys="form.module_ids"
              :data="selectableModuleTree"
              :loading="!editorLoading && moduleLoading"
              checkable
              check-strictly
              block-node
              @check="onModuleCheck"
            />
          </div>
          <div v-if="form.project_product_id" class="mango-task-group-editor__module-help">
            选中上级模块后将覆盖其整个子树，下级模块无需重复选择。
          </div>
        </section>
      </a-form>
    </mango-panel-spin>
    <template #footer>
      <a-space :size="12" class="mango-modal-dialog-footer-actions">
        <a-button @click="editorVisible = false">取消</a-button>
        <a-button  type="primary" :loading="previewLoading" @click="openPreview">
          预览并保存
        </a-button>
      </a-space>
    </template>
  </a-modal>

  <a-modal
    v-model:visible="previewVisible"
    title="任务组拆分预览"
    width="min(960px, calc(100vw - 32px))"
    :mask-closable="false"
    :ok-loading="saveLoading"
    ok-text="确认保存"
    cancel-text="返回修改"
    :on-before-ok="saveGroup"
  >
    <a-space class="mango-task-group-preview__summary">
      <a-tag color="green">新增 {{ preview.create_count || 0 }}</a-tag>
      <a-tag color="blue">更新 {{ preview.update_count || 0 }}</a-tag>
      <a-tag color="orange">移除 {{ preview.remove_count || 0 }}</a-tag>
    </a-space>
    <a-table
      :data="preview.rows || []"
      :pagination="false"
      :scroll="{ x: 760, y: 420 }"
      class="mango-native-scroll-table"
      row-key="module_id"
    >
      <template #columns>
        <a-table-column title="变更" :width="90" align="center">
          <template #cell="{ record }">
            <a-tag :color="previewActionColor(record.action)" size="small">
              {{ previewActionText(record.action) }}
            </a-tag>
          </template>
        </a-table-column>
        <a-table-column title="模块" data-index="module_full_path" :width="300" ellipsis tooltip />
        <a-table-column title="定时任务名称" data-index="task_name" :width="360" ellipsis tooltip />
      </template>
    </a-table>
  </a-modal>

  <a-drawer
    v-model:visible="detailVisible"
    title="任务组详情"
    width="min(1100px, calc(100vw - 24px))"
    :footer="false"
  >
    <a-spin :loading="detailLoading" class="mango-task-group-detail__spin">
      <div v-if="detail.id" class="mango-task-group-detail">
        <div class="mango-soft-panel mango-task-group-detail__summary">
          <strong>{{ detail.name }}</strong>
          <span>{{ detail.enabled_task_count }}/{{ detail.module_count }} 个子任务启用</span>
          <a-tag :color="syncColor(detail.sync_status)" size="small">
            {{ syncText(detail.sync_status) }}
          </a-tag>
        </div>
        <a-table
          :data="detail.members || []"
          :pagination="false"
          :scroll="{ x: 900, y: 'calc(100vh - 220px)' }"
          class="mango-native-scroll-table"
          row-key="id"
        >
          <template #columns>
            <a-table-column title="模块" :width="320" ellipsis tooltip>
              <template #cell="{ record }">{{ record.module.full_path }}</template>
            </a-table-column>
            <a-table-column title="任务ID" data-index="task_id" :width="90" align="center" />
            <a-table-column title="任务名称" data-index="task_name" :width="320" ellipsis tooltip />
            <a-table-column title="单独启用" :width="100" align="center">
              <template #cell="{ record }">
                <a-switch
                  :model-value="record.child_enabled"
                  :before-change="(value) => changeMemberStatus(record, value)"
                />
              </template>
            </a-table-column>
            <a-table-column title="同步状态" :width="110" align="center">
              <template #cell="{ record }">
                <a-tag :color="syncColor(record.sync_status)" size="small">
                  {{ syncText(record.sync_status) }}
                </a-tag>
              </template>
            </a-table-column>
          </template>
        </a-table>
      </div>
    </a-spin>
  </a-drawer>
  <OfflineReportExportDialog v-model:visible="offlineExport.visible" source-kind="group" :source-id="offlineExport.sourceId" select-report />
</template>

<script lang="ts" setup>
  import { computed, reactive, ref, watch } from 'vue'
  import { useRouter } from 'vue-router'

  import TaskRecentResults from './TaskRecentResults.vue'
  import OfflineReportExportDialog from '@/components/reports/OfflineReportExportDialog.vue'
  import type { TaskGroupRecentResult } from '@/api/system/tasks'
  import { Message, Modal } from '@arco-design/web-vue'
  import { fieldNames } from '@/setting'
  import { useEnum } from '@/store/modules/get-enum'
  import { usePagination } from '@/hooks/table'
  import { getUserModuleTree } from '@/api/system/module'
  import { getSystemTimingList } from '@/api/system/time'
  import { getSystemNoticeName } from '@/api/system/notice_group'
  import { getUserName } from '@/api/user/user'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import {
    createScheduledTaskGroup,
    deleteScheduledTaskGroup,
    getScheduledTaskGroupDetail,
    getScheduledTaskGroups,
    previewScheduledTaskGroup,
    updateScheduledTaskGroup,
    updateScheduledTaskGroupMemberStatus,
    triggerScheduledTaskGroup,
    getLatestTaskGroupExecutions,
    resendTaskGroupNotice,
  } from '@/api/system/tasks'
  import ExecutionSceneTagGrid from '@/components/display/ExecutionSceneTagGrid.vue'
  import { formatProjectProductPath, getOptionId } from '@/utils/business-format'

  const DEFAULT_TASK_NAME_TEMPLATE = '【${{任务组名称}}】${{模块名称}}'

  const props = defineProps<{ projectProductId: number | null; filters: Record<string, any> }>()
  const emit = defineEmits<{ (event: 'filter-tasks', record: any): void }>()
  const enumStore = useEnum()
  const router = useRouter()

  function openGroupReport(result: TaskGroupRecentResult) {
    router.push({ path: '/report/index', query: { group_execution_id: result.group_execution_id } })
  }
  const loading = ref(false)
  const offlineExport = reactive({ visible: false, sourceId: 0 })
  const triggeringIds = reactive(new Set<number>())
  const triggerConfirmingIds = new Set<number>()
  const noticeLoadingIds = reactive(new Set<number>())
  const noticeVisible = ref(false)
  const noticeSending = ref(false)
  const noticeGroup = ref<any>(null)
  const noticeExecutions = ref<any[]>([])
  const noticeExecutionId = ref<number | null>(null)
  const rows = ref<any[]>([])
  const editorVisible = ref(false)
  const editorLoading = ref(false)
  const previewVisible = ref(false)
  const previewLoading = ref(false)
  const saveLoading = ref(false)
  const detailVisible = ref(false)
  const detailLoading = ref(false)
  const editingId = ref<number | null>(null)
  const moduleTree = ref<any[]>([])
  const expandedModuleKeys = ref<Array<string | number>>([])
  const moduleLoading = ref(false)
  const timingOptions = ref<any[]>([])
  const userOptions = ref<any[]>([])
  const noticeOptions = ref<any[]>([])
  const detail = reactive<Record<string, any>>({})
  const preview = reactive<Record<string, any>>({ rows: [] })
  const pagination = usePagination(load, loading)

  const form = reactive({
    name: '',
    project_product_id: null as number | null,
    module_ids: [] as number[],
    timing_strategies: [] as number[],
    test_envs: [] as number[],
    case_types: [] as number[],
    execution_scenes: [] as string[],
    new_task_report_retention_policy: 'all',
    case_people: null as number | null,
    status: 0,
    is_notice: 0,
    fail_notice: 0,
    notice_group: null as number | null,
    task_name_template: DEFAULT_TASK_NAME_TEMPLATE,
  })

  const caseTypeOptions = computed(() =>
    (enumStore.test_case_type || []).map((item: any) => ({
      ...item,
      disabled: [3, 4].includes(Number(item.key)),
    }))
  )
  const allSceneOptions = computed(() =>
    (enumStore.automation_execution_scene || []).filter(
      (item: any) =>
        ![
          'unclassified',
          'effectiveness_test',
          'temporary_validation',
          'performance_test',
        ].includes(String(item.key))
    )
  )
  const productionScenes = [
    'stability_monitoring',
    'production_inspection',
    'production_regression',
  ]
  const selectableSceneOptions = computed(() => {
    if (!form.test_envs.length) return allSceneOptions.value
    const hasProduction = form.test_envs.map(Number).includes(2)
    const hasOther = form.test_envs.map(Number).some((value) => value !== 2)
    if (hasProduction && hasOther) return allSceneOptions.value
    return allSceneOptions.value.filter((item: any) =>
      hasProduction
        ? productionScenes.includes(String(item.key))
        : String(item.key) !== 'stability_monitoring'
    )
  })
  function hasStabilitySceneConflict(scenes: string[]) {
    return scenes.includes('stability_monitoring') &&
      scenes.some((scene) => ['production_inspection', 'production_regression'].includes(scene))
  }
  const mutuallyExclusiveSceneOptions = computed(() =>
    selectableSceneOptions.value.map((item: any) => ({
      ...item,
      disabled: !form.execution_scenes.includes(String(item.key)) &&
        hasStabilitySceneConflict([...form.execution_scenes, String(item.key)]),
    }))
  )
  const moduleParentMap = computed(() => {
    const result = new Map<number, number | null>()
    const visit = (items: any[], parentId: number | null = null) => {
      items.forEach((item) => {
        const id = Number(item.key)
        result.set(id, parentId)
        visit(item.children || [], id)
      })
    }
    visit(moduleTree.value)
    return result
  })
  const selectableModuleTree = computed(() => {
    const selected = new Set(form.module_ids.map(Number))
    const decorate = (items: any[], ancestorSelected = false): any[] =>
      items.map((item) => {
        const currentSelected = selected.has(Number(item.key))
        return {
          ...item,
          disableCheckbox: Boolean(item.disableCheckbox || ancestorSelected),
          children: decorate(item.children || [], ancestorSelected || currentSelected),
        }
      })
    return decorate(moduleTree.value)
  })

  watch(
    () => props.projectProductId,
    () => {
      pagination.page = 1
      void load()
    },
    { immediate: true }
  )
  watch(
    () => props.filters,
    () => {
      pagination.page = 1
      void load()
    },
    { deep: true }
  )

  function optionTitle(options: any[], value: any) {
    const option = (options || []).find(
      (item: any) => String(item.key ?? item.value) === String(value)
    )
    return option?.title ?? option?.label ?? value
  }
  function syncText(value: string) {
    return (
      { pending: '待同步', synced: '已同步', failed: '同步失败', archived: '已归档' }[value] ||
      value
    )
  }
  function syncColor(value: string) {
    return { pending: 'orange', synced: 'green', failed: 'red', archived: 'gray' }[value] || 'gray'
  }
  function previewActionText(value: string) {
    return { create: '新增', update: '更新', remove: '移除' }[value] || value
  }
  function previewActionColor(value: string) {
    return { create: 'green', update: 'blue', remove: 'orange' }[value] || 'gray'
  }
  function cleanFilters() {
    const filters: Record<string, any> = {
      project_product_id: props.projectProductId,
      module_ids: props.filters.navigation_module_ids || [],
      name: props.filters.name,
      test_envs: props.filters.test_envs,
      case_types: props.filters.case_types,
      execution_scenes: props.filters.execution_scenes,
      status: props.filters.status,
      is_notice: props.filters.is_notice,
      sync_status: props.filters.sync_status,
      page: pagination.page,
      pageSize: pagination.pageSize,
    }
    return Object.fromEntries(
      Object.entries(filters).filter(([, value]) =>
        Array.isArray(value)
          ? value.length > 0
          : value !== '' && value !== null && value !== undefined
      )
    )
  }
  async function load() {
    loading.value = true
    try {
      await enumStore.getEnum()
      const response = await getScheduledTaskGroups(cleanFilters())
      rows.value = response.data?.items || []
      pagination.setTotalSize(response.data?.count || 0)
    } finally {
      loading.value = false
    }
  }
  function resetForm() {
    Object.assign(form, {
      name: '',
      project_product_id: props.projectProductId,
      module_ids: [],
      timing_strategies: [],
      test_envs: [],
      case_types: [],
      execution_scenes: [],
      new_task_report_retention_policy: 'all',
      case_people: null,
      status: 0,
      is_notice: 0,
      fail_notice: 0,
      notice_group: null,
      task_name_template: DEFAULT_TASK_NAME_TEMPLATE,
    })
    editingId.value = null
  }
  function flattenKeys(items: any[]): Array<string | number> {
    return items.flatMap((item) => [item.key, ...flattenKeys(item.children || [])])
  }
  function normalizeModuleIds(values: Array<string | number>) {
    const selected = new Set(values.map(Number))
    return [...selected].filter((id) => {
      let parentId = moduleParentMap.value.get(id) ?? null
      while (parentId !== null) {
        if (selected.has(parentId)) return false
        parentId = moduleParentMap.value.get(parentId) ?? null
      }
      return true
    })
  }
  function onModuleCheck(checkedKeys: Array<string | number>) {
    form.module_ids = normalizeModuleIds(checkedKeys)
  }
  async function loadCommonEditorOptions() {
    const [timing, users] = await Promise.all([getSystemTimingList(), getUserName()])
    timingOptions.value = timing.data || []
    userOptions.value = users.data || []
  }
  async function loadProductEditorOptions(projectProductId: number | null) {
    moduleTree.value = []
    noticeOptions.value = []
    expandedModuleKeys.value = []
    if (!projectProductId) return
    moduleLoading.value = true
    try {
      const [modules, notices] = await Promise.all([
        getUserModuleTree(projectProductId),
        getSystemNoticeName(projectProductId),
      ])
      moduleTree.value = modules.data || []
      expandedModuleKeys.value = flattenKeys(moduleTree.value)
      form.module_ids = normalizeModuleIds(form.module_ids)
      noticeOptions.value = notices.data || []
    } finally {
      moduleLoading.value = false
    }
  }
  async function onEditorProductChange(value: any) {
    const projectProductId = Number(getOptionId(value))
    form.project_product_id =
      Number.isInteger(projectProductId) && projectProductId > 0 ? projectProductId : null
    form.module_ids = []
    form.notice_group = null
    await loadProductEditorOptions(form.project_product_id)
  }
  async function openCreate() {
    resetForm()
    editorVisible.value = true
    editorLoading.value = true
    try {
      await Promise.all([
        loadCommonEditorOptions(),
        loadProductEditorOptions(form.project_product_id),
      ])
    } finally {
      editorLoading.value = false
    }
  }
  function fillFromDetail(data: any) {
    Object.assign(form, {
      name: data.name,
      project_product_id: data.project_product?.id,
      module_ids: (data.members || []).map((item: any) => Number(item.module.id)),
      timing_strategies: (data.timing_strategies || []).map((item: any) => Number(item.id)),
      test_envs: [...(data.test_envs || [])],
      case_types: [...(data.case_types || [])],
      execution_scenes: [...(data.execution_scenes || [])],
      case_people: getOptionId(data.case_people),
      status: Number(data.status),
      is_notice: Number(data.is_notice),
      fail_notice: Number(data.fail_notice),
      notice_group: getOptionId(data.notice_group),
      task_name_template: DEFAULT_TASK_NAME_TEMPLATE,
    })
  }
  async function openEdit(record: any) {
    editingId.value = Number(record.id)
    editorVisible.value = true
    editorLoading.value = true
    try {
      const [response] = await Promise.all([
        getScheduledTaskGroupDetail(record.id),
        loadCommonEditorOptions(),
      ])
      fillFromDetail(response.data)
      await loadProductEditorOptions(Number(response.data.project_product?.id) || null)
    } finally {
      editorLoading.value = false
    }
  }
  function validateForm() {
    if (!form.name.trim()) return '请输入任务组名称'
    if (!form.project_product_id) return '请选择项目/产品'
    if (!form.timing_strategies.length) return '请选择定时策略'
    if (!form.test_envs.length) return '请选择测试环境'
    if (!form.execution_scenes.length) return '请选择执行场景'
    if (hasStabilitySceneConflict(form.execution_scenes)) return '稳定性监测不能与生产巡检、生产回归同时选择，请分开配置任务组'
    if (!form.case_people) return '请选择负责人'
    if (!form.module_ids.length) return '请至少选择一个拆分模块'
    return ''
  }
  function payload() {
    const { new_task_report_retention_policy, ...values } = JSON.parse(JSON.stringify(form))
    return {
      ...(editingId.value ? { id: editingId.value } : {}),
      ...values,
      ...(!editingId.value ? { new_task_report_retention_policy } : {}),
      project_product_id: Number(form.project_product_id),
      task_name_template: DEFAULT_TASK_NAME_TEMPLATE,
    }
  }
  async function openPreview() {
    const error = validateForm()
    if (error) {
      Message.error(error)
      return
    }
    previewLoading.value = true
    try {
      const response = await previewScheduledTaskGroup(payload())
      Object.assign(preview, response.data || { rows: [] })
      previewVisible.value = true
    } finally {
      previewLoading.value = false
    }
  }
  async function saveGroup() {
    saveLoading.value = true
    try {
      const response = editingId.value
        ? await updateScheduledTaskGroup(payload())
        : await createScheduledTaskGroup(payload())
      Message.success(response.msg)
      previewVisible.value = false
      editorVisible.value = false
      await load()
      return true
    } catch (error) {
      console.log(error)
      return false
    } finally {
      saveLoading.value = false
    }
  }
  async function openDetail(record: any) {
    detailVisible.value = true
    detailLoading.value = true
    try {
      const response = await getScheduledTaskGroupDetail(record.id)
      Object.assign(detail, response.data || {})
    } finally {
      detailLoading.value = false
    }
  }
  async function changeGroupSwitch(
    record: any,
    field: 'status' | 'is_notice' | 'fail_notice',
    value: boolean
  ) {
    try {
      const response = await getScheduledTaskGroupDetail(record.id)
      const data = response.data
      const changes: Record<string, number> = { [field]: value ? 1 : 0 }
      if (field === 'is_notice' && !value) changes.fail_notice = 0
      const updateResponse = await updateScheduledTaskGroup({
        ...data,
        id: record.id,
        project_product_id: data.project_product.id,
        module_ids: data.members.map((item: any) => item.module.id),
        timing_strategies: data.timing_strategies.map((item: any) => item.id),
        case_people: data.case_people.id,
        notice_group: data.notice_group?.id ?? null,
        ...changes,
      })
      Object.assign(record, updateResponse.data?.item || changes)
      Message.success('任务组配置已更新')
      return true
    } catch (error) {
      console.log(error)
      return false
    }
  }
  async function changeMemberStatus(member: any, value: boolean) {
    try {
      const response = await updateScheduledTaskGroupMemberStatus(
        Number(detail.id),
        Number(member.id),
        value
      )
      Object.assign(member, response.data || {})
      detail.enabled_task_count = (detail.members || []).filter(
        (item: any) => item.effective_enabled
      ).length
      Message.success('子任务状态已更新')
      await load()
      return true
    } catch (error) {
      console.log(error)
      return false
    }
  }
  function triggerGroup(record: any) {
    const groupId = record.id
    if (triggeringIds.has(groupId) || triggerConfirmingIds.has(groupId)) return
    triggerConfirmingIds.add(groupId)
    Modal.confirm({
      title: '触发任务组',
      content: `确认立即触发任务组“${record.name}”中的全部定时任务吗？本次将生成执行报告并开始执行。`,
      okText: '确认触发',
      cancelText: '取消',
      onBeforeOk: () => executeGroupTrigger(groupId),
      onOk: () => triggerConfirmingIds.delete(groupId),
      onCancel: () => triggerConfirmingIds.delete(groupId),
    })
  }

  async function executeGroupTrigger(groupId: number) {
    if (triggeringIds.has(groupId)) return false
    triggeringIds.add(groupId)
    try {
      const response = await triggerScheduledTaskGroup(groupId)
      const result = response.data
      if (result.failed_count) {
        Message.warning(`已触发任务组：生成 ${result.generated_count} 个执行报告，${result.failed_count} 个子任务生成失败，请查看定时触发记录`)
      } else {
        Message.success(`已触发任务组：生成 ${result.generated_count} 个执行报告`)
      }
      return true
    } catch (error) {
      console.log(error)
      return false
    } finally {
      triggeringIds.delete(groupId)
    }
  }

  async function openResendNotice(record: any) {
    if (noticeLoadingIds.size || noticeSending.value || noticeVisible.value) return
    noticeLoadingIds.add(record.id)
    try {
      const response = await getLatestTaskGroupExecutions(record.id)
      const executions = response.data || []
      if (!executions.length) {
        Message.warning('该任务组暂无执行批次')
        return
      }
      noticeGroup.value = record
      noticeExecutions.value = executions
      noticeExecutionId.value = executions[0].id
      noticeVisible.value = true
    } catch (error) {
      console.log(error)
    } finally {
      noticeLoadingIds.delete(record.id)
    }
  }

  async function confirmResendNotice() {

    if (noticeSending.value || !noticeGroup.value || !noticeExecutionId.value) return false
    noticeSending.value = true
    try {
      const response = await resendTaskGroupNotice(noticeGroup.value.id, noticeExecutionId.value)
      Message.success(response.msg)
      return true
    } catch (error) {
      console.log(error)
      return false
    } finally {
      noticeSending.value = false
    }
  }

  function deleteGroup(record: any) {
    Modal.confirm({
      title: '删除任务组',
      content: `删除后将同时删除“${record.name}”及其生成的定时任务，历史执行报告和触发记录仍会保留。确认继续吗？`,
      okText: '删除',
      okButtonProps: { status: 'danger' },
      cancelText: '取消',
      onBeforeOk: async () => {
        try {
          const response = await deleteScheduledTaskGroup(record.id)
          Message.success(response.msg)
          await load()
          return true
        } catch (error) {
          console.log(error)
          return false
        }
      },
    })
  }
  function onEnvironmentChange() {
    const allowed = new Set(selectableSceneOptions.value.map((item: any) => String(item.key)))
    form.execution_scenes = form.execution_scenes.filter((value) => allowed.has(String(value)))
  }
  function applyFilters() {
    pagination.page = 1
    void load()
  }
  defineExpose({ applyFilters, load, openCreate })
</script>

<style scoped>
  .mango-task-group-manager {
    display: flex;
    min-height: 0;
    flex: 1;
    flex-direction: column;
  }

  .mango-task-group-manager__ellipsis {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-task-group-editor__spin,
  .mango-task-group-detail__spin {
    display: block;
    width: 100%;
  }

  :global(.arco-modal-body.mango-task-group-editor-body) {
    box-sizing: border-box;
    height: min(760px, calc(100dvh - 144px));
    min-height: 0;
    overflow: hidden;
  }

  .mango-task-group-editor__spin,
  .mango-task-group-editor__spin :deep(> .mango-panel-spin__content) {
    height: 100%;
    min-height: 0;
  }

  .mango-task-group-editor {
    display: grid;
    grid-template-rows: minmax(0, auto) minmax(120px, 1fr);
    height: 100%;
    min-height: 0;
    overflow: hidden;
  }

  .mango-task-group-editor__configuration {
    min-height: 0;
    overflow: auto;
    overscroll-behavior: contain;
  }

  .mango-task-group-editor__section {
    padding: var(--m-space-md) 0 var(--m-space-xs);
    border-bottom: 1px solid var(--m-border);
  }

  .mango-task-group-editor__section:first-child {
    padding-top: 0;
  }

  .mango-task-group-editor__section:last-child {
    border-bottom: 0;
  }

  .mango-task-group-editor__section-header {
    display: flex;
    min-height: 28px;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 10px;
    flex-shrink: 0;
  }

  .mango-task-group-editor__section-header > div,
  .mango-task-group-editor__section-header > strong {
    display: flex;
    align-items: center;
  }

  .mango-task-group-editor__section-header strong {
    color: var(--m-text);
    font-size: 15px;
    font-weight: 600;
  }

  .mango-task-group-editor__section-header span {
    margin-left: 10px;
    color: var(--m-muted);
    font-size: 13px;
    font-weight: 400;
  }

  .mango-task-group-editor__grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    column-gap: var(--m-space-lg);
  }

  .mango-task-group-editor__grid :deep(.arco-form-item) {
    display: flex;
    flex-direction: row;
    flex-wrap: nowrap;
    align-items: center;
    margin-bottom: var(--m-space-sm);
  }

  .mango-task-group-editor__grid :deep(.arco-form-item-label-col) {
    display: flex;
    width: 112px;
    max-width: 112px;
    flex: 0 0 112px;
    align-items: center;
    justify-content: flex-end;
    padding-right: var(--m-space-sm);
  }

  .mango-task-group-editor__grid :deep(.arco-form-item-wrapper-col) {
    min-width: 0;
    width: 0;
    max-width: none;
    flex: 1 1 0;
  }

  .mango-task-group-editor__grid :deep(.arco-form-item-content-flex) {
    width: 100%;
  }

  .mango-task-group-editor__wide {
    grid-column: 1 / -1;
  }

  .mango-task-group-editor__modules {
    display: flex;
    flex-direction: column;
    min-height: 0;
  }

  .mango-task-group-editor__tree {
    flex: 1;
    min-height: 0;
    overflow: auto;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius);
    background: var(--m-surface-soft);
    padding: var(--m-space-sm) var(--m-card-padding);
    overscroll-behavior: contain;
  }

  .mango-task-group-editor__module-empty {
    display: flex;
    flex: 1;
    min-height: 0;
    align-items: center;
    justify-content: center;
    border: 1px dashed var(--m-border);
    border-radius: var(--m-radius);
    color: var(--m-muted);
  }

  .mango-task-group-editor__module-help {
    flex-shrink: 0;
    margin-top: 6px;
    color: var(--m-muted);
    font-size: 12px;
  }

  @media (max-width: 600px) {
    .mango-task-group-editor__grid {
      grid-template-columns: minmax(0, 1fr);
    }
  }

  .mango-task-group-preview__summary {
    margin-bottom: var(--m-page-gap);
  }

  .mango-task-group-detail {
    display: flex;
    height: calc(100vh - 100px);
    min-height: 0;
    flex-direction: column;
    gap: var(--m-page-gap);
  }

  .mango-task-group-detail__summary {
    display: flex;
    align-items: center;
    gap: var(--m-page-gap);
  }
</style>
