<template>
  <div>
    <div class="main-container">
      <TableBody ref="tableBody">
        <template #header>
          <TableHeader
            :show-filter="true"
            title="定时任务"
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
                  <template v-else-if="item.type === 'select'">
                    <a-select
                      style="width: 150px"
                      v-model="item.value"
                      :placeholder="item.placeholder"
                      :options="item.optionItems"
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
          <a-tabs>
            <template #extra>
              <a-space>
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
                <template v-else-if="item.key === 'timing_strategy'" #cell="{ record }">
                  {{ record.timing_strategy?.name }}
                </template>
                <template v-else-if="item.key === 'case_people'" #cell="{ record }">
                  {{ record.case_people?.nickname }}
                </template>
                <template v-else-if="item.key === 'test_obj'" #cell="{ record }">
                  {{ record.test_obj?.name }}
                </template>
                <template v-else-if="item.key === 'case_executor'" #cell="{ record }">
                  {{ record.case_executor }}
                </template>
                <template v-else-if="item.key === 'status'" #cell="{ record }">
                  <a-switch
                    :default-checked="record.status === 1"
                    :beforeChange="(newValue) => onModifyStatus(newValue, record.id)"
                  />
                </template>
                <template v-else-if="item.key === 'is_notice'" #cell="{ record }">
                  <a-switch
                    :default-checked="record.is_notice === 1"
                    :beforeChange="(newValue) => onModifyIsNotice(newValue, record.id)"
                  />
                </template>
                <template v-else-if="item.key === 'type'" #cell="{ record }">
                  <a-tag color="orangered" size="small" v-if="record.type === 0">界面自动化</a-tag>
                  <a-tag color="cyan" size="small" v-else-if="record.type === 1">接口自动化</a-tag>
                  <a-tag color="green" size="small" v-else-if="record.type === 2">性能自动化</a-tag>
                </template>
                <template v-else-if="item.key === 'actions'" #cell="{ record }">
                  <a-space>
                    <a-button type="text" size="mini" @click="onTrigger(record)">触发</a-button>
                    <a-button type="text" size="mini" @click="onClick(record)">添加用例</a-button>
                    <a-dropdown trigger="hover">
                      <a-button type="text" size="mini">···</a-button>
                      <template #content>
                        <a-doption>
                          <a-button type="text" size="mini" @click="onUpdate(record)"
                            >编辑</a-button
                          >
                        </a-doption>
                        <a-doption>
                          <a-button
                            status="danger"
                            type="text"
                            size="mini"
                            @click="onDelete(record)"
                            >删除</a-button
                          >
                        </a-doption>
                      </template>
                    </a-dropdown>
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
      <ModalDialog
        ref="modalDialogRef"
        :title="scheduledTasksData.actionTitle"
        @confirm="onDataForm"
      >
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
              <template v-else-if="item.type === 'input' && item.key === 'name'">
                <a-input :placeholder="item.placeholder" v-model="item.value" />
              </template>

              <template v-else-if="item.type === 'select' && item.key === 'timing_strategy'">
                <a-select
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="scheduledTasksData.timingList"
                  :field-names="fieldNames"
                  value-key="key"
                  allow-clear
                  allow-search
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'test_obj'">
                <a-select
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="testObj.data"
                  :field-names="fieldNames"
                  value-key="key"
                  allow-clear
                  allow-search
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'case_people'">
                <a-select
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="scheduledTasksData.userList"
                  :field-names="fieldNames"
                  value-key="key"
                  allow-clear
                  allow-search
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'type'">
                <a-select
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="scheduledTasksData.type"
                  :field-names="fieldNames"
                  value-key="key"
                  allow-clear
                  allow-search
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'case_executor'">
                <a-select
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  multiple
                  :scrollbar="true"
                >
                  <a-option v-for="user of scheduledTasksData.userList" :key="user.key">{{
                    user.title
                  }}</a-option>
                </a-select>
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
  import {
    userNickname,
    systemScheduledTasks,
    systemScheduledPutNotice,
    systemScheduledPutStatus,
    systemTimingList,
    systemTriggerTiming,
    systemEnumAutotest,
  } from '@/api/url'
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
  import { fieldNames } from '@/setting'
  import { useRouter } from 'vue-router'
  import { useTestObj } from '@/store/modules/get-test-obj'

  const testObj = useTestObj()
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const pagination = usePagination(doRefresh)
  const { onSelectionChange } = useRowSelection()
  const table = useTable()
  const rowKey = useRowKey('id')
  const router = useRouter()

  const scheduledTasksData = reactive({
    isAdd: false,
    updateId: 0,
    actionTitle: '添加定时任务',
    userList: [],
    timingList: [],
    type: [],
  })
  const conditionItems: Array<FormItem> = reactive([
    {
      key: 'id',
      label: 'ID',
      type: 'input',
      placeholder: '请输入任务ID',
      value: '',
      reset: function () {
        this.value = ''
      },
    },
    {
      key: 'name',
      label: '任务名称',
      type: 'input',
      placeholder: '请输入任务名称',
      value: '',
      reset: function () {
        this.value = ''
      },
    },
    {
      key: 'test_obj',
      label: '测试环境',
      value: '',
      type: 'select',
      placeholder: '请选择测试环境',
      optionItems: testObj.data,
      reset: function () {},
    },
  ])
  const formItems: FormItem[] = reactive([
    {
      label: '任务名称',
      key: 'name',
      value: '',
      placeholder: '请输入任务名称',
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
      label: '定时策略',
      key: 'timing_strategy',
      value: '',
      placeholder: '请输入选择定时器策略',
      required: true,
      type: 'select',
      validator: function () {
        if (!this.value && this.value !== '0') {
          Message.error(this.placeholder || '')
          return false
        }
        return true
      },
    },
    {
      label: '自动化类型',
      key: 'type',
      value: 0,
      placeholder: '请选择自动化类型',
      required: true,
      type: 'select',
      validator: function () {
        if (!this.value && this.value !== 0) {
          Message.error(this.placeholder || '')
          return false
        }
        return true
      },
    },
    {
      label: '测试环境',
      key: 'test_obj',
      value: '',
      placeholder: '请选择执行环境',
      required: true,
      type: 'select',
      validator: function () {
        if (!this.value && this.value !== '0') {
          Message.error(this.placeholder || '')
          return false
        }
        return true
      },
    },
    {
      label: '负责人',
      key: 'case_people',
      value: '',
      placeholder: '请选择定时任务负责人',
      required: true,
      type: 'select',
      validator: function () {
        if (!this.value && this.value !== '0') {
          Message.error(this.placeholder || '')
          return false
        }
        return true
      },
    },
    {
      label: '执行器',
      key: 'case_executor',
      value: '',
      placeholder: '请选择定执行器',
      required: true,
      type: 'select',
      validator: function () {
        if (this.value.length === 0) {
          Message.error(this.placeholder || '')
          return false
        }
        this.value = this.value.filter(
          (item: any) => item !== null && item !== undefined && item !== ''
        )
        return true
      },
    },
  ])

  const tableColumns = useTableColumn([
    table.indexColumn,
    {
      title: '任务名称',
      key: 'name',
      dataIndex: 'name',
      align: 'left',
    },
    {
      title: '任务类型',
      key: 'type',
      dataIndex: 'type',
    },
    {
      title: '定时器介绍',
      key: 'timing_strategy',
      dataIndex: 'timing_strategy',
      align: 'left',
    },
    {
      title: '测试环境',
      key: 'test_obj',
      dataIndex: 'test_obj',
      align: 'left',
    },
    {
      title: '负责人',
      key: 'case_people',
      dataIndex: 'case_people',
      align: 'left',
    },
    {
      title: '执行器',
      key: 'case_executor',
      dataIndex: 'case_executor',
      align: 'left',
    },
    {
      title: '任务状态',
      key: 'status',
      dataIndex: 'status',
    },
    {
      title: '通知',
      key: 'is_notice',
      dataIndex: 'is_notice',
    },
    {
      title: '操作',
      key: 'actions',
      dataIndex: 'actions',
      fixed: 'right',
      width: 150,
    },
  ])

  const formModel = ref({})

  function doRefresh() {
    get({
      url: systemScheduledTasks,
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
    scheduledTasksData.actionTitle = '添加定时任务'
    scheduledTasksData.isAdd = true
    modalDialogRef.value?.toggle()
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
          url: systemScheduledTasks,
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

  function onTrigger(record: any) {
    get({
      url: systemTriggerTiming,
      data: () => {
        return {
          id: record.id,
        }
      },
    }).then((res) => {
      Message.success(res.msg)
    })
  }

  function onUpdate(item: any) {
    scheduledTasksData.actionTitle = '编辑定时器'
    scheduledTasksData.isAdd = false
    scheduledTasksData.updateId = item.id
    modalDialogRef.value?.toggle()
    nextTick(() => {
      formItems.forEach((it) => {
        const propName = item[it.key]
        if (typeof propName === 'object' && propName !== null) {
          if (propName.name) {
            it.value = propName.id
          } else if (propName.id) {
            it.value = propName.id
          } else {
            it.value = propName
          }
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
      if (scheduledTasksData.isAdd) {
        post({
          url: systemScheduledTasks,
          data: () => {
            value['status'] = 0
            value['is_notice'] = 1
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
          url: systemScheduledTasks,
          data: () => {
            value['id'] = scheduledTasksData.updateId
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

  function getNickName() {
    get({
      url: userNickname,
      data: () => {
        return {}
      },
    })
      .then((res) => {
        scheduledTasksData.userList = res.data
      })
      .catch(console.log)
  }

  function getTiming() {
    get({
      url: systemTimingList,
      data: () => {
        return {}
      },
    })
      .then((res) => {
        scheduledTasksData.timingList = res.data
      })
      .catch(console.log)
  }

  function getAutoTestName() {
    get({
      url: systemEnumAutotest,
      data: () => {
        return {}
      },
    })
      .then((res) => {
        scheduledTasksData.type = res.data
      })
      .catch(console.log)
  }

  const onModifyStatus = async (newValue: boolean, id: number) => {
    return new Promise<any>((resolve, reject) => {
      setTimeout(async () => {
        try {
          let value: any = false
          await put({
            url: systemScheduledPutStatus,
            data: () => {
              return {
                id: id,
                status: newValue ? 1 : 0,
              }
            },
          })
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
  const onModifyIsNotice = async (newValue: boolean, id: number) => {
    return new Promise<any>((resolve, reject) => {
      setTimeout(async () => {
        try {
          let value: any = false
          await put({
            url: systemScheduledPutNotice,
            data: () => {
              return {
                id: id,
                is_notice: newValue ? 1 : 0,
              }
            },
          })
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

  function onClick(record: any) {
    router.push({
      path: '/timing/runcase',
      query: {
        id: record.id,
        name: record.name,
        type: record.type,
      },
    })
  }

  onMounted(() => {
    nextTick(async () => {
      doRefresh()
      getNickName()
      getTiming()
      getAutoTestName()
    })
  })
</script>
