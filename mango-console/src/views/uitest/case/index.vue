<template>
  <TableBody ref="tableBody">
    <template #header>
      <TableHeader
        :show-filter="true"
        title="测试用例"
        @search="onSearchRefresh"
        @reset-search="onResetSearch"
      >
        <template #search-content>
          <a-form :model="{}" layout="inline" @keyup.enter="onSearchRefresh">
            <a-form-item v-for="item of conditionItems" :key="item.key" :label="item.label">
              <template v-if="item.type === 'input'">
                <a-input
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  allow-clear
                  @blur="onSearchRefresh"
                  @clear="onSearchRefresh"
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
                  @change="onSearchRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'case_people'">
                <a-select
                  v-model="item.value"
                  :field-names="fieldNames"
                  :options="data.userList"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="onSearchRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'status'">
                <a-select
                  v-model="item.value"
                  :field-names="fieldNames"
                  :options="enumStore.task_status"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="onSearchRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'level'">
                <a-select
                  v-model="item.value"
                  :field-names="fieldNames"
                  :options="enumStore.case_level"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="onSearchRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'scenario_layer'">
                <a-select
                  v-model="item.value"
                  :field-names="fieldNames"
                  :options="enumStore.api_case_scenario_layer"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="onSearchRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'scenario_type'">
                <a-select
                  v-model="item.value"
                  :field-names="fieldNames"
                  :options="enumStore.api_case_scenario_type"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="onSearchRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'scenario_tags'">
                <a-select
                  v-model="item.value"
                  :field-names="fieldNames"
                  :options="enumStore.api_case_scenario_tag"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  multiple
                  value-key="key"
                  @change="onSearchRefresh"
                />
              </template>
            </a-form-item>
          </a-form>
        </template>
      </TableHeader>
    </template>

    <template #default>
      <a-tabs>
        <template #extra>
          <a-space>
            <div>
              <a-button
                size="small"
                status="success"
                :loading="caseRunning"
                @click="onConcurrency('批量执行')"
                >批量执行
              </a-button>
            </div>
            <div>
              <a-button size="small" status="warning" @click="handleClick">设为定时任务</a-button>
              <a-modal v-model:visible="data.visible" @cancel="handleCancel" @ok="handleOk">
                <template #title> 设为定时任务</template>
                <div>
                  <a-select
                    v-model="data.value"
                    :field-names="fieldNames"
                    :options="data.scheduledName"
                    allow-clear
                    allow-search
                    placeholder="请选择定时任务进行绑定"
                    value-key="key"
                  />
                </div>
              </a-modal>
            </div>
            <div>
              <a-button size="small" type="primary" @click="onAdd">新增</a-button>
            </div>
            <div>
              <a-button size="small" status="danger" @click="onDelete(null)">批量删除</a-button>
            </div>
          </a-space>
        </template>
      </a-tabs>

      <a-table
        :bordered="false"
        :columns="tableColumns"
        :data="table.dataList"
        :loading="table.tableLoading.value"
        :pagination="false"
        :row-selection="{ selectedRowKeys, showCheckedAll }"
        :rowKey="rowKey"
        :scroll="{ x: 1640 }"
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
            <template v-else-if="item.key === 'project_product'" #cell="{ record }">
              {{ formatProjectProductPath(record?.project_product) }}
            </template>
            <template v-else-if="item.key === 'module'" #cell="{ record }">
              {{ formatModulePath(record?.module) }}
            </template>
            <template v-else-if="item.key === 'scenario_type'" #cell="{ record }">
              <a-tag :color="enumStore.colors[record.scenario_type]" size="small">
                {{ getEnumTitle(enumStore.api_case_scenario_type, record.scenario_type) }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'scenario_layer'" #cell="{ record }">
              <a-tag :color="enumStore.colors[record.scenario_layer]" size="small">
                {{ getEnumTitle(enumStore.api_case_scenario_layer, record.scenario_layer) }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'scenario_tags'" #cell="{ record }">
              <a-space wrap :size="4">
                <a-tag
                  v-for="tag of getScenarioTagList(record)"
                  :key="tag.key"
                  :color="enumStore.colors[tag.key]"
                  size="small"
                >
                  {{ tag.title }}
                </a-tag>
                <span v-if="!getScenarioTagList(record).length">-</span>
              </a-space>
            </template>
            <template v-else-if="item.key === 'scenario_description'" #cell="{ record }">
              {{ record.scenario_description || '-' }}
            </template>
            <template v-else-if="item.key === 'level'" #cell="{ record }">
              <a-tag :color="enumStore.colors[record?.level]" size="small"
                >{{ record.level !== null ? enumStore.case_level[record.level]?.title || '-' : '-' }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'case_people'" #cell="{ record }">
              {{ record.case_people.name }}
            </template>
            <template v-else-if="item.key === 'status'" #cell="{ record }">
              <a-tag :color="enumStore.status_colors[record.status]" size="small"
                >{{ enumStore.task_status[record.status]?.title || '-' }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <MangoTableActions
                :actions="[
                  { label: '执行', loading: caseRunning, onClick: () => onCaseRun(record.id) },
                  { label: '步骤', onClick: () => onClick(record) },
                  { label: '套件', onClick: () => clickSuite(record) },
                  { label: '编辑', onClick: () => onUpdate(record) },
                  { label: '复制', onClick: () => caseCody(record) },
                  { label: '删除', danger: true, onClick: () => onDelete(record) },
                ]"
              />
            </template>
          </a-table-column>
        </template>
      </a-table>
      <ParametrizeDrawer
        v-model:initial-data="data.row.parametrize"
        :visible="data.drawerVisible"
        @cancel="data.drawerVisible = false"
        @ok="drawerOk"
      />
    </template>
    <template #footer>
      <TableFooter :pagination="pagination" />
    </template>
  </TableBody>
  <ModalDialog ref="modalDialogRef" :title="data.actionTitle" @confirm="onDataForm">
    <template #content>
      <a-form :model="formModel">
        <a-form-item
          v-for="item of formItems"
          :key="item.key"
          :class="[item.required ? 'mango-form-item__require' : 'mango-form-item__no_require']"
          :label="item.label"
        >
          <template v-if="item.type === 'input'">
            <a-input v-model="item.value" :placeholder="item.placeholder" />
          </template>
          <template v-else-if="item.type === 'cascader'">
            <ProjectProductSelect
              v-model="item.value"
              :placeholder="item.placeholder"
              @change="onFormProjectProductChange"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'module'">
            <ProductModuleSelect
              v-model="item.value"
              :project-product-id="getFormItemValue('project_product')"
              :placeholder="item.placeholder"
              :auto-clear="false"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'case_people'">
            <a-select
              v-model="item.value"
              :field-names="fieldNames"
              :options="data.userList"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              value-key="key"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'level'">
            <a-select
              v-model="item.value"
              :field-names="fieldNames"
              :options="enumStore.case_level"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              value-key="key"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'scenario_layer'">
            <a-select
              v-model="item.value"
              :field-names="fieldNames"
              :options="enumStore.api_case_scenario_layer"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              value-key="key"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'scenario_type'">
            <a-select
              v-model="item.value"
              :field-names="fieldNames"
              :options="enumStore.api_case_scenario_type"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              value-key="key"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'scenario_tags'">
            <a-select
              v-model="item.value"
              :field-names="fieldNames"
              :options="enumStore.api_case_scenario_tag"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              multiple
              value-key="key"
            />
          </template>
          <template v-else-if="item.type === 'textarea'">
            <a-textarea
              v-model="item.value"
              :placeholder="item.placeholder"
              :auto-size="{ minRows: 3, maxRows: 5 }"
            />
          </template>
        </a-form-item>
      </a-form>
    </template>
  </ModalDialog>
</template>

<script lang="ts" setup>
  import { usePagination, useRowKey, useRowSelection, useTable } from '@/hooks/table'
  import { ModalDialogType } from '@/types/components'
  import { Message, Modal } from '@arco-design/web-vue'
  import { onMounted, ref, nextTick, reactive, onUnmounted } from 'vue'
  import { fieldNames } from '@/setting'
  import { getFormItems } from '@/utils/datacleaning'
  import { useRouter } from 'vue-router'
  import { usePageData } from '@/store/page-data'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import {
    formatModulePath,
    formatProjectProductPath,
    getItemValue,
    setItemValue,
  } from '@/utils/business-format'
  import { conditionItems, formItems, tableColumns } from './config'
  import {
    deleteUiCase,
    getUiCase,
    getUiCaseRun,
    postUiCase,
    postUiCaseCopy,
    putUiCase,
    postUiRunCaseBatch,
  } from '@/api/uitest/case'
  import { getSystemTasksName } from '@/api/system/tasks'
  import { postSystemTasksBatchSetCases } from '@/api/system/tasks_details'
  import { getUserName } from '@/api/user/user'
  import { useEnum } from '@/store/modules/get-enum'
  import useUserStore from '@/store/modules/user'

  const enumStore = useEnum()

  const userStore = useUserStore()
  const router = useRouter()

  const modalDialogRef = ref<ModalDialogType | null>(null)
  const pagination = usePagination(doRefresh)
  const { selectedRowKeys, onSelectionChange, showCheckedAll } = useRowSelection()
  const table = useTable()
  const rowKey = useRowKey('id')
  const formModel = ref({})

  const data: any = reactive({
    isAdd: false,
    updateId: 0,
    actionTitle: '新增',
    userList: [],
    moduleList: [],
    systemStatus: [],
    scheduledName: [],
    value: null,
    visible: false,
    drawerVisible: false,
    row: {},
  })
  const caseRunning = ref(false)

  const pollingTimer = ref<NodeJS.Timeout | null>(null)

  function clearPollingTimer() {
    if (pollingTimer.value) {
      clearInterval(pollingTimer.value)
      pollingTimer.value = null
    }
  }

  function getConditionValue(key: string) {
    return getItemValue(conditionItems, key)
  }

  function getFormItemValue(key: string) {
    return getItemValue(formItems, key)
  }

  function onSearchProjectProductChange(value: any) {
    setItemValue(conditionItems, 'module', null)
    doRefresh(value, true, true)
  }

  function onFormProjectProductChange() {
    setItemValue(formItems, 'module', null)
  }

  function onSearchRefresh() {
    doRefresh(null, false, true)
  }

  function doRefresh(projectProductId: any = null, bool_ = false, showLoading = false) {
    clearPollingTimer()
    if (showLoading) {
      table.tableLoading.value = true
    }
    let value = getFormItems(conditionItems)
    if (!Array.isArray(value.scenario_tags) || !value.scenario_tags.length) {
      delete value.scenario_tags
    }
    value['page'] = pagination.page
    value['pageSize'] = pagination.pageSize
    if (projectProductId && bool_) {
      value['project_product'] = projectProductId
    }
    getUiCase(value)
      .then((res) => {
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
        const hasRunningItem =
          res.data && Array.isArray(res.data) && res.data.some((item: any) => item.status === 3)

        if (hasRunningItem) {
          // 5秒后再次刷新
          pollingTimer.value = setInterval(() => {
            doRefresh(projectProductId, bool_, false)
          }, 5000)
        }
      })
      .catch(console.log)
      .finally(() => {
        if (showLoading) {
          table.tableLoading.value = false
        }
      })
  }

  function onResetSearch() {
    conditionItems.forEach((it) => {
      if (it.key === 'project_product' || it.key === 'module') {
        it.value = null
      } else if (it.reset) {
        it.reset()
      } else {
        it.value = ''
      }
    })
    doRefresh(null, false, true)
  }

  function getEnumTitle(options: any[] | null, value: any) {
    return options?.find((item: any) => Number(item.key) === Number(value))?.title || '-'
  }

  function getScenarioTagList(record: any) {
    const tags = Array.isArray(record.scenario_tags) ? record.scenario_tags : []
    return tags
      .map((tag: any) =>
        (enumStore.api_case_scenario_tag || []).find(
          (item: any) => Number(item.key) === Number(tag)
        )
      )
      .filter(Boolean)
  }

  function onAdd() {
    data.actionTitle = '添加'
    data.isAdd = true
    modalDialogRef.value?.toggle()
    formItems.forEach((it: any) => {
      if (it.reset) {
        it.reset()
      } else {
        it.value = ''
      }
    })
  }

  function onDelete(record: any) {
    const batch = record === null
    if (batch) {
      if (selectedRowKeys.value.length === 0) {
        Message.error('请选择要删除的数据')
        return
      }
    }
    Modal.confirm({
      title: '提示',
      content: '是否要删除此用例？',
      cancelText: '取消',
      okText: '删除',
      onBeforeOk: () => {
        return deleteUiCase(batch ? selectedRowKeys.value : record.id)
          .then((res) => {
            Message.success(res.msg)
          })
          .catch(console.log)
          .finally(() => {
            doRefresh()
            if (batch) {
              selectedRowKeys.value = []
            }
          })
      },
    })
  }

  function onUpdate(item: any) {
    data.actionTitle = '编辑'
    data.isAdd = false
    data.updateId = item.id
    modalDialogRef.value?.toggle()
    nextTick(() => {
      formItems.forEach((it) => {
        const propName = item[it.key]
        if (it.key === 'scenario_layer' && (propName === undefined || propName === null)) {
          it.value = 0
        } else if (Array.isArray(propName)) {
          it.value = propName
        } else if (typeof propName === 'object' && propName !== null) {
          it.value = propName.id
        } else {
          it.value = propName
        }
      })
    })
  }

  const onCaseRun = async (param) => {
    if (userStore.selected_environment == null) {
      Message.error('请先选择用例执行的环境')
      return
    }
    if (caseRunning.value) return
    caseRunning.value = true
    try {
      const res = await getUiCaseRun(param, userStore.selected_environment)
      Message.loading(res.msg)
    } catch (e) {
    } finally {
      caseRunning.value = false
      doRefresh()
    }
  }

  function onConcurrency(name: string) {
    if (userStore.selected_environment == null) {
      Message.error('请先选择用例执行的环境')
      return
    }
    if (selectedRowKeys.value.length === 0) {
      Message.error('请选择要' + name + '的用例数据')
      return
    }
    Modal.confirm({
      title: '提示',
      content: '确定要' + name + '这些用例吗？批量执行会生成多个浏览器来执行用例',
      cancelText: '取消',
      okText: '执行',
      onBeforeOk: () => {
        return postUiRunCaseBatch(selectedRowKeys.value, userStore.selected_environment)
          .then((res) => {
            Message.success(res.msg)
            selectedRowKeys.value = []
            doRefresh()
          })
          .catch(console.log)
      },
    })
  }

  const handleClick = () => {
    if (selectedRowKeys.value.length === 0) {
      Message.error('请选择要添加定时任务的用例')
      return
    }
    data.visible = true
  }
  const handleOk = () => {
    postSystemTasksBatchSetCases(selectedRowKeys.value, data.value, 0)
      .then((res) => {
        Message.success(res.msg)
        data.visible = false
        doRefresh()
      })
      .catch(console.log)
  }
  const handleCancel = () => {
    data.visible = false
  }

  function onDataForm() {
    if (formItems.every((it) => (it.validator ? it.validator() : true))) {
      let value = getFormItems(formItems)
      value['scenario_tags'] = value['scenario_tags'] || []
      if (data.isAdd) {
        value['front_custom'] = []
        value['front_sql'] = []
        value['posterior_sql'] = []
        value['scenario_layer'] = value['scenario_layer'] ?? 0
        postUiCase(value)
          .then((res) => {
            modalDialogRef.value?.toggle()
            Message.success(res.msg)
            doRefresh()
          })
          .catch((error) => {
            console.log(error)
          })
          .finally(() => {
            modalDialogRef.value?.setConfirmLoading(false)
          })
      } else {
        value['id'] = data.updateId
        putUiCase(value)
          .then((res) => {
            modalDialogRef.value?.toggle()
            Message.success(res.msg)
            doRefresh()
          })
          .catch((error) => {
            console.log(error)
          })
          .finally(() => {
            modalDialogRef.value?.setConfirmLoading(false)
          })
      }
    } else {
      modalDialogRef.value?.setConfirmLoading(false)
    }
  }

  function getNickName() {
    getUserName()
      .then((res) => {
        data.userList = res.data
      })
      .catch(console.log)
  }

  function onClick(record: any) {
    const pageData = usePageData()
    pageData.setRecord(record)
    router.push({
      path: '/uitest/case/details',
      query: {
        id: parseInt(record.id, 10),
      },
    })
  }

  function clickSuite(record: any) {
    data.row = JSON.parse(JSON.stringify(record))

    if (
      !data.row.parametrize ||
      !Array.isArray(data.row.parametrize) ||
      data.row.parametrize.length === 0
    ) {
      data.row.parametrize = [
        {
          name: '',
          parametrize: [{ key: '', value: '' }],
        },
      ]
    }

    data.drawerVisible = true
  }

  function drawerOk(paramData: any) {
    data.drawerVisible = false

    const hasValidData = paramData.some(
      (suite: any) => suite.name || suite.parametrize.some((param: any) => param.key || param.value)
    )

    let value = {
      id: data.row.id,
      parametrize: hasValidData ? paramData : [],
    }

    putUiCase(value)
      .then((res) => {
        Message.success(res.msg)
        doRefresh()
      })
      .catch(console.log)
  }

  function caseCody(record: any) {
    postUiCaseCopy(record.id)
      .then((res) => {
        Message.success(res.msg)
        doRefresh()
      })
      .catch(console.log)
  }

  function scheduledName() {
    getSystemTasksName()
      .then((res) => {
        data.scheduledName = res.data
      })
      .catch(console.log)
  }

  onMounted(() => {
    nextTick(async () => {
      await getNickName()
      await scheduledName()
      doRefresh()
    })
  })
  onUnmounted(() => {
    clearPollingTimer()
  })
</script>
