<template>
  <TableBody ref="tableBody">
    <template #header>
      <TableHeader
        :show-filter="true"
        title="定时任务"
        @search="doRefresh"
        @reset-search="onResetSearch"
      >
        <template #search-content>
          <a-form :model="{}" layout="inline" @keyup.enter="doRefresh">
            <a-form-item v-for="item of conditionItems" :key="item.key" :label="item.label">
              <template v-if="item.type === 'input'">
                <a-input v-model="item.value" :placeholder="item.placeholder" @blur="doRefresh" />
              </template>
              <template v-else-if="item.type === 'cascader'">
                <a-cascader
                  v-model="item.value"
                  :field-names="fieldNames"
                  :options="enumStore.environment_type"
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
                  <a-checkbox v-for="it of item.optionItems" :key="it.value" :value="it.value">
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
              <a-button size="small" type="primary" @click="onAdd">新增</a-button>
            </div>
          </a-space>
        </template>
      </a-tabs>
      <a-table
        :bordered="false"
        :columns="tableColumns"
        :data="table.dataList"
        :loading="table.tableLoading.value"
        :pagination="false"
        :rowKey="rowKey"
        @selection-change="onSelectionChange"
      >
        <template #columns>
          <a-table-column
            v-for="item of tableColumns"
            :key="item.key"
            :align="item.align"
            :data-index="item.key"
            :fixed="item.fixed"
            :title="item.title"
            :width="item.width"
            :ellipsis="item.ellipsis"
            :tooltip="item.tooltip"
          >
            <template v-if="item.key === 'index'" #cell="{ record }">
              {{ record.id }}
            </template>
            <template v-else-if="item.key === 'project_product'" #cell="{ record }">
              {{ record?.project_product?.project?.name + '/' + record?.project_product?.name }}
            </template>
            <template v-else-if="item.key === 'timing_strategy'" #cell="{ record }">
              {{ record.timing_strategy?.name }}
            </template>
            <template v-else-if="item.key === 'case_people'" #cell="{ record }">
              {{ record.case_people?.name }}
            </template>
            <template v-else-if="item.key === 'test_env'" #cell="{ record }">
              <a-tag :color="enumStore.colors[record.test_env]" size="small">
                {{
                  record.test_env !== null ? enumStore.environment_type[record.test_env].title : ''
                }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'case_executor'" #cell="{ record }">
              {{ record.case_executor }}
            </template>
            <template v-else-if="item.key === 'notice_group'" #cell="{ record }">
              {{ record.notice_group?.name }}
            </template>
            <template v-else-if="item.key === 'status'" #cell="{ record }">
              <a-switch
                :beforeChange="(newValue) => onModifyStatus(newValue, record.id, 'status')"
                :default-checked="record.status === 1"
              />
            </template>
            <template v-else-if="item.key === 'is_notice'" #cell="{ record }">
              <a-switch
                :beforeChange="(newValue) => onModifyStatus(newValue, record.id, 'is_notice')"
                :default-checked="record.is_notice === 1"
              />
            </template>
            <template v-else-if="item.key === 'fail_notice'" #cell="{ record }">
              <a-switch
                :beforeChange="(newValue) => onModifyStatus(newValue, record.id, 'fail_notice')"
                :default-checked="record.fail_notice === 1"
              />
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <a-space>
                <a-button size="mini" type="text" class="custom-mini-btn" @click="onTrigger(record)"
                  >触发
                </a-button>
                <a-button size="mini" type="text" class="custom-mini-btn" @click="onClick(record)"
                  >添加用例
                </a-button>
                <a-dropdown trigger="hover">
                  <a-button size="mini" type="text">···</a-button>
                  <template #content>
                    <a-doption>
                      <a-button
                        size="mini"
                        type="text"
                        class="custom-mini-btn"
                        @click="onUpdate(record)"
                        >编辑
                      </a-button>
                    </a-doption>
                    <a-doption>
                      <a-button
                        size="mini"
                        status="danger"
                        type="text"
                        class="custom-mini-btn"
                        @click="onDelete(record)"
                        >删除
                      </a-button>
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
          v-for="item of formItems"
          :key="item.key"
          :class="[item.required ? 'form-item__require' : 'form-item__no_require']"
          :label="item.label"
        >
          <template v-if="item.type === 'input' && item.key === 'trigger_type'">
            <a-input v-model="item.value" :placeholder="item.placeholder" disabled />
          </template>
          <template v-else-if="item.type === 'input' && item.key === 'name'">
            <a-input v-model="item.value" :placeholder="item.placeholder" />
          </template>
          <template v-else-if="item.type === 'cascader'">
            <a-cascader
              v-model="item.value"
              :options="projectInfo.projectProduct"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              @change="onProjectChange(item.value)"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'timing_strategy'">
            <a-select
              v-model="item.value"
              :field-names="fieldNames"
              :options="data.timingList"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              value-key="key"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'notice_group'">
            <a-select
              v-model="item.value"
              :options="data.noticeList"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              value-key="key"
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
          <template v-else-if="item.type === 'select' && item.key === 'case_people'">
            <a-select
              v-model="item.value"
              :field-names="fieldNames"
              :options="data.userList"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              value-key="key"
            />
          </template>

          <template v-else-if="item.type === 'select' && item.key === 'case_executor'">
            <a-select
              v-model="item.value"
              :placeholder="item.placeholder"
              :scrollbar="true"
              multiple
            >
              <a-option v-for="user of data.userList" :key="user.key">{{ user.title }}</a-option>
            </a-select>
          </template>
          <template v-else-if="item.type === 'switch' && item.key === 'status'">
            <a-switch v-model="item.value" :checked-value="1" :unchecked-value="0" />
          </template>
        </a-form-item>
      </a-form>
    </template>
  </ModalDialog>
</template>

<script lang="ts" setup>
  import { usePagination, useRowKey, useRowSelection, useTable } from '@/hooks/table'
  import { ModalDialogType } from '@/types/components'
  import { Message, Modal } from '@arco-design/web-vue'
  import { onMounted, ref, nextTick, reactive } from 'vue'
  import { getFormItems } from '@/utils/datacleaning'
  import { fieldNames } from '@/setting'
  import { useRouter } from 'vue-router'
  import { formItems, tableColumns, conditionItems } from './config'
  import {
    deleteSystemTasks,
    getSystemTasks,
    postSystemTasks,
    getSystemTriggerTiming,
    putSystemTasks,
  } from '@/api/system/tasks'
  import { getSystemTimingList } from '@/api/system/time'
  import { getUserName } from '@/api/user/user'
  import { useProject } from '@/store/modules/get-project'
  import { useEnum } from '@/store/modules/get-enum'
  import { getSystemNoticeName } from '@/api/system/notice_group'

  const projectInfo = useProject()
  const enumStore = useEnum()

  const modalDialogRef = ref<ModalDialogType | null>(null)
  const pagination = usePagination(doRefresh)
  const { onSelectionChange } = useRowSelection()
  const table = useTable()
  const rowKey = useRowKey('id')
  const router = useRouter()

  const data = reactive({
    isAdd: false,
    updateId: 0,
    actionTitle: '新增',
    userList: [],
    timingList: [],
    noticeList: [],
  })

  const formModel = ref({})

  function doRefresh() {
    let value = getFormItems(conditionItems)
    value['page'] = pagination.page
    value['pageSize'] = pagination.pageSize
    getSystemTasks(value)
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
    doRefresh()
  }

  function onAdd() {
    data.actionTitle = '新增'
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

  function onDelete(record: any) {
    Modal.confirm({
      title: '提示',
      content: '是否要删除此定时任务？',
      cancelText: '取消',
      okText: '删除',
      onOk: () => {
        deleteSystemTasks(record.id)
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

  function onTrigger(record: any) {
    getSystemTriggerTiming(record.id).then((res) => {
      Message.success(res.msg)
    })
  }

  function onUpdate(item: any) {
    data.actionTitle = '编辑'
    data.isAdd = false
    data.updateId = item.id
    onProjectChange(item.project_product.id)
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
      let value = getFormItems(formItems)
      if (data.isAdd) {
        value['status'] = 0
        value['is_notice'] = 0
        postSystemTasks(value)
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
        putSystemTasks(value)
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

  function getNickName() {
    getUserName()
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

  const onModifyStatus = async (newValue: any, id: number, field: string) => {
    return new Promise<any>((resolve, reject) => {
      setTimeout(async () => {
        try {
          let value: any = false
          await putSystemTasks({ id: id, [field]: newValue ? 1 : 0 })
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
        project_product_id: record.project_product.id,
      },
    })
  }
  function onProjectChange(id) {
    getSystemNoticeName(id)
      .then((res) => {
        data.noticeList = res.data
      })
      .catch(console.log)
  }
  onMounted(() => {
    nextTick(async () => {
      getTiming()
      getNickName()
      doRefresh()
    })
  })
</script>
