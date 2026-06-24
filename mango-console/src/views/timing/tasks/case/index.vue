<template>
  <TableBody class="mango-detail-workbench-page mango-timing-case-page">
    <template #header>
      <div class="mango-detail-toolbar">
        <div class="mango-detail-heading">
          <div class="mango-detail-title">{{ taskCaseDetailTitle }}</div>
          <div class="mango-detail-subtitle">维护当前定时任务绑定的执行用例和执行顺序</div>
        </div>
        <a-space class="mango-detail-actions" wrap>
          <a-button size="small" @click="doResetSearch">返回</a-button>
        </a-space>
      </div>
    </template>

    <template #default>
      <div class="mango-timing-case-workbench">
        <section class="mango-section-card mango-timing-case-picker">
        <div class="mango-section-title">
          <div>
            <h3>添加用例</h3>
            <p>按类型、项目、模块名称筛选后批量添加到当前定时任务</p>
          </div>
          <a-button
            size="small"
            type="primary"
            :disabled="addSelectionKeys.length === 0"
            :loading="addLoading"
            @click="onAddSelectedCases"
          >
            添加选中 {{ addSelectionKeys.length }}
          </a-button>
        </div>

        <div class="mango-soft-panel mango-timing-case-filter">
          <a-form :model="addForm" layout="horizontal" @keyup.enter="loadCandidateCases">
            <a-form-item label="测试类型">
              <a-select
                v-model="addForm.type"
                :field-names="fieldNames"
                :options="enumStore.test_case_type"
                allow-search
                value-key="key"
                @change="changeType"
              />
            </a-form-item>
            <a-form-item label="项目/产品">
              <ProjectProductSelect
                v-model="addForm.projectProduct"
                placeholder="请选择项目/产品"
                @change="onProjectProductChange"
              />
            </a-form-item>
            <a-form-item label="模块名称">
              <ProductModuleSelect
                v-model="addForm.module"
                :auto-clear="false"
                :project-product-id="addForm.projectProduct"
                placeholder="请选择模块名称"
                @change="loadCandidateCases"
              />
            </a-form-item>
            <a-form-item label="优先级">
              <a-select
                v-model="addForm.levels"
                :field-names="fieldNames"
                :options="enumStore.case_level"
                allow-clear
                allow-search
                multiple
                placeholder="请选择优先级"
                value-key="key"
                @change="loadCandidateCases"
              />
            </a-form-item>
            <a-form-item label="场景层级">
              <a-select
                v-model="addForm.scenarioLayers"
                :field-names="fieldNames"
                :options="enumStore.api_case_scenario_layer"
                allow-clear
                allow-search
                multiple
                placeholder="请选择场景层级"
                value-key="key"
                @change="loadCandidateCases"
              />
            </a-form-item>
            <a-form-item label="场景类型">
              <a-select
                v-model="addForm.scenarioTypes"
                :field-names="fieldNames"
                :options="enumStore.api_case_scenario_type"
                allow-clear
                allow-search
                multiple
                placeholder="请选择场景类型"
                value-key="key"
                @change="loadCandidateCases"
              />
            </a-form-item>
            <a-form-item label="场景标签">
              <a-select
                v-model="addForm.scenarioTags"
                :field-names="fieldNames"
                :options="enumStore.api_case_scenario_tag"
                allow-clear
                allow-search
                multiple
                placeholder="请选择场景标签"
                value-key="key"
                @change="loadCandidateCases"
              />
            </a-form-item>
            <a-form-item label="用例名称">
              <a-input
                v-model="addForm.caseName"
                allow-clear
                placeholder="请输入用例名称"
                @blur="loadCandidateCases"
                @clear="loadCandidateCases"
              />
            </a-form-item>
          </a-form>
        </div>

        <div class="mango-timing-case-list-head">
          <a-checkbox
            :disabled="selectableCandidateCases.length === 0"
            :indeterminate="candidateAllCheckedIndeterminate"
            :model-value="candidateAllChecked"
            @change="toggleAllCandidateCases"
          >
            可添加用例
          </a-checkbox>
          <small>
            已加载 {{ candidateCases.length }}
          </small>
        </div>
        <div class="mango-timing-case-candidate-table">
          <a-table
            class="mango-timing-case-table"
            :bordered="false"
            :columns="candidateColumns"
            :data="pagedCandidateCases"
            :loading="candidateLoading || boundCaseKeysLoading"
            :pagination="false"
            :row-key="'key'"
            size="small"
            :scroll="{ x: 640 }"
          >
            <template #columns>
              <a-table-column title="" data-index="selected" :width="54" align="center">
                <template #cell="{ record }">
                  <a-checkbox
                    :disabled="isCaseBound(record.key)"
                    :model-value="addSelectionKeys.includes(record.key)"
                    @change="(checked) => toggleCandidateCase(record.key, checked as boolean)"
                  />
                </template>
              </a-table-column>
              <a-table-column title="用例名称" data-index="title" :ellipsis="true" :tooltip="true">
                <template #cell="{ record }">
                  <span :class="{ 'mango-muted-text': isCaseBound(record.key) }">
                    {{ record.title }}
                  </span>
                </template>
              </a-table-column>
              <a-table-column title="状态" data-index="status" :width="86" align="center">
                <template #cell="{ record }">
                  <a-tag v-if="isCaseBound(record.key)" size="small">已添加</a-tag>
                  <a-tag v-else color="green" size="small">可添加</a-tag>
                </template>
              </a-table-column>
            </template>
          </a-table>
          <TableFooter
            class="mango-timing-case-footer"
            :pagination="candidatePagination"
          />
        </div>
      </section>

        <section class="mango-section-card mango-timing-case-bound">
        <div class="mango-section-title">
          <div>
            <h3>已绑定用例</h3>
            <p>支持搜索、拖拽排序、单个删除和批量删除</p>
          </div>
          <div class="mango-timing-case-bound-actions">
            <div class="mango-timing-case-summary">
              <span>总数 {{ boundStats.total }}</span>
              <span>UI {{ boundStats.ui }}</span>
              <span>API {{ boundStats.api }}</span>
              <span>Pytest {{ boundStats.pytest }}</span>
            </div>
            <a-button size="small" status="danger" :loading="deleteLoading" @click="onDelete(null)">
              批量删除
            </a-button>
          </div>
        </div>

        <div class="mango-soft-panel mango-timing-case-bound-filter">
          <a-form :model="boundFilter" layout="vertical">
            <a-form-item label="测试类型">
              <a-select
                v-model="boundFilter.type"
                :field-names="fieldNames"
                :options="enumStore.test_case_type"
                allow-clear
                allow-search
                placeholder="全部类型"
                value-key="key"
                @change="onBoundTypeChange"
              />
            </a-form-item>
            <a-form-item label="项目/产品">
              <ProjectProductSelect
                v-model="boundFilter.projectProduct"
                placeholder="全部项目/产品"
                @change="onBoundProjectProductChange"
              />
            </a-form-item>
            <a-form-item label="模块名称">
              <ProductModuleSelect
                v-if="!isBoundPytestCaseType"
                v-model="boundFilter.module"
                :auto-clear="false"
                :project-product-id="boundFilter.projectProduct"
                placeholder="全部模块名称"
                @change="onBoundFilterChange"
              />
              <a-select
                v-else
                v-model="boundFilter.module"
                :field-names="fieldNames"
                :options="data.boundModuleList"
                allow-clear
                allow-search
                placeholder="全部模块名称"
                value-key="key"
                @change="onBoundFilterChange"
              />
            </a-form-item>
            <a-form-item label="负责人">
              <a-select
                v-model="boundFilter.casePeople"
                :field-names="fieldNames"
                :options="data.nickname"
                allow-clear
                allow-search
                placeholder="全部负责人"
                value-key="key"
                @change="onBoundFilterChange"
              />
            </a-form-item>
            <a-form-item label="用例名称">
              <a-input
                v-model="boundFilter.caseName"
                allow-clear
                placeholder="搜索用例名称"
                @blur="onBoundFilterChange"
                @clear="onBoundFilterChange"
                @press-enter="onBoundFilterChange"
              />
            </a-form-item>
          </a-form>
        </div>

        <div class="mango-timing-case-bound-table">
          <a-table
            class="mango-timing-case-table"
            :bordered="false"
            :columns="tableColumns"
            :data="table.dataList"
            :draggable="{ type: 'handle', width: 40 }"
            :loading="table.tableLoading.value"
            :pagination="false"
            :row-selection="{ selectedRowKeys, showCheckedAll }"
            :row-key="rowKey"
            size="small"
            :scroll="{ x: 1700 }"
            @selection-change="onSelectionChange"
          >
            <template #columns>
              <a-table-column
                v-for="item of tableColumns"
                :key="item.key"
                :align="item.align"
                :data-index="item.key"
                :ellipsis="item.ellipsis"
                :fixed="item.fixed"
                :title="item.title"
                :tooltip="item.tooltip"
                :width="item.width"
              >
                <template v-if="item.key === 'index'" #cell="{ record }">
                  {{ record.id }}
                </template>
                <template v-else-if="item.key === 'type'" #cell="{ record }">
                  <a-tag :color="enumStore.colors[record.type]" size="small">
                    {{ enumStore.test_case_type[record.type]?.title || '-' }}
                  </a-tag>
                </template>
                <template v-else-if="item.key === 'case_id'" #cell="{ record }">
                  {{ getBoundCaseName(record) }}
                </template>
                <template v-else-if="item.key === 'project_product'" #cell="{ record }">
                  {{ getBoundCaseProjectProduct(record) }}
                </template>
                <template v-else-if="item.key === 'module'" #cell="{ record }">
                  {{ getBoundCaseModule(record) }}
                </template>
                <template v-else-if="item.key === 'case_people'" #cell="{ record }">
                  {{ getBoundCaseOwner(record) }}
                </template>
                <template v-else-if="item.key === 'scenario_layer'" #cell="{ record }">
                  <a-tag
                    v-if="getBoundCaseEnumValue(record, 'scenario_layer') !== null"
                    :color="enumStore.colors[getBoundCaseEnumValue(record, 'scenario_layer')]"
                    size="small"
                  >
                    {{ getEnumTitle(enumStore.api_case_scenario_layer, getBoundCaseEnumValue(record, 'scenario_layer')) }}
                  </a-tag>
                  <span v-else>-</span>
                </template>
                <template v-else-if="item.key === 'scenario_tags'" #cell="{ record }">
                  <a-space v-if="getBoundCaseTags(record).length" size="mini" wrap>
                    <a-tag
                      v-for="tag of getBoundCaseTags(record)"
                      :key="tag"
                      :color="enumStore.colors[tag]"
                      size="small"
                    >
                      {{ getEnumTitle(enumStore.api_case_scenario_tag, tag) }}
                    </a-tag>
                  </a-space>
                  <span v-else>-</span>
                </template>
                <template v-else-if="item.key === 'scenario_type'" #cell="{ record }">
                  <a-tag
                    v-if="getBoundCaseEnumValue(record, 'scenario_type') !== null"
                    :color="enumStore.colors[getBoundCaseEnumValue(record, 'scenario_type')]"
                    size="small"
                  >
                    {{ getEnumTitle(enumStore.api_case_scenario_type, getBoundCaseEnumValue(record, 'scenario_type')) }}
                  </a-tag>
                  <span v-else>-</span>
                </template>
                <template v-else-if="item.key === 'level'" #cell="{ record }">
                  <a-tag
                    v-if="getBoundCaseEnumValue(record, 'level') !== null"
                    :color="enumStore.colors[getBoundCaseEnumValue(record, 'level')]"
                    size="small"
                  >
                    {{ getEnumTitle(enumStore.case_level, getBoundCaseEnumValue(record, 'level')) }}
                  </a-tag>
                  <span v-else>-</span>
                </template>
                <template v-else-if="item.key === 'actions'" #cell="{ record }">
                  <MangoTableActions
                    :actions="[{ label: '删除', danger: true, onClick: () => onDelete(record) }]"
                  />
                </template>
              </a-table-column>
            </template>
          </a-table>
          <TableFooter
            class="mango-timing-case-footer"
            :pagination="pagination"
            :show-refresh="false"
          />
        </div>
        </section>
      </div>
    </template>
  </TableBody>
</template>

<script lang="ts" setup>
  import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import { useRoute } from 'vue-router'
  import { fieldNames } from '@/setting'
  import { usePagination, useRowKey, useRowSelection, useTable } from '@/hooks/table'
  import { tableColumns } from './config'
  import {
    deleteSystemTasksRunCase,
    getSystemTasksRunCase,
    getSystemTasksTypeCaseName,
    postSystemTasksRunCase,
  } from '@/api/system/tasks_details'
  import { useEnum } from '@/store/modules/get-enum'
  import { getPytestProductName } from '@/api/pytest/product'
  import { getUserName } from '@/api/user/user'
  import TableBody from '@/components/table/TableBody.vue'
  import TableFooter from '@/components/table/TableFooter.vue'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'

  type CandidateCase = {
    key: string | number
    title: string
  }

  const enumStore = useEnum()
  const { selectedRowKeys, onSelectionChange, showCheckedAll } = useRowSelection()
  const table = useTable()
  const pagination = usePagination(doRefresh)
  const candidatePagination = usePagination(() => loadCandidateCases(false))
  const rowKey = useRowKey('id')
  const route = useRoute()

  const addForm = reactive({
    type: Number(route.query.type ?? 1),
    projectProduct: route.query.project_product_id || '',
    module: route.query.module_id || '',
    caseName: '',
    levels: [] as Array<number | string>,
    scenarioLayers: [] as Array<number | string>,
    scenarioTypes: [] as Array<number | string>,
    scenarioTags: [] as Array<number | string>,
  })
  const data: any = reactive({
    boundModuleList: [],
    nickname: [],
  })
  const candidateCases = ref<CandidateCase[]>([])
  const addSelectionKeys = ref<Array<string | number>>([])
  const candidateLoading = ref(false)
  const boundCaseKeysLoading = ref(false)
  const boundCaseKeySet = ref<Set<string>>(new Set())
  const addLoading = ref(false)
  const deleteLoading = ref(false)
  const boundFilter = reactive({
    type: '',
    projectProduct: '',
    module: '',
    casePeople: '',
    caseName: '',
  })
  const candidateColumns = [
    { title: '', dataIndex: 'selected', width: 54 },
    { title: '用例名称', dataIndex: 'title' },
    { title: '状态', dataIndex: 'status', width: 86 },
  ]

  const taskCaseDetailTitle = computed(() => {
    const id = route.query.id || '-'
    const name = route.query.name || '-'
    return `定时任务用例配置 / ${id} / ${name}`
  })
  const isBoundPytestCaseType = computed(() => Number(boundFilter.type) === 2)
  const pagedCandidateCases = computed(() => {
    const start = (candidatePagination.page - 1) * candidatePagination.pageSize
    return candidateCases.value.slice(start, start + candidatePagination.pageSize)
  })
  const selectableCandidateCases = computed(() =>
    candidateCases.value.filter((item) => !isCaseBound(item.key))
  )
  const candidateAllChecked = computed(() => {
    if (selectableCandidateCases.value.length === 0) return false
    return selectableCandidateCases.value.every((item) => addSelectionKeys.value.includes(item.key))
  })
  const candidateAllCheckedIndeterminate = computed(() => {
    const selectedCount = selectableCandidateCases.value.filter((item) =>
      addSelectionKeys.value.includes(item.key)
    ).length
    return selectedCount > 0 && selectedCount < selectableCandidateCases.value.length
  })
  const boundStats = computed(() => {
    return table.dataList.reduce(
      (acc: any, item: any) => {
        acc.total += 1
        if (Number(item.type) === 0) acc.ui += 1
        if (Number(item.type) === 1) acc.api += 1
        if (Number(item.type) === 2) acc.pytest += 1
        return acc
      },
      { total: 0, ui: 0, api: 0, pytest: 0 }
    )
  })
  watch(
    () => candidateCases.value.length,
    (total) => {
      candidatePagination.setTotalSize(total)
      const maxPage = Math.max(1, Math.ceil(total / candidatePagination.pageSize))
      if (candidatePagination.page > maxPage) {
        candidatePagination.page = maxPage
      }
    },
    { immediate: true }
  )

  watch(
    () => candidatePagination.pageSize,
    () => {
      candidatePagination.page = 1
    }
  )

  function getBoundCaseName(record: any) {
    return record.ui_case?.name || record.api_case?.name || record.pytest_case?.name || '-'
  }

  function getLeafValue(value: any) {
    if (Array.isArray(value)) {
      return value[value.length - 1] ?? ''
    }
    return value || ''
  }

  function getBoundCase(record: any) {
    return record.ui_case || record.api_case || record.pytest_case || {}
  }

  function getBoundCaseId(record: any) {
    return record.ui_case?.id || record.api_case?.id || record.pytest_case?.id || ''
  }

  function getBoundCaseProjectProduct(record: any) {
    const caseInfo = getBoundCase(record)
    return (
      caseInfo.project_product?.name ||
      caseInfo.project_product_name ||
      caseInfo.project?.name ||
      caseInfo.product?.name ||
      '-'
    )
  }

  function getBoundCaseModule(record: any) {
    const caseInfo = getBoundCase(record)
    return caseInfo.module?.name || caseInfo.module?.title || caseInfo.module_name || '-'
  }

  function getBoundCaseOwner(record: any) {
    const caseInfo = getBoundCase(record)
    return (
      caseInfo.case_people?.name ||
      caseInfo.case_people_name ||
      caseInfo.user?.name ||
      caseInfo.create_user?.name ||
      '-'
    )
  }

  function getBoundCaseEnumValue(record: any, key: string) {
    const caseInfo = getBoundCase(record)
    const value = caseInfo[key]
    return value === undefined || value === null || value === '' ? null : value
  }

  function getBoundCaseTags(record: any) {
    const tags = getBoundCase(record).scenario_tags
    return Array.isArray(tags) ? tags : []
  }

  function getEnumTitle(options: any[], value: any) {
    return options?.[value]?.title || '-'
  }

  function isCaseBound(caseId: string | number) {
    return boundCaseKeySet.value.has(String(caseId))
  }

  function toggleCandidateCase(caseId: string | number, checked: boolean) {
    if (isCaseBound(caseId)) return
    if (checked) {
      if (!addSelectionKeys.value.includes(caseId)) addSelectionKeys.value.push(caseId)
      return
    }
    addSelectionKeys.value = addSelectionKeys.value.filter((item) => item !== caseId)
  }

  function toggleAllCandidateCases(checked: boolean) {
    const selectableKeys = selectableCandidateCases.value.map((item) => item.key)
    if (checked) {
      addSelectionKeys.value = Array.from(new Set([...addSelectionKeys.value, ...selectableKeys]))
      return
    }
    addSelectionKeys.value = addSelectionKeys.value.filter((item) => !selectableKeys.includes(item))
  }

  function clearCandidateCases() {
    candidateCases.value = []
    addSelectionKeys.value = []
    candidatePagination.page = 1
  }

  function onProjectProductChange() {
    addForm.module = ''
    clearCandidateCases()
    loadCandidateCases()
  }

  function onBoundFilterChange() {
    pagination.page = 1
    selectedRowKeys.value = []
    doRefresh()
  }

  function onBoundTypeChange(value: number | string) {
    boundFilter.type = value as any
    boundFilter.module = ''
    data.boundModuleList = []
    if (Number(value) === 2) {
      loadBoundPytestModules(boundFilter.projectProduct)
    }
    onBoundFilterChange()
  }

  function onBoundProjectProductChange(value: any) {
    boundFilter.projectProduct = value
    boundFilter.module = ''
    data.boundModuleList = []
    if (isBoundPytestCaseType.value) {
      loadBoundPytestModules(value)
    }
    onBoundFilterChange()
  }

  function changeType(value: number) {
    addForm.type = value
    clearCandidateCases()
    loadBoundCaseKeys()
    loadCandidateCases()
  }

  function loadCandidateCases(resetPage = true) {
    if (resetPage) {
      clearCandidateCases()
    }
    const projectProductId = getLeafValue(addForm.projectProduct || route.query.project_product_id)
    const moduleId = getLeafValue(addForm.module)
    if (!moduleId && !projectProductId) return
    candidateLoading.value = true
    getSystemTasksTypeCaseName(
      addForm.type,
      moduleId || undefined,
      projectProductId || undefined,
      undefined,
      {
        case_name: addForm.caseName || undefined,
        levels: addForm.levels?.join(','),
        scenario_layers: addForm.scenarioLayers?.join(','),
        scenario_types: addForm.scenarioTypes?.join(','),
        scenario_tags: addForm.scenarioTags?.join(','),
      }
    )
      .then((res) => {
        candidateCases.value = res.data || []
      })
      .catch(console.log)
      .finally(() => {
        candidateLoading.value = false
      })
  }

  function loadBoundCaseKeys() {
    if (!route.query.id) {
      boundCaseKeySet.value = new Set()
      return Promise.resolve()
    }
    boundCaseKeysLoading.value = true
    return getSystemTasksRunCase({
      task_id: route.query.id,
      type: addForm.type,
    })
      .then((res) => {
        boundCaseKeySet.value = new Set(
          (res.data || [])
            .map((item: any) => String(getBoundCaseId(item)))
            .filter(Boolean)
        )
      })
      .catch(console.log)
      .finally(() => {
        boundCaseKeysLoading.value = false
      })
  }

  function onAddSelectedCases() {
    if (addSelectionKeys.value.length === 0) {
      Message.error('请选择要添加的用例')
      return
    }
    const typeList = ['ui_case', 'api_case', 'pytest_case']
    const payload: any = {
      type: addForm.type,
      task: route.query.id,
      [typeList[Number(addForm.type)]]: addSelectionKeys.value,
    }
    addLoading.value = true
    postSystemTasksRunCase(payload)
      .then((res) => {
        Message.success(res.msg)
        addSelectionKeys.value = []
        loadBoundCaseKeys()
        doRefresh()
      })
      .catch(console.log)
      .finally(() => {
        addLoading.value = false
      })
  }

  function onDelete(record: any) {
    const batch = record === null
    if (batch && selectedRowKeys.value.length === 0) {
      Message.error('请选择要删除的数据')
      return
    }
    Modal.confirm({
      title: '提示',
      content: batch ? '是否要删除选中的定时任务用例？' : '是否要删除此定时任务用例？',
      cancelText: '取消',
      okText: '删除',
      onBeforeOk: () => {
        deleteLoading.value = batch
        return deleteSystemTasksRunCase(batch ? selectedRowKeys.value : record.id)
          .then((res) => {
            Message.success(res.msg)
          })
          .catch(console.log)
          .finally(() => {
            loadBoundCaseKeys()
            doRefresh()
            deleteLoading.value = false
            if (batch) selectedRowKeys.value = []
          })
      },
    })
  }

  function doResetSearch() {
    window.history.back()
  }

  function doRefresh() {
    table.tableLoading.value = true
    const projectProductId = getLeafValue(boundFilter.projectProduct)
    const moduleId = getLeafValue(boundFilter.module)
    const boundType = boundFilter.type === '' || boundFilter.type === null ? undefined : boundFilter.type
    getSystemTasksRunCase({
      task_id: route.query.id,
      type: boundType,
      project_product_id: projectProductId || undefined,
      module_id: moduleId || undefined,
      case_people_id: boundFilter.casePeople || undefined,
      case_name: boundFilter.caseName || undefined,
      page: pagination.page,
      pageSize: pagination.pageSize,
    })
      .then((res) => {
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
      })
      .catch((error) => {
        table.tableLoading.value = false
        console.log(error)
      })
  }

  function loadBoundPytestModules(projectProductId: any) {
    const productId = getLeafValue(projectProductId)
    if (!productId) return
    getPytestProductName(productId)
      .then((res) => {
        data.boundModuleList = res.data
      })
      .catch(console.log)
  }

  function getNickName() {
    getUserName()
      .then((res) => {
        data.nickname = res.data
      })
      .catch(console.log)
  }

  onMounted(() => {
    nextTick(async () => {
      await loadBoundCaseKeys()
      doRefresh()
      getNickName()
      loadCandidateCases()
    })
  })
</script>

<style lang="less" scoped>
  .mango-timing-case-workbench {
    display: grid;
    min-height: calc(100% - 12px);
    margin-top: 12px;
    grid-template-columns: minmax(420px, 0.9fr) minmax(0, 1.35fr);
    gap: 12px;
    align-items: start;
  }

  .mango-timing-case-workbench > .mango-section-card + .mango-section-card {
    margin-top: 0;
  }

  .mango-timing-case-picker,
  .mango-timing-case-bound {
    display: flex;
    min-width: 0;
    flex-direction: column;
    overflow: visible;
  }

  .mango-timing-case-table {
    min-height: 0;
  }

  .mango-timing-case-candidate-table {
    display: flex;
    flex-direction: column;
    min-width: 0;
  }

  .mango-timing-case-bound-table {
    display: flex;
    flex-direction: column;
    min-width: 0;
  }

  .mango-timing-case-footer {
    flex: 0 0 42px;
    margin-top: 8px;
  }

  .mango-timing-case-footer.mango-table-mango-footer-container {
    height: 42px;
  }

  .mango-timing-case-picker > .mango-section-title,
  .mango-timing-case-bound > .mango-section-title {
    min-height: 42px;
    align-items: center;
    margin-bottom: 6px;
  }

  .mango-timing-case-picker > .mango-section-title h3,
  .mango-timing-case-bound > .mango-section-title h3 {
    margin: 0;
    color: var(--m-text);
    font-size: 15px;
    font-weight: 600;
    line-height: 20px;
  }

  .mango-timing-case-picker > .mango-section-title p,
  .mango-timing-case-bound > .mango-section-title p {
    margin: 2px 0 0;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 17px;
  }

  .mango-timing-case-filter {
    margin-bottom: 10px;
    padding: 10px 10px 0;
  }

  .mango-timing-case-filter :deep(.arco-form) {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0 12px;
  }

  .mango-timing-case-filter :deep(.arco-form-item) {
    display: flex;
    align-items: center;
    margin-bottom: 10px;
  }

  .mango-timing-case-filter :deep(.arco-form-item-label-col) {
    flex: 0 0 78px;
    width: 78px;
    min-width: 78px;
    padding-right: 8px;
    text-align: right;
  }

  .mango-timing-case-filter :deep(.arco-form-item-label) {
    justify-content: flex-end;
  }

  .mango-timing-case-filter :deep(.arco-form-item-wrapper-col) {
    flex: 1;
    min-width: 0;
  }

  .mango-timing-case-list-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
    color: var(--m-text-2);
    font-size: 13px;
  }

  .mango-timing-case-list-head small {
    color: var(--m-muted);
    font-size: 12px;
  }

  .mango-timing-case-bound-filter {
    margin-bottom: 10px;
    padding: 10px 10px 0;
  }

  .mango-timing-case-bound-filter :deep(.arco-form) {
    display: grid;
    grid-template-columns: repeat(5, minmax(120px, 1fr));
    gap: 0 10px;
  }

  .mango-timing-case-bound-filter :deep(.arco-form-item) {
    margin-bottom: 10px;
  }

  .mango-timing-case-summary {
    display: flex;
    flex-wrap: nowrap;
    justify-content: flex-end;
    gap: 4px;
  }

  .mango-timing-case-bound-actions {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    flex-wrap: nowrap;
    gap: 6px;
  }

  .mango-timing-case-summary span {
    padding: 2px 6px;
    border: 1px solid var(--m-border);
    border-radius: 999px;
    background: var(--m-surface-soft);
    color: var(--m-text-2);
    font-size: 12px;
    line-height: 17px;
  }

  @media (max-width: 1380px) {
    .mango-timing-case-workbench {
      grid-template-columns: minmax(360px, 0.82fr) minmax(0, 1.28fr);
    }

    .mango-timing-case-filter :deep(.arco-form) {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .mango-timing-case-bound-filter :deep(.arco-form) {
      grid-template-columns: repeat(3, minmax(120px, 1fr));
    }
  }

  @media (max-width: 1120px) {
    .mango-timing-case-workbench {
      grid-template-columns: minmax(0, 1fr);
    }

    .mango-timing-case-filter :deep(.arco-form),
    .mango-timing-case-bound-filter :deep(.arco-form) {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }
</style>
