<template>
  <TableBody ref="tableBody">
    <template #header>
      <TableHeader
        :show-filter="true"
        title="Token授权管理"
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
              <template v-else-if="item.type === 'cascader'">
                <ProjectProductSelect
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  @change="onSearchRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'test_env'">
                <a-select
                  v-model="item.value"
                  :field-names="fieldNames"
                  :options="enumStore.environment_type"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
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
          <div>
            <a-space>
              <a-button size="small" type="primary" @click="onAdd">新增</a-button>
              <a-button size="small" status="danger" @click="onDelete(null)">批量删除</a-button>
            </a-space></div
          >
        </template>
      </a-tabs>
      <a-table
        :scroll="{ x: 1100 }"
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
            <template v-else-if="item.key === 'project_product'" #cell="{ record }">
              {{ formatProjectProductPath(record?.project_product) }}
            </template>
            <template v-else-if="item.key === 'test_env'" #cell="{ record }">
              <a-tag :color="enumStore.colors[record.test_env]" size="small">
                {{ enumStore.environment_type[record.test_env]?.title }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'auth_type'" #cell="{ record }">
              <a-tag :color="enumStore.colors[record.auth_type]" size="small">
                {{ enumStore.api_auth_type[record.auth_type]?.title }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'auth_source'" #cell="{ record }">
              <a-tooltip :content="getAuthSourceText(record)">
                <div class="auth-source-text">
                  {{ getAuthSourceText(record) }}
                </div>
              </a-tooltip>
            </template>
            <template v-else-if="item.key === 'refresh_mode'" #cell="{ record }">
              <a-tag :color="enumStore.colors[record.refresh_mode]" size="small">
                {{ enumStore.api_auth_refresh_mode[record.refresh_mode]?.title }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'time_task'" #cell="{ record }">
              <a-tooltip :content="getRefreshStrategyText(record)">
                <div class="auth-source-text">
                  {{ getRefreshStrategyText(record) }}
                </div>
              </a-tooltip>
            </template>
            <template v-else-if="item.key === 'last_refresh_status'" #cell="{ record }">
              <a-tag :color="enumStore.status_colors[record.last_refresh_status]" size="small">
                {{ enumStore.api_auth_refresh_status[record.last_refresh_status]?.title }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'status'" #cell="{ record }">
              <a-switch
                :beforeChange="(newValue) => onModifyStatus(newValue, record.id)"
                :default-checked="record.status === 1"
              />
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <MangoTableActions
                :actions="[
                  { label: '查看', onClick: () => onPreview(record) },
                  { label: '刷新', onClick: () => onRefresh(record) },
                  { label: '编辑', onClick: () => onUpdate(record) },
                  { label: '清空', onClick: () => onClear(record) },
                  { label: '删除', danger: true, onClick: () => onDelete(record) },
                ]"
              />
            </template>
          </a-table-column>
        </template>
      </a-table>
    </template>
    <template #footer>
      <TableFooter :pagination="pagination" />
    </template>
  </TableBody>

  <ModalDialog ref="modalDialogRef" :title="data.actionTitle" width="650px" @confirm="onDataForm">
    <template #content>
      <a-form :model="formModel">
        <a-form-item
          v-for="item of visibleFormItems"
          :key="item.key"
          :class="[item.required ? 'mango-form-item__require' : 'mango-form-item__no_require']"
          :label="item.label"
        >
          <template v-if="item.type === 'input'">
            <a-input v-model="item.value" :placeholder="item.placeholder" />
          </template>
          <template v-else-if="item.type === 'number'">
            <a-input-number v-model="item.value" :min="0" :placeholder="item.placeholder" />
          </template>
          <template v-else-if="item.type === 'cascader'">
            <ProjectProductSelect
              v-model="item.value"
              :placeholder="item.placeholder"
              @change="item.key === 'project_product' ? onFormProjectProductChange() : undefined"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'test_env'">
            <a-select
              v-model="item.value"
              :field-names="fieldNames"
              :options="enumStore.environment_type"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              value-key="key"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'auth_type'">
            <a-select
              v-model="item.value"
              :field-names="fieldNames"
              :options="enumStore.api_auth_type"
              :placeholder="item.placeholder"
              allow-clear
              value-key="key"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'api_info'">
            <a-select
              v-model="item.value"
              :options="data.apiInfoList"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'refresh_mode'">
            <a-select
              v-model="item.value"
              :field-names="fieldNames"
              :options="enumStore.api_auth_refresh_mode"
              :placeholder="item.placeholder"
              allow-clear
              value-key="key"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'time_task'">
            <a-select
              v-model="item.value"
              :options="data.timeTaskList"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
            />
          </template>
          <template v-else-if="item.type === 'code'">
            <CodeEditor
              v-model="item.value"
              :line-height="220"
              :placeholder="item.placeholder"
              :code-style="{ width: '100%' }"
            />
          </template>
        </a-form-item>
      </a-form>
    </template>
  </ModalDialog>

  <a-drawer
    v-model:visible="cacheModal.visible"
    title="授权缓存"
    width="50%"
    :footer="false"
    unmount-on-close
  >
    <div class="cache-drawer-body">
      <a-descriptions v-if="cacheModal.data" :column="1" bordered>
        <a-descriptions-item label="授权名称">{{ cacheModal.data.name }}</a-descriptions-item>
        <a-descriptions-item label="过期时间">{{
          cacheModal.data.expires_at || '-'
        }}</a-descriptions-item>
        <a-descriptions-item label="剩余分钟">{{
          cacheModal.data.remaining_minutes ?? '-'
        }}</a-descriptions-item>
        <a-descriptions-item label="最近刷新时间">
          {{ cacheModal.data.last_refresh_time || '-' }}
        </a-descriptions-item>
        <a-descriptions-item label="最近错误">
          {{ cacheModal.data.last_refresh_error || '-' }}
        </a-descriptions-item>
      </a-descriptions>
      <div v-if="cacheModal.data" class="cache-json-section">
        <div class="cache-json-title">缓存数据</div>
        <JsonDisplay :data="cacheModal.data.cache_data || {}" />
      </div>
    </div>
  </a-drawer>
</template>

<script lang="ts" setup>
  import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import { usePagination, useRowKey, useRowSelection, useTable } from '@/hooks/table'
  import { ModalDialogType } from '@/types/components'
  import { getFormItems } from '@/utils/datacleaning'
  import { fieldNames } from '@/setting'
  import { useEnum } from '@/store/modules/get-enum'
  import useUserStore from '@/store/modules/user'
  import CodeEditor from '@/components/editors/CodeEditor.vue'
  import JsonDisplay from '@/components/display/JsonDisplay.vue'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import { formatProjectProductPath } from '@/utils/business-format'
  import { getApiInfo } from '@/api/apitest/info'
  import { getSystemTimingList } from '@/api/system/time'
  import { conditionItems, formItems, tableColumns } from './config'
  import {
    deleteApiAuthConfig,
    getApiAuthConfig,
    getApiAuthConfigCache,
    postApiAuthConfig,
    postApiAuthConfigClear,
    postApiAuthConfigRefresh,
    putApiAuthConfig,
    putApiAuthConfigStatus,
  } from '@/api/apitest/auth-config'

  const enumStore = useEnum()
  const userStore = useUserStore()
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const pagination = usePagination(doRefresh)
  const { selectedRowKeys, onSelectionChange, showCheckedAll } = useRowSelection()
  const table = useTable()
  const rowKey = useRowKey('id')
  const formModel = ref({})
  const data = reactive({
    actionTitle: '新增',
    isAdd: false,
    updateId: 0,
    apiInfoList: [] as any[],
    timeTaskList: [] as any[],
  })
  const cacheModal = reactive({
    visible: false,
    data: null as any,
  })
  const customAuthCodeExample = `def auth(context):
    """
    函数名字，参数都不可以改。
    必须返回 dict。
    dict 的 key 会作为缓存 key，value 会作为缓存值。
    接口执行时可以通过 \${token}、\${tenant_id} 引用。
    """
    return {
        "token": "your_token",
        "tenant_id": "your_tenant_id"
    }`

  const authTypeItem = computed(() => formItems.find((it) => it.key === 'auth_type'))
  const refreshModeItem = computed(() => formItems.find((it) => it.key === 'refresh_mode'))
  const projectProductItem = computed(() => formItems.find((it) => it.key === 'project_product'))
  const isExecutionCheckRefreshMode = computed(() => [0, 2].includes(refreshModeItem.value?.value))
  const visibleFormItems = computed(() => {
    return formItems.filter((it) => {
      if (it.key === 'api_info') {
        return authTypeItem.value?.value === 0
      }
      if (it.key === 'custom_code') {
        return authTypeItem.value?.value === 1
      }
      if (it.key === 'token_ttl' || it.key === 'refresh_margin') {
        return isExecutionCheckRefreshMode.value
      }
      if (it.key === 'time_task') {
        return [1, 2].includes(refreshModeItem.value?.value)
      }
      return true
    })
  })

  function onSearchRefresh() {
    doRefresh(true)
  }

  function doRefresh(showLoading = false) {
    if (showLoading) {
      table.tableLoading.value = true
    }
    const value = getFormItems(conditionItems)
    value['page'] = pagination.page
    value['pageSize'] = pagination.pageSize
    return getApiAuthConfig(value)
      .then((res) => {
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
      })
      .catch(console.log)
      .finally(() => {
        if (showLoading) {
          table.tableLoading.value = false
        }
      })
  }

  function refreshTable() {
    selectedRowKeys.value = []
    return doRefresh()
  }

  function onResetSearch() {
    conditionItems.forEach((it) => {
      it.value = ''
    })
    doRefresh(true)
  }

  function resetFormItems() {
    formItems.forEach((it) => {
      if (it.reset) {
        it.reset()
      } else if (it.key === 'auth_type' || it.key === 'refresh_mode') {
        it.value = 0
      } else if (it.key === 'token_ttl') {
        it.value = 1440
      } else if (it.key === 'refresh_margin') {
        it.value = 5
      } else if (it.key === 'custom_code') {
        it.value = customAuthCodeExample
      } else {
        it.value = ''
      }
    })
    const envItem = formItems.find((it) => it.key === 'test_env')
    if (envItem && userStore.selected_environment != null) {
      envItem.value = userStore.selected_environment
    }
    data.apiInfoList = []
  }

  function onAdd() {
    data.actionTitle = '新增'
    data.isAdd = true
    resetFormItems()
    modalDialogRef.value?.toggle()
  }

  function fillCustomCodeExample() {
    const customCodeItem = formItems.find((it) => it.key === 'custom_code')
    if (customCodeItem && !customCodeItem.value) {
      customCodeItem.value = customAuthCodeExample
    }
  }

  function onUpdate(item: any) {
    data.actionTitle = '编辑'
    data.isAdd = false
    data.updateId = item.id
    modalDialogRef.value?.toggle()
    nextTick(() => {
      formItems.forEach((it) => {
        const propName = item[it.key]
        if (Array.isArray(propName)) {
          it.value = [...propName]
        } else if (typeof propName === 'object' && propName !== null) {
          it.value = propName.id
        } else {
          it.value = propName
        }
      })
      getApiInfoList(item.project_product?.id || item.project_product)
    })
  }

  function onFormProjectProductChange() {
    nextTick(() => {
      const apiInfoItem = formItems.find((it) => it.key === 'api_info')
      if (apiInfoItem) {
        apiInfoItem.value = ''
      }
      getApiInfoList(projectProductItem.value?.value)
    })
  }

  function validateVisibleForm() {
    const authType = authTypeItem.value?.value
    const refreshMode = refreshModeItem.value?.value
    if (authType === 0 && !formItems.find((it) => it.key === 'api_info')?.value) {
      Message.error('请选择登录接口')
      return false
    }
    if (authType === 1 && !formItems.find((it) => it.key === 'custom_code')?.value) {
      Message.error('请输入自定义授权代码')
      return false
    }
    if ([1, 2].includes(refreshMode) && !formItems.find((it) => it.key === 'time_task')?.value) {
      Message.error('请选择定时策略')
      return false
    }
    return visibleFormItems.value.every((it) => (it.validator ? it.validator() : true))
  }

  function normalizeSubmitValue(value: any) {
    if (value.auth_type === 0) {
      value.custom_code = null
    } else {
      value.api_info = null
    }
    if (![1, 2].includes(value.refresh_mode)) {
      value.time_task = null
    }
    return value
  }

  function getAuthSourceText(record: any) {
    if (record.auth_type === 0) {
      const apiInfo = record.api_info
      if (!apiInfo) return '-'
      const method = apiInfo.method !== undefined && apiInfo.method !== null
        ? enumStore.api_method?.[apiInfo.method]?.title || apiInfo.method
        : ''
      const url = apiInfo.url ? ` ${apiInfo.url}` : ''
      return `${apiInfo.name || '-'}${method ? ` / ${method}` : ''}${url}`
    }
    if (record.auth_type === 1) {
      return record.custom_code || '-'
    }
    return '-'
  }

  function getRefreshStrategyText(record: any) {
    const tokenStrategy = `有效期${record.token_ttl ?? '-'}分钟，提前${record.refresh_margin ?? '-'}分钟刷新`
    const timeTaskStrategy = record.time_task?.name ? `定时策略：${record.time_task.name}` : '定时策略：-'
    if (record.refresh_mode === 0) {
      return tokenStrategy
    }
    if (record.refresh_mode === 1) {
      return timeTaskStrategy
    }
    if (record.refresh_mode === 2) {
      return `${timeTaskStrategy}；${tokenStrategy}`
    }
    if (record.refresh_mode === 3) {
      return '手动刷新'
    }
    return '-'
  }

  function onDataForm() {
    if (!validateVisibleForm()) {
      modalDialogRef.value?.setConfirmLoading(false)
      return
    }
    const value = normalizeSubmitValue(getFormItems(formItems))
    if (data.isAdd) {
      value['status'] = 1
      postApiAuthConfig(value)
        .then((res) => {
          modalDialogRef.value?.toggle()
          Message.success(res.msg)
          refreshTable()
        })
        .catch(console.log)
        .finally(() => modalDialogRef.value?.setConfirmLoading(false))
    } else {
      value['id'] = data.updateId
      putApiAuthConfig(value)
        .then((res) => {
          modalDialogRef.value?.toggle()
          Message.success(res.msg)
          refreshTable()
        })
        .catch(console.log)
        .finally(() => modalDialogRef.value?.setConfirmLoading(false))
    }
  }

  function onDelete(record: any) {
    const batch = record === null
    if (batch && selectedRowKeys.value.length === 0) {
      Message.error('请选择要删除的数据')
      return
    }
    Modal.confirm({
      title: '提示',
      content: '是否要删除此授权配置？',
      cancelText: '取消',
      okText: '删除',
      onBeforeOk: () => {
        return deleteApiAuthConfig(batch ? selectedRowKeys.value : record.id)
          .then((res) => Message.success(res.msg))
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

  function onPreview(record: any) {
    getApiAuthConfigCache(record.id)
      .then((res) => {
        cacheModal.data = res.data
        cacheModal.visible = true
      })
      .catch(console.log)
  }

  function onRefresh(record: any) {
    postApiAuthConfigRefresh(record.id)
      .then((res) => {
        Message.success(res.msg)
        cacheModal.data = res.data
        cacheModal.visible = true
        doRefresh()
      })
      .catch(console.log)
  }

  function onClear(record: any) {
    postApiAuthConfigClear(record.id)
      .then((res) => {
        Message.success(res.msg)
        doRefresh()
      })
      .catch(console.log)
  }

  const onModifyStatus = async (newValue: boolean, id: number) => {
    return new Promise<any>((resolve, reject) => {
      setTimeout(async () => {
        try {
          let value: any = false
          await putApiAuthConfigStatus(id, newValue ? 1 : 0)
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

  function getApiInfoList(projectProductId?: any) {
    if (!projectProductId) {
      data.apiInfoList = []
      return
    }
    getApiInfo({ project_product: projectProductId, page: 1, pageSize: 10000 })
      .then((res) => {
        data.apiInfoList = (res.data || []).map((item: any) => ({
          label: `${item.id} - ${item.name}`,
          value: item.id,
        }))
      })
      .catch(console.log)
  }

  function getTiming() {
    getSystemTimingList()
      .then((res) => {
        data.timeTaskList = (res.data || []).map((item: any) => ({
          label: item.title,
          value: item.key,
        }))
      })
      .catch(console.log)
  }

  watch(
    () => authTypeItem.value?.value,
    (value) => {
      if (value === 1) {
        fillCustomCodeExample()
      }
    }
  )

  onMounted(() => {
    nextTick(() => {
      getTiming()
      doRefresh()
    })
  })
</script>

<style scoped>
  .cache-drawer-body {
    height: 100%;
    overflow: auto;
  }

  .cache-json-section {
    margin-top: 16px;
  }

  .cache-json-title {
    margin-bottom: 8px;
    color: var(--m-text);
    font-weight: 500;
  }

  .auth-source-text {
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
</style>
