<template>
  <div>
    <div class="main-container">
      <TableBody ref="tableBody">
        <template #header>
          <TableHeader
            :show-filter="true"
            title="接口信息收集"
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
                  <template v-else-if="item.type === 'select' && item.key === 'module'">
                    <a-select
                      style="width: 150px"
                      v-model="item.value"
                      :placeholder="item.placeholder"
                      :options="data.moduleList"
                      :field-names="fieldNames"
                      value-key="key"
                      allow-clear
                      allow-search
                      @change="doRefresh"
                    />
                  </template>
                  <template v-else-if="item.type === 'select' && item.key === 'client'">
                    <a-select
                      style="width: 150px"
                      v-model="item.value"
                      :placeholder="item.placeholder"
                      :options="data.apiPublicEnd"
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
          <a-tabs @tab-click="(key) => switchType(key)" default-active-key="1">
            <template #extra>
              <a-space v-if="data.apiType === '0'">
                <a-button type="primary" size="small" @click="onBatchUpload">录制</a-button>
                <a-button type="primary" size="small" @click="onImport">导入</a-button>
                <a-button status="success" size="small" @click="onConcurrency">批量执行</a-button>
                <a-button status="warning" size="small" @click="setCase('设为调试')"
                  >设为调试</a-button
                >
                <a-button status="danger" size="small" @click="onDeleteItems">批量删除</a-button>
              </a-space>
              <a-space v-else-if="data.apiType === '1'">
                <a-button type="primary" size="small" @click="onAddPage">新增</a-button>
                <a-button status="success" size="small" @click="onConcurrency">批量执行</a-button>
                <a-button status="warning" size="small" @click="setCase('调试完成')"
                  >调试完成</a-button
                >
                <a-button status="danger" size="small" @click="onDeleteItems">批量删除</a-button>
              </a-space>
            </template>
            <a-tab-pane key="0" title="批量生成" />
            <a-tab-pane key="1" title="调试接口" />
          </a-tabs>
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
                :ellipsis="item.ellipsis"
                :tooltip="item.tooltip"
              >
                <template v-if="item.key === 'index'" #cell="{ record }">
                  {{ record.id }}
                </template>
                <template v-else-if="item.key === 'project_product'" #cell="{ record }">
                  {{ record.project_product?.project?.name + '/' + record.project_product?.name }}
                </template>
                <template v-else-if="item.key === 'module'" #cell="{ record }">
                  {{ record.module?.superior_module ? record.module?.superior_module + '/' : ''
                  }}{{ record.module?.name }}
                </template>
                <template v-else-if="item.key === 'client'" #cell="{ record }">
                  <a-tag color="arcoblue" size="small" v-if="record.client === 0">WEB</a-tag>
                  <a-tag color="magenta" size="small" v-else-if="record.client === 1">APP</a-tag>
                  <a-tag color="green" size="small" v-else-if="record.client === 2">MINI</a-tag>
                </template>
                <template v-else-if="item.key === 'method'" #cell="{ record }">
                  <a-tag color="orangered" size="small" v-if="record.method === 0">GET</a-tag>
                  <a-tag color="gold" size="small" v-else-if="record.method === 1">POST</a-tag>
                  <a-tag color="arcoblue" size="small" v-else-if="record.method === 2">PUT</a-tag>
                  <a-tag color="magenta" size="small" v-else-if="record.method === 3">DELETE</a-tag>
                </template>
                <template v-else-if="item.key === 'status'" #cell="{ record }">
                  <a-tag color="green" size="small" v-if="record.status === 1">通过</a-tag>
                  <a-tag color="red" size="small" v-else-if="record.status === 2">失败</a-tag>
                  <a-tag color="gray" size="small" v-else>未测试</a-tag>
                </template>
                <template v-else-if="item.key === 'actions'" #cell="{ record }">
                  <template>
                    <a-button @click="onRunCase">Open Modal</a-button>
                    <a-modal
                      width="50%"
                      v-model:visible="visible"
                      @ok="handleOk"
                      @cancel="handleCancel"
                    >
                      <template #title> {{ record.name }}接口-测试结果</template>
                      <a-space direction="vertical">
                        <!-- eslint-disable-next-line vue/valid-v-for -->
                        <a-space v-for="(value, key) in data.caseResult">
                          <a-tag class="header-tag" color="#0fc6c2">{{ key }}</a-tag>
                          <span>{{ value }}</span>
                        </a-space>
                      </a-space>
                    </a-modal>
                  </template>
                  <a-button type="text" size="mini" @click="onRunCase(record)">执行</a-button>
                  <a-button type="text" size="mini" @click="onStep(record)">详情</a-button>
                  <a-dropdown trigger="hover">
                    <a-button type="text" size="mini">···</a-button>
                    <template #content>
                      <a-doption>
                        <a-button type="text" size="mini" @click="onUpdate(record)"
                          >编辑</a-button
                        ></a-doption
                      >
                      <a-doption>
                        <a-button type="text" size="mini" @click="apiInfoCopy(record)"
                          >复制</a-button
                        >
                      </a-doption>
                      <a-doption>
                        <a-button status="danger" type="text" size="mini" @click="onDelete(record)"
                          >删除</a-button
                        >
                      </a-doption>
                    </template>
                  </a-dropdown>
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
              <template v-else-if="item.type === 'textarea'">
                <a-textarea
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :auto-size="{ minRows: 3, maxRows: 5 }"
                />
              </template>
              <template v-else-if="item.type === 'cascader'">
                <a-cascader
                  v-model="item.value"
                  @change="onProductModuleName(item.value)"
                  :placeholder="item.placeholder"
                  :options="projectInfo.projectProduct"
                  allow-search
                  allow-clear
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'module'">
                <a-select
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="data.moduleList"
                  :field-names="fieldNames"
                  value-key="key"
                  allow-clear
                  allow-search
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'client'">
                <a-select
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="data.apiPublicEnd"
                  :field-names="fieldNames"
                  value-key="key"
                  allow-clear
                  allow-search
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'method'">
                <a-select
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="data.apiMethodType"
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
  import { onMounted, ref, reactive, nextTick } from 'vue'
  import { useTestObj } from '@/store/modules/get-test-obj'
  import { getFormItems } from '@/utils/datacleaning'
  import { fieldNames } from '@/setting'
  import { useProject } from '@/store/modules/get-project'
  import { useProjectModule } from '@/store/modules/project_module'
  import { usePageData } from '@/store/page-data'
  import { useRouter } from 'vue-router'
  import { tableColumns, formItems, conditionItems } from './config'
  import {
    deleteApiInfo,
    getApiCaseInfoRun,
    getApiInfo,
    postApiCopyInfo,
    postApiInfo,
    putApiInfo,
    putApiPutApiInfoType,
  } from '@/api/apitest'
  import { getUiConfigNewBrowserObj } from '@/api/uitest'
  import { getSystemEnumEnd, getSystemEnumMethod } from '@/api/system'
  import { getUserModuleName } from '@/api/user'

  const router = useRouter()

  const projectModule = useProjectModule()

  const projectInfo = useProject()
  const testObj = useTestObj()
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const pagination = usePagination(doRefresh)
  const { selectedRowKeys, onSelectionChange, showCheckedAll } = useRowSelection()
  const table = useTable()
  const rowKey = useRowKey('id')
  const formModel = ref({})

  const data = reactive({
    actionTitle: '添加接口',
    isAdd: false,
    updateId: 0,
    apiType: '1',
    caseResult: {},
    apiPublicEnd: [],
    apiMethodType: [],
    moduleList: projectModule.data,
  })
  const visible = ref(false)

  const handleOk = () => {
    visible.value = false
  }
  const handleCancel = () => {
    visible.value = false
  }

  function switchType(key: any) {
    data.apiType = key
    doRefresh()
  }

  function doRefresh() {
    let value = getFormItems(conditionItems)
    value['page'] = pagination.page
    value['type'] = data.apiType
    value['pageSize'] = pagination.pageSize
    getApiInfo(value)
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
  }

  function onAddPage() {
    data.actionTitle = '新建接口'
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

  function onUpdate(item: any) {
    data.actionTitle = '编辑公共参数'
    data.isAdd = false
    data.updateId = item.id
    modalDialogRef.value?.toggle()
    onProductModuleName(item.project_product.id)
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

  function onBatchUpload() {
    Modal.confirm({
      title: '注意事项',
      content:
        '录制接口只支持web端，开始时会结合执行器启动一个浏览器，用例会自动绑定给所选择的项目，请确认是否已选择项目；使用所选择测试环境的域名进行进行过滤请求，请确认是否准备完成！',
      cancelText: '取消',
      okText: '确定',
      onOk: () => {
        getUiConfigNewBrowserObj(1)
          .then((res) => {
            Message.success(res.msg)
          })
          .catch(console.log)
      },
    })
  }
  function onImport() {
    Modal.input({
      title: '请输入数据',
      content: '请输入您要传递给后端的数据：',
      onOk: (value: any) => {
        // 在这里可以将输入的数据传递给后端
        console.log(value)
      },
      onCancel: () => {
        Message.success('取消输入')
      },
    })
  }

  function onDelete(data: any) {
    Modal.confirm({
      title: '提示',
      content: '是否要删除此接口？',
      cancelText: '取消',
      okText: '删除',
      onOk: () => {
        deleteApiInfo(data.id)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      },
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
        deleteApiInfo(selectedRowKeys.value)
          .then((res) => {
            Message.success(res.msg)
            selectedRowKeys.value = []
            doRefresh()
          })
          .catch(console.log)
      },
    })
  }

  function setCase(name: any) {
    if (selectedRowKeys.value.length === 0) {
      Message.error('请选择要设为' + name + '的数据')
      return
    }
    let type: any = 1
    if (name === '调试完成') {
      type = 2
    }
    Modal.confirm({
      title: '提示',
      content: '确定要把这些设为' + name + '的吗？',
      cancelText: '取消',
      okText: '确定',
      onOk: () => {
        putApiPutApiInfoType(selectedRowKeys.value, type)
          .then((res) => {
            Message.success(res.msg)
            selectedRowKeys.value = []
            doRefresh()
          })
          .catch(console.log)
      },
    })
  }

  function onDataForm() {
    if (formItems.every((it) => (it.validator ? it.validator() : true))) {
      modalDialogRef.value?.toggle()
      let value = getFormItems(formItems)
      value['type'] = data.apiType
      if (data.isAdd) {
        postApiInfo(value)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      } else {
        value['id'] = data.updateId
        putApiInfo(value)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      }
    }
  }

  // 获取所有项目
  function onRunCase(record: any) {
    if (testObj.selectValue == null) {
      Message.error('请先选择用例执行的环境')
      return
    }
    Message.loading('接口开始执行中~')
    getApiCaseInfoRun(record.id, testObj.selectValue)
      .then((res) => {
        data.caseResult = res.data
        visible.value = true
      })
      .catch(console.log)
  }

  function onConcurrency() {
    Message.loading('调用了并发按钮')
  }

  function doEnd() {
    getSystemEnumEnd()
      .then((res) => {
        data.apiPublicEnd = res.data
      })
      .catch(console.log)
  }

  function doMethod() {
    getSystemEnumMethod()
      .then((res) => {
        data.apiMethodType = res.data
      })
      .catch(console.log)
  }

  function onProductModuleName(projectId: number) {
    getUserModuleName(projectId)
      .then((res) => {
        data.moduleList = res.data
      })
      .catch(console.log)
  }
  function apiInfoCopy(record: any) {
    postApiCopyInfo(record.id)
      .then((res) => {
        Message.success(res.msg)
        doRefresh()
      })
      .catch(console.log)
  }
  function onStep(record: any) {
    const pageData = usePageData()
    pageData.setRecord(record)
    router.push({
      path: '/apitest/info/details',
      query: {
        case_id: record.id,
        test_suite_id: record.test_suite_id,
      },
    })
  }
  onMounted(() => {
    nextTick(async () => {
      doRefresh()
      doEnd()
      doMethod()
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

  .header-tag {
    width: 100px; /* 设置标签的宽度 */
  }
</style>
