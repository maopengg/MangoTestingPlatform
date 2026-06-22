<template>
  <TableBody>
    <template #header>
      <TableHeader
        :title="pageTitle"
        @search="loadActiveView"
        @reset-search="resetActiveSearch"
      >
        <template v-if="activeView === 'suite'" #search-content>
          <a-form :model="{}" layout="inline" @keyup.enter="loadSuites">
            <a-form-item v-for="item of conditionItems" :key="item.key" :label="item.label">
              <template v-if="item.type === 'input'">
                <a-input
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  allow-clear
                  @blur="loadSuites"
                  @clear="loadSuites"
                />
              </template>
              <template v-else-if="item.type === 'cascader' && item.key === 'project_product'">
                <ProjectProductSelect
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  @change="onSearchProjectProductChange"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'module'">
                <ProductModuleSelect
                  v-model="item.value"
                  :project-product-id="getConditionValue('project_product')"
                  :placeholder="item.placeholder"
                  :auto-clear="false"
                  @change="loadSuites"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'sync_status'">
                <a-select
                  v-model="item.value"
                  :field-names="fieldNames"
                  :options="enumStore.manual_test_sync_status"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="loadSuites"
                />
              </template>
            </a-form-item>
          </a-form>
        </template>
      </TableHeader>
    </template>
    <template #default>
      <div v-if="activeView === 'suite'" class="mango-functional-suite-toolbar">
        <a-button size="small" type="primary" @click="openSuite()">新增需求</a-button>
      </div>
      <template v-if="activeView === 'suite'">
        <div
          ref="suiteTableShellRef"
          class="mango-functional-suite-table mango-functional-scroll-table"
          @wheel="onHorizontalTableWheel($event, 'suite')"
        >
          <a-table
            :bordered="false"
            :columns="suiteColumns"
            :data="suites"
            :loading="suiteLoading"
            :pagination="false"
            :row-key="'id'"
            :scroll="{ x: 1580 }"
          >
            <template #columns>
              <a-table-column v-for="item of suiteColumns" :key="item.key" v-bind="item">
                <template v-if="item.key === 'requirement_name'" #cell="{ record }">
                  <a-link @click="goSuite(record)">{{ record.requirement_name || '-' }}</a-link>
                </template>
                <template v-else-if="item.key === 'project_product'" #cell="{ record }">
                  {{ formatProjectProductPath(record.project_product) }}
                </template>
                <template v-else-if="item.key === 'module'" #cell="{ record }">
                  {{ formatModulePath(record.module) }}
                </template>
                <template v-else-if="item.key === 'owner'" #cell="{ record }">
                  {{ record.owner?.name || '-' }}
                </template>
                <template v-else-if="item.key === 'coverage'" #cell="{ record }">
                  <a-progress :percent="Number(record.automation_coverage_percent || 0) / 100" size="small" />
                </template>
                <template v-else-if="item.key === 'sync_status'" #cell="{ record }">
                  <a-tag :color="statusColor(record.sync_status)" size="small">{{ enumTitle(enumStore.manual_test_sync_status, record.sync_status) }}</a-tag>
                </template>
                <template v-else-if="item.key === 'last_sync_time'" #cell="{ record }">
                  {{ formatDateTime(record.last_sync_time) }}
                </template>
                <template v-else-if="item.key === 'actions'" #cell="{ record }">
                  <MangoTableActions
                    :actions="[
                      { label: '用例', onClick: () => goSuite(record) },
                      { label: '编辑', onClick: () => openSuite(record) },
                      { label: '删除', danger: true, onClick: () => deleteSuite(record) },
                    ]"
                  />
                </template>
              </a-table-column>
            </template>
          </a-table>
        </div>
      </template>
      <div v-else class="mango-functional-case-list-workbench">
        <aside class="mango-functional-case-module-panel">
          <div class="mango-functional-case-module-head">
            <div>
              <h3>模块导航</h3>
              <p>点击模块筛选用例</p>
            </div>
            <a-tag size="small">{{ moduleOptions.length }}</a-tag>
          </div>
          <div class="mango-functional-case-module-filter">
            <ProjectProductSelect
              v-model="caseFilter.project_product"
              placeholder="请选择项目产品"
              @change="onCaseProjectProductChange"
            />
          </div>
          <a-input-search
            v-model="caseFilter.moduleKeyword"
            allow-clear
            placeholder="搜索模块"
          />
          <div class="mango-functional-case-module-tree">
            <a-tree
              v-model:expanded-keys="caseModuleExpandedKeys"
              v-model:selected-keys="caseModuleSelectedKeys"
              :data="caseModuleTree"
              block-node
              size="small"
              @select="onCaseModuleSelect"
            />
          </div>
        </aside>
        <section class="mango-functional-case-list-main">
          <div class="mango-functional-case-filter">
            <a-form :model="caseFilter" layout="inline" @keyup.enter="loadCases">
              <a-form-item label="需求名称">
                <a-select
                  v-model="caseFilter.requirement_name"
                  :loading="requirementLoading"
                  :options="requirementOptions"
                  allow-clear
                  allow-search
                  placeholder="请选择需求名称"
                  @change="onCaseRequirementChange"
                />
              </a-form-item>
              <a-form-item label="用例编号">
                <a-input
                  v-model="caseFilter.case_no"
                  allow-clear
                  placeholder="请输入用例编号"
                  @blur="loadCases"
                  @clear="loadCases"
                />
              </a-form-item>
              <a-form-item label="用例标题">
                <a-input
                  v-model="caseFilter.title"
                  allow-clear
                  placeholder="请输入用例标题"
                  @blur="loadCases"
                  @clear="loadCases"
                />
              </a-form-item>
              <a-form-item label="测试类型">
                <a-select
                  v-model="caseFilter.test_type"
                  :field-names="fieldNames"
                  :options="enumStore.manual_test_type"
                  allow-clear
                  allow-search
                  placeholder="请选择测试类型"
                  value-key="key"
                  @change="onCaseTestTypeChange"
                />
              </a-form-item>
              <a-form-item>
                <a-space>
                  <a-button size="small" type="primary" @click="loadCases">查询</a-button>
                  <a-button size="small" @click="resetCaseSearch">重置</a-button>
                  <a-button size="small" :loading="exportLoading" @click="exportCases">导出</a-button>
                </a-space>
              </a-form-item>
            </a-form>
          </div>
          <div
            ref="caseTableShellRef"
            class="mango-functional-case-table-shell mango-functional-scroll-table"
            @wheel="onHorizontalTableWheel($event, 'case')"
          >
            <a-table
              class="mango-functional-case-list-table"
              :bordered="false"
              :columns="caseColumns"
              :data="cases"
              :loading="caseLoading"
              :pagination="false"
              :row-key="'id'"
              :scroll="{ x: 3060 }"
            >
              <template #columns>
                <a-table-column v-for="item of caseColumns" :key="item.key" v-bind="item">
                  <template v-if="item.key === 'title'" #cell="{ record }">
                    <a-link @click="goSuite({ id: record.suite?.id || record.suite })">{{ record.title || '-' }}</a-link>
                  </template>
                  <template v-else-if="item.key === 'suite'" #cell="{ record }">
                    {{ record.suite?.requirement_name || '-' }}
                  </template>
                  <template v-else-if="item.key === 'suite_iteration'" #cell="{ record }">
                    {{ record.suite?.iteration || '-' }}
                  </template>
                  <template v-else-if="item.key === 'project_product'" #cell="{ record }">
                    {{ formatProjectProductPath(record.project_product) }}
                  </template>
                  <template v-else-if="item.key === 'module'" #cell="{ record }">
                    {{ formatModulePath(record.module) }}
                  </template>
                  <template v-else-if="item.key === 'test_types'" #cell="{ record }">
                    <a-space wrap :size="4">
                      <a-tag v-for="type of record.test_types || []" :key="type" :color="enumColor(type)" size="small">
                        {{ enumTitle(enumStore.manual_test_type, type) }}
                      </a-tag>
                    </a-space>
                  </template>
                  <template v-else-if="item.key === 'owner'" #cell="{ record }">
                    {{ record.owner?.name || '-' }}
                  </template>
                  <template v-else-if="item.key === 'priority'" #cell="{ record }">
                    <a-tag :color="enumColor(record.priority)" size="small">{{ enumTitle(enumStore.case_level, record.priority) }}</a-tag>
                  </template>
                  <template v-else-if="item.key === 'scenario_layer'" #cell="{ record }">
                    <a-tag :color="enumColor(record.scenario_layer)" size="small">{{ enumTitle(enumStore.api_case_scenario_layer, record.scenario_layer) }}</a-tag>
                  </template>
                  <template v-else-if="item.key === 'scenario_type'" #cell="{ record }">
                    <a-tag :color="enumColor(record.scenario_type)" size="small">{{ enumTitle(enumStore.manual_test_scenario_type, record.scenario_type) }}</a-tag>
                  </template>
                  <template v-else-if="item.key === 'scenario_tags'" #cell="{ record }">
                    <a-space wrap :size="4">
                      <a-tag v-for="tag of record.scenario_tags || []" :key="tag" :color="enumColor(tag)" size="small">
                        {{ enumTitle(enumStore.api_case_scenario_tag, tag) }}
                      </a-tag>
                    </a-space>
                  </template>
                  <template v-else-if="item.key === 'api_case_id'" #cell="{ record }">
                    {{ bindingCaseId(record, AUTOMATION_TYPE_API) || '-' }}
                  </template>
                  <template v-else-if="item.key === 'ui_case_id'" #cell="{ record }">
                    {{ bindingCaseId(record, AUTOMATION_TYPE_UI) || '-' }}
                  </template>
                  <template v-else-if="item.key === 'change_status'" #cell="{ record }">
                    <a-tag :color="statusColor(record.change_status)" size="small">{{ enumTitle(enumStore.manual_test_change_status, record.change_status) }}</a-tag>
                  </template>
                  <template v-else-if="item.key === 'automation_impact_status'" #cell="{ record }">
                    <a-tag :color="statusColor(record.automation_impact_status)" size="small">{{ enumTitle(enumStore.manual_test_automation_impact_status, record.automation_impact_status) }}</a-tag>
                  </template>
                  <template v-else-if="item.key === 'actions'" #cell="{ record }">
                    <MangoTableActions
                      :actions="[
                        { label: '编辑', onClick: () => openCase(record) },
                        { label: '删除', danger: true, onClick: () => deleteCase(record) },
                      ]"
                    />
                  </template>
                </a-table-column>
              </template>
            </a-table>
          </div>
        </section>
      </div>
    </template>
    <template #footer>
      <TableFooter :pagination="activeView === 'suite' ? pagination : casePagination" />
    </template>
  </TableBody>

  <a-modal v-model:visible="suiteVisible" title="需求" @ok="saveSuite">
    <a-form :model="suiteForm" layout="vertical">
      <a-form-item label="需求名称" required>
        <a-input v-model="suiteForm.requirement_name" />
      </a-form-item>
      <a-form-item label="项目产品" required>
        <ProjectProductSelect v-model="suiteForm.project_product" @change="suiteForm.module = null" />
      </a-form-item>
      <a-form-item label="模块">
        <ProductModuleSelect v-model="suiteForm.module" :project-product-id="suiteForm.project_product" :auto-clear="false" />
      </a-form-item>
      <a-form-item label="所属迭代">
        <a-input v-model="suiteForm.iteration" />
      </a-form-item>
      <a-form-item label="测试负责人" required>
        <a-select
          v-model="suiteForm.owner"
          :options="userOptions"
          :field-names="fieldNames"
          allow-search
          placeholder="请选择测试负责人"
        />
      </a-form-item>
    </a-form>
  </a-modal>

  <a-drawer v-model:visible="caseVisible" title="编辑测试用例" width="720px" @ok="saveCase">
    <a-form :model="caseForm" layout="vertical">
      <a-grid :cols="2" :col-gap="16">
        <a-grid-item>
          <a-form-item label="用例编号" required>
            <a-input v-model="caseForm.case_no" />
          </a-form-item>
        </a-grid-item>
        <a-grid-item>
          <a-form-item label="优先级" required>
            <a-select v-model="caseForm.priority" :options="enumStore.case_level" :field-names="fieldNames" />
          </a-form-item>
        </a-grid-item>
        <a-grid-item :span="2">
          <a-form-item label="用例标题" required>
            <a-input v-model="caseForm.title" />
          </a-form-item>
        </a-grid-item>
        <a-grid-item :span="2">
          <a-form-item label="测试点" required>
            <a-textarea v-model="caseForm.test_point" :auto-size="{ minRows: 3, maxRows: 7 }" />
          </a-form-item>
        </a-grid-item>
        <a-grid-item :span="2">
          <a-form-item label="测试类型" required>
            <a-select v-model="caseForm.test_types" :options="enumStore.manual_test_type" :field-names="fieldNames" multiple />
          </a-form-item>
        </a-grid-item>
        <a-grid-item>
          <a-form-item label="项目产品" required>
            <ProjectProductSelect v-model="caseForm.project_product" @change="caseForm.module = null" />
          </a-form-item>
        </a-grid-item>
        <a-grid-item>
          <a-form-item label="模块" required>
            <ProductModuleSelect v-model="caseForm.module" :project-product-id="caseForm.project_product" />
          </a-form-item>
        </a-grid-item>
        <a-grid-item>
          <a-form-item label="场景层级" required>
            <a-select v-model="caseForm.scenario_layer" :options="enumStore.api_case_scenario_layer" :field-names="fieldNames" />
          </a-form-item>
        </a-grid-item>
        <a-grid-item>
          <a-form-item label="场景类型" required>
            <a-select v-model="caseForm.scenario_type" :options="enumStore.api_case_scenario_type" :field-names="fieldNames" />
          </a-form-item>
        </a-grid-item>
        <a-grid-item :span="2">
          <a-form-item label="场景标签" required>
            <a-select v-model="caseForm.scenario_tags" :options="enumStore.api_case_scenario_tag" :field-names="fieldNames" multiple />
          </a-form-item>
        </a-grid-item>
        <a-grid-item :span="2">
          <a-form-item label="负责人" required>
            <a-select v-model="caseForm.owner" :options="userOptions" :field-names="fieldNames" allow-search placeholder="请选择负责人" />
          </a-form-item>
        </a-grid-item>
      </a-grid>
    </a-form>
  </a-drawer>
</template>

<script setup lang="ts">
  import { Message, Modal } from '@arco-design/web-vue'
  import { computed, onMounted, reactive, ref, watch } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import * as XLSX from 'xlsx'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import { useEnum } from '@/store/modules/get-enum'
  import { usePagination } from '@/hooks/table'
  import { getUserName } from '@/api/user/user'
  import { formatModulePath, formatProjectProductPath } from '@/utils/business-format'
  import {
    getManualCase,
    getManualCaseModules,
    getManualSuite,
    deleteManualCase,
    deleteManualSuite,
    postManualSuite,
    putManualCase,
    putManualSuite,
  } from '@/api/functional-test'

  const router = useRouter()
  const route = useRoute()
  const enumStore = useEnum()
  const fieldNames = { value: 'key', label: 'title' }
  const activeView = ref<'suite' | 'case'>(getViewFromRoute())
  const suites = ref<any[]>([])
  const cases = ref<any[]>([])
  const moduleOptions = ref<any[]>([])
  const requirementOptions = ref<any[]>([])
  const caseProjectProducts = ref<any[]>([])
  const userOptions = ref<any[]>([])
  const pagination = usePagination(loadSuites)
  const casePagination = usePagination(loadCases)
  const suiteLoading = ref(false)
  const caseLoading = ref(false)
  const moduleLoading = ref(false)
  const requirementLoading = ref(false)
  const exportLoading = ref(false)
  const suiteVisible = ref(false)
  const caseVisible = ref(false)
  const suiteForm = reactive<any>({})
  const caseForm = reactive<any>({})
  const suiteTableShellRef = ref<HTMLElement>()
  const caseTableShellRef = ref<HTMLElement>()
  const caseModuleSelectedKeys = ref<Array<string>>(['all'])
  const caseModuleExpandedKeys = ref<Array<string>>(['all'])
  const conditionItems = reactive([
    { key: 'project_product', label: '项目产品', type: 'cascader', value: undefined as number | undefined, placeholder: '请选择项目产品' },
    { key: 'module', label: '模块', type: 'select', value: undefined as number | undefined, placeholder: '请选择模块' },
    { key: 'requirement_name', label: '需求名称', type: 'input', value: '', placeholder: '请输入需求名称' },
    { key: 'iteration', label: '所属迭代', type: 'input', value: '', placeholder: '请输入迭代名称' },
    { key: 'sync_status', label: '同步状态', type: 'select', value: undefined as string | undefined, placeholder: '请选择同步状态' },
  ])
  const caseFilter = reactive({
    project_product: undefined as number | string | Array<number | string> | undefined,
    module: undefined as number | string | undefined,
    moduleKeyword: '',
    requirement_name: '',
    title: '',
    case_no: '',
    test_type: undefined as number | string | undefined,
  })
  const AUTOMATION_TYPE_API = 0
  const AUTOMATION_TYPE_UI = 1
  const pageTitle = computed(() => `功能测试 / ${activeView.value === 'case' ? '测试用例' : '需求列表'}`)

  const suiteColumns = [
    { title: 'ID', key: 'id', dataIndex: 'id', width: 72 },
    { title: '项目/产品', key: 'project_product', dataIndex: 'project_product', width: 150, ellipsis: true, tooltip: true },
    { title: '模块名称', key: 'module', dataIndex: 'module', width: 150, ellipsis: true, tooltip: true },
    { title: '需求名称', key: 'requirement_name', dataIndex: 'requirement_name', width: 220, ellipsis: true, tooltip: true },
    { title: '所属迭代', key: 'iteration', dataIndex: 'iteration', width: 140, ellipsis: true, tooltip: true },
    { title: '测试负责人', key: 'owner', dataIndex: 'owner', width: 120 },
    { title: '用例数', key: 'case_count', dataIndex: 'case_count', width: 90 },
    { title: '自动化数', key: 'automated_case_count', dataIndex: 'automated_case_count', width: 100 },
    { title: '完成百分比', key: 'coverage', dataIndex: 'automation_coverage_percent', width: 160 },
    { title: '同步状态', key: 'sync_status', dataIndex: 'sync_status', width: 110 },
    { title: '最近同步', key: 'last_sync_time', dataIndex: 'last_sync_time', width: 180 },
    { title: '操作', key: 'actions', dataIndex: 'actions', align: 'center', fixed: 'right', width: 160 },
  ]
  const caseColumns = [
    { title: 'ID', key: 'id', dataIndex: 'id', width: 72 },
    { title: '项目/产品', key: 'project_product', dataIndex: 'project_product', width: 150, ellipsis: true, tooltip: true },
    { title: '模块名称', key: 'module', dataIndex: 'module', width: 150, ellipsis: true, tooltip: true },
    { title: '需求名称', key: 'suite', dataIndex: 'suite', width: 220, ellipsis: true, tooltip: true },
    { title: '所属迭代', key: 'suite_iteration', dataIndex: 'suite_iteration', width: 140, ellipsis: true, tooltip: true },
    { title: '用例编号', key: 'case_no', dataIndex: 'case_no', width: 130, ellipsis: true, tooltip: true },
    { title: '标题', key: 'title', dataIndex: 'title', width: 220, ellipsis: true, tooltip: true },
    { title: '前置条件', key: 'precondition', dataIndex: 'precondition', width: 220, ellipsis: true, tooltip: true },
    { title: '测试点', key: 'test_point', dataIndex: 'test_point', width: 260, ellipsis: true, tooltip: true },
    { title: '测试数据', key: 'test_data', dataIndex: 'test_data', width: 220, ellipsis: true, tooltip: true },
    { title: '测试类型', key: 'test_types', dataIndex: 'test_types', width: 150 },
    { title: '优先级', key: 'priority', dataIndex: 'priority', width: 90 },
    { title: '场景层级', key: 'scenario_layer', dataIndex: 'scenario_layer', width: 120 },
    { title: '场景类型', key: 'scenario_type', dataIndex: 'scenario_type', width: 110 },
    { title: '场景标签', key: 'scenario_tags', dataIndex: 'scenario_tags', width: 220 },
    { title: 'API 用例 ID', key: 'api_case_id', dataIndex: 'api_case_id', width: 120 },
    { title: 'UI 用例 ID', key: 'ui_case_id', dataIndex: 'ui_case_id', width: 110 },
    { title: '变更', key: 'change_status', dataIndex: 'change_status', width: 90 },
    { title: '自动化影响', key: 'automation_impact_status', dataIndex: 'automation_impact_status', width: 120 },
    { title: '负责人', key: 'owner', dataIndex: 'owner', width: 110 },
    { title: '备注', key: 'remark', dataIndex: 'remark', width: 180, ellipsis: true, tooltip: true },
    { title: '操作', key: 'actions', dataIndex: 'actions', align: 'center', fixed: 'right', width: 120 },
  ]

  const filteredModuleOptions = computed(() => {
    const keyword = caseFilter.moduleKeyword.trim().toLowerCase()
    if (!keyword) return moduleOptions.value
    return moduleOptions.value.filter((item) =>
      [item.title, item.superior_module_1, item.superior_module_2]
        .some((text) => String(text || '').toLowerCase().includes(keyword))
    )
  })

  const caseModuleTree = computed(() => {
    const groups = new Map<string, Map<string, any[]>>()
    filteredModuleOptions.value.forEach((item) => {
      const level1 = normalizeName(item.superior_module_1)
      const level2 = normalizeName(item.superior_module_2)
      if (!groups.has(level1)) groups.set(level1, new Map())
      const second = groups.get(level1)!
      if (!second.has(level2)) second.set(level2, [])
      second.get(level2)!.push(item)
    })
    const children = Array.from(groups.entries()).map(([level1, second]) => {
      const moduleCount = Array.from(second.values()).reduce(
        (count, modules) => count + modules.reduce((total, module) => total + Number(module.case_count || 0), 0),
        0
      )
      const secondChildren = Array.from(second.entries()).map(([level2, modules]) => ({
        key: moduleTreeKey('level2', level2, level1),
        title: `${displayGroupName(level2, 'level2')} (${modules.reduce((count, module) => count + Number(module.case_count || 0), 0)})`,
        children: modules.map((module) => ({
          key: moduleTreeKey('module', String(module.key), `${level1}/${level2}`),
          title: `${module.title} (${module.case_count || 0})`,
        })),
      }))
      return {
        key: moduleTreeKey('level1', level1),
        title: `${displayGroupName(level1, 'level1')} (${moduleCount})`,
        children: secondChildren,
      }
    })
    const total = filteredModuleOptions.value.reduce((count, module) => count + Number(module.case_count || 0), 0)
    return [{ key: 'all', title: `全部模块 (${total})`, children }]
  })

  function enumTitle(options: any[] = [], value: any) {
    return options.find((item) => item.key === value)?.title || value || '-'
  }
  function enumColor(value: any) {
    return enumStore.colors?.[Number(value)]
  }
  function statusColor(value: any) {
    return enumStore.status_colors?.[Number(value)]
  }
  function enumTitles(options: any[] = [], values: any[] = []) {
    if (!Array.isArray(values) || values.length === 0) return '-'
    return values.map((value) => enumTitle(options, value)).join('、')
  }
  function bindingCaseId(record: any, type: number) {
    const binding = (record.bindings || []).find((item: any) => item.automation_type === type)
    return binding?.api_case_id || binding?.ui_case_id || binding?.automation_case_id || ''
  }
  function formatDateTime(value?: string) {
    if (!value) return '-'
    return value.replace('T', ' ').split('.')[0]
  }
  function formatExportFileName() {
    const stamp = new Date()
      .toISOString()
      .replace('T', '_')
      .replaceAll(':', '-')
      .split('.')[0]
    return `功能测试用例_${stamp}.xlsx`
  }
  function getHorizontalScrollTarget(shell?: HTMLElement) {
    if (!shell) return null
    const selectors = ['.arco-table-content', '.arco-scrollbar-container', '.arco-table-body']
    for (const selector of selectors) {
      const target = shell.querySelector<HTMLElement>(selector)
      if (target && target.scrollWidth > target.clientWidth) return target
    }
    return shell.scrollWidth > shell.clientWidth ? shell : null
  }
  function onHorizontalTableWheel(event: WheelEvent, type: 'suite' | 'case') {
    const shell = type === 'suite' ? suiteTableShellRef.value : caseTableShellRef.value
    const target = getHorizontalScrollTarget(shell)
    if (!target) return
    const delta = Math.abs(event.deltaX) > 0 ? event.deltaX : event.shiftKey ? event.deltaY : 0
    if (!delta) return
    const next = Math.max(0, Math.min(target.scrollLeft + delta, target.scrollWidth - target.clientWidth))
    if (next === target.scrollLeft) return
    event.preventDefault()
    target.scrollLeft = next
  }
  function getConditionValue(key: string) {
    return conditionItems.find((item) => item.key === key)?.value
  }
  function normalizeName(value: any) {
    return String(value || '').trim()
  }
  function displayGroupName(value: string, level: 'level1' | 'level2' = 'level1') {
    if (value) return value
    return level === 'level2' ? '无二级模块' : '未分组'
  }
  function moduleTreeKey(type: string, value: string, parent = '') {
    return `${type}:${encodeURIComponent(parent || '__empty__')}/${encodeURIComponent(value || '__empty__')}`
  }
  function decodeModuleTreeKey(value: string) {
    const [parent = '__empty__', current = '__empty__'] = value.split('/')
    return {
      parent: decodeURIComponent(parent) === '__empty__' ? '' : decodeURIComponent(parent),
      current: decodeURIComponent(current) === '__empty__' ? '' : decodeURIComponent(current),
    }
  }
  function getLeafValue(value: any) {
    return Array.isArray(value) ? value[value.length - 1] : value
  }
  function normalizeProjectProductValue(value: any) {
    const leaf = getLeafValue(value)
    return leaf === undefined || leaf === null || leaf === '' ? undefined : Number(leaf)
  }
  function buildQuery() {
    const query: Record<string, unknown> = { page: pagination.page, pageSize: pagination.pageSize }
    conditionItems.forEach((item) => {
      if (item.value !== undefined && item.value !== null && item.value !== '') {
        query[item.key] = item.value
      }
    })
    return query
  }
  function buildCaseQuery() {
    const query: Record<string, unknown> = { page: casePagination.page, pageSize: casePagination.pageSize }
    const projectProduct = normalizeProjectProductValue(caseFilter.project_product)
    if (projectProduct) query.project_product = projectProduct
    if (caseFilter.module) query.module = caseFilter.module
    if (caseFilter.title) query.title = caseFilter.title
    if (caseFilter.case_no) query.case_no = caseFilter.case_no
    if (caseFilter.test_type !== undefined && caseFilter.test_type !== null && caseFilter.test_type !== '') {
      query.test_type = caseFilter.test_type
    }
    if (caseFilter.requirement_name) query.suite__requirement_name = caseFilter.requirement_name
    return query
  }
  function buildRequirementQuery() {
    const query: Record<string, unknown> = { page: 1, pageSize: 1000 }
    const projectProduct = normalizeProjectProductValue(caseFilter.project_product)
    if (projectProduct) query.project_product = projectProduct
    if (caseFilter.module) query.module = caseFilter.module
    return query
  }
  function onSearchProjectProductChange() {
    const moduleItem = conditionItems.find((item) => item.key === 'module')
    if (moduleItem) {
      moduleItem.value = undefined
    }
    loadSuites()
  }
  function getViewFromRoute() {
    return route.path.includes('/functional-test/case/index') ? 'case' : 'suite'
  }
  function loadActiveView() {
    if (activeView.value === 'case') {
      loadCases()
      return
    }
    loadSuites()
  }
  function resetActiveSearch() {
    if (activeView.value === 'case') {
      resetCaseSearch()
      return
    }
    resetSearch()
  }

  function onCaseProjectProductChange() {
    caseFilter.module = undefined
    caseFilter.requirement_name = ''
    caseModuleSelectedKeys.value = ['all']
    casePagination.page = 1
    loadCaseModules()
    loadRequirementOptions()
    loadCases()
  }
  function onCaseRequirementChange() {
    casePagination.page = 1
    loadCases()
  }
  function onCaseTestTypeChange() {
    casePagination.page = 1
    loadCases()
  }
  function onCaseModuleSelect(keys: Array<string>) {
    const key = keys[0] || 'all'
    caseModuleSelectedKeys.value = [key]
    casePagination.page = 1
    if (key === 'all') {
      caseFilter.module = undefined
      caseFilter.requirement_name = ''
      loadRequirementOptions()
      loadCases()
      return
    }
    const [type, value = ''] = key.split(':')
    const treeValue = decodeModuleTreeKey(value)
    if (type === 'module') {
      caseFilter.module = treeValue.current
      caseFilter.requirement_name = ''
      loadRequirementOptions()
      loadCases()
      return
    }
    caseFilter.module = undefined
    caseFilter.requirement_name = ''
    loadRequirementOptions()
    loadCases()
  }
  function resetSearch() {
    conditionItems.forEach((item) => {
      item.value = undefined
    })
    const requirementItem = conditionItems.find((item) => item.key === 'requirement_name')
    const iterationItem = conditionItems.find((item) => item.key === 'iteration')
    if (requirementItem) requirementItem.value = ''
    if (iterationItem) iterationItem.value = ''
    loadSuites()
  }
  function resetCaseSearch() {
    caseFilter.project_product = undefined
    caseFilter.module = undefined
    caseFilter.moduleKeyword = ''
    caseFilter.requirement_name = ''
    caseFilter.title = ''
    caseFilter.case_no = ''
    caseFilter.test_type = undefined
    caseModuleSelectedKeys.value = ['all']
    caseModuleExpandedKeys.value = ['all']
    casePagination.page = 1
    requirementOptions.value = []
    loadCaseModules()
    loadRequirementOptions()
    loadCases()
  }
  async function loadSuites() {
    suiteLoading.value = true
    try {
      const res = await getManualSuite(buildQuery())
      suites.value = res.data || []
      pagination.setTotalSize((res as any).totalSize || suites.value.length)
    } finally {
      suiteLoading.value = false
    }
  }
  async function loadCases() {
    caseLoading.value = true
    try {
      const res = await getManualCase(buildCaseQuery())
      cases.value = res.data || []
      casePagination.setTotalSize((res as any).totalSize || cases.value.length)
    } finally {
      caseLoading.value = false
    }
  }
  async function loadCaseModules() {
    moduleLoading.value = true
    try {
      const projectProduct = normalizeProjectProductValue(caseFilter.project_product)
      const res = await getManualCaseModules(projectProduct ? { project_product_id: projectProduct } : {})
      if (Array.isArray(res.data)) {
        moduleOptions.value = res.data
      } else {
        caseProjectProducts.value = Array.isArray(res.data?.products) ? res.data.products : caseProjectProducts.value
        moduleOptions.value = Array.isArray(res.data?.modules) ? res.data.modules : []
      }
      caseModuleExpandedKeys.value = ['all']
    } finally {
      moduleLoading.value = false
    }
  }
  async function loadRequirementOptions() {
    requirementLoading.value = true
    try {
      const res = await getManualSuite(buildRequirementQuery())
      const seen = new Set()
      requirementOptions.value = (res.data || [])
        .filter((item: any) => item.requirement_name)
        .filter((item: any) => {
          if (seen.has(item.requirement_name)) return false
          seen.add(item.requirement_name)
          return true
        })
        .map((item: any) => ({ label: item.requirement_name, value: item.requirement_name }))
      if (
        caseFilter.requirement_name &&
        !requirementOptions.value.some((item) => item.value === caseFilter.requirement_name)
      ) {
        caseFilter.requirement_name = ''
      }
    } finally {
      requirementLoading.value = false
    }
  }
  async function initCaseView() {
    const res = await getManualCaseModules({})
    const products = Array.isArray(res.data?.products) ? res.data.products : []
    caseProjectProducts.value = products
    if (!normalizeProjectProductValue(caseFilter.project_product) && products.length) {
      caseFilter.project_product = products[0].key
    }
    await Promise.all([loadCaseModules(), loadRequirementOptions(), loadCases()])
  }
  async function fetchExportCases() {
    const pageSize = 1000
    const firstRes = await getManualCase({ ...buildCaseQuery(), page: 1, pageSize })
    const rows = [...(firstRes.data || [])]
    const total = Number((firstRes as any).totalSize || rows.length)
    const pageCount = Math.ceil(total / pageSize)
    for (let page = 2; page <= pageCount; page += 1) {
      const res = await getManualCase({ ...buildCaseQuery(), page, pageSize })
      rows.push(...(res.data || []))
    }
    return rows
  }
  function buildExportRows(rows: any[]) {
    return rows.map((record) => ({
      ID: record.id || '',
      '项目/产品': formatProjectProductPath(record.project_product),
      模块名称: formatModulePath(record.module),
      用例编号: record.case_no || '',
      标题: record.title || '',
      需求名称: record.suite?.requirement_name || '',
      所属迭代: record.suite?.iteration || '',
      前置条件: record.precondition || '',
      测试点: record.test_point || '',
      测试数据: record.test_data || '',
      测试类型: enumTitles(enumStore.manual_test_type, record.test_types),
      优先级: enumTitle(enumStore.case_level, record.priority),
      场景层级: enumTitle(enumStore.api_case_scenario_layer, record.scenario_layer),
      场景类型: enumTitle(enumStore.manual_test_scenario_type, record.scenario_type),
      场景标签: enumTitles(enumStore.api_case_scenario_tag, record.scenario_tags),
      'API 用例 ID': bindingCaseId(record, AUTOMATION_TYPE_API),
      'UI 用例 ID': bindingCaseId(record, AUTOMATION_TYPE_UI),
      变更: enumTitle(enumStore.manual_test_change_status, record.change_status),
      自动化影响: enumTitle(enumStore.manual_test_automation_impact_status, record.automation_impact_status),
      备注: record.remark || '',
    }))
  }
  async function exportCases() {
    if (exportLoading.value) return
    exportLoading.value = true
    try {
      const rows = await fetchExportCases()
      if (!rows.length) {
        Message.warning('暂无可导出的用例')
        return
      }
      const worksheet = XLSX.utils.json_to_sheet(buildExportRows(rows))
      const workbook = XLSX.utils.book_new()
      XLSX.utils.book_append_sheet(workbook, worksheet, '测试用例')
      XLSX.writeFile(workbook, formatExportFileName())
      Message.success('导出成功')
    } finally {
      exportLoading.value = false
    }
  }
  function openSuite(record?: any) {
    Object.keys(suiteForm).forEach((key) => delete suiteForm[key])
    Object.assign(
      suiteForm,
      record
        ? {
            ...record,
            project_product: record.project_product?.id || record.project_product,
            module: record.module?.id || record.module,
            owner: record.owner?.id || record.owner,
          }
        : {}
    )
    suiteVisible.value = true
  }
  async function saveSuite() {
    const payload = { ...suiteForm }
    if (!payload.owner) {
      Message.error('请选择测试负责人')
      return
    }
    const action = payload.id ? putManualSuite : postManualSuite
    await action(payload)
    Message.success('保存成功')
    suiteVisible.value = false
    await loadSuites()
  }
  function deleteSuite(record: any) {
    Modal.confirm({
      title: '删除需求',
      content: `确认删除需求「${record.requirement_name || record.id}」吗？需求下的测试用例也会一起删除。`,
      cancelText: '取消',
      okText: '删除',
      okButtonProps: { status: 'danger' },
      onBeforeOk: async () => {
        suiteLoading.value = true
        try {
          await deleteManualSuite(record.id)
          Message.success('删除成功')
          await loadSuites()
        } finally {
          suiteLoading.value = false
        }
      },
    })
  }
  function openCase(record: any) {
    Object.keys(caseForm).forEach((key) => delete caseForm[key])
    Object.assign(caseForm, {
      ...record,
      suite: record.suite?.id || record.suite,
      project_product: record.project_product?.id || record.project_product,
      module: record.module?.id || record.module,
      owner: record.owner?.id || record.owner,
    })
    caseVisible.value = true
  }
  function validateCaseForm() {
    const required = [
      ['case_no', '请输入用例编号'],
      ['title', '请输入用例标题'],
      ['test_point', '请输入测试点'],
      ['project_product', '请选择项目产品'],
      ['module', '请选择模块'],
      ['owner', '请选择负责人'],
    ]
    for (const [field, message] of required) {
      if (!String(caseForm[field] || '').trim()) {
        Message.error(message)
        return false
      }
    }
    if (!caseForm.test_types?.length) {
      Message.error('请选择测试类型')
      return false
    }
    if (caseForm.priority === undefined || caseForm.priority === null || caseForm.priority === '') {
      Message.error('请选择优先级')
      return false
    }
    if (caseForm.scenario_layer === undefined || caseForm.scenario_layer === null || caseForm.scenario_layer === '') {
      Message.error('请选择场景层级')
      return false
    }
    if (caseForm.scenario_type === undefined || caseForm.scenario_type === null || caseForm.scenario_type === '') {
      Message.error('请选择场景类型')
      return false
    }
    if (!caseForm.scenario_tags?.length) {
      Message.error('请选择场景标签')
      return false
    }
    return true
  }
  async function saveCase() {
    if (!validateCaseForm()) return
    await putManualCase({ ...caseForm, suite: caseForm.suite?.id || caseForm.suite })
    Message.success('保存成功')
    caseVisible.value = false
    await loadCases()
  }
  function deleteCase(record: any) {
    Modal.confirm({
      title: '删除测试用例',
      content: `确认删除测试用例「${record.case_no || record.title || record.id}」吗？`,
      cancelText: '取消',
      okText: '删除',
      okButtonProps: { status: 'danger' },
      onBeforeOk: async () => {
        caseLoading.value = true
        try {
          await deleteManualCase(record.id)
          Message.success('删除成功')
          await Promise.all([loadCases(), loadCaseModules(), loadRequirementOptions()])
        } finally {
          caseLoading.value = false
        }
      },
    })
  }
  function goSuite(record: any) {
    router.push({ path: '/functional-test/suite/details', query: { id: record.id } })
  }
  onMounted(async () => {
    await enumStore.getEnum()
    getUserName().then((res) => (userOptions.value = res.data || []))
    if (activeView.value === 'case') {
      initCaseView()
      return
    }
    loadSuites()
  })

  watch(
    () => route.path,
    () => {
      const view = getViewFromRoute()
      if (activeView.value === view) return
      activeView.value = view
      if (view === 'case') {
        initCaseView()
        return
      }
      loadSuites()
    }
  )

  watch(
    () => caseFilter.moduleKeyword,
    (keyword) => {
      if (keyword.trim()) {
        caseModuleExpandedKeys.value = ['all', ...caseModuleTree.value.flatMap((item: any) => item.children?.map((child: any) => child.key) || [])]
      }
    }
  )
</script>

<style scoped>
  .mango-functional-case-list-workbench {
    display: grid;
    min-height: 100%;
    padding-top: 8px;
    box-sizing: border-box;
    grid-template-columns: minmax(240px, 300px) minmax(0, 1fr);
    gap: 12px;
    align-items: start;
  }

  .mango-functional-suite-toolbar {
    display: flex;
    justify-content: flex-end;
    margin-bottom: 8px;
  }

  .mango-functional-case-module-panel,
  .mango-functional-case-list-main {
    display: flex;
    min-width: 0;
    flex-direction: column;
    overflow: visible;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
  }

  .mango-functional-case-module-panel {
    position: sticky;
    top: 8px;
    overflow: hidden;
    max-height: calc(100vh - 158px);
    padding: 12px;
  }

  .mango-functional-case-module-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 10px;
  }

  .mango-functional-case-module-head h3 {
    margin: 0;
    color: var(--m-text);
    font-size: 15px;
    font-weight: 600;
    line-height: 20px;
  }

  .mango-functional-case-module-head p {
    margin: 2px 0 0;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 17px;
  }

  .mango-functional-case-module-tree {
    flex: 1;
    min-height: 0;
    margin-top: 10px;
    overflow: auto;
  }

  .mango-functional-case-module-filter {
    margin-bottom: 10px;
  }

  .mango-functional-case-module-filter :deep(.arco-cascader),
  .mango-functional-case-module-filter :deep(.arco-cascader-view),
  .mango-functional-case-module-filter :deep(.arco-select),
  .mango-functional-case-module-filter :deep(.arco-select-view) {
    width: 100%;
  }

  .mango-functional-case-module-tree :deep(.arco-tree-node-title) {
    max-width: 210px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-functional-case-list-main {
    padding: 10px;
  }

  .mango-functional-suite-table,
  .mango-functional-case-table-shell {
    min-width: 0;
  }

  .mango-functional-scroll-table {
    width: 100%;
    overflow-x: auto;
    overflow-y: hidden;
    -webkit-overflow-scrolling: touch;
    overscroll-behavior-x: contain;
    scrollbar-width: thin;
    scrollbar-color: var(--m-scrollbar-thumb) transparent;
  }

  .mango-functional-scroll-table::-webkit-scrollbar {
    height: 6px;
  }

  .mango-functional-scroll-table::-webkit-scrollbar-track {
    background: transparent;
  }

  .mango-functional-scroll-table::-webkit-scrollbar-thumb {
    border-radius: 999px;
    background: var(--m-scrollbar-thumb);
  }

  .mango-functional-scroll-table :deep(.arco-table-container),
  .mango-functional-scroll-table :deep(.arco-table-content),
  .mango-functional-scroll-table :deep(.arco-scrollbar),
  .mango-functional-scroll-table :deep(.arco-scrollbar-container) {
    min-width: 0;
  }

  .mango-functional-scroll-table :deep(.arco-table-content),
  .mango-functional-scroll-table :deep(.arco-scrollbar-container) {
    overflow-x: auto !important;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: thin;
    scrollbar-color: var(--m-scrollbar-thumb) transparent;
  }

  .mango-functional-scroll-table :deep(.arco-table-content)::-webkit-scrollbar,
  .mango-functional-scroll-table :deep(.arco-scrollbar-container)::-webkit-scrollbar {
    width: 0;
    height: 6px;
  }

  .mango-functional-scroll-table :deep(.arco-table-content)::-webkit-scrollbar-track,
  .mango-functional-scroll-table :deep(.arco-scrollbar-container)::-webkit-scrollbar-track {
    background: transparent;
  }

  .mango-functional-scroll-table :deep(.arco-table-content)::-webkit-scrollbar-thumb,
  .mango-functional-scroll-table :deep(.arco-scrollbar-container)::-webkit-scrollbar-thumb {
    border-radius: 999px;
    background: var(--m-scrollbar-thumb);
  }

  .mango-functional-scroll-table :deep(.arco-scrollbar-track-direction-vertical),
  .mango-functional-scroll-table :deep(.arco-scrollbar-thumb-direction-vertical),
  .mango-functional-scroll-table :deep(.arco-scrollbar.arco-scrollbar-type-embed:hover .arco-scrollbar-thumb-direction-vertical),
  .mango-functional-scroll-table :deep(.arco-scrollbar-track-direction-vertical::after) {
    display: none !important;
    width: 0 !important;
    opacity: 0 !important;
    pointer-events: none !important;
  }

  .mango-functional-case-filter {
    flex: none;
    margin-bottom: 10px;
    padding: 8px 10px 0;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-sm);
    background: var(--m-surface-soft);
  }

  .mango-functional-case-filter :deep(.arco-form) {
    display: grid;
    grid-template-columns: repeat(4, minmax(150px, 1fr)) auto;
    gap: 0 10px;
  }

  .mango-functional-case-filter :deep(.arco-form-item) {
    margin-bottom: 10px;
  }

  @media (max-width: 1120px) {
    .mango-functional-case-list-workbench {
      grid-template-columns: 1fr;
    }

    .mango-functional-case-module-panel {
      position: static;
      max-height: none;
      min-height: 260px;
    }

    .mango-functional-case-filter :deep(.arco-form) {
      grid-template-columns: repeat(2, minmax(150px, 1fr));
    }
  }
</style>
