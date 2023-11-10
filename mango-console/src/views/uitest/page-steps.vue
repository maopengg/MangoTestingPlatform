<template>
  <div>
    <div class="main-container">
      <TableBody ref="tableBody">
        <template #header>
          <TableHeader :show-filter="true" title="调试页面步骤" @search="onSearch" @reset-search="onResetSearch">
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
          <a-tabs @tab-click="(key) => switchType(key)">
            <template #extra>
              <a-space v-if="pageStepsData.stepsType === '0'">
                <a-button type="primary" size="small" @click="onAddPage">新增</a-button>
                <a-button status="warning" size="small" @click="setCase('已完成')">设为已完成</a-button>
                <a-button status="danger" size="small" @click="onDeleteItems">批量删除</a-button>
              </a-space>
              <a-space v-else-if="pageStepsData.stepsType === '1'">
                <a-button status="warning" size="small" @click="setCase('调试中')">设为调试中</a-button>
              </a-space>
            </template>
            <a-tab-pane key="0" title="调试中" />
            <a-tab-pane key="1" title="已完成" />
          </a-tabs>
          <a-table
            :bordered="false"
            :row-selection="{ selectedRowKeys, showCheckedAll }"
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
                <template v-else-if="item.key === 'page'" #cell="{ record }">
                  {{ record.page.name }}
                </template>
                <template v-else-if="item.key === 'type'" #cell="{ record }">
                  <a-tag color="green" size="small" v-if="record.type === 1">已完成</a-tag>
                  <a-tag color="red" size="small" v-else-if="record.type === 0">调试中</a-tag>
                  <a-tag color="gray" size="small" v-else>未调试</a-tag>
                </template>
                <template v-else-if="item.key === 'actions'" #cell="{ record }">
                  <a-space v-if="pageStepsData.stepsType === '0'">
                    <a-button type="text" size="mini" @click="onRunCase(record)">调试</a-button>
                    <a-button type="text" size="mini" @click="onUpdate(record)">编辑</a-button>
                    <a-button type="text" size="mini" @click="onClick(record)">步骤</a-button>
                    <a-button status="danger" type="text" size="mini" @click="onDelete(record)">删除</a-button>
                  </a-space>
                  <a-space v-else-if="pageStepsData.stepsType === '1'">
                    <a-button type="text" size="mini" @click="onRunCase(record)">执行</a-button>
                    <a-button type="text" size="mini" @click="onUpdate(record)">编辑</a-button>
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
      <ModalDialog ref="modalDialogRef" :title="pageStepsData.actionTitle" @confirm="onDataForm">
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
              <template v-else-if="item.type === 'select' && item.key === 'project'">
                <a-select
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="project.data"
                  :field-names="fieldNames"
                  value-key="key"
                  allow-clear
                  allow-search
                  @change="onQueryProjectPage(item.value)"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'page'">
                <a-select
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="pageStepsData.platformEnum"
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
// import {Search} from '@/components/ListSearch.vue'
import { get, post, put, deleted } from '@/api/http'
import { uiSteps, uiStepsQuery, uiStepsPutType, uiPageNameProject, UiStepsRun } from '@/api/url'
import { usePagination, useRowKey, useRowSelection, useTable, useTableColumn } from '@/hooks/table'
import { FormItem, ModalDialogType } from '@/types/components'
import { Input, Message, Modal } from '@arco-design/web-vue'
import { h, onMounted, ref, nextTick, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useProject } from '@/store/modules/get-project'
import { fieldNames } from '@/setting'
import { useTestObj } from '@/store/modules/get-test-obj'
import { getFormItems } from '@/utils/datacleaning'
const modalDialogRef = ref<ModalDialogType | null>(null)
const pagination = usePagination(doRefresh)
const { selectedRowKeys, onSelectionChange, showCheckedAll } = useRowSelection()
const table = useTable()
const rowKey = useRowKey('id')
const testObj = useTestObj()
const project = useProject()
const formModel = ref({})
const pageStepsData = reactive({
  isAdd: false,
  updateId: 0,
  actionTitle: '添加测试对象',
  stepsType: '0',
  platformEnum: []
})
const conditionItems: Array<FormItem> = reactive([
  {
    key: 'id',
    label: 'ID',
    type: 'input',
    placeholder: '请输入步骤ID',
    value: '',
    reset: function () {
      this.value = ''
    },
    render: (formItem: FormItem) => {
      return h(Input, {
        placeholder: '请输入步骤ID',
        modelValue: formItem.value,
        'onUpdate:modelValue': (value) => {
          formItem.value = value
        }
      })
    }
  },
  {
    key: 'name',
    label: '名称',
    type: 'input',
    placeholder: '请输入步骤名称',
    value: '',
    reset: function () {
      this.value = ''
    },
    render: (formItem: FormItem) => {
      return h(Input, {
        placeholder: '请输入步骤名称',
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
      if (!this.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  },
  {
    label: '所属页面',
    key: 'page',
    value: '',
    placeholder: '请选择步骤所属页面',
    required: true,
    type: 'select',
    validator: function () {
      if (!this.value) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  },
  {
    label: '步骤名称',
    key: 'name',
    value: ref(''),
    type: 'input',
    required: true,
    placeholder: '请输入页面步骤名称',
    validator: function () {
      if (!this.value) {
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
    title: '项目',
    key: 'project',
    dataIndex: 'project',
    width: 130
  },
  {
    title: '所属页面',
    key: 'page',
    dataIndex: 'page',
    width: 150
  },
  {
    title: '步骤名称',
    key: 'name',
    dataIndex: 'name',
    align: 'left',
    width: 170
  },
  {
    title: '步骤顺序',
    key: 'run_flow',
    dataIndex: 'run_flow',
    align: 'left'
  },
  {
    title: '状态',
    key: 'type',
    dataIndex: 'type'
  },
  {
    title: '操作',
    key: 'actions',
    dataIndex: 'actions',
    fixed: 'right',
    width: 200
  }
])

function switchType(key: number) {
  pageStepsData.stepsType = key
  doRefresh()
}

function doRefresh() {
  get({
    url: uiSteps,
    data: () => {
      return {
        page: pagination.page,
        pageSize: pagination.pageSize,
        type: pageStepsData.stepsType
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
  value['type'] = pageStepsData.stepsType
  get({
    url: uiStepsQuery,
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
  pageStepsData.actionTitle = '添加页面'
  pageStepsData.isAdd = true
  modalDialogRef.value?.toggle()
  formItems.forEach((it: any) => {
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
        url: uiSteps,
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

function onDeleteItems() {
  if (selectedRowKeys.value.length === 0) {
    Message.error('请选择要删除的数据')
    return
  }
  Modal.confirm({
    title: '提示',
    content: '确定要删除此数据吗？',
    cancelText: '取消',
    okText: '删除',
    onOk: () => {
      deleted({
        url: uiSteps,
        data: () => {
          return {
            id: JSON.stringify(selectedRowKeys.value)
          }
        }
      })
        .then((res) => {
          Message.success(res.msg)
          selectedRowKeys.value = []
          doRefresh()
        })
        .catch(console.log)
    }
  })
}

function onUpdate(item: any) {
  pageStepsData.actionTitle = '编辑页面步骤'
  pageStepsData.isAdd = false
  pageStepsData.updateId = item.id
  modalDialogRef.value?.toggle()
  onQueryProjectPage(item.project.id)
  nextTick(() => {
    formItems.forEach((it) => {
      const propName = item[it.key]
      if (typeof propName === 'object' && propName !== null) {
        it.value = propName.id
      } else {
        it.value = item.name
      }
    })
  })
}

function setCase(name: string) {
  if (selectedRowKeys.value.length === 0) {
    Message.error('请选择要设为' + name + '的数据')
    return
  }
  Modal.confirm({
    title: '提示',
    content: '确定要把这些设为' + name + '的吗？',
    cancelText: '取消',
    okText: '确定',
    onOk: () => {
      put({
        url: uiStepsPutType,
        data: () => {
          return {
            id: JSON.stringify(selectedRowKeys.value),
            type: name === '已完成' ? 1 : 0
          }
        }
      })
        .then((res) => {
          Message.success(res.msg)
          selectedRowKeys.value = []
          doRefresh()
        })
        .catch(console.log)
    }
  })
}

function onDataForm() {
  if (formItems.every((it) => (it.validator ? it.validator() : true))) {
    modalDialogRef.value?.toggle()
    let value = getFormItems(formItems)
    value['type'] = 0

    if (pageStepsData.isAdd) {
      post({
        url: uiSteps,
        data: () => {
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
        url: uiSteps,
        data: () => {
          value['id'] = pageStepsData.updateId
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

function onRunCase(record: any) {
  if (testObj.te == null) {
    Message.error('请先选择用例执行的环境')
    return
  }
  // Message.info('测试用例正在执行，请稍后')
  get({
    url: UiStepsRun,
    data: () => {
      return {
        page_step_id: record.id,
        te: testObj.te
      }
    }
  })
    .then((res) => {
      Message.success(res.msg)
    })
    .catch(console.log)
}

const router = useRouter()

function onClick(record: any) {
  router.push({
    path: '/uitest/page-steps-details',
    query: {
      id: parseInt(record.id, 10),
      name: record.name,
      pageId: record.page.id,
      project_name: record.project.name,
      type: parseInt(record.type),
      pageType: record.page.type
    }
  })
}

function onQueryProjectPage(project_id: number) {
  get({
    url: uiPageNameProject,
    data: () => {
      return {
        project_id: project_id
      }
    }
  })
    .then((res) => {
      pageStepsData.platformEnum = res.data
    })
    .catch((res) => {
      pageStepsData.platformEnum = []
      formItems.forEach((obj: any) => {
        if (obj.key == 'page') {
          obj.value = null
        }
      })
    })
}

onMounted(() => {
  nextTick(async () => {
    doRefresh()
  })
})
</script>

<style lang="less" scoped>
.avatar-container {
  position: relative;
  width: 30px;
  height: 30px;
  margin: 0 auto;
  vertical-align: middle;

  .avatar {
    width: 100%;
    height: 100%;
    border-radius: 50%;
  }

  .avatar-vip {
    border: 2px solid #cece1e;
  }

  .vip {
    position: absolute;
    top: 0;
    right: -9px;
    width: 15px;
    transform: rotate(60deg);
  }
}

.gender-container {
  .gender-icon {
    width: 20px;
  }
}
</style>
