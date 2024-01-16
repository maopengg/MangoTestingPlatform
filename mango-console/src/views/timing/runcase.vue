<template>
  <div>
    <div id="tableHeaderContainer" class="relative" :style="{ zIndex: 9 }">
      <a-card :title="'定时任务：' + route.query.name">
        <template #extra>
          <a-affix :offsetTop="80">
            <a-space>
              <a-button type="primary" size="small" @click="doAppend">增加</a-button>
              <a-button status="danger" size="small" @click="doResetSearch">返回</a-button>
            </a-space>
          </a-affix>
        </template>
        <a-table :columns="columns" :data="runCaseData.data" :pagination="false" :bordered="false">
          <template #columns>
            <a-table-column
              :key="item.key"
              v-for="item of columns"
              :align="item.align"
              :title="item.title"
              :width="item.width"
              :data-index="item.dataIndex"
              :fixed="item.fixed"
            >
              <template v-if="item.dataIndex === 'task'" #cell="{ record }">
                {{ record.task.name }}
              </template>
              <template v-else-if="item.dataIndex === 'case'" #cell="{ record }">
                {{ record.case }}
              </template>
              <template v-else-if="item.dataIndex === 'actions'" #cell="{ record }">
                <a-button type="text" size="mini" @click="onUpdate(record)">编辑</a-button>
                <a-button status="danger" type="text" size="mini" @click="onDelete(record)">删除</a-button>
              </template>
            </a-table-column>
          </template>
        </a-table>
      </a-card>
      <ModalDialog ref="modalDialogRef" :title="runCaseData.actionTitle" @confirm="onDataForm">
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
              <template v-else-if="item.type === 'select' && item.key === 'module_name'">
                <a-select
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="projectModule.data"
                  :field-names="fieldNames"
                  value-key="key"
                  allow-clear
                  allow-search
                  @change="tasksTypeCaseName(item.value)"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'case'">
                <a-select
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="runCaseData.caseList"
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
import { nextTick, onMounted, reactive, ref } from 'vue'
import { Message, Modal } from '@arco-design/web-vue'
import { systemTasksRunCase, systemTasksTypeCaseName } from '@/api/url'
import { deleted, get, post, put } from '@/api/http'
import { FormItem, ModalDialogType } from '@/types/components'
import { useRoute } from 'vue-router'
import { getFormItems } from '@/utils/datacleaning'
import { fieldNames } from '@/setting'
import { useProjectModule } from '@/store/modules/project_module'

const projectModule = useProjectModule()

const route = useRoute()
const formModel = ref({})
const modalDialogRef = ref<ModalDialogType | null>(null)
const runCaseData = reactive({
  isAdd: false,
  updateId: 0,
  actionTitle: '添加定时任务',
  data: [],
  caseList: []
})
const columns = reactive([
  {
    title: '任务名称',
    dataIndex: 'task',
    width: 200
  },
  {
    title: '用例名称',
    dataIndex: 'case'
  },
  {
    title: '操作',
    dataIndex: 'actions',
    align: 'center',
    width: 130
  }
])

const formItems: FormItem[] = reactive([
  {
    label: '模块',
    key: 'module_name',
    value: '',
    placeholder: '请选择测试模块',
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
    label: '用例名称',
    key: 'case',
    value: '',
    placeholder: '请选择用例名称',
    required: true,
    type: 'select',
    validator: function () {
      if (!this.value && this.value !== 0) {
        Message.error(this.placeholder || '')
        return false
      }
      return true
    }
  }
])

function doAppend() {
  runCaseData.actionTitle = '添加用例'
  runCaseData.isAdd = true
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
    content: '是否要删除此页面？',
    cancelText: '取消',
    okText: '删除',
    onOk: () => {
      deleted({
        url: systemTasksRunCase,
        data: () => {
          return {
            id: '[' + record.id + ']'
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

function onUpdate(record: any) {
  runCaseData.actionTitle = '编辑用例'
  runCaseData.isAdd = false
  runCaseData.updateId = record.id
  modalDialogRef.value?.toggle()
  nextTick(() => {
    formItems.forEach((it) => {
      const propName = record[it.key]
      console.log(propName)
      if (propName) {
        it.value = record.case
      }
    })
  })
}

function onDataForm() {
  if (formItems.every((it) => (it.validator ? it.validator() : true))) {
    modalDialogRef.value?.toggle()
    let value = getFormItems(formItems)
    if (runCaseData.isAdd) {
      post({
        url: systemTasksRunCase,
        data: () => {
          value['task'] = route.query.id
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
        url: systemTasksRunCase,
        data: () => {
          value['id'] = runCaseData.updateId
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

function doResetSearch() {
  window.history.back()
}

function doRefresh() {
  get({
    url: systemTasksRunCase,
    data: () => {
      return {
        id: route.query.id,
        type: route.query.type
      }
    }
  })
    .then((res) => {
      runCaseData.data = res.data
    })
    .catch(console.log)
}

function tasksTypeCaseName(value: number) {
  get({
    url: systemTasksTypeCaseName,
    data: () => {
      return {
        type: route.query.type,
        module_name: value
      }
    }
  })
    .then((res) => {
      runCaseData.caseList = res.data
    })
    .catch(console.log)
}

onMounted(() => {
  nextTick(async () => {
    doRefresh()
  })
})
</script>
