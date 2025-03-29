<template>
  <TableBody ref="tableBody">
    <template #header>
      <a-card title="页面元素详情" :bordered="false">
        <template #extra>
          <a-space>
            <a-upload
              type="primary"
              size="small"
              @before-upload="beforeUpload"
              :show-file-list="false"
            />
            <a-button type="primary" size="small" @click="onDownload">下载模版</a-button>
            <a-button type="primary" size="small" @click="doAppend">增加</a-button>
            <a-button status="danger" size="small" @click="doResetSearch">返回</a-button>
          </a-space>
        </template>
        <div class="container">
          <a-space direction="vertical" style="width: 25%">
            <p>页面ID：{{ pageData.record.id }}</p>
            <span>所属项目：{{ pageData.record.project_product?.project?.name }}</span>
            <span>顶级模块：{{ pageData.record.module?.superior_module }}</span>
            <span>所属模块：{{ pageData.record.module?.name }}</span>
          </a-space>
          <a-space direction="vertical" style="width: 75%">
            <span>页面名称：{{ pageData.record.name }}</span>
            <span>页面地址：{{ pageData.record.url }}</span>
            <span>元素个数：{{ data.totalSize }}</span>
            <span>页面类型：{{ pageData.record.type }}</span>
          </a-space>
        </div>
      </a-card>
    </template>
    <template #default>
      <a-card :bordered="false">
        <a-table :columns="columns" :data="data.data" :pagination="false" :bordered="false">
          <template #columns>
            <a-table-column
              :key="item.key"
              v-for="item of columns"
              :align="item.align"
              :title="item.title"
              :width="item.width"
              :data-index="item.dataIndex"
              :fixed="item.fixed"
              :ellipsis="item.ellipsis"
              :tooltip="item.tooltip"
            >
              <template v-if="item.dataIndex === 'exp'" #cell="{ record }">
                <a-tag :color="enumStore.colors[record.exp]" size="small">
                  {{ enumStore.element_exp.find((item) => item.key === record.exp)?.title }}
                </a-tag>
              </template>
              <template v-else-if="item.dataIndex === 'is_iframe'" #cell="{ record }">
                <a-switch
                  :default-checked="record.is_iframe === 1"
                  :beforeChange="(newValue) => onModifyStatus(newValue, record.id)"
                />
              </template>
              <template v-else-if="item.dataIndex === 'actions'" #cell="{ record }">
                <a-button type="text" size="mini" @click="onDebug(record)">调试</a-button>
                <a-button type="text" size="mini" @click="onUpdate(record)">编辑</a-button>
                <a-button status="danger" type="text" size="mini" @click="onDelete(record)"
                  >删除
                </a-button>
              </template>
            </a-table-column>
          </template>
        </a-table>
      </a-card>
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
          <template v-else-if="item.type === 'select'">
            <a-select
              v-model="item.value"
              :placeholder="item.placeholder"
              :options="enumStore.element_exp"
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
  <ModalDialog ref="modalDialogRef1" :title="data.actionTitle" @confirm="onDataForm1">
    <template #content>
      <a-form :model="formModel1">
        <a-form-item
          :class="[item.required ? 'form-item__require' : 'form-item__no_require']"
          :label="item.label"
          v-for="item of formItems1"
          :key="item.key"
        >
          <template v-if="item.type === 'input'">
            <a-input :placeholder="item.placeholder" v-model="item.value" />
          </template>
          <template v-else-if="item.type === 'cascader' && item.label === '元素操作'">
            <a-space direction="vertical">
              <a-cascader
                v-model="item.value"
                :options="data.ope"
                :default-value="item.value"
                expand-trigger="hover"
                :placeholder="item.placeholder"
                @change="upDataOpeValue(item.value)"
                value-key="key"
                style="width: 380px"
                allow-search
                allow-clear
              />
            </a-space>
          </template>
          <template v-else-if="item.type === 'textarea' && item.key === 'ope_value'">
            <a-textarea
              :auto-size="{ minRows: 4, maxRows: 7 }"
              :placeholder="item.placeholder"
              :default-value="item.value"
              v-model="item.value"
              allow-clear
            />
          </template>
          <template v-else-if="item.type === 'cascader' && item.label === '断言类型'">
            <a-space direction="vertical">
              <a-cascader
                v-model="item.value"
                :options="data.ass"
                :default-value="item.value"
                expand-trigger="hover"
                :placeholder="item.placeholder"
                @change="upDataAssValue(item.value)"
                value-key="key"
                style="width: 380px"
                allow-search
                allow-clear
              />
            </a-space>
          </template>
          <template v-else-if="item.type === 'radio' && item.key === 'type'">
            <a-radio-group
              @change="changeStatus"
              v-model="data.type"
              :options="data.plainOptions"
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
  import { formItems1, columns, formItems } from './config'
  import { ModalDialogType } from '@/types/components'
  import { useRoute } from 'vue-router'
  import { getFormItems } from '@/utils/datacleaning'
  import { fieldNames } from '@/setting'
  import { usePageData } from '@/store/page-data'
  import {
    deleteUiElement,
    getUiElement,
    getUiElementUpload,
    postUiElement,
    putUiElement,
    putUiUiElementPutIsIframe,
    putUiUiElementTest,
  } from '@/api/uitest/element'
  import {
    getUiPageStepsDetailedOpe,
    getUiPageStepsDetailedAss,
  } from '@/api/uitest/page-steps-detailed'
  import { assForm, eleForm } from '@/views/uitest/page/elements/config'
  import useUserStore from '@/store/modules/user'
  import { useEnum } from '@/store/modules/get-enum'
  import { baseURL } from '@/api/axios.config'

  const userStore = useUserStore()
  const enumStore = useEnum()

  const pageData: any = usePageData()

  const route = useRoute()
  const formModel = ref({})
  const formModel1 = ref({})
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const modalDialogRef1 = ref<ModalDialogType | null>(null)
  const data: any = reactive({
    id: 0,
    isAdd: false,
    updateId: 0,
    actionTitle: '添加元素',
    eleExp: [],
    totalSize: 0,
    type: 0,
    data: [],
    ope: [],
    ass: [],
    plainOptions: [
      { label: '操作', value: 0 },
      { label: '断言', value: 1 },
    ],
  })

  function doAppend() {
    data.actionTitle = '添加元素'
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

  const beforeUpload = (file: any) => {
    return new Promise((resolve, reject) => {
      Modal.confirm({
        title: '上传文件',
        content: `确认上传：${file.name}`,
        onOk: () => {
          const formData = new FormData()
          formData.append('file', file)
          formData.append('page_id', route.query.id)
          formData.append('name', file.name)
          getUiElementUpload(formData)
            .then((res) => {
              Message.success(res.msg)
              doRefresh()
              // resolve(true)
            })
            .catch(console.log)
        },
        onCancel: () => reject('cancel'),
      })
    })
  }

  function onDelete(record: any) {
    Modal.confirm({
      title: '提示',
      content: '是否要删除此元素？',
      cancelText: '取消',
      okText: '删除',
      onOk: () => {
        deleteUiElement(record.id)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      },
    })
  }

  function onUpdate(record: any) {
    data.actionTitle = '编辑添加元素'
    data.isAdd = false
    data.updateId = record.id
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
      value['page'] = route.query.id
      if (data.isAdd) {
        value['is_iframe'] = 0
        postUiElement(value)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      } else {
        value['id'] = data.updateId
        putUiElement(value)
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
    getUiElement(route.query.id)
      .then((res) => {
        data.data = res.data
        data.totalSize = res.totalSize
      })
      .catch(console.log)
  }

  const onModifyStatus = async (newValue: boolean, id: number) => {
    return new Promise<any>((resolve, reject) => {
      setTimeout(async () => {
        try {
          let value: any = false
          await putUiUiElementPutIsIframe(id, newValue ? 1 : 0)
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

  function getUiRunSortOpe() {
    getUiPageStepsDetailedOpe(pageData.record.project_product.ui_client_type)
      .then((res) => {
        data.ope = res.data
      })
      .catch(console.log)
  }

  function getUiRunSortAss() {
    getUiPageStepsDetailedAss(pageData.record.project_product.ui_client_type)
      .then((res) => {
        data.ass = res.data
      })
      .catch(console.log)
  }

  function changeStatus(event: number) {
    data.type = event
    for (let i = formItems1.length - 1; i >= 0; i--) {
      if (formItems1[i].key !== 'type') {
        formItems1.splice(i, 1)
      }
    }
    if (event === 0) {
      if (
        !formItems1.some(
          (item) => item.key === 'ele_name' || formItems1.some((item) => item.key === 'ope_type')
        )
      ) {
        formItems1.push(...eleForm)
      }
    } else {
      if (!formItems1.some((item) => item.key === 'ass_type')) {
        formItems1.push(...assForm)
      }
    }
  }

  function upDataAssValue(value: any) {
    const inputItem = findItemByValue(data.ass, value)
    if (inputItem) {
      const parameter: any = inputItem.parameter
      Object.keys(parameter).forEach((key) => {
        parameter[key] = ''
      })
      if (!formItems1.some((item) => item.key === 'ope_value')) {
        formItems1.push({
          label: '断言值',
          key: 'ope_value',
          value: JSON.stringify(parameter),
          type: 'textarea',
          required: true,
          placeholder: '请输入断言内容',
          validator: function () {
            if (this.value !== '') {
              try {
                this.value = JSON.parse(this.value)
              } catch (e) {
                Message.error(this.placeholder || '')
                return false
              }
            }
            return true
          },
        })
      }
    }
  }

  function upDataOpeValue(value: any) {
    const inputItem = findItemByValue(data.ope, value)
    if (inputItem) {
      const parameter: any = inputItem.parameter
      Object.keys(parameter).forEach((key) => {
        parameter[key] = ''
      })

      if (!formItems1.some((item) => item.key === 'ope_value')) {
        formItems1.push({
          label: '元素操作值',
          key: 'ope_value',
          value: JSON.stringify(parameter),
          type: 'textarea',
          required: true,
          placeholder: '请输入对元素的操作内容',
          validator: function () {
            if (this.value !== '') {
              try {
                this.value = JSON.parse(this.value)
              } catch (e) {
                Message.error('元素操作值请输入json数据类型')
                return false
              }
            }
            return true
          },
        })
      }
    }
  }

  function onDataForm1() {
    if (formItems1.every((it) => (it.validator ? it.validator() : true))) {
      modalDialogRef1.value?.toggle()
      let value = getFormItems(formItems1)
      value['test_env'] = userStore.selected_environment
      value['id'] = data.id
      value['page_id'] = pageData.record.id
      value['project_product_id'] = pageData.record.project_product.id
      value['type'] = data.type
      value['is_send'] = true
      putUiUiElementTest(value)
        .then((res) => {
          Message.success(res.msg)
        })
        .catch(console.log)
    }
  }

  interface Item {
    value: string
    label: string
    parameter?: {
      [key: string]: any
    }
    children?: Item[]
  }

  function findItemByValue(data: Item[], value: string): Item | undefined {
    for (let i = 0; i < data.length; i++) {
      const item = data[i]
      if (item.value === value) {
        return item
      }
      if (item.children) {
        const childItem = findItemByValue(item.children, value)
        if (childItem) {
          return childItem
        }
      }
    }
    return undefined
  }

  function onDebug(record: any) {
    changeStatus(0)
    if (userStore.selected_environment === null) {
      Message.error('请先选择测试环境')
      return
    }
    data.actionTitle = `对元素：${record.name} 进行操作或断言`
    data.id = record.id
    modalDialogRef1.value?.toggle()
    nextTick(() => {
      formItems1.forEach((it) => {
        const propName = record[it.key]
        if (typeof propName === 'object' && propName !== null) {
          it.value = propName.id
        } else {
          it.value = propName
        }
      })
    })
  }

  function onDownload() {
    const file_name = '元素批量上传模版.xlsx'
    const file_path = `${baseURL}/download?file_name=${encodeURIComponent(file_name)}`
    let aLink = document.createElement('a')
    aLink.href = file_path
    aLink.download = file_name
    Message.loading('文件下载中~')
    document.body.appendChild(aLink)
    aLink.click()
    document.body.removeChild(aLink)
  }

  onMounted(() => {
    nextTick(async () => {
      doRefresh()
      getUiRunSortOpe()
      getUiRunSortAss()
    })
  })
</script>
