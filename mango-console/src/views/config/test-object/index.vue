<template>
  <div>
    <div class="main-container">
      <TableBody ref="tableBody">
        <template #header>
          <TableHeader
            :show-filter="true"
            title="配置测试对象"
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
                      :options="project.data"
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
                  <a-button type="primary" size="small" @click="onAddPage">新增</a-button>
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
                <template v-else-if="item.key === 'project_product'" #cell="{ record }">
                  {{ record.project_product?.project?.name + '/' + record.project_product?.name }}
                </template>
                <template v-else-if="item.key === 'executor_name'" #cell="{ record }">
                  {{ record.executor_name ? record.executor_name.nickname : '-' }}
                </template>
                <template v-else-if="item.key === 'db_c_status'" #cell="{ record }">
                  <a-switch
                    :default-checked="record.db_c_status === 1"
                    :beforeChange="(newValue) => onModifyStatus(newValue, record.id, 'db_c_status')"
                  />
                </template>
                <template v-else-if="item.key === 'db_rud_status'" #cell="{ record }">
                  <a-switch
                    :default-checked="record.db_rud_status === 1"
                    :beforeChange="
                      (newValue) => onModifyStatus(newValue, record.id, 'db_rud_status')
                    "
                  />
                </template>
                <template v-else-if="item.key === 'environment'" #cell="{ record }">
                  <a-tag color="orangered" size="small" v-if="record.environment === 0"
                    >测试环境</a-tag
                  >
                  <a-tag color="cyan" size="small" v-else-if="record.environment === 1"
                    >预发环境</a-tag
                  >
                  <a-tag color="green" size="small" v-else-if="record.environment === 2"
                    >生产环境</a-tag
                  >
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
      <ModalDialog ref="modalDialogRef" :title="data.actionTitle" @confirm="onDataForm">
        <template #content>
          <a-form :model="formModel">
            <a-form-item
              :class="[item.required ? 'form-item__require' : 'form-item__no_require']"
              :label="item.label"
              v-for="item of formItems"
              :key="item.key"
            >
              <template v-if="item.type === 'input'">
                <a-input :placeholder="item.placeholder" v-model="item.value" />
              </template>
              <template v-else-if="item.type === 'cascader'">
                <a-cascader
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="projectInfo.projectProduct"
                  allow-search
                  allow-clear
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'environment'">
                <a-select
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="uEnvironment.data"
                  :field-names="fieldNames"
                  value-key="key"
                  allow-clear
                  allow-search
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'executor_name'">
                <a-select
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="data.nickname"
                  :field-names="fieldNames"
                  value-key="key"
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
  import { usePagination, useRowKey, useRowSelection, useTable } from '@/hooks/table'
  import { ModalDialogType } from '@/types/components'
  import { Message, Modal } from '@arco-design/web-vue'
  import { onMounted, ref, nextTick, reactive } from 'vue'
  import { useProject } from '@/store/modules/get-project'
  import { useEnvironment } from '@/store/modules/get-environment'
  import { getFormItems } from '@/utils/datacleaning'
  import { fieldNames } from '@/setting'
  import { useTestObj } from '@/store/modules/get-test-obj'
  import { conditionItems, formItems, tableColumns } from './config'
  import {
    deleteUserTestObject,
    getUserTestObject,
    postUserTestObject,
    putUserTestObject,
    putUserTestObjectPutStatus,
  } from '@/api/user'
  import { getUserNickname } from '@/api/user'

  const projectInfo = useProject()
  const uEnvironment = useEnvironment()
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const pagination = usePagination(doRefresh)
  const { onSelectionChange } = useRowSelection()
  const table = useTable()
  const rowKey = useRowKey('id')
  const formModel = ref({})
  const testObj = useTestObj()
  const data = reactive({
    nickname: [],
    isAdd: false,
    updateId: 0,
    actionTitle: '添加测试对象',
  })

  function onResetSearch() {
    conditionItems.forEach((it) => {
      it.value = ''
    })
  }

  function onAddPage() {
    data.actionTitle = '添加测试对象'
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
        deleteUserTestObject(data.id)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      },
    })
  }

  function onUpdate(item: any) {
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
    if (formItems.every((it) => (it.validator ? it.validator() : true))) {
      modalDialogRef.value?.toggle()
      let value = getFormItems(formItems)
      if (data.isAdd) {
        value['db_c_status'] = 0
        value['db_rud_status'] = 0
        postUserTestObject(value)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
            testObj.getEnvironment()
          })
          .catch(console.log)
      } else {
        value['id'] = data.updateId
        putUserTestObject(value)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
            testObj.getEnvironment()
          })
          .catch(console.log)
      }
    }
  }

  function doRefresh() {
    let value = getFormItems(conditionItems)
    value['page'] = pagination.page
    value['pageSize'] = pagination.pageSize
    getUserTestObject(value)
      .then((res) => {
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
      })
      .catch(console.log)
  }

  function getNickName() {
    getUserNickname()
      .then((res) => {
        data.nickname = res.data
      })
      .catch(console.log)
  }

  const onModifyStatus = async (newValue: boolean, id: number, field: string) => {
    let dataObj: any = {
      id: id,
    }
    dataObj[field] = newValue ? 1 : 0 // 使用[field]作为对象的字段键
    return new Promise<any>((resolve, reject) => {
      setTimeout(async () => {
        try {
          let value: any = false
          await putUserTestObjectPutStatus(dataObj)
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
  onMounted(() => {
    nextTick(async () => {
      doRefresh()
      getNickName()
      uEnvironment.getEnvironment()
    })
  })
</script>
