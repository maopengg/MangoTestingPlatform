<template>
  <TableBody>
    <template #header>
      <TableHeader title="数据工厂 / 执行记录" @search="doRefresh" @reset-search="onResetSearch">
        <template #search-content>
          <a-form :model="{}" layout="inline" @keyup.enter="doRefresh">
            <a-form-item
              v-for="item of executionConditionItems"
              :key="item.key"
              :label="item.label"
            >
              <template v-if="item.type === 'input'">
                <a-input v-model="item.value" :placeholder="item.placeholder" @blur="doRefresh" />
              </template>
              <template v-else-if="item.type === 'cascader' && item.key === 'project_product'">
                <a-cascader
                  v-model="item.value"
                  :options="projectInfo.projectProduct"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  style="width: 150px"
                  value-key="key"
                  @change="onSearchProjectChange(item.value)"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'module'">
                <a-select
                  v-model="item.value"
                  :field-names="enumFieldNames"
                  :options="productModule.data"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  style="width: 150px"
                  value-key="key"
                  @change="doRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'stage'">
                <a-select
                  v-model="item.value"
                  :field-names="enumFieldNames"
                  :options="enumStore.data_factory_execution_stage"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  style="width: 120px"
                  value-key="key"
                  @change="doRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'status'">
                <a-select
                  v-model="item.value"
                  :field-names="enumFieldNames"
                  :options="enumStore.data_factory_execution_status"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  style="width: 120px"
                  value-key="key"
                  @change="doRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'cleanup_status'">
                <a-select
                  v-model="item.value"
                  :field-names="enumFieldNames"
                  :options="enumStore.data_factory_cleanup_status"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  style="width: 140px"
                  value-key="key"
                  @change="doRefresh"
                />
              </template>
            </a-form-item>
          </a-form>
        </template>
      </TableHeader>
    </template>

    <template #default>
      <a-table
        :columns="executionTableColumns"
        :data="table.dataList"
        :loading="table.tableLoading.value"
        :pagination="false"
        :row-key="'id'"
      >
        <template #columns>
          <a-table-column
            v-for="item of executionTableColumns"
            :key="item.key"
            :align="item.align"
            :data-index="item.key"
            :fixed="item.fixed"
            :ellipsis="item.ellipsis"
            :tooltip="item.tooltip"
            :title="item.title"
            :width="item.width"
          >
            <template v-if="item.key === 'index'" #cell="{ record }">
              {{ record.id }}
            </template>
            <template v-else-if="item.key === 'project_product'" #cell="{ record }">
              {{ record?.project_product?.project?.name + '/' + record?.project_product?.name }}
            </template>
            <template v-else-if="item.key === 'module'" #cell="{ record }">
              {{ record?.module?.superior_module ? record?.module?.superior_module + '/' : ''
              }}{{ record?.module?.name }}
            </template>
            <template v-else-if="item.key === 'stage'" #cell="{ record }">
              <a-tag :color="enumStore.colors[record.stage]" size="small">
                {{ enumTitle(enumStore.data_factory_execution_stage, record.stage) }}</a-tag
              >
            </template>
            <template v-else-if="item.key === 'status'" #cell="{ record }">
              <a-tag :color="enumStore.status_colors[record.status]" size="small">
                {{ enumTitle(enumStore.data_factory_execution_status, record.status) }}</a-tag
              >
            </template>
            <template v-else-if="item.key === 'cleanup_status'" #cell="{ record }">
              <a-tag :color="enumStore.colors[record.cleanup_status]" size="small">{{
                enumTitle(enumStore.data_factory_cleanup_status, record.cleanup_status)
              }}</a-tag>
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <a-space>
                <a-button
                  :loading="actionLoading === `detail-${record.id}`"
                  size="mini"
                  type="text"
                  class="custom-mini-btn"
                  @click="openDetail(record)"
                  >详情</a-button
                >
                <a-button
                  :loading="actionLoading === `cleanup-${record.id}`"
                  size="mini"
                  status="danger"
                  type="text"
                  class="custom-mini-btn"
                  @click="cleanup(record)"
                  >清理</a-button
                >
              </a-space>
            </template>
          </a-table-column>
        </template>
      </a-table>
    </template>

    <template #footer><TableFooter :pagination="pagination" /></template>
  </TableBody>

  <a-drawer v-model:visible="detailVisible" title="执行详情" width="860px">
    <a-tabs>
      <a-tab-pane key="context" title="上下文">
        <a-textarea
          :model-value="JSON.stringify(detail.context || {}, null, 2)"
          :auto-size="{ minRows: 18, maxRows: 28 }"
          readonly
        />
      </a-tab-pane>
      <a-tab-pane key="items" title="创建明细">
        <a-table
          :columns="executionItemColumns"
          :data="detail.items || []"
          :pagination="false"
          :scroll="{ x: 1200 }"
        >
          <template #columns>
            <a-table-column
              v-for="item of executionItemColumns"
              :key="item.key"
              :align="item.align"
              :data-index="item.key"
              :ellipsis="item.ellipsis"
              :tooltip="item.tooltip"
              :title="item.title"
              :width="item.width"
            >
              <template v-if="item.key === 'index'" #cell="{ record }">
                {{ record.id }}
              </template>
              <template v-else-if="item.key === 'cleanup_status'" #cell="{ record }">
                {{ enumTitle(enumStore.data_factory_cleanup_status, record.cleanup_status) }}
              </template>
              <template v-else-if="item.key === 'data'" #cell="{ record }">
                <a-typography-paragraph copyable>{{
                  JSON.stringify(record.data)
                }}</a-typography-paragraph>
              </template>
            </a-table-column>
          </template>
        </a-table>
      </a-tab-pane>
      <a-tab-pane key="error" title="错误">
        <a-alert v-if="detail.execution?.error_message" type="error">{{
          detail.execution.error_message
        }}</a-alert>
        <a-empty v-else description="暂无错误" />
      </a-tab-pane>
    </a-tabs>
  </a-drawer>
</template>

<script lang="ts" setup>
  import {
    getDataFactoryExecution,
    getDataFactoryExecutionDetail,
    postDataFactoryExecutionCleanup,
  } from '@/api/data-factory'
  import { usePagination, useTable } from '@/hooks/table'
  import { useEnum } from '@/store/modules/get-enum'
  import { useProject } from '@/store/modules/get-project'
  import { useProductModule } from '@/store/modules/project_module'
  import { getFormItems } from '@/utils/datacleaning'
  import { Message, Modal } from '@arco-design/web-vue'
  import { onMounted, ref } from 'vue'
  import { executionConditionItems, executionItemColumns, executionTableColumns } from './config'

  const table = useTable()
  const pagination = usePagination(doRefresh)
  const enumStore = useEnum()
  const projectInfo = useProject()
  const productModule = useProductModule()
  const enumFieldNames = { value: 'key', label: 'title' }
  const detailVisible = ref(false)
  const detail = ref<any>({})
  const actionLoading = ref('')

  function enumTitle(options: any[] = [], value: any) {
    return options.find((it) => it.key === value)?.title || value
  }

  function getOptionId(value: any) {
    return value?.id ?? value
  }

  function getSearchItem(key: string) {
    return executionConditionItems.find((item) => item.key === key)
  }

  function onSearchProjectChange(value: any) {
    const moduleItem = getSearchItem('module')
    if (moduleItem) {
      moduleItem.value = ''
    }
    productModule.getProjectModule(getOptionId(value))
    doRefresh()
  }

  function doRefresh() {
    table.tableLoading.value = true
    const query = getFormItems(executionConditionItems)
    getDataFactoryExecution({
      ...query,
      page: pagination.page,
      pageSize: pagination.pageSize,
    }).then((res) => {
      table.handleSuccess(res)
      pagination.setTotalSize((res as any).totalSize)
    })
  }

  function onResetSearch() {
    executionConditionItems.forEach((it) => {
      it.value = ''
    })
    doRefresh()
  }

  function openDetail(record: any) {
    actionLoading.value = `detail-${record.id}`
    getDataFactoryExecutionDetail({ execution_id: record.id })
      .then((res) => {
        detail.value = res.data || {}
        detailVisible.value = true
      })
      .finally(() => {
        actionLoading.value = ''
      })
  }

  function cleanup(record: any) {
    if (record.cleanup_status === 1) {
      Message.info('当前执行记录已清理，无需重复清理')
      return
    }
    Modal.confirm({
      title: '清理执行数据',
      content: `确认清理 ${record.execution_no} 创建的数据？`,
      onOk: () => {
        actionLoading.value = `cleanup-${record.id}`
        return postDataFactoryExecutionCleanup({ execution_id: record.id })
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .finally(() => {
            actionLoading.value = ''
          })
      },
    })
  }

  onMounted(() => {
    enumStore.getEnum()
    projectInfo.projectProductName()
    productModule.getProjectModule()
    doRefresh()
  })
</script>
