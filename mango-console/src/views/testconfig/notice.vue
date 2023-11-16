<template>
  <div>
    <div class="main-container">
      <TableBody ref="tableBody">
        <template #header>
          <TableHeader :show-filter="true" title="自动化通知配置" @search="onSearch" @reset-search="onResetSearch">
            <template #search-content>
              <a-form layout="inline" :model="{}">
                <a-form-item v-for="item of conditionItems" :key="item.key" :label="item.label">
                  <template v-if="item.render">
                    <FormRender :render="item.render" :formItem="item" />
                  </template>
                  <template v-else>
                    <template v-if="item.type === 'input'">
                      <a-input v-model="item.value" :placeholder="item.placeholder" />
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
                <template v-else-if="item.key === 'project'" #cell="{ record }">
                  {{ record.project?.name }}
                </template>
                <template v-else-if="item.key === 'type'" #cell="{ record }">
                  <a-tag color="orangered" size="small" v-if="record.type === 0">邮箱</a-tag>
                  <a-tag color="cyan" size="small" v-else-if="record.type === 1">企微群</a-tag>
                  <a-tag color="green" size="small" v-else-if="record.type === 2">钉钉</a-tag>
                </template>
                <template v-else-if="item.key === 'status'" #cell="{ record }">
                  <a-switch
                    :default-checked="record.status === 1"
                    :beforeChange="(newValue) => onModifyStatus(newValue, record.id)"
                  />
                </template>
                <template v-else-if="item.key === 'actions'" #cell="{ record }">
                  <a-space>
                    <a-button type="text" size="mini" @click="onTest(record)">测试一下</a-button>
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
      <ModalDialog ref="modalDialogRef" :title="noticeData.actionTitle" @confirm="onDataForm">
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
              <template v-else-if="item.type === 'textarea'">
                <a-textarea v-model="item.value" :placeholder="item.placeholder" :auto-size="{ minRows: 5, maxRows: 9 }" />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'project'">
                <a-select
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="project.data"
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
                  :options="noticeData.noticeType"
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
import { get, post, put, deleted } from '@/api/http'
import { getNoticeConfig, getNoticeConfigQuery, getNoticeTest, getNoticeType, getNoticePutStatus } from '@/api/url'
import { usePagination, useRowKey, useRowSelection, useTable, useTableColumn } from '@/hooks/table'
import { FormItem, ModalDialogType } from '@/types/components'
import { Input, Message, Modal } from '@arco-design/web-vue'
import { h, onMounted, ref, nextTick, reactive } from 'vue'
import { useProject } from '@/store/modules/get-project'
import { fieldNames } from '@/setting'
import { getFormItems } from '@/utils/datacleaning'
const modalDialogRef = ref<ModalDialogType | null>(null)
const pagination = usePagination(doRefresh)
const { onSelectionChange } = useRowSelection()
const table = useTable()
const rowKey = useRowKey('id')
const project = useProject()
const formModel = ref({})

const noticeData = reactive({
  noticeType: [],
  isAdd: false,
  updateId: 0,
  actionTitle: '添加通知'
})
const conditionItems: Array<FormItem> = reactive([
  {
    key: 'id',
    label: 'ID',
    type: 'input',
    placeholder: '请输入通知ID',
    value: '',
    reset: function () {
      this.value = ''
    },
    render: (formItem: FormItem) => {
      return h(Input, {
        placeholder: '请输入通知ID',
        modelValue: formItem.value,
        'onUpdate:modelValue': (value) => {
          formItem.value = value
        }
      })
    }
  },
  {
    key: 'project',
    label: '筛选项目',
    value: '',
    type: 'select',
    placeholder: '请选择项目',
    optionItems: project.data,
    reset: function () {}
  }
])
const formItems: FormItem[] = reactive([
  {
    label: '项目名称',
    key: 'project',
    value: '',
    placeholder: '请选择项目名称',
    required: true,
    type: 'select',
    validator: function () {
      if (!this.value && this.value !== '0') {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  },
  {
    label: '通知类型',
    key: 'type',
    value: 0,
    type: 'select',
    required: true,
    placeholder: '请选择通知类型',
    validator: function () {
      if (!this.value && this.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  },
  {
    label: '配置详情',
    key: 'config',
    value: '',
    type: 'textarea',
    required: true,
    placeholder: '请输入配置详情',
    validator: function () {
      if (!this.value && this.value !== '0') {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  }
])

const tableColumns = useTableColumn([
  table.indexColumn,
  {
    title: '项目名称',
    key: 'project',
    dataIndex: 'project',
    width: 100
  },
  {
    title: '通知类型',
    key: 'type',
    dataIndex: 'type',
    width: 150
  },
  {
    title: '配置详情',
    key: 'config',
    dataIndex: 'config',
    align: 'left'
  },
  {
    title: '状态',
    key: 'status',
    dataIndex: 'status',
    width: 80
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 150
  }
])

function doRefresh() {
  get({
    url: getNoticeConfig,
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
  let value = getFormItems(conditionItems)
  if (JSON.stringify(value) === '{}') {
    doRefresh()
    return
  }
  get({
    url: getNoticeConfigQuery,
    data: () => {
      value['page'] = pagination.page
      value['pageSize'] = pagination.pageSize
      return value
    }
  })
    .then((res) => {
      table.handleSuccess(res)
      pagination.setTotalSize(res.totalSize || 10)
      Message.success(res.msg)
    })
    .catch(console.log)
}

function onResetSearch() {
  conditionItems.forEach((it) => {
    it.value = ''
  })
}

function onAddPage() {
  noticeData.actionTitle = '添加通知'
  modalDialogRef.value?.toggle()
  noticeData.isAdd = true
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
        url: getNoticeConfig,
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
  noticeData.actionTitle = '编辑通知'
  modalDialogRef.value?.toggle()
  noticeData.isAdd = false
  noticeData.updateId = item.id
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

    if (noticeData.isAdd) {
      post({
        url: getNoticeConfig,
        data: () => {
          value['status'] = 0
          return value
        }
      })
        .then((res) => {
          Message.success(res.msg)
          doRefresh()
        })
        .catch(console.log)
    } else {
      put({
        url: getNoticeConfig,
        data: () => {
          value['id'] = noticeData.updateId
          return value
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

function getNoticeTpyeF() {
  get({
    url: getNoticeType,
    data: () => {
      return {
        page: pagination.page,
        pageSize: pagination.pageSize
      }
    }
  })
    .then((res) => {
      noticeData.noticeType = res.data
    })
    .catch(console.log)
}

const onModifyStatus = async (newValue: boolean, id: number) => {
  return new Promise<any>((resolve, reject) => {
    setTimeout(async () => {
      try {
        let value: any = false
        await put({
          url: getNoticePutStatus,
          data: () => {
            return {
              id: id,
              status: newValue ? 1 : 0
            }
          }
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
function onTest(record: any) {
  get({
    url: getNoticeTest,
    data: () => {
      return {
        id: record.id
      }
    }
  })
    .then((res) => {
      Message.success(res.msg)
    })
    .catch(console.log)
}

onMounted(() => {
  nextTick(async () => {
    doRefresh()
    getNoticeTpyeF()
  })
})
onMounted(doRefresh)
</script>
