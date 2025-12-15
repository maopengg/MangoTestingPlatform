<template>
  <TableBody ref="tableBody">
    <template #header>
      <a-card title="页面元素详情" :bordered="false">
        <template #extra>
          <a-space>
            <a-button  size="small" status="warning" @click="doResetSearch">返回</a-button>
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
      <a-tabs>
        <template #extra>
          <a-space>
            <div>
              <a-button type="primary" size="small" @click="onDownload">下载模版</a-button>
            </div>
            <div>
              <a-upload
                @before-upload="beforeUpload"
                :show-file-list="false"
                class="custom-upload"
              />
            </div>
            <div>
              <a-button type="primary" size="small" @click="doAppend">单个新增</a-button>
            </div>
            <div>
              <a-button size="small" status="danger" @click="onDelete(null)">批量删除</a-button>
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
        :row-selection="{ selectedRowKeys, showCheckedAll }"
        :rowKey="rowKey"
        @selection-change="onSelectionChange"
        :scroll="{ x: 2000 }"
      >
        <template #columns>
          <a-table-column
            v-for="item of tableColumns"
            :key="item.key"
            :align="item.align"
            :data-index="item.key"
            :ellipsis="item.ellipsis"
            :fixed="item.fixed"
            :title="item.title"
            :tooltip="item.tooltip"
            :width="item.width"
          >
            <template v-if="item.key === 'index'" #cell="{ record }">
              {{ record.id }}
            </template>
            <template v-else-if="item.dataIndex === 'exp'" #cell="{ record }">
              <a-tag :color="enumStore.colors[record.exp]" size="small">
                {{ enumStore.element_exp.find((item) => item.key === record.exp)?.title }}
              </a-tag>
            </template>
            <template v-else-if="item.dataIndex === 'exp2'" #cell="{ record }">
              <a-tag
                v-if="record.exp2 !== null"
                :color="enumStore.colors[record.exp2]"
                size="small"
              >
                {{ enumStore.element_exp.find((item) => item.key === record.exp2)?.title }}
              </a-tag>
            </template>
            <template v-else-if="item.dataIndex === 'exp3'" #cell="{ record }">
              <a-tag
                v-if="record.exp3 !== null"
                :color="enumStore.colors[record.exp3]"
                size="small"
              >
                {{ enumStore.element_exp.find((item) => item.key === record.exp3)?.title }}
              </a-tag>
            </template>
            <template v-else-if="item.dataIndex === 'is_iframe'" #cell="{ record }">
              <a-switch
                :default-checked="record.is_iframe === 1"
                :beforeChange="(newValue) => onModifyStatus(newValue, record.id)"
              />
            </template>
            <template v-else-if="item.dataIndex === 'actions'" #cell="{ record }">
              <a-button type="text" size="mini" class="custom-mini-btn" @click="onDebug(record)"
                >调试
              </a-button>
              <a-button type="text" size="mini" class="custom-mini-btn" @click="onUpdate(record)"
                >编辑
              </a-button>
              <a-button
                status="danger"
                type="text"
                size="mini"
                class="custom-mini-btn"
                @click="onDelete(record)"
                >删除
              </a-button>
            </template>
          </a-table-column>
        </template>
      </a-table>
    </template>
    <template #footer>
      <TableFooter :pagination="pagination" />
    </template>
  </TableBody>
  <ModalDialog
    ref="modalDialogRef"
    :title="data.actionTitle"
    :show-continuous-submit="true"
    @confirm="onDataForm"
    @continuous-submit="onContinuousSubmit"
  >
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
                :options="
                  String(pageData.record.project_product.ui_client_type === '0')
                    ? useSelectValue.webOpe
                    : useSelectValue.androidOpe
                "
                :default-value="item.value"
                expand-trigger="hover"
                :placeholder="item.placeholder"
                @change="
                  upDataOpeValue(
                    String(pageData.record.project_product.ui_client_type === '0')
                      ? useSelectValue.webOpe
                      : useSelectValue.androidOpe,
                    item.value
                  )
                "
                value-key="key"
                style="width: 380px"
                allow-search
                allow-clear
              />
            </a-space>
          </template>
          <template v-else-if="item.type === 'textarea'">
            <a-textarea
              :auto-size="{ minRows: 4, maxRows: 7 }"
              :placeholder="item.placeholder"
              :default-value="item.value"
              v-model="item.value"
              allow-clear
            />
          </template>
          <template v-else-if="item.type === 'cascader' && item.label === '断言操作'">
            <a-space direction="vertical">
              <a-cascader
                v-model="item.value"
                :options="
                  String(pageData.record.project_product.ui_client_type === '0')
                    ? useSelectValue.assWeb
                    : useSelectValue.assAndroid
                "
                :default-value="item.value"
                expand-trigger="hover"
                :placeholder="item.placeholder"
                @change="
                  upDataOpeValue(
                    String(pageData.record.project_product.ui_client_type === '0')
                      ? useSelectValue.assWeb
                      : useSelectValue.assAndroid,
                    item.value
                  )
                "
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
  import { formItems1, tableColumns, formItems } from './config'
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

  import { opeForm } from '@/views/uitest/page/elements/config'
  import useUserStore from '@/store/modules/user'
  import { useEnum } from '@/store/modules/get-enum'
  import { baseURL } from '@/api/axios.config'
  import { getSystemCacheDataKeyValue } from '@/api/system/cache_data'
  import { usePagination, useRowKey, useRowSelection, useTable } from '@/hooks/table'
  import { useSelectValueStore } from '@/store/modules/get-ope-value'

  const { selectedRowKeys, onSelectionChange, showCheckedAll } = useRowSelection()
  const pagination = usePagination(doRefresh)
  const rowKey = useRowKey('id')
  const table = useTable()

  const userStore = useUserStore()
  const enumStore = useEnum()
  const useSelectValue = useSelectValueStore()

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
    actionTitle: '新增',
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
    select: [],
  })

  function doAppend() {
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
    const batch = record === null
    if (batch) {
      if (selectedRowKeys.value.length === 0) {
        Message.error('请选择要删除的数据')
        return
      }
    }
    Modal.confirm({
      title: '提示',
      content: '是否要删除此元素？',
      cancelText: '取消',
      okText: '删除',
      onOk: () => {
        deleteUiElement(batch ? selectedRowKeys.value : record.id)
          .then((res) => {
            Message.success(res.msg)
          })
          .catch(console.log)
          .finally(() => {
            doRefresh()
            if (batch) {
              selectedRowKeys.value = []
            }
          })
      },
    })
  }

  function onUpdate(record: any) {
    data.actionTitle = '编辑'
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
      let value = getFormItems(formItems)
      value['page'] = route.query.id
      if (data.isAdd) {
        value['is_iframe'] = 0
        postUiElement(value)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
            modalDialogRef.value?.toggle()
          })
          .catch((error) => {
            console.log(error)
          })
          .finally(() => {
            modalDialogRef.value?.setConfirmLoading(false)
          })
      } else {
        value['id'] = data.updateId
        putUiElement(value)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
            modalDialogRef.value?.toggle()
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

  function doResetSearch() {
    window.history.back()
  }

  function doRefresh() {
    let value = {}
    value['page'] = pagination.page
    value['pageSize'] = pagination.pageSize
    value['page_id'] = route.query.id
    getUiElement(value)
      .then((res) => {
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
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

  function changeStatus(event: number) {
    data.type = event
    for (let i = formItems1.length - 1; i >= 0; i--) {
      if (formItems1[i].key !== 'type') {
        formItems1.splice(i, 1)
      }
    }
    if (event === 0) {
      formItems1.push(...opeForm)
    } else if (event === 1) {
      formItems1.push({
        label: '断言操作',
        key: 'ope_key',
        value: ref(''),
        type: 'cascader',
        required: true,
        placeholder: '请选择断言类型',
        validator: function () {
          if (!this.value && this.value !== 0) {
            Message.error(this.placeholder || '')
            return false
          }
          return true
        },
      })
    }
  }

  function upDataOpeValue(selectData: any, value: any) {
    const inputItem = findItemByValue(selectData, value)
    if (inputItem && inputItem.parameter) {
      inputItem.parameter.forEach((select: any) => {
        if (select.d === true && !formItems1.some((item) => item.key === select.f)) {
          formItems1.push({
            label: select.n ? select.n : select.f,
            key: `${select.f}-ope_value`,
            value: select.v,
            type: 'textarea',
            required: true,
            placeholder: select.p,
            validator: function () {
              if (!this.value && this.value !== 0) {
                Message.error(this.placeholder || '')
                return false
              }
              return true
            },
          })
        } else if (select.d === false && !formItems.some((item) => item.key === select.f)) {
          data.select = select
        } else {
          data.select = []
        }
      })
    }
  }

  function onDataForm1() {
    if (formItems1.every((it) => (it.validator ? it.validator() : true))) {
      let value = getFormItems(formItems1)
      const extractedValues = []

      for (const key in value) {
        if (key.includes('-ope_value')) {
          const newKey = key.replace('-ope_value', '')
          if (newKey && data.type === 0) {
            findItemByValue(
              String(pageData.record.project_product.ui_client_type === '0')
                ? useSelectValue.webOpe
                : useSelectValue.androidOpe,
              value.ope_key
            ).parameter.forEach((item: any) => {
              if (newKey === 'locating') {
                value['ele_name'] = value[key]
              }
              if (item.f === newKey) {
                extractedValues.push({
                  f: newKey,
                  v: value[key],
                  d: item.d,
                })
              }
            })
          } else {
            findItemByValue(
              String(pageData.record.project_product.ui_client_type === '0')
                ? useSelectValue.assWeb
                : useSelectValue.assAndroid,
              value.ope_key
            ).parameter.forEach((item: any) => {
              if (newKey === 'actual') {
                value['ele_name'] = value[key]
              }
              if (item.f === newKey) {
                extractedValues.push({
                  f: newKey,
                  v: value[key],
                  d: item.d,
                })
              }
            })
          }
          delete value[key]
        }
      }
      value['ope_value'] = extractedValues
      if (data.select && typeof data.select === 'object' && !Array.isArray(data.select)) {
        value['ope_value'] = value['ope_value'] || []
        value['ope_value'].push(data.select)
      }
      value['test_env'] = userStore.selected_environment
      value['id'] = data.id
      value['page_id'] = pageData.record.id
      value['project_product_id'] = pageData.record.project_product.id
      value['type'] = data.type
      value['is_send'] = true
      putUiUiElementTest(value)
        .then((res) => {
          Message.success(res.msg)
          // 只有在成功的情况下才关闭模态框
          modalDialogRef1.value?.toggle()
        })
        .catch((error) => {
          console.log(error)
        })
        .finally(() => {
          // 重置 loading 状态
          modalDialogRef1.value?.setConfirmLoading(false)
        })
    } else {
      // 表单验证失败时也需要重置 loading 状态
      modalDialogRef1.value?.setConfirmLoading(false)
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

  function onContinuousSubmit() {
    if (formItems.every((it) => (it.validator ? it.validator() : true))) {
      let value = getFormItems(formItems)
      value['page'] = route.query.id
      if (data.isAdd) {
        value['is_iframe'] = 0
        postUiElement(value)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
            // 成功后不清空表单，保持模态框打开以便连续提交
          })
          .catch((error) => {
            console.log(error)
            Message.error('操作失败，请重试')
          })
          .finally(() => {
            modalDialogRef.value?.setContinuousLoading(false)
          })
      } else {
        Message.warning('编辑模式下不支持连续提交')
        modalDialogRef.value?.setContinuousLoading(false)
      }
    } else {
      // 表单验证失败时也需要重置 loading 状态
      modalDialogRef.value?.setContinuousLoading(false)
    }
  }

  onMounted(() => {
    nextTick(async () => {
      doRefresh()
      useSelectValue.getSelectValue()
    })
  })
</script>
<style scoped>
  .container .a-space span {
    font-size: 14px !important;
    display: block;
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .custom-upload :deep(.arco-btn) {
    height: 28px;
    width: 88px;
    line-height: 28px;
  }

  .custom-upload :deep(.arco-btn-text) {
    height: 28px;
    width: 88px;

    line-height: 28px;
  }
</style>
