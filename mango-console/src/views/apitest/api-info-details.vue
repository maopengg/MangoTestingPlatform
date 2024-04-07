<template>
  <div>
    <a-card title="页面元素详情">
      <template #extra>
        <a-affix :offsetTop="80">
          <a-space>
            <a-button type="primary" size="small" @click="doAppend">增加</a-button>
            <a-button status="danger" size="small" @click="doResetSearch">返回</a-button>
          </a-space>
        </a-affix>
      </template>
      <div class="container">
        <a-space direction="vertical" style="width: 25%">
          <p>接口ID：{{ pageData.record.id }}</p>
          <span>所属项目：{{ pageData.record.project?.name }}</span>
          <span>顶级模块：{{ pageData.record.module_name?.superior_module }}</span>
          <span>所属模块：{{ pageData.record.module_name?.name }}</span>
        </a-space>
        <a-space direction="vertical" style="width: 25%">
          <span>接口名称：{{ pageData.record.name }}</span>
          <span>接口URL：{{ pageData.record.url }}</span>
          <span>接口方法：{{ ApiInfoDetailsData.apiMethodType[pageData.record.method] }}</span>
        </a-space>
      </div>
    </a-card>
    <a-card>
      <a-table
        :bordered="false"
        :row-selection="{ selectedRowKeys, showCheckedAll }"
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
            <template v-else-if="item.key === 'type'" #cell="{ record }">
              <a-tag color="orangered" size="small" v-if="record.type === 0">参数</a-tag>
              <a-tag color="gold" size="small" v-else-if="record.type === 1">表单</a-tag>
              <a-tag color="arcoblue" size="small" v-else-if="record.type === 2">json</a-tag>
              <a-tag color="lime" size="small" v-else-if="record.type === 3">文件</a-tag>
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <a-button type="text" size="mini" @click="onUpdate(record)">编辑</a-button>
              <a-button status="danger" type="text" size="mini" @click="onDelete(record)"
                >删除
              </a-button>
            </template>
          </a-table-column>
        </template>
      </a-table>
    </a-card>
  </div>
  <ModalDialog ref="modalDialogRef" :title="ApiInfoDetailsData.actionTitle" @confirm="onDataForm">
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
          <template v-else-if="item.type === 'select' && item.key === 'type'">
            <a-select
              v-model="item.value"
              :placeholder="item.placeholder"
              :options="ApiInfoDetailsData.apiParameterType"
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
  import { nextTick, onMounted, reactive, ref } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import { apiInfoDetails, systemEnumApiParameterType, systemEnumMethod } from '@/api/url'
  import { deleted, get, post, put } from '@/api/http'
  import { FormItem, ModalDialogType } from '@/types/components'
  import { useRoute } from 'vue-router'
  import { getFormItems } from '@/utils/datacleaning'
  import { fieldNames } from '@/setting'
  import { usePageData } from '@/store/page-data'
  import {
    usePagination,
    useRowKey,
    useRowSelection,
    useTable,
    useTableColumn,
  } from '@/hooks/table'

  const pageData: any = usePageData()
  const { selectedRowKeys, onSelectionChange, showCheckedAll } = useRowSelection()
  const table = useTable()
  const pagination = usePagination(doRefresh)
  const rowKey = useRowKey('id')
  const route = useRoute()
  const formModel = ref({})
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const ApiInfoDetailsData = reactive({
    id: 0,
    isAdd: false,
    updateId: 0,
    actionTitle: '添加元素',
    data: [],
    apiParameterType: [],
    apiMethodType: [],
  })
  const tableColumns = useTableColumn([
    table.indexColumn,
    {
      title: '参数类型',
      key: 'type',
      dataIndex: 'project',
    },
    {
      title: 'key',
      key: 'key',
      dataIndex: 'key',
    },
    {
      title: 'value',
      key: 'value',

      dataIndex: 'value',
      ellipsis: true,
      tooltip: true,
    },
    {
      title: '描述',
      key: 'describe',
      dataIndex: 'describe',
      width: 200,
      ellipsis: true,
      tooltip: true,
    },
    {
      title: '操作',
      key: 'actions',
      dataIndex: 'actions',
      align: 'center',
      width: 200,
    },
  ])

  const formItems: FormItem[] = reactive([
    {
      label: '参数类型',
      key: 'type',
      value: null,
      type: 'select',
      required: true,
      placeholder: '请选择参数类型',
      validator: function () {
        if (!this.value && this.value !== 0) {
          Message.error(this.placeholder || '')
          return false
        }
        return true
      },
    },
    {
      label: 'key',
      key: 'key',
      value: '',
      type: 'input',
      required: false,
      placeholder: '请输入key',
      validator: function () {
        return true
      },
    },
    {
      label: 'value',
      key: 'value',
      value: '',
      type: 'input',
      required: false,
      placeholder: '请输入value',
    },
    {
      label: '描述',
      key: 'describe',
      value: '',
      type: 'input',
      required: false,
      placeholder: '请输入参数描述',
    },
  ])
  function doResetSearch() {
    window.history.back()
  }
  function doAppend() {
    ApiInfoDetailsData.actionTitle = '添加元素'
    ApiInfoDetailsData.isAdd = true
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
      content: '是否要删除此元素？',
      cancelText: '取消',
      okText: '删除',
      onOk: () => {
        deleted({
          url: apiInfoDetails,
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
    ApiInfoDetailsData.actionTitle = '编辑添加元素'
    ApiInfoDetailsData.isAdd = false
    ApiInfoDetailsData.updateId = record.id
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
      value['api_info_id'] = route.query.id
      if (ApiInfoDetailsData.isAdd) {
        post({
          url: apiInfoDetails,
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
          url: apiInfoDetails,
          data: () => {
            value['id'] = ApiInfoDetailsData.updateId
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

  function doRefresh() {
    get({
      url: apiInfoDetails,
      data: () => {
        let value: any = {}
        value['page'] = pagination.page
        value['pageSize'] = pagination.pageSize
        value['api_info_id'] = pageData.record.id
        return value
      },
    })
      .then((res) => {
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
      })
      .catch(console.log)
  }

  function enumApiParameterType() {
    get({
      url: systemEnumApiParameterType,
      data: () => {
        return {}
      },
    })
      .then((res) => {
        ApiInfoDetailsData.apiParameterType = res.data
      })
      .catch(console.log)
  }
  function doMethod() {
    get({
      url: systemEnumMethod,
      data: () => {
        return {}
      },
    })
      .then((res) => {
        res.data.forEach((item: any) => {
          ApiInfoDetailsData.apiMethodType.push(item.title)
        })
      })
      .catch(console.log)
  }

  onMounted(() => {
    nextTick(async () => {
      await doMethod()
      doRefresh()
      enumApiParameterType()
    })
  })
</script>
