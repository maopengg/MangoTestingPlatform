<template>
  <TableBody ref="tableBody" plain class="mango-api-resource-page mango-detail-workbench-page">
    <template #header>
      <TableHeader title="全局变量" />
    </template>

    <template #default>
      <ProjectProductNavigationWorkbench
        ref="navigationCreateRef"
          contained-body
          :model-value="projectProductCondition?.value"
          :reset-key="sidebarResetKey"
          @filter-change="onSidebarFilterChange"
          @search="onSearchRefresh"
          @reset-search="onResetSearch"
        >
          <template #search>
              <ApiResourceSearchFilters
                :items="headerConditionItems"
                :field-names="fieldNames"
                :enum-store="enumStore"
                :user-list="data.userList"
                :environment-options="environmentOptions"
                @search="onSearchRefresh"
                @reset="onResetSearch"
              />
          </template>
          <template #toolbar>
          <a-space>
            <div>
              <a-button  size="small" type="primary" @click="onAdd" data-testid="qa-views-apitest-public-button-新增">新增</a-button>
            </div>
            <div>
              <a-button  size="small" status="danger" @click="onDelete(null)" data-testid="qa-views-apitest-public-button-批量删除">批量删除</a-button>
            </div>
          </a-space>
          </template>
      <a-table
        class="mango-native-scroll-table"
        :scroll="{ x: tableScrollX, y: '100%' }"
        :bordered="false"
        :columns="tableColumns"
        :data="table.dataList"
        :loading="table.tableLoading.value"
        :pagination="false"
        :row-selection="{ selectedRowKeys, showCheckedAll }"
        :rowKey="rowKey"
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
            <template v-else-if="item.key === 'test_env'" #cell="{ record }">
              <a-tag v-if="isCommonEnvironment(record.test_envs)" size="small">环境通用</a-tag>
              <a-space v-else wrap :size="4">
                <a-tag
                  v-for="env in normalizeEnvironmentList(record.test_envs)"
                  :key="env"
                  :color="enumStore.colors[env]"
                  size="small"
                >
                  {{ enumStore.environment_type.find((item) => String(item.key) === String(env))?.title || '-' }}
                </a-tag>
              </a-space>
            </template>
            <template v-else-if="item.key === 'type'" #cell="{ record }">
              <a-tag :color="enumStore.colors[record.type]" size="small"
                >{{ enumStore.api_public_type[record.type]?.title }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'datasource_alias'" #cell="{ record }">
              <a-tag v-if="record.datasource_alias" size="small">
                {{ record.datasource_alias.name }}
              </a-tag>
              <span v-else>-</span>
            </template>

            <template v-else-if="item.key === 'status'" #cell="{ record }">
              <a-switch
                :beforeChange="(newValue) => onModifyStatus(newValue, record.id)"
                :default-checked="record.status === 1"
              />
            </template>
            <template v-else-if="item.key === 'project_product'" #cell="{ record }">
              {{ formatProjectProductPath(record.project_product) }}
            </template>
            <template v-else-if="item.key === 'update_user'" #cell="{ record }">
              {{ record.update_user?.name || '-' }}
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <MangoTableActions
                :actions="[
    { label: '编辑', onClick: () => onUpdate(record) },
    { label: '删除', danger: true, onClick: () => onDelete(record) },
]"
              />
            </template>
          </a-table-column>
        </template>
      </a-table>
          <template #footer>
            <TableFooter :pagination="pagination" />
          </template>
      </ProjectProductNavigationWorkbench>
    </template>
  </TableBody>
  <ModalDialog ref="modalDialogRef" :title="data.actionTitle" @confirm="onDataForm">
    <template #content>
      <a-form :model="formModel">
        <a-form-item
          v-for="item of formItems"
          v-show="isFormItemVisible(item)"
          :key="item.key"
          :class="[item.required ? 'mango-form-item__require' : 'mango-form-item__no_require']"
          :label="getFormItemLabel(item)"
        >
          <template v-if="item.type === 'input'">
            <a-input v-model="item.value" :placeholder="item.placeholder" />
          </template>
          <template
            v-else-if="item.type === 'textarea' && item.key === 'value' && isCodePublicType"
          >
            <CodeEditor
              v-model="item.value"
              :line-height="260"
              :placeholder="item.placeholder"
              :code-style="{ width: '100%' }"
            />
          </template>
          <template v-else-if="item.type === 'textarea'">
            <a-textarea
              v-model="item.value"
              :auto-size="{ minRows: 3, maxRows: 5 }"
              :placeholder="item.placeholder"
            />
          </template>
          <template v-else-if="item.type === 'cascader'">
            <ProjectProductSelect
              v-model="item.value"
              :placeholder="item.placeholder"
              @change="onProjectProductChange"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'type'">
            <a-select
              v-model="item.value"
              :multiple="item.multiple"
              :max-tag-count="item.multiple ? 1 : undefined"
              :field-names="fieldNames"
              :options="enumStore.api_public_type"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              value-key="key"
              @change="onTypeChange"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'test_envs'">
            <a-select
              v-model="item.value"
              :field-names="fieldNames"
              :options="environmentOptions"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              multiple
              value-key="key"
              @change="onEnvironmentMultiChange(item)"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'datasource_alias'">
            <a-select
              v-if="isSqlPublicType"
              v-model="item.value"
              :multiple="item.multiple"
              :max-tag-count="item.multiple ? 1 : undefined"
              :options="datasourceAliasOptions"
              :field-names="{ value: 'id', label: 'name' }"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
            />
          </template>
        </a-form-item>
      </a-form>
    </template>
  </ModalDialog>
</template>

<script lang="ts" setup>
  import { formatProjectProductPath } from '@/utils/business-format'
  import { usePagination, useRowKey, useRowSelection, useTable } from '@/hooks/table'
  import { useLatestRequest } from '@/hooks/use-latest-request'
  import { ModalDialogType } from '@/types/components'
  import { Message, Modal } from '@arco-design/web-vue'
  import { computed, onMounted, ref, nextTick, reactive } from 'vue'
  import { getFormItems } from '@/utils/datacleaning'
  import { fieldNames } from '@/setting'
  import { tableColumns, formItems, conditionItems, tableScrollX } from './config'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import CodeEditor from '@/components/editors/CodeEditor.vue'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import ApiResourceSearchFilters from '@/components/business/ApiResourceSearchFilters.vue'
  import {
    deleteApiPublic,
    getApiPublic,
    postApiPublic,
    putApiPublic,
    putApiPublicPutStatus,
  } from '@/api/apitest/public'
  import { useEnum } from '@/store/modules/get-enum'
  import { getDataFactoryDatasourceAlias } from '@/api/data-factory'
  import { getUserName } from '@/api/user/user'
  import { prefillNavigationFormItems, NavigationCreateSource } from '@/utils/navigation-create-defaults'

  const navigationCreateRef = ref<NavigationCreateSource | null>(null)

  const enumStore = useEnum()
  const headerConditionItems = computed(() => conditionItems.filter((item) => item.key !== 'project_product'))
  const projectProductCondition = computed(() => conditionItems.find((item) => item.key === 'project_product'))
  const sidebarResetKey = ref(0)

  function onSidebarFilterChange({ projectProduct }: { projectProduct: string | number | null }) {
    if (projectProductCondition.value) projectProductCondition.value.value = projectProduct
    selectedRowKeys.value = []
    pagination.page = 1
    doRefresh(true)
  }
  const COMMON_ENV_VALUE = '__common__'

  const modalDialogRef = ref<ModalDialogType | null>(null)
  const pagination = usePagination(doRefresh, () => table.tableLoading)
  const { selectedRowKeys, onSelectionChange, showCheckedAll } = useRowSelection()
  const table = useTable()
  const { beginRequest, isLatestRequest } = useLatestRequest()
  const rowKey = useRowKey('id')
  const formModel = ref({})
  const datasourceAliasOptions = ref<any[]>([])
  const data = reactive({
    actionTitle: '新增',
    isAdd: false,
    updateId: 0,
    moduleList: [],
    userList: [],
  })

  const isSqlPublicType = computed(() => Number(getFormValue('type')) === 1)
  const isCodePublicType = computed(() => Number(getFormValue('type')) === 2)
  const environmentOptions = computed(() => [
    { key: COMMON_ENV_VALUE, title: '环境通用' },
    ...enumStore.environment_type,
  ])
  const codeVariableExample = `def variable(context):
    """
    函数名字和参数不可以改。
    必须返回 dict。
    dict 的 key 会作为变量 key，value 会作为变量值。
    接口执行时可以通过 \${tenant_id}、\${user_id} 引用。
    """
    return {
        "tenant_id": "14",
        "user_id": 123
    }`

  function getFormValue(key: string) {
    return formItems.find((it) => it.key === key)?.value
  }

  function setFormValue(key: string, value: any) {
    const item = formItems.find((it) => it.key === key)
    if (item) {
      item.value = value
    }
  }

  function getFormNumberValue(key: string) {
    const value = getFormValue(key)
    return value === '' || value == null ? null : Number(value)
  }

  function normalizeEnvironmentList(value: any) {
    return Array.isArray(value)
      ? value
      : value === null || value === undefined || value === ''
      ? []
      : [value]
  }

  function isCommonEnvironment(value: any) {
    return normalizeEnvironmentList(value).length === 0
  }

  function normalizeEnvironmentValues(value: any) {
    const list = normalizeEnvironmentList(value)
    if (list.length === 0 || list.includes(COMMON_ENV_VALUE)) {
      return []
    }
    return list.filter((it) => it !== null && it !== undefined && it !== '').map((it) => Number(it))
  }

  function toEnvironmentSelectValue(item: any) {
    const envs = normalizeEnvironmentList(item?.test_envs)
    if (envs.length > 0) {
      return envs
    }
    const oldValue = item?.test_env
    return isCommonEnvironment(oldValue) ? [COMMON_ENV_VALUE] : [oldValue]
  }

  function onEnvironmentMultiChange(item: any) {
    const value = normalizeEnvironmentList(item.value)
    if (value.length === 0) {
      item.value = [COMMON_ENV_VALUE]
    } else if (value.includes(COMMON_ENV_VALUE)) {
      item.value =
        value[value.length - 1] === COMMON_ENV_VALUE
          ? [COMMON_ENV_VALUE]
          : value.filter((it) => it !== COMMON_ENV_VALUE)
    }
  }

  function isFormItemVisible(item: any) {
    return item.key !== 'datasource_alias' || isSqlPublicType.value
  }

  function getFormItemLabel(item: any) {
    if (item.key === 'value' && isCodePublicType.value) {
      return '自定义代码'
    }
    return item.label
  }

  function fillCodeVariableExample() {
    const valueItem = formItems.find((it) => it.key === 'value')
    if (valueItem && !valueItem.value) {
      valueItem.value = codeVariableExample
    }
  }

  function clearCodeVariableExample() {
    const valueItem = formItems.find((it) => it.key === 'value')
    if (valueItem?.value === codeVariableExample) {
      valueItem.value = ''
    }
  }

  function loadDatasourceAliasOptions(projectProductId?: any) {
    const productId = projectProductId ?? getFormValue('project_product')
    datasourceAliasOptions.value = []
    if (!productId && productId !== 0) {
      return Promise.resolve()
    }
    return getDataFactoryDatasourceAlias({
      project_product: productId,
      status: 1,
      page: 1,
      pageSize: 999,
    }).then((res) => {
      datasourceAliasOptions.value = (res.data || []).filter(
        (item: any) => Number(item.status) === 1 && [0, 1, 2].includes(Number(item.db_type))
      )
    })
  }

  function onProjectProductChange(value: any) {
    setFormValue('datasource_alias', '')
    loadDatasourceAliasOptions(value)
  }

  function onTypeChange(value: any) {
    if (Number(value) !== 1) {
      setFormValue('datasource_alias', '')
    } else {
      loadDatasourceAliasOptions()
    }
    if (Number(value) === 2) {
      fillCodeVariableExample()
    } else {
      clearCodeVariableExample()
    }
  }

  function onSearchRefresh() {
    doRefresh(true)
  }

  function doRefresh(showLoading = false) {
    const requestId = beginRequest()
    if (showLoading) {
      table.tableLoading.value = true
    }
    let value = getFormItems(conditionItems)
    const filterEnvs = normalizeEnvironmentList(value.test_envs)
    if (filterEnvs.length > 0) {
      value.test_envs = filterEnvs.join(',')
    } else {
      delete value.test_envs
    }
    clearEmptyFilter(value, 'type')
    clearEmptyFilter(value, 'update_user')
    value['page'] = pagination.page
    value['pageSize'] = pagination.pageSize
    getApiPublic(value)
      .then((res) => {
        if (!isLatestRequest(requestId)) return
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
      })
      .catch((error) => {
        if (isLatestRequest(requestId)) console.log(error)
      })
      .finally(() => {
        if (isLatestRequest(requestId)) {
          table.tableLoading.value = false
        }
      })
  }

  function clearEmptyFilter(value: Record<string, any>, key: string) {
    if (value[key] === null || value[key] === '') {
      delete value[key]
    }
  }

  function onResetSearch() {
    conditionItems.forEach((it) => {
      it.value = it.multiple ? [] : ''
    })
    sidebarResetKey.value += 1
    doRefresh(true)
  }

  function onAdd() {
    data.actionTitle = '新增'
    data.isAdd = true
    modalDialogRef.value?.toggle()
    formItems.forEach((it) => {
      if (it.reset) {
        it.reset()
      } else {
        it.value = it.multiple ? [] : ''
      }
    })
    setFormValue('test_envs', [COMMON_ENV_VALUE])
    datasourceAliasOptions.value = []
    if (Number(getFormValue('type')) === 2) {
      fillCodeVariableExample()
    }
    void prefillNavigationFormItems(navigationCreateRef.value, formItems, () => data.isAdd)
      .then(() => { if (data.isAdd) loadDatasourceAliasOptions() })
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
      content: '是否要删除此参数？',
      cancelText: '取消',
      okText: '删除',
      onBeforeOk: () => {
        return deleteApiPublic(batch ? selectedRowKeys.value : record.id)
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
      loadDatasourceAliasOptions(item?.project_product?.id || item?.project_product)
      formItems.forEach((it) => {
        const propName = item[it.key]
        if (it.key === 'test_envs') {
          it.value = toEnvironmentSelectValue(item)
        } else if (typeof propName === 'object' && propName !== null) {
          it.value = propName.id
        } else {
          it.value = propName
        }
      })
    })
  }

  function onDataForm() {
    if (formItems.every((it) => (it.validator ? it.validator() : true))) {
      let value = getFormItems(formItems)
      value.test_envs = normalizeEnvironmentValues(value.test_envs)
      delete value.test_env
      if (Number(value.type) === 1 && !getFormNumberValue('datasource_alias')) {
        Message.error('SQL公共变量必须选择逻辑数据库')
        modalDialogRef.value?.setConfirmLoading(false)
        return
      }
      if (Number(value.type) !== 1) {
        value.datasource_alias = null
      }
      if (Number(value.type) === 2 && !value.value) {
        value.value = codeVariableExample
      }
      if (data.isAdd) {
        value['status'] = 1
        postApiPublic(value)
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
        putApiPublic(value)
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

  const onModifyStatus = async (newValue: boolean, id: number) => {
    return new Promise<any>((resolve, reject) => {
      setTimeout(async () => {
        try {
          let value: any = false
          await putApiPublicPutStatus(id, newValue ? 1 : 0)
            .then((res) => {
              Message.success(res.msg)
              value = res.code === 200
            })
            .catch(reject)
          resolve(value)
        } catch (error) {
          reject(error)
        }
      }, 300)
    })
  }

  function getNickName() {
    getUserName()
      .then((res) => {
        data.userList = res.data
      })
      .catch(console.log)
  }

  onMounted(() => {
    if (projectProductCondition.value) projectProductCondition.value.value = ''
    nextTick(async () => {
      doRefresh()
      getNickName()
    })
  })
</script>
