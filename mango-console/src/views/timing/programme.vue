<template>
  <div>
    <div class="main-container">
      <TableBody ref="tableBody">
        <template #header>
          <TableHeader :show-filter="true" title="定时策略" @search="onSearch" @reset-search="onResetSearch">
            <template #search-content>
              <a-form layout="inline" :model="{}">
                <a-form-item v-for="item of conditionItems" :key="item.key" :label="item.label">
                  <template v-if="item.render">
                    <FormRender :render="item.render" :formItem="item" />
                  </template>
                  <template v-else>
                    <template v-if="item.type === 'input'">
                      <a-input v-model="item.value.value" :placeholder="item.placeholder" />
                    </template>
                    <template v-if="item.type === 'date'">
                      <a-date-picker v-model="item.value.value" />
                    </template>
                    <template v-if="item.type === 'time'">
                      <a-time-picker v-model="item.value.value" value-format="HH:mm:ss" />
                    </template>
                    <template v-if="item.type === 'check-group'">
                      <a-checkbox-group v-model="item.value.value">
                        <a-checkbox v-for="it of item.optionItems" :value="it.value" :key="it.value">
                          {{ item.label }}
                        </a-checkbox>
                      </a-checkbox-group>
                    </template>
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
                  <a-button type="primary" size="small" @click="onAddPage">新增</a-button>
                </div>
              </a-space>
            </template>
          </a-tabs>
          <a-table
            :bordered="false"
            :loading="table.tableLoading"
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
              >
                <template v-if="item.key === 'index'" #cell="{ record }">
                  {{ record.id }}
                </template>
                <template v-else-if="item.key === 'actions'" #cell="{ record }">
                  <a-space>
                    <a-button type="text" size="mini" @click="onUpdate(record)">编辑</a-button>
                    <a-button status="danger" type="text" size="mini" @click="onDelete(record)">删除</a-button>
                  </a-space>
                </template>
              </a-table-column>
            </template>
          </a-table>
        </template>
        <template #footer>
          <TableFooter :pagination="pagination" />
        </template>
      </TableBody>
      <ModalDialog ref="modalDialogRef" :title="actionTitle" @confirm="onDataForm">
        <template #content>
          <a-form :model="formModel">
            <a-form-item
              :class="[item.required ? 'form-item__require' : 'form-item__no_require']"
              :label="item.label"
              v-for="item of formItems"
              :key="item.key"
            >
              <template v-if="item.type === 'input' && item.key === 'trigger_type'">
                <a-input :placeholder="item.placeholder" v-model="item.value.value" disabled />
              </template>
              <template v-else-if="item.type === 'input'">
                <a-input :placeholder="item.placeholder" v-model="item.value.value" />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'month'">
                <a-select
                  v-model="item.value.value"
                  :placeholder="item.placeholder"
                  :options="timeDataR.month"
                  :field-names="fieldNames"
                  allow-clear
                  allow-search
                />
              </template>
            </a-form-item>
          </a-form>
        </template>
      </ModalDialog>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { get, post, put, deleted } from '@/api/http'
import { getTimeList, getTimeData } from '@/api/url'
import { usePagination, useRowKey, useRowSelection, useTable, useTableColumn } from '@/hooks/table'
import { FormItem, ModalDialogType } from '@/types/components'
import { Input, Message, Modal } from '@arco-design/web-vue'
import { h, onMounted, ref, nextTick, reactive } from 'vue'
import { transformData } from '@/utils/datacleaning'
import { fieldNames } from '@/setting'

const conditionItems: Array<FormItem> = [
  {
    key: 'name',
    label: '定时器介绍',
    type: 'input',
    placeholder: '请输入页面名称',
    value: ref(''),
    reset: function () {
      this.value.value = ''
    },
    render: (formItem: FormItem) => {
      return h(Input, {
        placeholder: '请输入页面名称',
        modelValue: formItem.value.value,
        'onUpdate:modelValue': (value) => {
          formItem.value.value = value
        }
      })
    }
  },
  {
    key: 'id',
    label: '定时器ID',
    type: 'input',
    placeholder: '请输入页面ID',
    value: ref(''),
    reset: function () {
      this.value.value = ''
    },
    render: (formItem: FormItem) => {
      return h(Input, {
        placeholder: '请输入页面ID',
        modelValue: formItem.value.value,
        'onUpdate:modelValue': (value) => {
          formItem.value.value = value
        }
      })
    }
  }
]
const formItems = [
  {
    label: '定时器类型',
    key: 'trigger_type',
    value: ref('cron'),
    placeholder: 'cron',
    required: true,
    type: 'input'
  },
  {
    label: '定时器介绍',
    key: 'name',
    value: ref(''),
    placeholder: '请输入定时器的介绍',
    required: true,
    type: 'input',
    validator: function () {
      if (!this.value.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  },
  {
    label: '月',
    key: 'month',
    value: ref(''),
    type: 'input',
    required: false,
    placeholder: '请输入月份',
    validator: function () {
      // 判断value是否为1-12之间的数字
      const value = parseInt(this.value.value)
      if (isNaN(value) || value < 1 || value > 12) {
        Message.error('月份请输入1-12之间的数字')
        return false
      }
      return true
    }
  },
  {
    label: '天',
    key: 'day',
    value: ref(''),
    type: 'input',
    required: false,
    placeholder: '请输入天',
    validator: function () {
      // 判断value是否为1-12之间的数字
      const value = parseInt(this.value.value)
      if (isNaN(value) || value < 1 || value > 31) {
        Message.error('天数请输入1-31之间的数字')
        return false
      }
      return true
    }
  },
  {
    label: '小时',
    key: 'hour',
    value: ref(''),
    type: 'input',
    required: false,
    placeholder: '请输入小时',
    validator: function () {
      // 判断value是否为1-12之间的数字
      const value = parseInt(this.value.value)
      if (isNaN(value) || value < 1 || value > 24) {
        Message.error('小时请输入1-24之间的数字')
        return false
      }
      return true
    }
  },
  {
    label: '分钟',
    key: 'minute',
    value: ref(''),
    type: 'input',
    required: false,
    placeholder: '请输入分钟',
    validator: function () {
      // 判断value是否为1-12之间的数字
      const value = parseInt(this.value.value)
      if (isNaN(value) || value < 1 || value > 60) {
        Message.error('分钟请输入1-60之间的数字')
        return false
      }
      return true
    }
  }
] as FormItem[]

const actionTitle = ref('添加定时器')
const modalDialogRef = ref<ModalDialogType | null>(null)
const pagination = usePagination(doRefresh)
const { onSelectionChange } = useRowSelection()
const table = useTable()
const rowKey = useRowKey('id')
const tableColumns = useTableColumn([
  table.indexColumn,
  {
    title: '定时器类型',
    key: 'trigger_type',
    dataIndex: 'trigger_type'
  },
  {
    title: '定时器介绍',
    key: 'name',
    dataIndex: 'name',
    align: 'left'
  },
  {
    title: '月',
    key: 'month',
    dataIndex: 'month'
  },
  {
    title: '天',
    key: 'day',
    dataIndex: 'day'
  },
  {
    title: '小时',
    key: 'hour',
    dataIndex: 'hour'
  },
  {
    title: '分钟',
    key: 'minute',
    dataIndex: 'minute'
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 150
  }
])

const formModel = ref({})

function doRefresh() {
  get({
    url: getTimeList,
    data: () => {
      return {
        page: pagination.page,
        pageSize: pagination.pageSize
      }
    }
  })
    .then((res) => {
      table.handleSuccess(res)
      pagination.setTotalSize((res as any).totalSize)
    })
    .catch(console.log)
}

function onSearch() {
  let data: { [key: string]: string } = {}
  conditionItems.forEach((it) => {
    if (it.value.value) {
      data[it.key] = it.value.value
    }
  })
  console.log(data)
  if (JSON.stringify(data) === '{}') {
    doRefresh()
  } else if (data.project) {
    get({
      url: getTimeList,
      data: () => {
        return {
          page: pagination.page,
          pageSize: pagination.pageSize,
          executor_name: data.executor_name
        }
      }
    })
      .then((res) => {
        table.handleSuccess(res)
        pagination.setTotalSize(res.totalSize || 10)
        Message.success(res.msg)
      })
      .catch(console.log)
  } else if (data) {
    get({
      url: getTimeList,
      data: () => {
        return {
          id: data.caseid,
          page: pagination.page,
          pageSize: pagination.pageSize,
          executor_name: data.executor_name
        }
      }
    })
      .then((res) => {
        table.handleSuccess(res)
        pagination.setTotalSize(res.totalSize || 10)
        Message.success(res.msg)
      })
      .catch(console.log)
  }
}

function onResetSearch() {
  conditionItems.forEach((it) => {
    it.reset ? it.reset() : (it.value.value = '')
  })
}

const addUpdate = ref(0)
const updateId: any = ref('')

function onAddPage() {
  actionTitle.value = '添加定时器'
  modalDialogRef.value?.toggle()
  addUpdate.value = 1
  formItems.forEach((it) => {
    if (it.reset) {
      it.reset()
    } else {
      it.value.value = ''
    }
  })
}

function onDelete(data: any) {
  Modal.confirm({
    title: '提示',
    content: '是否要删除此页面？',
    cancelText: '取消',
    okText: '删除',
    onOk: () => {
      deleted({
        url: getTimeList,
        data: () => {
          return {
            id: '[' + data.id + ']'
          }
        }
      })
        .then((res) => {
          Message.success(res.msg)
          doRefresh()
        })
        .catch(console.log)
    }
  })
}

function onUpdate(item: any) {
  actionTitle.value = '编辑定时器'
  modalDialogRef.value?.toggle()
  addUpdate.value = 0
  updateId.value = item.id
  nextTick(() => {
    formItems.forEach((it) => {
      const key = it.key
      const propName = item[key]
      if (typeof propName === 'object' && propName !== null) {
        it.value.value = propName.name
      } else {
        it.value.value = propName
      }
    })
  })
}

function onDataForm() {
  if (formItems.every((it) => (it.validator ? it.validator() : true))) {
    modalDialogRef.value?.toggle()
    let value = transformData(formItems)
    console.log(value)
    if (addUpdate.value === 1) {
      addUpdate.value = 0
      post({
        url: getTimeList,
        data: () => {
          return {
            name: value.name,
            trigger_type: 'cron',
            month: value.month,
            day: value.day,
            hour: value.hour,
            minute: value.minute
          }
        }
      })
        .then((res) => {
          Message.success(res.msg)
          doRefresh()
        })
        .catch(console.log)
    } else if (addUpdate.value === 0) {
      addUpdate.value = 0
      value['id'] = updateId.value
      updateId.value = 0
      put({
        url: getTimeList,
        data: () => {
          return {
            id: value.id,
            name: value.name,
            trigger_type: 'cron',
            month: value.month,
            day: value.day,
            hour: value.hour,
            minute: value.minute
          }
        }
      })
        .then((res) => {
          Message.success(res.msg)
          doRefresh()
        })
        .catch(console.log)
    }
  }
}

const timeDataR = reactive({
  month: [],
  day: [],
  hour: [],
  minute: []
})

// function timeData() {
//   get({
//     url: getTimeData
//   })
//     .then((res) => {
//       timeDataR.month = res.data[0].month
//       console.log(timeDataR.month)
//       timeDataR.day = res.data[1].day
//       timeDataR.hour = res.data[2].hour
//       timeDataR.minute = res.data[3].minute
//     })
//     .catch(console.log)
// }

onMounted(() => {
  nextTick(async () => {
    doRefresh()
  })
})
</script>
