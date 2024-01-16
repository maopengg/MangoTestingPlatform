<template>
  <div>
    <div class="main-container">
      <TableBody ref="tableBody">
        <template #header>
          <TableHeader :show-filter="true" title="登录日志" @search="doRefresh" @reset-search="onResetSearch">
            <template #search-content>
              <a-form layout="inline" :model="{}" @keyup.enter="doRefresh">
                <a-form-item v-for="item of conditionItems" :key="item.key" :label="item.label">
                  <template v-if="item.type === 'input'">
                    <a-input v-model="item.value" :placeholder="item.placeholder" @change="doRefresh" />
                  </template>
                  <template v-else-if="item.type === 'select' && item.key === 'user_id'">
                    <a-select
                      style="width: 150px"
                      v-model="item.value"
                      :placeholder="item.placeholder"
                      :options="userLogsData.userList"
                      :field-names="fieldNames"
                      value-key="key"
                      allow-clear
                      allow-search
                      @change="doRefresh"
                    />
                  </template>
                  <template v-else-if="item.type === 'select' && item.key === 'source_type'">
                    <a-select
                      style="width: 150px"
                      v-model="item.value"
                      :placeholder="item.placeholder"
                      :options="userLogsData.enumClientTypeList"
                      :field-names="fieldNames"
                      value-key="key"
                      allow-clear
                      allow-search
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
          </TableHeader>
        </template>

        <template #default>
          <a-table
            :bordered="false"
            :loading="table.tableLoading.value"
            :data="table.dataList"
            :columns="tableColumns"
            :pagination="false"
            :rowKey="rowKey"
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
              >
                <template v-if="item.key === 'index'" #cell="{ record }">
                  {{ record.id }}
                </template>
                <template v-else-if="item.key === 'source_type'" #cell="{ record }">
                  <a-tag color="green" size="small" v-if="record.source_type === '1'">控制端</a-tag>
                  <a-tag color="red" size="small" v-else-if="record.source_type === '2'">执行端</a-tag>
                </template>
              </a-table-column>
            </template>
          </a-table>
        </template>
        <template #footer>
          <TableFooter :pagination="pagination" />
        </template>
      </TableBody>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { get } from '@/api/http'
import { userNickname, userUserLogs, systemEnumClient } from '@/api/url'
import { usePagination, useRowKey, useTable, useTableColumn } from '@/hooks/table'
import { FormItem } from '@/types/components'
import { onMounted, nextTick, reactive } from 'vue'
import { getFormItems } from '@/utils/datacleaning'
import { fieldNames } from '@/setting'

const pagination = usePagination(doRefresh)
const table = useTable()
const rowKey = useRowKey('id')
const userLogsData = reactive({
  userList: [],
  enumClientTypeList: []
})
const tableColumns = useTableColumn([
  table.indexColumn,
  {
    title: '昵称',
    key: 'nickname',
    dataIndex: 'nickname'
  },
  {
    title: '账号',
    key: 'username',
    dataIndex: 'username'
  },
  {
    title: '来源',
    key: 'source_type',
    dataIndex: 'source_type'
  },
  {
    title: 'IP',
    key: 'ip',
    dataIndex: 'ip'
  },
  {
    title: '登录时间',
    key: 'create_time',
    dataIndex: 'create_time'
  }
])

const conditionItems: Array<FormItem> = reactive([
  {
    key: 'user_id',
    label: '筛选用户',
    value: '',
    type: 'select',
    placeholder: '请选择用户',
    optionItems: userLogsData.userList,
    reset: function () {}
  },
  {
    key: 'source_type',
    label: '筛选来源',
    type: 'select',
    placeholder: '请选择来源',
    value: '',
    optionItems: userLogsData.enumClientTypeList,
    reset: function () {}
  }
])

function doRefresh() {
  get({
    url: userUserLogs,
    data: () => {
      let value = getFormItems(conditionItems)
      value['page'] = pagination.page
      value['pageSize'] = pagination.pageSize
      return value
    }
  })
    .then((res) => {
      table.handleSuccess(res)
      pagination.setTotalSize((res as any).totalSize)
    })
    .catch(console.log)
}

function onResetSearch() {
  conditionItems.forEach((it) => {
    it.value = ''
  })
}

function getNickName() {
  get({
    url: userNickname,
    data: () => {
      return {}
    }
  })
    .then((res) => {
      userLogsData.userList = res.data
    })
    .catch(console.log)
}

function enumClientType() {
  get({
    url: systemEnumClient,
    data: () => {
      return {}
    }
  })
    .then((res) => {
      userLogsData.enumClientTypeList = res.data
      console.log(userLogsData.enumClientTypeList)
    })
    .catch(console.log)
}

onMounted(() => {
  nextTick(async () => {
    doRefresh()
    getNickName()
    enumClientType()
  })
})
</script>

<style>
.title-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
