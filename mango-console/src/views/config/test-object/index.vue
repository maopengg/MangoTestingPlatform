<template>
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
                <a-input v-model="item.value" :placeholder="item.placeholder" @blur="doRefresh" />
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
            :ellipsis="item.ellipsis"
            :tooltip="item.tooltip"
          >
            <template v-if="item.key === 'index'" #cell="{ record }">
              {{ record.id }}
            </template>
            <template v-else-if="item.key === 'project_product'" #cell="{ record }">
              {{ record?.project_product?.project?.name + '/' + record?.project_product?.name }}
            </template>
            <template v-else-if="item.key === 'auto_type'" #cell="{ record }">
              <a-tag :color="enumStore.colors[record.auto_type]" size="small"
                >{{ enumStore.auto_type[record.auto_type].title }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'executor_name'" #cell="{ record }">
              {{ record.executor_name ? record.executor_name.name : '-' }}
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
                :beforeChange="(newValue) => onModifyStatus(newValue, record.id, 'db_rud_status')"
              />
            </template>
            <template v-else-if="item.key === 'environment'" #cell="{ record }">
              <a-tag :color="enumStore.colors[record.environment]" size="small">
                {{ enumStore.environment_type[record.environment].title }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <a-space>
                <a-button type="text" size="mini" class="custom-mini-btn" @click="onUpdate(record)"
                  >编辑
                </a-button>
                <a-button
                  type="text"
                  size="mini"
                  class="custom-mini-btn"
                  @click="clickNotice(record)"
                  >通知配置
                </a-button>

                <a-dropdown trigger="hover">
                  <a-button size="mini" type="text">···</a-button>
                  <template #content>
                    <a-doption>
                      <a-button
                        type="text"
                        size="mini"
                        class="custom-mini-btn"
                        @click="clickDataBase(record)"
                        >数据库配置
                      </a-button>
                    </a-doption>
                    <a-doption>
                      <a-button
                        status="danger"
                        type="text"
                        class="custom-mini-btn"
                        size="mini"
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
              :options="enumStore.environment_type"
              :field-names="fieldNames"
              value-key="key"
              allow-clear
              allow-search
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'auto_type'">
            <a-select
              v-model="item.value"
              :placeholder="item.placeholder"
              :options="enumStore.auto_type"
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
</template>

<script lang="ts" setup>
  import { usePagination, useRowKey, useRowSelection, useTable } from '@/hooks/table'
  import { ModalDialogType } from '@/types/components'
  import { Message, Modal } from '@arco-design/web-vue'
  import { onMounted, ref, nextTick, reactive } from 'vue'
  import { useProject } from '@/store/modules/get-project'
  import { getFormItems } from '@/utils/datacleaning'
  import { fieldNames } from '@/setting'
  import { conditionItems, formItems, tableColumns } from './config'
  import {
    deleteUserTestObject,
    getUserTestObject,
    postUserTestObject,
    putUserTestObject,
    putUserTestObjectPutStatus,
  } from '@/api/system/test_object'
  import { getUserName } from '@/api/user/user'
  import { usePageData } from '@/store/page-data'
  import { useRouter } from 'vue-router'
  import { useEnum } from '@/store/modules/get-enum'

  const router = useRouter()
  const projectInfo = useProject()
  const enumStore = useEnum()

  const modalDialogRef = ref<ModalDialogType | null>(null)
  const pagination = usePagination(doRefresh)
  const { onSelectionChange } = useRowSelection()
  const table = useTable()
  const rowKey = useRowKey('id')
  const formModel = ref({})
  const data = reactive({
    nickname: [],
    isAdd: false,
    updateId: 0,
    actionTitle: '新增',
  })

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

  function onDelete(data: any) {
    Modal.confirm({
      title: '提示',
      content: '是否要删除此测试环境？',
      cancelText: '取消',
      okText: '删除',
      onOk: () => {
        deleteUserTestObject(data.id)
          .then((res) => {
            Message.success(res.msg)
          })
          .catch(console.log)
        doRefresh()
      },
    })
  }

  function onUpdate(item: any) {
    data.actionTitle = '编辑'
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
          })
          .catch(console.log)
      } else {
        value['id'] = data.updateId
        putUserTestObject(value)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
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
    getUserName()
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

  function clickNotice(record: any) {
    const pageData = usePageData()
    pageData.setRecord(record)
    router.push({
      path: '/config/test/object/notice',
      query: {
        id: record.id,
      },
    })
  }

  function clickDataBase(record: any) {
    const pageData = usePageData()
    pageData.setRecord(record)
    router.push({
      path: '/config/test/object/database',
      query: {
        id: record.id,
      },
    })
  }

  onMounted(() => {
    nextTick(async () => {
      doRefresh()
      getNickName()
    })
  })
</script>
