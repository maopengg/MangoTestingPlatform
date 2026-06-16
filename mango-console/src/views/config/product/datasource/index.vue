<template>
  <TableBody ref="tableBody" class="mango-detail-workbench-page">
    <template #header>
      <div class="mango-detail-toolbar">
        <div class="mango-detail-heading">
          <div class="mango-detail-title">{{ datasourceDetailTitle }}</div>
          <div class="mango-detail-subtitle">维护当前产品下稳定的业务数据库名称，环境绑定在测试对象数据源中配置</div>
        </div>
        <a-space class="mango-detail-actions" wrap>
          <a-button size="small" type="primary" @click="onAdd">新增</a-button>
          <a-button size="small" @click="doResetSearch">返回</a-button>
        </a-space>
      </div>
    </template>

    <template #default>
      <a-table
        :scroll="{ x: 1100 }"
        :bordered="false"
        :columns="tableColumns"
        :data="table.dataList"
        :loading="table.tableLoading.value"
        :pagination="false"
        :row-key="rowKey"
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
            <template v-else-if="item.key === 'db_type'" #cell="{ record }">
              <a-tag :color="enumStore.colors[record.db_type]" size="small">
                {{ getDatabaseTypeName(record.db_type) }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'status'" #cell="{ record }">
              <a-switch
                :before-change="(newValue) => onModifyStatus(newValue, record)"
                :default-checked="record.status === 1"
              />
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <MangoTableActions
                :max-inline="3"
                :actions="[
                  { label: '查询', onClick: () => onOpenQueryDrawer(record) },
                  { label: '编辑', onClick: () => onUpdate(record) },
                  { label: '删除', danger: true, onClick: () => onDelete(record) },
                ]"
              />
            </template>
          </a-table-column>
        </template>
      </a-table>
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
          <template v-else-if="item.type === 'select' && item.key === 'db_type'">
            <a-select
              v-model="item.value"
              :field-names="fieldNames"
              :options="enumStore.database_type"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              value-key="key"
            />
          </template>
          <template v-else-if="item.type === 'textarea'">
            <a-textarea
              v-model="item.value"
              :auto-size="{ minRows: 3, maxRows: 5 }"
              :placeholder="item.placeholder"
            />
          </template>
        </a-form-item>
      </a-form>
    </template>
  </ModalDialog>

  <a-drawer
    v-model:visible="queryDrawer.visible"
    :width="'50%'"
    :footer="false"
    unmount-on-close
  >
    <template #title>
      SQL查询 / {{ queryDrawer.datasourceName || '-' }}
    </template>
    <div class="mango-sql-query-drawer">
      <div class="mango-sql-query-editor">
        <a-textarea
          v-model="queryDrawer.sql"
          :auto-size="{ minRows: 6, maxRows: 10 }"
          placeholder="请输入查询SQL，例如：SELECT * FROM table_name LIMIT 20"
        />
        <div class="mango-sql-query-actions">
          <a-button size="small" @click="queryDrawer.sql = ''">清空</a-button>
          <a-button
            size="small"
            type="primary"
            :loading="queryDrawer.loading"
            @click="onQueryDatasource"
          >
            查询
          </a-button>
        </div>
      </div>
      <div class="mango-sql-query-result">
        <div class="mango-sql-query-summary">
          <span>结果集</span>
          <span class="mango-muted-text">
            {{ queryDrawer.result.rows.length }} 条
            <template v-if="queryDrawer.result.truncated">，仅展示前 100 条</template>
          </span>
        </div>
        <a-table
          :bordered="false"
          :columns="queryResultColumns"
          :data="queryDrawer.result.rows"
          :loading="queryDrawer.loading"
          :pagination="false"
          :scroll="{ x: 'max-content', y: 360 }"
          row-key="__row_key"
          size="small"
        />
      </div>
    </div>
  </a-drawer>
</template>

<script lang="ts" setup>
  import {
    deleteDataFactoryDatasourceAlias,
    getDataFactoryDatasourceAlias,
    postDataFactoryDatasourceAlias,
    postDataFactoryDatasourceAliasQuery,
    putDataFactoryDatasourceAlias,
  } from '@/api/data-factory'
  import { useRowKey, useTable } from '@/hooks/table'
  import { fieldNames } from '@/setting'
  import { useEnum } from '@/store/modules/get-enum'
  import useUserStore from '@/store/modules/user'
  import { ModalDialogType } from '@/types/components'
  import { getFormItems } from '@/utils/datacleaning'
  import { Message, Modal } from '@arco-design/web-vue'
  import { computed, nextTick, onMounted, reactive, ref } from 'vue'
  import { useRoute } from 'vue-router'
  import { formItems, tableColumns } from './config'

  const route = useRoute()
  const enumStore = useEnum()
  const userStore = useUserStore()
  const table = useTable()
  const rowKey = useRowKey('id')
  const formModel = ref({})
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const data = reactive({
    actionTitle: '新增',
    isAdd: true,
    updateId: 0,
  })
  const queryDrawer = reactive({
    visible: false,
    loading: false,
    datasourceId: '',
    datasourceName: '',
    sql: '',
    result: {
      columns: [] as string[],
      rows: [] as any[],
      truncated: false,
    },
  })

  const datasourceDetailTitle = computed(() => {
    const id = route.query.id || '-'
    const name = route.query.name || '-'
    return `产品逻辑数据源 / ${id} / ${name}`
  })
  const queryResultColumns = computed(() => {
    return queryDrawer.result.columns.map((column) => ({
      title: column,
      dataIndex: column,
      key: column,
      ellipsis: true,
      tooltip: true,
      width: 180,
    }))
  })

  function getDatabaseTypeName(value: number) {
    return enumStore.database_type?.find((item) => item.key === value)?.title || value
  }

  function doResetSearch() {
    window.history.back()
  }

  function doRefresh() {
    table.tableLoading.value = true
    getDataFactoryDatasourceAlias({
      project_product: route.query.id,
      page: 1,
      pageSize: 999,
    })
      .then((res) => {
        table.dataList = res.data || []
      })
      .finally(() => {
        table.tableLoading.value = false
      })
  }

  function onAdd() {
    data.actionTitle = '新增'
    data.isAdd = true
    modalDialogRef.value?.toggle()
    formItems.forEach((it) => {
      if (it.reset) {
        it.reset()
      } else if (it.key === 'db_type') {
        it.value = 0
      } else {
        it.value = ''
      }
    })
  }

  function onUpdate(record: any) {
    data.actionTitle = '编辑'
    data.isAdd = false
    data.updateId = record.id
    modalDialogRef.value?.toggle()
    nextTick(() => {
      formItems.forEach((it) => {
        it.value = record[it.key] ?? ''
      })
    })
  }

  function onDelete(record: any) {
    Modal.confirm({
      title: '删除产品逻辑源',
      content: `确认删除 ${record.name}？删除后会影响引用它的数据工厂实体、API SQL 和 UI SQL 配置。`,
      cancelText: '取消',
      okText: '删除',
      onBeforeOk: () => {
        return deleteDataFactoryDatasourceAlias(record.id)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      },
    })
  }

  function onOpenQueryDrawer(record: any) {
    queryDrawer.visible = true
    queryDrawer.datasourceId = record.id
    queryDrawer.datasourceName = record.name
    queryDrawer.sql = ''
    queryDrawer.result = {
      columns: [],
      rows: [],
      truncated: false,
    }
  }

  function onQueryDatasource() {
    const sql = queryDrawer.sql.trim()
    if (!sql) {
      Message.error('请输入查询SQL')
      return
    }
    if (userStore.selected_environment == null) {
      Message.error('请先在顶部选择测试环境')
      return
    }
    queryDrawer.loading = true
    postDataFactoryDatasourceAliasQuery({
      datasource_alias_id: queryDrawer.datasourceId,
      project_product: route.query.id,
      test_env: userStore.selected_environment,
      sql,
    })
      .then((res) => {
        const result = res.data || {}
        queryDrawer.result = {
          columns: result.columns || [],
          rows: (result.rows || []).map((row: any, index: number) => ({
            __row_key: index,
            ...row,
          })),
          truncated: Boolean(result.truncated),
        }
        Message.success(res.msg)
      })
      .catch(console.log)
      .finally(() => {
        queryDrawer.loading = false
      })
  }

  function onDataForm() {
    if (formItems.every((it) => (it.validator ? it.validator() : true))) {
      const value = getFormItems(formItems)
      value.project_product = route.query.id
      value.status = 1
      const request = data.isAdd ? postDataFactoryDatasourceAlias : putDataFactoryDatasourceAlias
      if (!data.isAdd) {
        value.id = data.updateId
      }
      request(value)
        .then((res) => {
          modalDialogRef.value?.toggle()
          Message.success(res.msg)
          doRefresh()
        })
        .catch(console.log)
        .finally(() => {
          modalDialogRef.value?.setConfirmLoading(false)
        })
    } else {
      modalDialogRef.value?.setConfirmLoading(false)
    }
  }

  const onModifyStatus = async (newValue: boolean, record: any) => {
    return new Promise<any>((resolve, reject) => {
      putDataFactoryDatasourceAlias({
        id: record.id,
        project_product: record.project_product?.id || record.project_product || route.query.id,
        name: record.name,
        code: record.code,
        db_type: record.db_type,
        description: record.description || '',
        status: newValue ? 1 : 2,
      })
        .then((res) => {
          Message.success(res.msg)
          doRefresh()
          resolve(res.code === 200)
        })
        .catch(reject)
    })
  }

  onMounted(() => {
    enumStore.getEnum()
    doRefresh()
  })
</script>

<style scoped>
  .mango-sql-query-drawer {
    display: flex;
    flex-direction: column;
    gap: 16px;
    height: 100%;
  }

  .mango-sql-query-editor {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .mango-sql-query-actions {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
  }

  .mango-sql-query-result {
    min-height: 0;
    flex: 1;
  }

  .mango-sql-query-summary {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
    color: var(--m-text);
    font-size: 13px;
  }
</style>
