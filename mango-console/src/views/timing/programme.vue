<template>
  <div>
    <div class="main-container">
      <TableBody ref="tableBody">
        <template #header>
          <TableHeader
            :show-filter="true"
            title="定时策略"
            @search="doRefresh"
            @reset-search="onResetSearch"
          >
            <template #search-content>
              <a-form layout="inline" :model="{}" @keyup.enter="doRefresh">
                <a-form-item v-for="item of conditionItems" :key="item.key" :label="item.label">
                  <template v-if="item.type === 'input'">
                    <a-input
                      v-model="item.value"
                      :placeholder="item.placeholder"
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
          <a-tabs>
            <template #extra>
              <a-space>
                <div>
                  <span>注意：新增的定时策略需要联系管理员重启服务才会生效！</span>
                </div>
                <div>
                  <a-button type="primary" size="small" @click="onAdd">新增</a-button>
                </div>
              </a-space>
            </template>
          </a-tabs>
          <a-table
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
              >
                <template v-if="item.key === 'index'" #cell="{ record }">
                  {{ record.id }}
                </template>
                <template v-else-if="item.key === 'actions'" #cell="{ record }">
                  <a-space>
                    <a-button type="text" size="mini" @click="onUpdate(record)">编辑</a-button>
                    <a-button status="danger" type="text" size="mini" @click="onDelete(record)"
                      >删除</a-button
                    >
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
      <ModalDialog ref="modalDialogRef" :title="programme.actionTitle" @confirm="onDataForm">
        <template #content>
          <a-form :model="formModel">
            <a-form-item
              :class="[item.required ? 'form-item__require' : 'form-item__no_require']"
              :label="item.label"
              v-for="item of formItems"
              :key="item.key"
            >
              <template v-if="item.type === 'input' && item.key === 'trigger_type'">
                <a-input :placeholder="item.placeholder" v-model="item.value" disabled />
              </template>
              <template v-else-if="item.type === 'input'">
                <a-input :placeholder="item.placeholder" v-model="item.value" />
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
  import { systemTime } from '@/api/url'
  import {
    usePagination,
    useRowKey,
    useRowSelection,
    useTable,
    useTableColumn,
  } from '@/hooks/table'
  import { FormItem, ModalDialogType } from '@/types/components'
  import { Message, Modal } from '@arco-design/web-vue'
  import { onMounted, ref, nextTick, reactive } from 'vue'
  import { getFormItems } from '@/utils/datacleaning'

  const modalDialogRef = ref<ModalDialogType | null>(null)
  const pagination = usePagination(doRefresh)
  const { onSelectionChange } = useRowSelection()
  const table = useTable()
  const rowKey = useRowKey('id')
  const formModel = ref({})

  const programme = reactive({
    isAdd: false,
    updateId: 0,
    actionTitle: '添加定时器',
  })
  const conditionItems: Array<FormItem> = reactive([
    {
      key: 'id',
      label: 'ID',
      type: 'input',
      placeholder: '请输入定时策略ID',
      value: '',
      reset: function () {
        this.value = ''
      },
    },
    {
      key: 'name',
      label: '定时器介绍',
      type: 'input',
      placeholder: '请输入定时器介绍',
      value: '',
      reset: function () {
        this.value = ''
      },
    },
  ])
  const formItems: FormItem[] = reactive([
    {
      label: '定时器类型',
      key: 'trigger_type',
      value: 'cron',
      placeholder: 'cron',
      required: true,
      type: 'input',
    },
    {
      label: '定时器介绍',
      key: 'name',
      value: '',
      placeholder: '请输入定时器的介绍',
      required: true,
      type: 'input',
      validator: function () {
        if (!this.value) {
          Message.error(this.placeholder || '')
          return false
        }
        return true
      },
    },
    {
      label: '每年某月',
      key: 'month',
      value: '',
      type: 'input',
      required: false,
      placeholder: '月份请输入1-12之间的数字',
      validator: function () {
        if (this.value) {
          // 判断value是否为1-12之间的数字
          const value = parseInt(this.value)
          if (isNaN(value) || value < 1 || value > 12) {
            Message.error(this.placeholder || '')
            return false
          }
        }
        return true
      },
    },
    {
      label: '每月某天',
      key: 'day',
      value: '',
      type: 'input',
      required: false,
      placeholder: '天数请输入1-31之间的数字',
      validator: function () {
        if (this.value) {
          // 判断value是否为1-12之间的数字
          const value = parseInt(this.value)
          if (isNaN(value) || value < 1 || value > 31) {
            Message.error(this.placeholder || '')
            return false
          }
        }
        return true
      },
    },
    {
      label: '每周几',
      key: 'day_of_week',
      value: '',
      type: 'input',
      required: false,
      placeholder: '请输1-7的数字代表周几',
      validator: function () {
        if (this.value) {
          // 判断value是否为1-12之间的数字
          const value = parseInt(this.value)
          if (isNaN(value) || value < 1 || value > 7) {
            Message.error(this.placeholder || '')
            return false
          }
        }
        return true
      },
    },
    {
      label: '每天某小时',
      key: 'hour',
      value: '',
      type: 'input',
      required: false,
      placeholder: '小时请输入1-24之间的数字',
      validator: function () {
        if (this.value) {
          // 判断value是否为1-12之间的数字
          const value = parseInt(this.value)
          if (isNaN(value) || value < 1 || value > 23) {
            Message.error(this.placeholder || '')
            return false
          }
        }
        return true
      },
    },
    {
      label: '某分钟',
      key: 'minute',
      value: '',
      type: 'input',
      required: false,
      placeholder: '分钟请输入1-60之间的数字',
      validator: function () {
        if (this.value) {
          // 判断value是否为1-12之间的数字
          const value = parseInt(this.value)
          if (isNaN(value) || value < 1 || value > 60) {
            Message.error(this.placeholder || '')
            return false
          }
        }
        return true
      },
    },
  ])

  const tableColumns = useTableColumn([
    table.indexColumn,
    {
      title: '定时器类型',
      key: 'trigger_type',
      dataIndex: 'trigger_type',
    },
    {
      title: '定时器介绍',
      key: 'name',
      dataIndex: 'name',
      align: 'left',
    },
    {
      title: '每年某月',
      key: 'month',
      dataIndex: 'month',
    },
    {
      title: '每月某天',
      key: 'day',
      dataIndex: 'day',
    },
    {
      title: '每周几',
      key: 'day_of_week',
      dataIndex: 'day_of_week',
    },
    {
      title: '每天某小时',
      key: 'hour',
      dataIndex: 'hour',
    },
    {
      title: '每小时的某分钟',
      key: 'minute',
      dataIndex: 'minute',
    },
    {
      title: '操作',
      key: 'actions',
      dataIndex: 'actions',
      fixed: 'right',
      width: 150,
    },
  ])

  function doRefresh() {
    get({
      url: systemTime,
      data: () => {
        let value = getFormItems(conditionItems)
        value['page'] = pagination.page
        value['pageSize'] = pagination.pageSize
        return value
      },
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

  function onAdd() {
    programme.actionTitle = '添加定时器'
    modalDialogRef.value?.toggle()
    programme.isAdd = true
    formItems.forEach((it) => {
      if (it.reset) {
        it.reset()
      } else {
        it.value = ''
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
          url: systemTime,
          data: () => {
            return {
              id: '[' + data.id + ']',
            }
          },
        })
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      },
    })
  }

  function onUpdate(item: any) {
    programme.actionTitle = '编辑定时器'
    modalDialogRef.value?.toggle()
    programme.isAdd = false
    programme.updateId = item.id
    nextTick(() => {
      formItems.forEach((it) => {
        const propName = item[it.key]
        if (typeof propName === 'object' && propName !== null) {
          it.value = propName.id
        } else {
          it.value = propName
        }
      })
    })
  }

  function onDataForm() {
    if (formItems.every((it) => (it.validator ? it.validator() : true))) {
      modalDialogRef.value?.toggle()
      let value = getFormItems(formItems)
      value['trigger_type'] = 'cron'
      if (programme.isAdd) {
        post({
          url: systemTime,
          data: () => {
            return value
          },
        })
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      } else {
        put({
          url: systemTime,
          data: () => {
            value['id'] = programme.updateId
            return value
          },
        })
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      }
    }
  }

  onMounted(() => {
    nextTick(async () => {
      doRefresh()
    })
  })
</script>
