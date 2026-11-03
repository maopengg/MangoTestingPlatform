<template>
  <TableBody ref="tableBody" plain class="mango-detail-workbench-page">
    <template #header>
      <TableHeader title="测试对象" />
    </template>
    <template #default>
      <ProjectProductNavigationWorkbench
        ref="navigationCreateRef"
        contained-body
        :model-value="projectProductCondition?.value"
        :reset-key="sidebarResetKey"
        emit-initial-filter
        @filter-change="onSidebarFilterChange"
        @search="doRefresh"
        @reset-search="onResetSearch"
      >
        <template #search>
          <a-form layout="inline" :model="{}" @keyup.enter="doRefresh">
            <a-form-item v-for="item of headerConditionItems" :key="item.key" :label="item.label">
              <template v-if="item.type === 'input'">
                <a-input
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  allow-clear
                  @blur="doRefresh"
                  @clear="doRefresh"
                />
              </template>
              <template v-else-if="item.type === 'cascader' && item.key === 'project_product'">
                <ProjectProductSelect
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  @change="doRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'environment'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :placeholder="item.placeholder"
                  :options="enumStore.environment_type"
                  :field-names="fieldNames"
                  value-key="key"
                  allow-clear
                  allow-search
                  @change="doRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'auto_type'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :placeholder="item.placeholder"
                  :options="enumStore.auto_type"
                  :field-names="fieldNames"
                  value-key="key"
                  allow-clear
                  allow-search
                  @change="doRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'update_user'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :field-names="fieldNames"
                  :options="item.optionItems"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="doRefresh"
                />
              </template>
              <template v-if="item.type === 'date'">
                <a-date-picker v-model="item.value" />
              </template>
              <template v-if="item.type === 'time'">
                <a-time-picker v-model="item.value" value-format="HH:mm:ss" />
              </template>
              <template v-if="item.type === 'check-group'">
                <a-checkbox-group v-model="item.value">
                  <a-checkbox v-for="it of item.optionItems" :value="it.value" :key="it.value">
                    {{ item.label }}
                  </a-checkbox>
                </a-checkbox-group>
              </template>
            </a-form-item>
          </a-form>
        </template>
        <template #toolbar>
          <a-space>
            <div>
              <a-button
                type="primary"
                size="small"
                @click="onAdd"
                data-testid="qa-views-config-test-object-button-新增"
                >新增</a-button
              >
            </div>
          </a-space>
        </template>
        <a-table
          class="mango-native-scroll-table"
          :scroll="{ x: 1020, y: '100%' }"
          :bordered="false"
          :loading="table.tableLoading.value"
          :data="table.dataList"
          :columns="tableColumns"
          :pagination="false"
          :rowKey="rowKey"
          @selection-change="onSelectionChange"
        >
          <template #columns>
            <a-table-column
              v-for="item of tableColumns"
              :key="item.key"
              :align="item.align"
              :title="item.title"
              :width="item.width"
              :data-index="item.key"
              :fixed="item.fixed"
              :ellipsis="item.ellipsis"
              :tooltip="item.tooltip"
            >
              <template v-if="item.key === 'index'" #cell="{ record }">
                {{ record.id }}
              </template>
              <template v-else-if="item.key === 'auto_type'" #cell="{ record }">
                <a-tag :color="enumStore.colors[record.auto_type]" size="small"
                  >{{ enumStore.auto_type[record.auto_type]?.title || '-' }}
                </a-tag>
              </template>
              <template v-else-if="item.key === 'value'" #cell="{ record }">
                <TestTargetDisplay :value="record.value" :config="record.target_config" />
              </template>
              <template v-else-if="item.key === 'project_product'" #cell="{ record }">
                {{ formatProjectProductPath(record.project_product) }}
              </template>
              <template v-else-if="item.key === 'update_user'" #cell="{ record }">
                {{ record.update_user?.name || record.update_user?.username || '-' }}
              </template>
              <template v-else-if="item.key === 'environment'" #cell="{ record }">
                <a-tag :color="enumStore.colors[record.environment]" size="small">
                  {{ enumStore.environment_type.find((item) => String(item.key) === String(record.environment))?.title || '-' }}
                </a-tag>
              </template>
              <template v-else-if="item.key === 'actions'" #cell="{ record }">
                <MangoTableActions
                  :actions="[
    { label: '测试', hidden: !record.network_test_addresses?.length, onClick: () => connectionDialog?.open(record) },
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
  <ModalDialog
    ref="modalDialogRef"
    :title="data.actionTitle"
    width="min(760px, calc(100vw - 32px))"
    @confirm="onDataForm"
  >
    <template #content>
      <a-form :model="formModel" layout="horizontal" class="mango-target-editor">
        <section class="mango-target-editor__section">
          <header class="mango-target-editor__heading">
            <strong>基础信息</strong>
            <span>设置所属项目产品、环境及自动化类型</span>
          </header>
          <div class="mango-target-editor__grid">
            <a-form-item
              :class="[item.required ? 'mango-form-item__require' : 'mango-form-item__no_require']"
              :label="item.label"
              v-for="item of formItems"
              :key="item.key"
            >
              <template v-if="item.type === 'input'">
                <a-input :placeholder="item.placeholder" v-model="item.value" />
              </template>
              <template v-else-if="item.type === 'cascader'">
                <ProjectProductSelect v-model="item.value" :placeholder="item.placeholder" />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'environment'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :placeholder="item.placeholder"
                  :options="enumStore.environment_type"
                  :field-names="fieldNames"
                  value-key="key"
                  allow-clear
                  allow-search
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'auto_type'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :placeholder="item.placeholder"
                  :options="enumStore.auto_type"
                  :field-names="fieldNames"
                  value-key="key"
                  allow-clear
                  allow-search
                />
              </template>
            </a-form-item>
          </div>
        </section>
        <section class="mango-target-editor__section">
          <header class="mango-target-editor__heading">
            <strong>被测对象</strong>
            <span>配置默认地址，按缓存中的条件值匹配不同地址</span>
          </header>
          <template v-if="legacyMode">
            <a-form-item label="历史地址">
              <a-input v-model="legacyValue" placeholder="域名/包名/路径" />
            </a-form-item>
            <a-form-item label="地址配置">
              <a-button size="small" @click="useNewTargetConfig">切换为变量映射配置</a-button>
            </a-form-item>
          </template>
          <TestTargetEditor v-else v-model="targetConfig" />
        </section>
      </a-form>
    </template>
  </ModalDialog>
  <TestConnectionDialog ref="connectionDialog" />
</template>

<script lang="ts" setup>
  import { usePagination, useRowKey, useRowSelection, useTable } from '@/hooks/table'
  import { useLatestRequest } from '@/hooks/use-latest-request'
  import { ModalDialogType } from '@/types/components'
  import { Message, Modal } from '@arco-design/web-vue'
  import { computed, onMounted, ref, nextTick, reactive } from 'vue'
  import { getFormItems } from '@/utils/datacleaning'
  import { fieldNames } from '@/setting'
  import { conditionItems, formItems, tableColumns } from './config'
  import {
    deleteUserTestObject,
    getUserTestObject,
    postUserTestObject,
    putUserTestObject,
  } from '@/api/system/test_object'
  import { getUserName } from '@/api/user/user'
  import { useEnum } from '@/store/modules/get-enum'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import { formatProjectProductPath, getOptionId } from '@/utils/business-format'
  import { setUpdateUserOptions } from '@/utils/update-user'
  import TestTargetEditor from './components/TestTargetEditor.vue'
  import TestTargetDisplay from './components/TestTargetDisplay.vue'
  import TestConnectionDialog from './components/TestConnectionDialog.vue'
  import { emptyTargetConfig, validateTargetConfig } from './target-config'
  import { prefillNavigationFormItems, NavigationCreateSource } from '@/utils/navigation-create-defaults'

  const navigationCreateRef = ref<NavigationCreateSource | null>(null)

  const enumStore = useEnum()

  const modalDialogRef = ref<ModalDialogType | null>(null)
  const connectionDialog = ref<InstanceType<typeof TestConnectionDialog> | null>(null)
  const pagination = usePagination(doRefresh, () => table.tableLoading)
  const { onSelectionChange } = useRowSelection()
  const table = useTable()
  const { beginRequest, isLatestRequest } = useLatestRequest()
  const rowKey = useRowKey('id')
  const sidebarResetKey = ref(0)
  const projectProductCondition = computed(() =>
    conditionItems.find((item) => item.key === 'project_product')
  )
  const headerConditionItems = computed(() =>
    conditionItems.filter((item) => item.key !== 'project_product')
  )
  const formModel = ref({})
  const legacyMode = ref(false)
  const legacyValue = ref('')
  const targetConfig = ref(emptyTargetConfig())

  function useNewTargetConfig() {
    targetConfig.value = { ...emptyTargetConfig(), default: legacyValue.value }
    legacyMode.value = false
  }
  const data = reactive({
    isAdd: false,
    updateId: 0,
    actionTitle: '新增',
  })

  function onResetSearch() {
    conditionItems.forEach((it) => {
      it.value = it.multiple ? [] : ''
    })
    sidebarResetKey.value += 1
    doRefresh()
  }

  function onAdd() {
    legacyMode.value = false
    legacyValue.value = ''
    targetConfig.value = emptyTargetConfig()
    data.actionTitle = '新增测试对象'
    data.isAdd = true
    modalDialogRef.value?.toggle()
    formItems.forEach((it) => {
      if (it.reset) {
        it.reset()
      } else {
        it.value = it.multiple ? [] : ''
      }
    })
    void prefillNavigationFormItems(navigationCreateRef.value, formItems, () => data.isAdd)
  }

  function onDelete(record: any) {
    Modal.confirm({
      title: '提示',
      content: '是否要删除此测试环境？',
      cancelText: '取消',
      okText: '删除',
      onBeforeOk: () => {
        return deleteUserTestObject(record.id)
          .then((res) => {
            Message.success(res.msg)
          })
          .catch(console.log)
          .finally(() => {
            doRefresh()
          })
      },
    })
  }

  function onUpdate(item: any) {
    legacyValue.value = item.value || ''
    legacyMode.value = Boolean(item.value)
    targetConfig.value = structuredClone(item.target_config || emptyTargetConfig())
    data.actionTitle = '编辑测试对象'
    data.isAdd = false
    data.updateId = item.id
    modalDialogRef.value?.toggle()
    nextTick(() => {
      formItems.forEach((it) => {
        const propName = item[it.key]
        if (typeof propName === 'object' && propName !== null) {
          if (propName.name) {
            it.value = propName.id
          } else {
            it.value = propName.id
          }
        } else {
          it.value = propName
        }
      })
    })
  }

  function onDataForm() {
    const error = legacyMode.value
      ? legacyValue.value
        ? ''
        : '请填写历史地址'
      : validateTargetConfig(targetConfig.value)
    if (error) {
      Message.error(error)
      modalDialogRef.value?.setConfirmLoading(false)
      return
    }
    if (formItems.every((it) => (it.validator ? it.validator() : true))) {
      let value = getFormItems(formItems)
      value.value = legacyMode.value ? legacyValue.value : ''
      if (!legacyMode.value) value.target_config = targetConfig.value
      if (data.isAdd) {
        postUserTestObject(value)
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
        putUserTestObject(value)
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

  function doRefresh() {
    const requestId = beginRequest()
    table.tableLoading.value = true
    let value = getFormItems(conditionItems)
    value['project_product'] = getOptionId(value['project_product'])
    clearEmptyFilter(value, 'project_product')
    clearEmptyFilter(value, 'environment')
    clearEmptyFilter(value, 'auto_type')
    clearEmptyFilter(value, 'update_user')
    value['page'] = pagination.page
    value['pageSize'] = pagination.pageSize
    getUserTestObject(value)
      .then((res) => {
        if (!isLatestRequest(requestId)) return
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
      })
      .catch((error) => {
        if (isLatestRequest(requestId)) console.log(error)
      })
      .finally(() => {
        if (isLatestRequest(requestId)) table.tableLoading.value = false
      })
  }

  function onSidebarFilterChange(filter: { projectProduct: any }) {
    if (projectProductCondition.value) projectProductCondition.value.value = filter.projectProduct
    pagination.page = 1
    doRefresh()
  }

  function clearEmptyFilter(value: Record<string, any>, key: string) {
    if (value[key] === null || value[key] === '' || value[key] === undefined) {
      delete value[key]
    }
  }

  function loadUpdateUserOptions() {
    getUserName()
      .then((res) => {
        const users = res.data || []
        setUpdateUserOptions(conditionItems, users)
      })
      .catch(console.log)
  }

  onMounted(() => {
    nextTick(async () => {
      loadUpdateUserOptions()
    })
  })
</script>

<style scoped>
  .mango-target-editor {
    padding: 0 4px;
  }
  .mango-target-editor__section {
    padding: 20px 0 4px;
    border-bottom: 1px solid var(--m-border);
  }
  .mango-target-editor__section:first-child {
    padding-top: 4px;
  }
  .mango-target-editor__section:last-child {
    border-bottom: 0;
  }
  .mango-target-editor__heading {
    display: flex;
    align-items: baseline;
    flex-wrap: wrap;
    gap: 8px 12px;
    margin-bottom: 20px;
  }
  .mango-target-editor__heading strong {
    color: var(--m-text);
    font-size: 15px;
    font-weight: 600;
  }
  .mango-target-editor__heading span {
    color: var(--m-muted);
    font-size: 13px;
  }
  .mango-target-editor__grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    column-gap: 24px;
  }
  .mango-target-editor :deep(.arco-form-item) {
    margin-bottom: 16px;
  }
  .mango-target-editor :deep(.arco-form-item-label-col) {
    width: 112px !important;
    max-width: 112px !important;
    flex: 0 0 112px !important;
    padding-right: 12px;
  }
  .mango-target-editor :deep(.arco-form-item-wrapper-col) {
    min-width: 0;
    max-width: none !important;
    flex: 1 1 0 !important;
  }
  .mango-target-editor :deep(.arco-form-item-content-flex) {
    width: 100%;
  }
  @media (max-width: 760px) {
    .mango-target-editor__grid {
      grid-template-columns: minmax(0, 1fr);
    }
  }
</style>
