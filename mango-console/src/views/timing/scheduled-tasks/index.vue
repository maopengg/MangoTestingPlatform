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
                      @blur="doRefresh"
                    />
                  </template>
                  <template v-else-if="item.type === 'cascader'">
                    <a-cascader
                      v-model="item.value"
                      :placeholder="item.placeholder"
                      :options="testObj.data"
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
                  {{
                    record.test_obj?.project_product?.project?.name +
                    '/' +
                    uEnvironment.data[record.test_obj?.environment].title
                  }}
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
      <ModalDialog ref="modalDialogRef" :title="data.actionTitle" @confirm="onDataForm">
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
                  :options="data.timingList"
                  :field-names="fieldNames"
                  value-key="key"
                  allow-clear
                  allow-search
                />
              </template>

              <template v-else-if="item.type === 'cascader'">
                <a-cascader
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="testObj.data"
                  value-key="key"
                  allow-search
                  allow-clear
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'case_people'">
                <a-select
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="data.userList"
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
                  :options="data.type"
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
                  <a-option v-for="user of data.userList" :key="user.key">{{
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
  import { usePagination, useRowKey, useRowSelection, useTable } from '@/hooks/table'
  import { ModalDialogType } from '@/types/components'
  import { Message, Modal } from '@arco-design/web-vue'
  import { onMounted, ref, nextTick, reactive } from 'vue'
  import { getFormItems } from '@/utils/datacleaning'
  import { fieldNames } from '@/setting'
  import { useRouter } from 'vue-router'
  import { useTestObj } from '@/store/modules/get-test-obj'
  import { formItems, tableColumns, conditionItems } from './config'
  import {
    deleteSystemScheduledTasks,
    getSystemEnumAutotest,
    getSystemScheduledTasks,
    getSystemTimingList,
    getSystemTriggerTiming,
    postSystemScheduledTasks,
    putSystemScheduledPutNotice,
    putSystemScheduledPutStatus,
    putSystemScheduledTasks,
  } from '@/api/system'
  import { getUserNickname } from '@/api/user'
  import { useEnvironment } from '@/store/modules/get-environment'

  const testObj = useTestObj()
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const pagination = usePagination(doRefresh)
  const { onSelectionChange } = useRowSelection()
  const table = useTable()
  const rowKey = useRowKey('id')
  const router = useRouter()
  const uEnvironment = useEnvironment()

  const data = reactive({
    isAdd: false,
    updateId: 0,
    actionTitle: '添加定时任务',
    userList: [],
    timingList: [],
    type: [],
  })

  const formModel = ref({})

  function doRefresh() {
    let value = getFormItems(conditionItems)
    value['page'] = pagination.page
    value['pageSize'] = pagination.pageSize
    getSystemScheduledTasks(value)
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
    data.actionTitle = '添加定时任务'
    data.isAdd = true
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
        deleteSystemScheduledTasks(data.id)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      },
    })
  }

  function onTrigger(record: any) {
    getSystemTriggerTiming(record.id).then((res) => {
      Message.success(res.msg)
    })
  }

  function onUpdate(item: any) {
    data.actionTitle = '编辑定时器'
    data.isAdd = false
    data.updateId = item.id
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
      if (data.isAdd) {
        value['status'] = 0
        value['is_notice'] = 1
        postSystemScheduledTasks(value)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      } else {
        value['id'] = data.updateId
        putSystemScheduledTasks(value)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      }
    }
  }

  function getNickName() {
    getUserNickname()
      .then((res) => {
        data.userList = res.data
      })
      .catch(console.log)
  }

  function getTiming() {
    getSystemTimingList()
      .then((res) => {
        data.timingList = res.data
      })
      .catch(console.log)
  }

  function getAutoTestName() {
    getSystemEnumAutotest()
      .then((res) => {
        data.type = res.data
      })
      .catch(console.log)
  }

  const onModifyStatus = async (newValue: boolean, id: number) => {
    return new Promise<any>((resolve, reject) => {
      setTimeout(async () => {
        try {
          let value: any = false
          await putSystemScheduledPutStatus(id, newValue ? 1 : 0)
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
          await putSystemScheduledPutNotice(id, newValue ? 1 : 0)
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
      path: '/timing/case',
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
