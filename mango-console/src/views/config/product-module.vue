<template>
  <div>
    <div id="tableHeaderContainer" class="relative" :style="{ zIndex: 9 }">
      <a-card :title="'产品名称：' + route.query.name">
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
              <template v-if="item.dataIndex === 'actions'" #cell="{ record }">
                <a-button type="text" size="mini" @click="onUpdate(record)">编辑</a-button>
                <a-button status="danger" type="text" size="mini" @click="onDelete(record)"
                  >删除</a-button
                >
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
  import { userModule } from '@/api/url'
  import { deleted, get, post, put } from '@/api/http'
  import { FormItem, ModalDialogType } from '@/types/components'
  import { useRoute } from 'vue-router'
  import { getFormItems } from '@/utils/datacleaning'

  const route = useRoute()
  const formModel = ref({})
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const runCaseData = reactive({
    isAdd: false,
    updateId: 0,
    actionTitle: '新增模块',
    data: [],
    caseList: [],
  })
  const columns = reactive([
    {
      title: '序号',
      dataIndex: 'id',
    },
    {
      title: '创建时间',
      dataIndex: 'create_time',
    },
    {
      title: '更新时间',
      dataIndex: 'update_time',
    },
    {
      title: '模块名称',
      dataIndex: 'name',
    },
    {
      title: '上级模块(一级模块)',
      dataIndex: 'superior_module',
    },
    {
      title: '操作',
      dataIndex: 'actions',
      align: 'center',
      width: 130,
    },
  ])

  const formItems: FormItem[] = reactive([
    {
      label: '模块名称',
      key: 'name',
      value: '',
      placeholder: '请输入模块名称',
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
      label: '上级模块',
      key: 'superior_module',
      value: '',
      placeholder: '请输入上级模块',
      required: false,
      type: 'input',
      validator: function () {
        // if (!this.value) {
        //   Message.error(this.placeholder || '')
        // return false
        // }
        return true
      },
    },
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
          url: userModule,
          data: () => {
            return {
              id: '[' + record.id + ']',
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

  function onUpdate(record: any) {
    runCaseData.actionTitle = '编辑用例'
    runCaseData.isAdd = false
    runCaseData.updateId = record.id
    modalDialogRef.value?.toggle()
    nextTick(() => {
      formItems.forEach((it) => {
        const propName = record[it.key]
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
      value['project'] = route.query.id
      if (runCaseData.isAdd) {
        post({
          url: userModule,
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
          url: userModule,
          data: () => {
            value['id'] = runCaseData.updateId
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

  function doResetSearch() {
    window.history.back()
  }

  function doRefresh() {
    get({
      url: userModule,
      data: () => {
        return {
          project_product: route.query.id,
        }
      },
    })
      .then((res) => {
        runCaseData.data = res.data
      })
      .catch(console.log)
  }

  onMounted(() => {
    nextTick(async () => {
      doRefresh()
    })
  })
</script>
