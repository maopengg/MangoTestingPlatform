<template>
  <TableBody plain class="mango-detail-workbench-page" :sticky-horizontal-scroll="false">
    <template #header>
      <TableHeader title="研发协同 / 测试用例">
        <template #header-extra>
          <a-space>
            <input
              ref="importInput"
              class="mango-case-library__file"
              type="file"
              accept=".xlsx,.xls"
              @change="importCases"
            />
            <a-button  size="small" :loading="importing" @click="importInput?.click()">
              导入
            </a-button>
            <a-button  size="small" :loading="exporting" @click="exportCases">导出</a-button>
            <a-button size="small" @click="refreshCases">刷新</a-button>
            <a-button  size="small" @click="startBatchCreate">批量新增</a-button>
            <a-button size="small" type="primary" @click="openEditor()">单个新增</a-button>
          </a-space>
        </template>
      </TableHeader>
    </template>
    <template #default>
      <ProjectProductNavigationWorkbench
        contained-body
        :sticky-horizontal-scroll="false"
        :show-search="false"
        show-modules
        :model-value="navigationProjectProduct"
        :module-value="navigationModule"
        @filter-change="onNavigationFilterChange"
      >
        <FunctionalCaseGrid
          class="mango-case-library__grid"
          ref="caseGrid"
          :rows="rows"
          :columns="columns"
          :loading="loading"
          :editable="editMode"
          :show-hint="false"
          @cell-change="saveInline"
          @selection-change="selectedRows = $event"
          @view-change="saveGridView"
          @filter-change="handleGridFilterChange"
          @load-more="loadMoreCases"
          @insert-rows="insertDraftRows"
          @remove-rows="removeGridRows"
          @sort-change="handleGridSortChange"
        >
          <template #summary>
            <span>已选择 {{ selectedRows.length }} 条</span>
            <a-tag v-if="editMode" size="small" :color="inlineSaveMeta.color">
              {{ inlineSaveMeta.text }}
            </a-tag>
            <span v-if="batchMode">批量新增草稿 {{ draftRows.length }} 行</span>
            <span v-if="filterActive && loadingAllForFilter">
              正在加载完整数据并应用筛选（{{ persistedRowCount }} / {{ pageState.total }}）…
            </span>
            <span v-else-if="filterActive">已对全部 {{ pageState.total }} 条用例应用表格筛选</span>
            <span v-else-if="loadingMore">正在加载更多…</span>
            <span v-else-if="hasMore"
              >已加载 {{ persistedRowCount }} / {{ pageState.total }} 条，向下滚动继续加载</span
            >
            <span v-else>已加载全部 {{ pageState.total }} 条</span>
          </template>
          <template #toolbar>
            <template v-if="batchMode">
              <a-button size="small" @click="insertDraftRows({ index: 0, count: 10 })">
                新增 10 行
              </a-button>
              <a-button size="small" :disabled="!selectedDraftRows.length" @click="copyDraftRows">
                复制所选行
              </a-button>
              <a-button size="small" :disabled="!selectedDraftRows.length" @click="removeSelectedDraftRows">
                删除草稿行
              </a-button>
              <a-button  size="small" :loading="batchSaving" @click="saveDraftRows">
                保存全部
              </a-button>
              <a-button size="small" :disabled="batchSaving" @click="exitBatchCreate">
                退出批量新增
              </a-button>
            </template>
            <a-tooltip :content="editMode ? '可直接编辑表格单元格' : '开启后可直接编辑表格单元格'">
              <span class="mango-case-library__edit-toggle">
                编辑模式
                <a-switch  size="small" :model-value="editMode" @change="toggleEditMode" />
              </span>
            </a-tooltip>
            <a-button
              size="small"
              :disabled="selectedPersistedRows.length !== 1"
              @click="openEditor(selectedPersistedRows[0])"
            >
              编辑详情
            </a-button>
            <a-button
              size="small"
              :disabled="selectedPersistedRows.length !== 1"
              @click="openHistory(selectedPersistedRows[0])"
            >
              历史版本
            </a-button>
            <a-button
              size="small"
              :disabled="selectedPersistedRows.length !== 1"
              @click="openAutomationBinding(selectedPersistedRows[0])"
            >
              自动化绑定
            </a-button>
            <a-button  size="small" @click="openCreatePlan">新建测试计划</a-button>
            <a-button  size="small" :disabled="!selectedPersistedRows.length" @click="openAddPlan">
              加入测试计划
            </a-button>
            <a-button  size="small" :disabled="!selectedPersistedRows.length" @click="createDefectFromCases">创建缺陷</a-button>
          </template>
        </FunctionalCaseGrid>
      </ProjectProductNavigationWorkbench>
    </template>
  </TableBody>

  <a-drawer
    v-model:visible="editorVisible"
    :title="form.id ? '编辑用例' : '新增用例'"
    width="760px"
    :ok-loading="saving"
    @ok="saveCase"
  >
    <a-form :model="form" layout="vertical">
      <a-grid :cols="2" :col-gap="16">
        <a-grid-item
          ><a-form-item label="用例编号" required><a-input v-model="form.case_no" /></a-form-item
        ></a-grid-item>
        <a-grid-item
          ><a-form-item label="优先级" required
            ><a-select
              v-model="form.priority"
              :options="enumStore.case_level"
              :field-names="fieldNames" /></a-form-item
        ></a-grid-item>
        <a-grid-item :span="2"
          ><a-form-item label="用例标题" required><a-input v-model="form.title" /></a-form-item
        ></a-grid-item>
        <a-grid-item
          ><a-form-item label="项目产品" required
            ><ProjectProductSelect
              v-model="form.project_product"
              @change="form.module = undefined" /></a-form-item
        ></a-grid-item>
        <a-grid-item
          ><a-form-item label="模块" required
            ><ProductModuleSelect
              v-model="form.module"
              :project-product-id="normalizeProduct(form.project_product)" /></a-form-item
        ></a-grid-item>
        <a-grid-item
          ><a-form-item label="分类一"
            ><a-auto-complete
              v-model="form.category_level_1"
              :data="categoryOptions.category_level_1"
              allow-clear
              @change="loadCategoryOptions" /></a-form-item
        ></a-grid-item>
        <a-grid-item
          ><a-form-item label="分类二"
            ><a-auto-complete
              v-model="form.category_level_2"
              :data="categoryOptions.category_level_2"
              allow-clear
              @change="loadCategoryOptions" /></a-form-item
        ></a-grid-item>
        <a-grid-item
          ><a-form-item label="分类三"
            ><a-auto-complete
              v-model="form.category_level_3"
              :data="categoryOptions.category_level_3"
              allow-clear /></a-form-item
        ></a-grid-item>
        <a-grid-item
          ><a-form-item label="负责人" required
            ><a-select
              v-model="form.owner"
              :options="userOptions"
              :field-names="fieldNames"
              allow-search /></a-form-item
        ></a-grid-item>
        <a-grid-item
          ><a-form-item label="测试类型" required
            ><a-select
              v-model="form.test_types"
              :options="enumStore.manual_test_type"
              :field-names="fieldNames"
              multiple /></a-form-item
        ></a-grid-item>
        <a-grid-item
          ><a-form-item label="资产状态"
            ><a-select
              v-model="form.status"
              :options="enumStore.functional_case_status"
              :field-names="fieldNames" /></a-form-item
        ></a-grid-item>
        <a-grid-item
          ><a-form-item label="自动化状态"
            ><a-select
              v-model="form.automation_status"
              :options="AUTOMATION_STATUS_OPTIONS" /></a-form-item
        ></a-grid-item>
        <a-grid-item
          ><a-form-item label="测试层级" required
            ><a-select
              v-model="form.scenario_layer"
              :options="enumStore.api_case_scenario_layer"
              :field-names="fieldNames" /></a-form-item
        ></a-grid-item>
        <a-grid-item
          ><a-form-item label="验证类型" required
            ><a-select
              v-model="form.scenario_type"
              :options="enumStore.api_case_scenario_type"
              :field-names="fieldNames" /></a-form-item
        ></a-grid-item>
        <a-grid-item :span="2"
          ><a-form-item label="执行场景" required
            ><a-select
              v-model="form.scenario_tags"
              :options="enumStore.api_case_scenario_tag"
              :field-names="fieldNames"
              multiple /></a-form-item
        ></a-grid-item>
        <a-grid-item :span="2"
          ><a-form-item label="关联用户故事"
            ><a-select
              v-model="form.story_refs"
              multiple
              allow-create
              allow-search
              placeholder="输入故事或验收点编号后回车" /></a-form-item
        ></a-grid-item>
        <a-grid-item :span="2"
          ><a-form-item label="前置条件"
            ><a-textarea
              v-model="form.precondition"
              :auto-size="{ minRows: 2, maxRows: 4 }" /></a-form-item
        ></a-grid-item>
        <a-grid-item :span="2"
          ><a-form-item label="测试场景" required
            ><a-textarea
              v-model="form.test_point"
              :auto-size="{ minRows: 2, maxRows: 5 }" /></a-form-item
        ></a-grid-item>
        <a-grid-item :span="2">
          <a-form-item label="测试步骤">
            <div class="mango-case-library__steps">
              <div
                v-for="(step, index) in form.test_steps"
                :key="index"
                class="mango-case-library__step"
              >
                <span>{{ index + 1 }}</span>
                <a-input v-model="step.action" placeholder="操作" />
                <a-input v-model="step.expected" placeholder="步骤预期" />
                <a-button type="text" status="danger" @click="form.test_steps.splice(index, 1)"
                  ><icon-delete
                /></a-button>
              </div>
              <a-button size="small" @click="form.test_steps.push({ action: '', expected: '' })"
                >增加步骤</a-button
              >
            </div>
          </a-form-item>
        </a-grid-item>
        <a-grid-item :span="2"
          ><a-form-item label="预期结果"
            ><a-textarea
              v-model="form.expected_result"
              :auto-size="{ minRows: 2, maxRows: 5 }" /></a-form-item
        ></a-grid-item>
        <a-grid-item :span="2"
          ><a-form-item label="验收标准来源"
            ><a-textarea
              v-model="form.acceptance_source"
              :auto-size="{ minRows: 2, maxRows: 4 }" /></a-form-item
        ></a-grid-item>
        <a-grid-item :span="2"
          ><a-form-item label="测试数据"
            ><a-textarea
              v-model="form.test_data"
              :auto-size="{ minRows: 2, maxRows: 4 }" /></a-form-item
        ></a-grid-item>
        <a-grid-item :span="2"
          ><a-form-item label="备注"><a-textarea v-model="form.remark" /></a-form-item
        ></a-grid-item>
      </a-grid>
    </a-form>
  </a-drawer>

  <a-drawer
    v-model:visible="historyVisible"
    :title="`${historyCase?.case_no || ''} ${historyCase?.title || ''} · 历史版本`"
    width="920px"
    :footer="false"
  >
    <a-spin :loading="historyLoading" class="mango-case-library__history-spin">
      <a-alert class="mango-case-library__history-notice" type="info">
        每条用例最多保留最近 20 个历史版本，超过后会自动清理最早版本。
      </a-alert>
      <div v-if="historyVersions.length" class="mango-case-library__history">
        <div class="mango-case-library__history-list">
          <button
            v-for="item in historyVersions"
            :key="item.id"
            type="button"
            class="mango-case-library__history-item"
            :class="{ 'is-active': item.id === activeHistory?.id }"
            @click="activeHistory = item"
          >
            <strong>V{{ item.version_no }}</strong>
            <span>{{ item.source_name }}</span>
            <small>{{ formatHistoryTime(item.create_time) }}</small>
            <small>{{ item.changed_by?.name || item.changed_by?.username || '系统' }}</small>
          </button>
        </div>
        <div v-if="activeHistory" class="mango-case-library__history-detail">
          <div class="mango-section-title">
            <span>V{{ activeHistory.version_no }} 快照</span>
            <a-tag>{{ activeHistory.source_name }}</a-tag>
          </div>
          <a-descriptions :column="2" bordered size="small">
            <a-descriptions-item label="用例编号">{{
              historySnapshot.case_no
            }}</a-descriptions-item>
            <a-descriptions-item label="优先级">{{
              enumLabel(enumStore.case_level, historySnapshot.priority)
            }}</a-descriptions-item>
            <a-descriptions-item label="测试类型">{{
              enumLabels(enumStore.manual_test_type, historySnapshot.test_types)
            }}</a-descriptions-item>
            <a-descriptions-item label="用例标题" :span="2">{{
              historySnapshot.title
            }}</a-descriptions-item>
            <a-descriptions-item label="项目产品">{{
              historySnapshot.project_product_name || `ID ${historySnapshot.project_product_id}`
            }}</a-descriptions-item>
            <a-descriptions-item label="模块">{{
              historySnapshot.module_path || `ID ${historySnapshot.module_id}`
            }}</a-descriptions-item>
            <a-descriptions-item label="分类一">{{
              historySnapshot.category_level_1 || '-'
            }}</a-descriptions-item>
            <a-descriptions-item label="分类二">{{
              historySnapshot.category_level_2 || '-'
            }}</a-descriptions-item>
            <a-descriptions-item label="分类三">{{
              historySnapshot.category_level_3 || '-'
            }}</a-descriptions-item>
            <a-descriptions-item label="负责人">{{
              historySnapshot.owner_name || `ID ${historySnapshot.owner_id}`
            }}</a-descriptions-item>
            <a-descriptions-item label="测试层级">{{
              enumLabel(enumStore.api_case_scenario_layer, historySnapshot.scenario_layer)
            }}</a-descriptions-item>
            <a-descriptions-item label="验证类型">{{
              enumLabel(enumStore.api_case_scenario_type, historySnapshot.scenario_type)
            }}</a-descriptions-item>
            <a-descriptions-item label="执行场景">{{
              enumLabels(enumStore.api_case_scenario_tag, historySnapshot.scenario_tags)
            }}</a-descriptions-item>
            <a-descriptions-item label="自动化状态">{{
              automationStatusLabel(historySnapshot.automation_status)
            }}</a-descriptions-item>
            <a-descriptions-item label="资产状态">{{
              enumLabel(enumStore.functional_case_status, historySnapshot.status)
            }}</a-descriptions-item>
            <a-descriptions-item label="自动化绑定" :span="2">{{
              formatAutomationBindings(historySnapshot.automation_bindings)
            }}</a-descriptions-item>
            <a-descriptions-item label="前置条件" :span="2">{{
              historySnapshot.precondition || '-'
            }}</a-descriptions-item>
            <a-descriptions-item label="测试场景" :span="2">{{
              historySnapshot.test_point || '-'
            }}</a-descriptions-item>
            <a-descriptions-item label="预期结果" :span="2">{{
              historySnapshot.expected_result || '-'
            }}</a-descriptions-item>
            <a-descriptions-item label="备注" :span="2">{{
              historySnapshot.remark || '-'
            }}</a-descriptions-item>
          </a-descriptions>
          <div class="mango-case-library__history-steps">
            <strong>测试步骤</strong>
            <div
              v-for="(step, index) in historySnapshot.test_steps || []"
              :key="index"
              class="mango-soft-panel"
            >
              <span>{{ index + 1 }}. {{ step.action || '-' }}</span>
              <span>预期：{{ step.expected || '-' }}</span>
            </div>
            <div v-if="!historySnapshot.test_steps?.length" class="mango-empty-state"
              >暂无测试步骤</div
            >
          </div>
        </div>
      </div>
      <div v-else-if="!historyLoading" class="mango-empty-state">
        暂无历史快照；该用例下次修改时会保留当前版本
      </div>
    </a-spin>
  </a-drawer>

  <a-modal
    v-model:visible="planVisible"
    title="加入测试计划"
    :ok-loading="planSaving"
    @ok="addToPlan"
  >
    <a-form :model="planForm" layout="vertical">
      <a-form-item label="测试计划" required>
        <a-select v-model="planForm.plan_id" :options="planOptions" allow-search />
      </a-form-item>
    </a-form>
  </a-modal>

  <a-modal
    v-model:visible="planCreateVisible"
    :title="
      planCreateCaseIds.length
        ? `新建测试计划并加入 ${planCreateCaseIds.length} 条用例`
        : '新建测试计划'
    "
    width="720px"
    :ok-loading="planCreateSaving"
    :on-before-ok="createPlan"
  >
    <a-form :model="planCreateForm" layout="vertical">
      <a-grid :cols="2" :col-gap="16">
        <a-grid-item :span="2">
          <a-form-item label="计划名称" required>
            <a-input v-model="planCreateForm.name" placeholder="请输入计划名称" />
          </a-form-item>
        </a-grid-item>
        <a-grid-item>
          <a-form-item label="项目产品" required>
            <ProjectProductSelect
              v-model="planCreateForm.project_product"
              :disabled="Boolean(planCreateCaseIds.length)"
              :allow-clear="!planCreateCaseIds.length"
              @change="onPlanCreateProductChange"
            />
          </a-form-item>
        </a-grid-item>
        <a-grid-item>
          <a-form-item label="计划类型" required>
            <a-select
              v-model="planCreateForm.scope_type"
              :options="enumStore.functional_test_plan_scope_type"
              :field-names="fieldNames"
              @change="onPlanCreateScopeChange"
            />
          </a-form-item>
        </a-grid-item>
        <a-grid-item v-if="planCreateForm.scope_type === 0">
          <a-form-item label="关联需求版本" required>
            <a-select
              v-model="planCreateForm.requirement_version"
              :options="planRequirementOptions"
              :loading="planRequirementLoading"
              allow-search
              placeholder="请选择具体需求版本"
            />
          </a-form-item>
        </a-grid-item>
        <a-grid-item v-else-if="planCreateForm.scope_type === 1">
          <a-form-item label="关联 Sprint" required>
            <a-select v-model="planCreateForm.iteration" :options="planIterationOptions" :loading="planIterationLoading" allow-search placeholder="请选择 Sprint" />
          </a-form-item>
        </a-grid-item>
        <a-grid-item v-else>
          <a-form-item label="范围标识">
            <a-input v-model="planCreateForm.scope_ref" placeholder="例如 Sprint 24 / v2.8.0" />
          </a-form-item>
        </a-grid-item>
        <a-grid-item>
          <a-form-item label="负责人" required>
            <a-select
              v-model="planCreateForm.owner"
              :options="userOptions"
              :field-names="fieldNames"
              allow-search
            />
          </a-form-item>
        </a-grid-item>
        <a-grid-item>
          <a-form-item label="计划开始">
            <a-date-picker
              v-model="planCreateForm.planned_start_time"
              show-time
              value-format="YYYY-MM-DD HH:mm:ss"
            />
          </a-form-item>
        </a-grid-item>
        <a-grid-item>
          <a-form-item label="计划结束">
            <a-date-picker
              v-model="planCreateForm.planned_end_time"
              show-time
              value-format="YYYY-MM-DD HH:mm:ss"
            />
          </a-form-item>
        </a-grid-item>
        <a-grid-item>
          <a-form-item label="状态">
            <a-select
              v-model="planCreateForm.status"
              :options="enumStore.functional_test_plan_status"
              :field-names="fieldNames"
            />
          </a-form-item>
        </a-grid-item>
        <a-grid-item :span="2">
          <a-form-item label="备注">
            <a-textarea v-model="planCreateForm.remark" />
          </a-form-item>
        </a-grid-item>
      </a-grid>
    </a-form>
  </a-modal>

  <a-modal
    v-model:visible="bindingVisible"
    title="自动化绑定"
    width="540px"
    :ok-loading="bindingSaving"
    :on-before-ok="saveAutomationBinding"
  >
    <a-form :model="bindingForm" layout="vertical">
      <a-form-item label="自动化类型" required>
        <a-select
          v-model="bindingForm.automation_type"
          :options="automationTypeOptions"
          :field-names="fieldNames"
          @change="loadBindingId"
        />
      </a-form-item>
      <a-form-item label="自动化 Case ID" required>
        <a-input-number
          v-model="bindingForm.automation_case_id"
          :min="1"
          :precision="0"
          placeholder="输入 API 或 UI 自动化 Case ID"
        />
      </a-form-item>
    </a-form>
  </a-modal>
</template>

<script lang="ts" setup>
  import { computed, onMounted, reactive, ref } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import { useRouter } from 'vue-router'
  import * as XLSX from 'xlsx'
  import FunctionalCaseGrid from '@/components/table/FunctionalCaseGrid.vue'
  import type { FunctionalGridColumn } from '@/components/table/functional-case-grid'
  import TableBody from '@/components/table/TableBody.vue'
  import TableHeader from '@/components/table/TableHeader.vue'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import { useEnum } from '@/store/modules/get-enum'
  import useUserStore from '@/store/modules/user'
  import { getUserName } from '@/api/user/user'
  import { formatModulePath, formatProjectProductPath } from '@/utils/business-format'
  import {
    addFunctionalPlanCases,
    getFunctionalCaseCategoryOptions,
    getFunctionalGridView,
    getFunctionalPlans,
    getFunctionalRequirements,
    getFunctionalIterations,
    getManualCase,
    getManualCaseExport,
    getManualCaseVersions,
    deleteManualCase,
    postManualAutomationBind,
    postManualCase,
    postManualCaseBatch,
    postFunctionalPlan,
    putManualCase,
    putManualCaseBatch,
    saveFunctionalGridView,
  } from '@/api/functional-test'
  import {
    AUTOMATION_STATUS_OPTIONS,
    CASE_LIBRARY_GRID_KEY,
    CASE_LIBRARY_GRID_LAYOUT_VERSION,
    createCaseLibraryColumns,
    emptyLibraryCase,
    formatAutomationBindings,
  } from './config'
  import { emptyPlan } from '../plan/config'

  const enumStore = useEnum()
  const userStore = useUserStore()
  const router = useRouter()
  const fieldNames = { value: 'key', label: 'title' }
  const rows = ref<any[]>([])
  const caseGrid = ref<any>()
  const columns = ref<FunctionalGridColumn[]>([])
  const editMode = ref(false)
  const batchMode = ref(false)
  const batchSaving = ref(false)
  const selectedRows = ref<any[]>([])
  const loading = ref(false)
  const loadingMore = ref(false)
  const importing = ref(false)
  const exporting = ref(false)
  const importInput = ref<HTMLInputElement>()
  const saving = ref(false)
  const pendingInlineCellCount = ref(0)
  const inflightInlineCellCount = ref(0)
  const inlineSaveState = ref<'saved' | 'pending' | 'saving' | 'error' | 'conflict'>('saved')
  const pendingInlineUpdates = new Map<
    number,
    {
      row: any
      changes: Record<string, any>
      originals: Record<string, any>
    }
  >()
  const editorVisible = ref(false)
  const historyVisible = ref(false)
  const historyLoading = ref(false)
  const historyCase = ref<any>()
  const historyVersions = ref<any[]>([])
  const activeHistory = ref<any>()
  const bindingVisible = ref(false)
  const bindingSaving = ref(false)
  const bindingCase = ref<any>()
  const bindingForm = reactive<any>({ automation_type: 0, automation_case_id: undefined })
  const form = reactive<any>(emptyLibraryCase())
  const userOptions = ref<any[]>([])
  const categoryOptions = reactive<any>({
    category_level_1: [],
    category_level_2: [],
    category_level_3: [],
  })
  const pageState = reactive({ page: 1, pageSize: 50, total: 0 })
  const INITIAL_LOAD_BATCHES = 4
  const navigationProjectProduct = ref<number>()
  const navigationModule = ref<number>()
  const filterActive = ref(false)
  const sortState = reactive<{ field?: string; direction?: 'asc' | 'desc' }>({})
  const loadingAllForFilter = ref(false)
  const planVisible = ref(false)
  const planSaving = ref(false)
  const planForm = reactive<{ plan_id?: number }>({ plan_id: undefined })
  const planOptions = ref<any[]>([])
  const planCreateVisible = ref(false)
  const planCreateSaving = ref(false)
  const planCreateCaseIds = ref<number[]>([])
  const planCreateForm = reactive<any>(emptyPlan())
  const planRequirementOptions = ref<any[]>([])
  const planRequirementLoading = ref(false)
  const planIterationOptions = ref<any[]>([])
  const planIterationLoading = ref(false)
  let viewTimer: number | undefined
  let inlineSaveTimer: number | undefined
  let inlineBatchSaving = false
  let loadRequestId = 0
  let draftSequence = 0

  const normalizeProduct = (value: any) => (Array.isArray(value) ? value[value.length - 1] : value)
  const draftRows = computed(() => rows.value.filter((row) => row.__draft))
  const persistedRowCount = computed(() => rows.value.length - draftRows.value.length)
  const selectedDraftRows = computed(() => selectedRows.value.filter((row) => row.__draft))
  const selectedPersistedRows = computed(() => selectedRows.value.filter((row) => !row.__draft))
  const hasMore = computed(() => persistedRowCount.value < pageState.total)
  const inlineSavingCount = computed(
    () => pendingInlineCellCount.value + inflightInlineCellCount.value
  )
  const inlineSaveMeta = computed(() => {
    if (inlineSaveState.value === 'pending') {
      return { text: `待保存 ${pendingInlineCellCount.value} 项`, color: 'orange' }
    }
    if (inlineSaveState.value === 'saving') {
      return { text: `正在保存 ${inflightInlineCellCount.value} 项…`, color: 'arcoblue' }
    }
    if (inlineSaveState.value === 'conflict') return { text: '保存冲突', color: 'red' }
    if (inlineSaveState.value === 'error') return { text: '保存失败', color: 'red' }
    return { text: '已保存', color: 'green' }
  })
  const historySnapshot = computed(() => activeHistory.value?.snapshot || {})
  const automationTypeOptions = computed(() =>
    (enumStore.manual_test_automation_type || []).filter(
      (item: any) => item.key === 0 || item.key === 1
    )
  )
  const enumLabel = (options: any[] = [], value: any) =>
    options.find((item) => item.key === value)?.title || value || '-'
  const enumLabels = (options: any[] = [], values: any[] = []) =>
    Array.isArray(values) && values.length
      ? values.map((value) => enumLabel(options, value)).join('、')
      : '-'
  const automationStatusLabels = Object.fromEntries(
    AUTOMATION_STATUS_OPTIONS.map((item) => [item.value, item.label])
  ) as Record<string, string>
  const automationStatusLabel = (value: string) => automationStatusLabels[value] || value || '-'
  const normalizeRow = (record: any) => ({
    ...record,
    project_product_id: record.project_product?.id || record.project_product_id,
    project_product_path: formatProjectProductPath(record.project_product),
    module_id: record.module?.id || record.module_id,
    module_path: formatModulePath(record.module),
    owner_id: record.owner?.id || record.owner_id,
    owner_name: record.owner?.name || record.owner?.username || '-',
    automation_bindings: formatAutomationBindings(record.bindings),
  })

  const createDraftRow = (source: any = {}) => {
    draftSequence += 1
    const draftId = `draft-${Date.now()}-${draftSequence}`
    const projectId = source.project_product_id || navigationProjectProduct.value
    const navigationSample = rows.value.find(
      (row) =>
        !row.__draft &&
        (!projectId || Number(row.project_product_id) === Number(projectId)) &&
        (!navigationModule.value || Number(row.module_id) === Number(navigationModule.value))
    )
    return {
      __touched: false,
      case_no: '',
      title: '',
      category_level_1: '',
      category_level_2: '',
      category_level_3: '',
      priority: 1,
      test_types: [0],
      story_refs: [],
      precondition: '',
      test_point: '',
      test_steps: [],
      expected_result: '',
      acceptance_source: '',
      test_data: '',
      scenario_layer: 0,
      scenario_type: 0,
      scenario_tags: ['routine_regression'],
      automation_status: 'not_automated',
      automation_bindings: '-',
      remark: '',
      status: 1,
      owner_id: userStore.userId || undefined,
      owner_name: userStore.nickName || userStore.userName || '-',
      project_product_id: projectId || undefined,
      project_product_path: source.project_product_path || navigationSample?.project_product_path || '',
      module_id:
        source.module_id ||
        (navigationSample && Number(navigationSample.module_id) === Number(navigationModule.value)
          ? navigationModule.value
          : undefined),
      module_path:
        source.module_path ||
        (navigationSample && Number(navigationSample.module_id) === Number(navigationModule.value)
          ? navigationSample.module_path
          : ''),
      version_no: '草稿',
      update_time: '-',
      ...source,
      id: draftId,
      draft_id: draftId,
      __draft: true,
    }
  }

  function insertDraftRows(payload: { index: number; count: number }) {
    const count = Math.min(Math.max(Number(payload.count) || 1, 1), 100)
    batchMode.value = true
    editMode.value = true
    const drafts = Array.from({ length: count }, () => createDraftRow())
    const requestedIndex = Math.max(0, Number(payload.index) || 0)
    const index = Math.min(requestedIndex, rows.value.length)
    rows.value = [...rows.value.slice(0, index), ...drafts, ...rows.value.slice(index)]
  }

  function startBatchCreate() {
    if (!draftRows.value.length) insertDraftRows({ index: 0, count: 20 })
    else {
      batchMode.value = true
      editMode.value = true
    }
  }

  function copyDraftRows() {
    const copies = selectedDraftRows.value.map((row) =>
      createDraftRow({
        ...row,
        case_no: row.case_no ? `${row.case_no}-COPY` : '',
        version_no: '草稿',
        update_time: '-',
      })
    )
    rows.value = [...copies, ...rows.value]
    selectedRows.value = []
  }

  function removeSelectedDraftRows() {
    const ids = new Set(selectedDraftRows.value.map((row) => row.id))
    rows.value = rows.value.filter((row) => !ids.has(row.id))
    selectedRows.value = []
    if (!draftRows.value.length) batchMode.value = false
  }

  function removeGridRows(targetRows: any[]) {
    const drafts = (targetRows.length ? targetRows : selectedRows.value).filter((row) => row.__draft)
    const persisted = (targetRows.length ? targetRows : selectedRows.value).filter(
      (row) => !row.__draft
    )
    const draftIds = new Set(drafts.map((row) => row.id))
    if (draftIds.size) rows.value = rows.value.filter((row) => !draftIds.has(row.id))
    if (!persisted.length) {
      selectedRows.value = []
      return
    }
    Modal.confirm({
      title: '删除用例',
      content: `确定删除选中的 ${persisted.length} 条正式用例吗？该操作不可撤销。`,
      okButtonProps: { status: 'danger' },
      onOk: async () => {
        const ids = persisted.map((row) => row.id)
        await deleteManualCase(ids)
        const idSet = new Set(ids)
        rows.value = rows.value.filter((row) => !idSet.has(row.id))
        pageState.total = Math.max(0, pageState.total - ids.length)
        selectedRows.value = []
        Message.success(`已删除 ${ids.length} 条用例`)
      },
    })
  }

  function exitBatchCreate() {
    if (!draftRows.value.length) {
      batchMode.value = false
      return
    }
    Modal.confirm({
      title: '退出批量新增',
      content: '未保存的草稿行将被移除，是否继续？',
      onOk: () => {
        rows.value = rows.value.filter((row) => !row.__draft)
        selectedRows.value = []
        batchMode.value = false
      },
    })
  }

  const draftHasContent = (row: any) =>
    row.__touched ||
    ['case_no', 'title', 'test_point', 'precondition', 'expected_result', 'remark'].some((field) =>
      String(row[field] || '').trim()
    )

  const draftPayload = (row: any) => ({
    draft_id: row.draft_id,
    case_no: String(row.case_no || '').trim(),
    title: String(row.title || '').trim(),
    category_level_1: String(row.category_level_1 || '').trim(),
    category_level_2: String(row.category_level_2 || '').trim(),
    category_level_3: String(row.category_level_3 || '').trim(),
    priority: row.priority,
    test_types: row.test_types || [],
    story_refs: row.story_refs || [],
    precondition: row.precondition || '',
    test_point: String(row.test_point || '').trim(),
    test_steps: row.test_steps || [],
    expected_result: row.expected_result || '',
    acceptance_source: row.acceptance_source || '',
    test_data: row.test_data || '',
    scenario_layer: row.scenario_layer,
    scenario_type: row.scenario_type,
    scenario_tags: row.scenario_tags || [],
    automation_status: row.automation_status,
    remark: row.remark || '',
    status: row.status,
    owner_id: row.owner_id,
    project_product_id: row.project_product_id,
    module_id: row.module_id,
  })

  async function saveDraftRows() {
    const candidates = draftRows.value.filter(draftHasContent)
    if (!candidates.length) {
      Message.warning('请至少填写一条用例')
      return
    }
    const invalidIndex = candidates.findIndex(
      (row) =>
        !String(row.case_no || '').trim() ||
        !String(row.title || '').trim() ||
        !String(row.test_point || '').trim() ||
        !row.project_product_id ||
        !row.module_id ||
        !row.owner_id
    )
    if (invalidIndex >= 0) {
      Message.warning(`第 ${invalidIndex + 1} 条草稿缺少编号、标题、测试场景、项目、模块或负责人`)
      return
    }
    batchSaving.value = true
    try {
      const response = await postManualCaseBatch({ items: candidates.map(draftPayload) })
      const created = (response.data || []).map(normalizeRow)
      const candidateIds = new Set(candidates.map((row) => row.id))
      const remaining = rows.value.filter((row) => !row.__draft || !candidateIds.has(row.id))
      rows.value = [...created, ...remaining.filter((row) => !row.__draft)]
      pageState.total += created.length
      pageState.page = Math.max(pageState.page, 1)
      selectedRows.value = []
      batchMode.value = false
      Message.success(`已创建 ${created.length} 条用例`)
    } catch (error: any) {
      Message.error(error?.message || '批量创建失败，请检查草稿行')
    } finally {
      batchSaving.value = false
    }
  }

  async function loadCases(showLoading = true, append = false) {
    if (append) {
      if (loading.value || loadingMore.value || !hasMore.value) return
      loadingMore.value = true
    } else {
      loadRequestId += 1
      if (showLoading) loading.value = true
    }
    const requestId = loadRequestId
    try {
      const firstPage = append ? pageState.page + 1 : 1
      const lastPage = append ? firstPage : firstPage + INITIAL_LOAD_BATCHES - 1
      const preservedDrafts = rows.value.filter((row) => row.__draft)
      let nextRows = append ? rows.value.filter((row) => !row.__draft) : []
      for (let targetPage = firstPage; targetPage <= lastPage; targetPage += 1) {
        const query: any = { page: targetPage, pageSize: pageState.pageSize }
        if (navigationProjectProduct.value) query.project_product = navigationProjectProduct.value
        if (navigationModule.value) {
          query.module = navigationModule.value
          query.include_descendants = true
        }
        if (sortState.field) {
          query.sort_field = sortState.field
          query.sort_order = sortState.direction || 'asc'
        }
        const res = await getManualCase(query)
        if (requestId !== loadRequestId) return
        const loadedRows = (res.data || []).map(normalizeRow)
        const existingIds = new Set(nextRows.map((item) => item.id))
        nextRows = [...nextRows, ...loadedRows.filter((item: any) => !existingIds.has(item.id))]
        rows.value = [...preservedDrafts, ...nextRows]
        pageState.page = targetPage
        pageState.total = res.totalSize || 0
        selectedRows.value = []
        if (!append && targetPage === firstPage) {
          loading.value = false
          loadingMore.value = targetPage < lastPage && nextRows.length < pageState.total
        }
        if (!loadedRows.length || nextRows.length >= pageState.total) break
      }
    } finally {
      if (requestId === loadRequestId) {
        loading.value = false
        loadingMore.value = false
      }
    }
  }

  const refreshCases = () => loadCases(true, false)
  const loadMoreCases = () => loadCases(false, true)

  function handleGridSortChange(payload: { field: string; direction: 'asc' | 'desc' }) {
    if (draftRows.value.length) {
      Message.warning('请先保存或退出批量新增，再对全部用例排序')
      return
    }
    sortState.field = payload.field
    sortState.direction = payload.direction
    pageState.page = 1
    loadCases(true, false)
  }

  function onNavigationFilterChange(filter: { projectProduct: any; module: any }) {
    navigationProjectProduct.value = filter.projectProduct || undefined
    navigationModule.value = filter.module || undefined
    pageState.page = 1
    loadCases()
  }

  async function handleGridFilterChange(payload: { active: boolean }) {
    filterActive.value = payload.active
    if (!payload.active || loadingAllForFilter.value || !hasMore.value) return
    loadingAllForFilter.value = true
    try {
      while (hasMore.value) {
        const previousCount = rows.value.length
        await loadCases(false, true)
        if (rows.value.length === previousCount) break
      }
    } finally {
      loadingAllForFilter.value = false
    }
  }

  async function openHistory(row: any) {
    historyCase.value = row
    historyVisible.value = true
    historyLoading.value = true
    historyVersions.value = []
    activeHistory.value = undefined
    try {
      const response = await getManualCaseVersions(row.id)
      historyVersions.value = response.data || []
      activeHistory.value = historyVersions.value[0]
    } finally {
      historyLoading.value = false
    }
  }

  function openAutomationBinding(row: any) {
    bindingCase.value = row
    loadBindingId()
    bindingVisible.value = true
  }

  function loadBindingId() {
    const current = (bindingCase.value?.bindings || []).find(
      (item: any) => item.automation_type === bindingForm.automation_type
    )
    bindingForm.automation_case_id = current?.automation_case_id
  }

  async function saveAutomationBinding() {
    if (!bindingCase.value?.id || !bindingForm.automation_case_id) {
      Message.warning('请选择自动化类型并填写 Case ID')
      return false
    }
    bindingSaving.value = true
    try {
      await postManualAutomationBind({ case_id: bindingCase.value.id, ...bindingForm })
      Message.success('自动化用例绑定成功')
      await loadCases()
      return true
    } finally {
      bindingSaving.value = false
    }
  }

  const formatHistoryTime = (value?: string) =>
    value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '-'

  const exportFields: Array<[string, string]> = [
    ['case_no', '用例编号'],
    ['title', '用例标题'],
    ['project_product_id', '项目产品ID'],
    ['module_id', '模块ID'],
    ['category_level_1', '分类一'],
    ['category_level_2', '分类二'],
    ['category_level_3', '分类三'],
    ['priority', '优先级'],
    ['test_types', '测试类型'],
    ['story_refs', '关联用户故事'],
    ['precondition', '前置条件'],
    ['test_point', '测试场景'],
    ['test_steps', '测试步骤JSON'],
    ['expected_result', '预期结果'],
    ['acceptance_source', '验收标准来源'],
    ['test_data', '测试数据'],
    ['owner_id', '负责人ID'],
    ['automation_status', '自动化状态'],
    ['bindings', '自动化绑定'],
    ['scenario_layer', '测试层级'],
    ['scenario_type', '验证类型'],
    ['scenario_tags', '执行场景'],
    ['status', '资产状态'],
    ['remark', '备注'],
  ]

  async function exportCases() {
    if (selectedDraftRows.value.length) {
      Message.warning('请先保存选中的草稿用例再导出')
      return
    }
    exporting.value = true
    try {
      const response = await getManualCaseExport({
        page: 1,
        pageSize: 10000,
        id__in: selectedRows.value.length
          ? selectedRows.value.map((row) => row.id).join(',')
          : undefined,
        project_product: navigationProjectProduct.value,
        module: navigationModule.value,
        include_descendants: navigationModule.value ? true : undefined,
      })
      const source = response.data || []
      const data = source.map((item: any) =>
        Object.fromEntries(
          exportFields.map(([field, title]) => {
            let value = item[field]
            if (field === 'bindings') value = formatAutomationBindings(item.bindings)
            if (field === 'project_product_id')
              value = item.project_product?.id || item.project_product_id
            if (field === 'module_id') value = item.module?.id || item.module_id
            if (field === 'owner_id') value = item.owner_id || item.owner?.id
            if (Array.isArray(value) || (value && typeof value === 'object'))
              value = JSON.stringify(value)
            return [title, value ?? '']
          })
        )
      )
      const workbook = XLSX.utils.book_new()
      XLSX.utils.book_append_sheet(workbook, XLSX.utils.json_to_sheet(data), '测试用例')
      XLSX.writeFile(workbook, `测试用例_${new Date().toISOString().slice(0, 10)}.xlsx`)
    } finally {
      exporting.value = false
    }
  }

  async function importCases(event: Event) {
    const input = event.target as HTMLInputElement
    const file = input.files?.[0]
    if (!file) return
    importing.value = true
    try {
      const workbook = XLSX.read(await file.arrayBuffer())
      const records = XLSX.utils.sheet_to_json<any>(workbook.Sheets[workbook.SheetNames[0]], {
        defval: '',
      })
      const reverse = Object.fromEntries(exportFields.map(([field, title]) => [title, field]))
      let success = 0
      for (const record of records) {
        const payload: any = {}
        Object.entries(record).forEach(([title, value]) => {
          if (reverse[title]) payload[reverse[title]] = value
        })
        for (const field of ['test_types', 'story_refs', 'test_steps', 'scenario_tags']) {
          if (typeof payload[field] === 'string' && payload[field]) {
            try {
              payload[field] = JSON.parse(payload[field])
            } catch {
              payload[field] = field === 'test_types' ? [Number(payload[field])] : [payload[field]]
            }
          }
        }
        Object.assign(payload, {
          project_product: Number(payload.project_product_id),
          module: Number(payload.module_id),
          owner: Number(payload.owner_id),
          priority: Number(payload.priority || 1),
          status: Number(payload.status || 1),
          scenario_layer: Number(payload.scenario_layer || 0),
          scenario_type: Number(payload.scenario_type || 0),
          scenario_tags: payload.scenario_tags || ['routine_regression'],
          story_refs: payload.story_refs || [],
        })
        delete payload.project_product_id
        delete payload.module_id
        delete payload.owner_id
        await postManualCase(payload)
        success += 1
      }
      Message.success(`成功导入 ${success} 条用例`)
      await loadCases()
    } finally {
      importing.value = false
      input.value = ''
    }
  }

  async function openEditor(row?: any) {
    Object.assign(
      form,
      emptyLibraryCase(),
      row
        ? {
            ...row,
            project_product: row.project_product?.id || row.project_product,
            module: row.module?.id || row.module,
            owner: row.owner_id || row.owner?.id || row.owner,
            test_steps: (row.test_steps || []).map((item: any) => ({ ...item })),
          }
        : {}
    )
    editorVisible.value = true
    await loadCategoryOptions()
  }

  async function loadCategoryOptions() {
    const res = await getFunctionalCaseCategoryOptions({
      project_product: normalizeProduct(form.project_product) || undefined,
      module: form.module || undefined,
      category_level_1: form.category_level_1 || undefined,
      category_level_2: form.category_level_2 || undefined,
    })
    Object.assign(categoryOptions, res.data || {})
  }

  async function saveCase() {
    if (
      !form.case_no ||
      !form.title ||
      !normalizeProduct(form.project_product) ||
      !form.module ||
      !form.owner ||
      !form.test_point
    ) {
      Message.warning('请填写所有必填字段')
      return false
    }
    saving.value = true
    try {
      const payload = {
        ...form,
        project_product: normalizeProduct(form.project_product),
        test_steps: (form.test_steps || []).filter((item: any) => item.action || item.expected),
      }
      if (form.id) await putManualCase(payload)
      else await postManualCase(payload)
      Message.success('保存成功')
      editorVisible.value = false
      await loadCases()
      return true
    } finally {
      saving.value = false
    }
  }

  const refreshPendingInlineCellCount = () => {
    pendingInlineCellCount.value = [...pendingInlineUpdates.values()].reduce(
      (total, item) => total + Object.keys(item.changes).length,
      0
    )
  }

  const scheduleInlineFlush = () => {
    window.clearTimeout(inlineSaveTimer)
    inlineSaveTimer = window.setTimeout(flushInlineUpdates, 450)
  }

  async function flushInlineUpdates() {
    window.clearTimeout(inlineSaveTimer)
    if (inlineBatchSaving || !pendingInlineUpdates.size) return
    const batch = [...pendingInlineUpdates.entries()].map(([id, item]) => ({
      id,
      version_no: item.row.version_no,
      changes: { ...item.changes },
      row: item.row,
      originals: { ...item.originals },
    }))
    pendingInlineUpdates.clear()
    refreshPendingInlineCellCount()
    inlineBatchSaving = true
    inflightInlineCellCount.value = batch.reduce(
      (total, item) => total + Object.keys(item.changes).length,
      0
    )
    inlineSaveState.value = 'saving'
    try {
      const response = await putManualCaseBatch({
        updates: batch.map(({ id, version_no, changes }) => ({ id, version_no, changes })),
      })
      const conflicts = response.data?.conflicts || []
      if (conflicts.length) {
        pendingInlineUpdates.clear()
        refreshPendingInlineCellCount()
        inlineSaveState.value = 'conflict'
        Message.warning(
          `${conflicts.length} 条用例已被其他用户修改，当前编辑未保存，已刷新最新数据`
        )
        await loadCases(false)
        return
      }
      const updatedMap = new Map((response.data?.updated || []).map((item: any) => [item.id, item]))
      batch.forEach((item) => {
        const updated: any = updatedMap.get(item.id)
        if (!updated) throw new Error(`服务器未确认用例 ${item.id} 的保存结果`)
        for (const field of ['project_product_id', 'module_id']) {
          if (
            field in item.changes &&
            String(updated[field] ?? '') !== String(item.changes[field] ?? '')
          ) {
            throw new Error(`服务器未确认“${field === 'module_id' ? '模块' : '项目产品'}”更新`)
          }
        }
        item.row.version_no = updated.version_no
        item.row.update_time = updated.update_time
        item.row.project_product_id = updated.project_product_id
        item.row.project_product_path = updated.project_product_path
        item.row.module_id = updated.module_id
        item.row.module_path = updated.module_path
        caseGrid.value?.refreshRowCells?.(item.id, [
          'project_product_id',
          'project_product_path',
          'module_id',
          'module_path',
          'version_no',
          'update_time',
        ])
      })
      inlineSaveState.value = 'saved'
    } catch (error: any) {
      pendingInlineUpdates.clear()
      refreshPendingInlineCellCount()
      inlineSaveState.value = 'error'
      batch.forEach((item) => {
        Object.entries(item.changes).forEach(([field, value]) => {
          if (item.row[field] === value) item.row[field] = item.originals[field]
        })
      })
      Message.error(error?.message || '批量保存失败，已恢复服务器数据')
      await loadCases(false)
    } finally {
      inlineBatchSaving = false
      inflightInlineCellCount.value = 0
      if (pendingInlineUpdates.size) {
        inlineSaveState.value = 'pending'
        scheduleInlineFlush()
      }
    }
  }

  function saveInline({ row, field, oldValue, changes, oldValues }: any) {
    if (!field || ['owner_name', 'version_no', 'update_time', 'test_steps'].includes(field)) return
    if (row.__draft) {
      row.__touched = true
      inlineSaveState.value = 'saved'
      return
    }
    const pending = pendingInlineUpdates.get(row.id) || {
      row,
      changes: {},
      originals: {},
    }
    const nextChanges = changes || { [field]: row[field] }
    const previousValues = oldValues || { [field]: oldValue }
    Object.entries(nextChanges).forEach(([changedField, value]) => {
      if (!(changedField in pending.originals)) {
        pending.originals[changedField] = previousValues[changedField]
      }
      pending.changes[changedField] = value
    })
    pendingInlineUpdates.set(row.id, pending)
    refreshPendingInlineCellCount()
    inlineSaveState.value = 'pending'
    scheduleInlineFlush()
  }

  async function toggleEditMode(value: boolean | string | number) {
    const enabled = value === true
    if (!enabled && inlineSavingCount.value) await flushInlineUpdates()
    editMode.value = enabled
  }

  async function openAddPlan() {
    const productIds = [
      ...new Set(
        selectedPersistedRows.value.map(
          (item) => item.project_product?.id || item.project_product_id
        )
      ),
    ]
    if (productIds.length !== 1) {
      Message.warning('请选择同一项目产品下的用例')
      return
    }
    const res = await getFunctionalPlans({ project_product: productIds[0], page: 1, pageSize: 500 })
    planOptions.value = (res.data || []).map((item: any) => ({ label: item.name, value: item.id }))
    planForm.plan_id = undefined
    planVisible.value = true
  }

  function createDefectFromCases() {
    const productIds = [
      ...new Set(
        selectedPersistedRows.value.map(
          (item) => item.project_product?.id || item.project_product_id
        )
      ),
    ]
    if (productIds.length !== 1) {
      Message.warning('请选择同一项目产品下的用例')
      return
    }
    router.push({
      path: '/functional-test/defect/index',
      query: {
        project_product: productIds[0],
        case_ids: selectedPersistedRows.value.map((item) => item.id).join(','),
      },
    })
  }

  async function loadPlanRequirements() {
    const productId = normalizeProduct(planCreateForm.project_product)
    planRequirementOptions.value = []
    if (!productId) return
    planRequirementLoading.value = true
    try {
      const response = await getFunctionalRequirements({
        project_product: productId,
        page: 1,
        pageSize: 500,
      })
      planRequirementOptions.value = (response.data || []).map((item: any) => ({
        label: `${item.name} · V${item.version_no || '-'}`,
        value: item.id,
      }))
    } finally {
      planRequirementLoading.value = false
    }
  }
  async function loadPlanIterations() {
    const productId = normalizeProduct(planCreateForm.project_product)
    planIterationOptions.value = []
    if (!productId) return
    planIterationLoading.value = true
    try {
      const response = await getFunctionalIterations({ project_product: productId, page: 1, pageSize: 500 })
      planIterationOptions.value = (response.data || []).map((item: any) => ({ label: `${item.iteration_no} ${item.name}`, value: item.id }))
    } finally { planIterationLoading.value = false }
  }

  async function openCreatePlan() {
    const productIds = [
      ...new Set(
        selectedPersistedRows.value
          .map((item) => item.project_product?.id || item.project_product_id)
          .filter(Boolean)
      ),
    ]
    if (productIds.length > 1) {
      Message.warning('创建计划并加入用例时，请选择同一项目产品下的用例')
      return
    }
    planCreateCaseIds.value = selectedPersistedRows.value.map((item) => item.id)
    Object.assign(planCreateForm, emptyPlan(), {
      project_product: productIds[0],
      owner: selectedPersistedRows.value[0]?.owner?.id || undefined,
    })
    await Promise.all([loadPlanRequirements(), loadPlanIterations()])
    planCreateVisible.value = true
  }

  async function onPlanCreateProductChange() {
    planCreateForm.requirement_version = undefined
    planCreateForm.iteration = undefined
    await Promise.all([loadPlanRequirements(), loadPlanIterations()])
  }

  function onPlanCreateScopeChange() {
    planCreateForm.scope_ref = ''
    if (planCreateForm.scope_type !== 0) planCreateForm.requirement_version = undefined
    if (planCreateForm.scope_type !== 1) planCreateForm.iteration = undefined
  }

  async function createPlan() {
    const productId = normalizeProduct(planCreateForm.project_product)
    if (
      !planCreateForm.name ||
      !productId ||
      !planCreateForm.owner ||
      (planCreateForm.scope_type === 0 && !planCreateForm.requirement_version) ||
      (planCreateForm.scope_type === 1 && !planCreateForm.iteration)
    ) {
      Message.warning('请填写所有必填字段')
      return false
    }
    planCreateSaving.value = true
    try {
      const payload = { ...planCreateForm, project_product: productId }
      if (planCreateForm.scope_type !== 0) payload.requirement_version = null
      if (planCreateForm.scope_type !== 1) payload.iteration = null
      const response = await postFunctionalPlan(payload)
      if (planCreateCaseIds.value.length) {
        await addFunctionalPlanCases({
          plan_id: response.data.id,
          case_ids: planCreateCaseIds.value,
        })
      }
      Message.success(
        planCreateCaseIds.value.length ? '测试计划创建成功，所选用例已加入' : '测试计划创建成功'
      )
      planCreateVisible.value = false
      return true
    } finally {
      planCreateSaving.value = false
    }
  }
  async function addToPlan() {
    if (!planForm.plan_id) return false
    planSaving.value = true
    try {
      await addFunctionalPlanCases({
        plan_id: planForm.plan_id,
        case_ids: selectedPersistedRows.value.map((item) => item.id),
      })
      Message.success('已加入测试计划')
      planVisible.value = false
      return true
    } finally {
      planSaving.value = false
    }
  }

  function saveGridView(value: FunctionalGridColumn[]) {
    columns.value = value
    persistGridView()
  }

  function persistGridView() {
    window.clearTimeout(viewTimer)
    viewTimer = window.setTimeout(() => {
      saveFunctionalGridView({
        grid_key: CASE_LIBRARY_GRID_KEY,
        name: '默认视图',
        config: {
          columns: columns.value.map(({ field, visible, width }) => ({ field, visible, width })),
          layout_version: CASE_LIBRARY_GRID_LAYOUT_VERSION,
        },
        is_default: true,
      })
    }, 500)
  }

  onMounted(async () => {
    await enumStore.getEnum()
    const [users, view] = await Promise.all([
      getUserName(),
      getFunctionalGridView(CASE_LIBRARY_GRID_KEY),
    ])
    userOptions.value = users.data || []
    columns.value = createCaseLibraryColumns(enumStore, userOptions.value)
    const savedConfig = view.data?.find((item: any) => item.is_default)?.config || {}
    const requiresLayoutUpgrade =
      Number(savedConfig.layout_version || 0) < CASE_LIBRARY_GRID_LAYOUT_VERSION
    const saved = Array.isArray(savedConfig.columns)
      ? savedConfig.columns.map((item: FunctionalGridColumn) =>
          item.field === 'owner_name'
            ? { ...item, field: 'owner_id' }
            : item.field === 'project_product_path'
            ? { ...item, field: 'project_product_id' }
            : item.field === 'module_path'
            ? { ...item, field: 'module_id' }
            : item
        )
      : savedConfig.columns
    if (Array.isArray(saved) && saved.length) {
      const orderedSaved = requiresLayoutUpgrade
        ? [
            ...saved.filter(
              (item: FunctionalGridColumn) =>
                !['project_product_id', 'module_id'].includes(item.field)
            ),
            ...['project_product_id', 'module_id']
              .map((field) => saved.find((item: FunctionalGridColumn) => item.field === field))
              .filter((item): item is FunctionalGridColumn => Boolean(item)),
          ]
        : saved
      const defaultMap = new Map(columns.value.map((item) => [item.field, item]))
      const savedMap = new Map(orderedSaved.map((item: FunctionalGridColumn) => [item.field, item]))
      columns.value = [
        ...orderedSaved
          .filter((item: FunctionalGridColumn) => defaultMap.has(item.field))
          .map((item: FunctionalGridColumn) => {
            const current = defaultMap.get(item.field)!
            return {
              ...current,
              visible: item.visible ?? current.visible,
              width: item.width ?? current.width,
            }
          }),
        ...columns.value.filter((column) => !savedMap.has(column.field)),
      ]
    }
    if (requiresLayoutUpgrade) persistGridView()
    await loadCases()
  })
</script>

<style lang="less" scoped>
  .mango-case-library__edit-toggle {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    color: var(--m-text-2);
  }
  .mango-case-library__grid {
    height: 100%;
    min-height: 0;
    flex: 1;
  }
  .mango-case-library__history-spin {
    width: 100%;
    min-height: 320px;
  }
  .mango-case-library__history-notice {
    margin-bottom: 10px;
  }
  .mango-case-library__history {
    display: grid;
    grid-template-columns: 190px minmax(0, 1fr);
    gap: var(--m-page-gap);
    min-height: 520px;
  }
  .mango-case-library__history-list,
  .mango-case-library__history-detail,
  .mango-case-library__history-steps {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .mango-case-library__history-list {
    overflow: auto;
    padding-right: 4px;
    border-right: 1px solid var(--m-border);
  }
  .mango-case-library__history-item {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 4px 8px;
    padding: 8px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-sm);
    color: var(--m-text-2);
    background: var(--m-surface);
    text-align: left;
    cursor: pointer;
    transition: border-color 0.2s ease, background-color 0.2s ease;
  }
  .mango-case-library__history-item:hover,
  .mango-case-library__history-item:focus-visible,
  .mango-case-library__history-item.is-active {
    border-color: var(--m-primary);
    background: var(--m-surface-soft);
    outline: none;
  }
  .mango-case-library__history-item small {
    color: var(--m-text-3);
  }
  .mango-case-library__history-detail {
    min-width: 0;
  }
  .mango-case-library__history-steps {
    margin-top: 4px;
  }
  .mango-case-library__history-steps .mango-soft-panel {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    padding: 8px;
  }
  .mango-case-library__steps {
    display: flex;
    flex-direction: column;
    gap: 8px;
    width: 100%;
  }
  .mango-case-library__file {
    display: none;
  }
  .mango-case-library__step {
    display: grid;
    grid-template-columns: 28px 1fr 1fr 32px;
    align-items: center;
    gap: 8px;
  }
</style>
