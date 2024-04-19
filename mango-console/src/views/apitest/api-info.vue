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
                  <template v-else-if="item.type === 'select' && item.key === 'module_name'">
                    <a-select
                      style="width: 150px"
                      v-model="item.value"
                      :placeholder="item.placeholder"
                      :options="apiInfoData.moduleList"
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
                      :options="apiInfoData.apiPublicEnd"
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
              <a-space v-if="apiInfoData.apiType === '0'">
                <a-button type="primary" size="small" @click="onBatchUpload">录制</a-button>
                <a-button type="primary" size="small" @click="onImport">导入</a-button>
                <a-button status="success" size="small" @click="onConcurrency">批量执行</a-button>
                <a-button status="warning" size="small" @click="setCase('设为调试')"
                  >设为调试</a-button
                >
                <a-button status="danger" size="small" @click="onDeleteItems">批量删除</a-button>
              </a-space>
              <a-space v-else-if="apiInfoData.apiType === '1'">
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
                <template v-else-if="item.key === 'module_name'" #cell="{ record }">
                  {{ record.module_name?.name }}
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
                        <a-space v-for="(value, key) in apiInfoData.caseResult">
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
      <ModalDialog ref="modalDialogRef" :title="apiInfoData.actionTitle" @confirm="onDataForm">
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
              <template v-else-if="item.type === 'select' && item.key === 'project'">
                <a-select
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="project.data"
                  :field-names="fieldNames"
                  @change="getProjectModule(item.value)"
                  value-key="key"
                  allow-clear
                  allow-search
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'module_name'">
                <a-select
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="apiInfoData.moduleList"
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
                  :options="apiInfoData.apiPublicEnd"
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
                  :options="apiInfoData.apiMethodType"
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
  import {
    apiInfo,
    apiCaseInfoRun,
    systemEnumEnd,
    systemEnumMethod,
    userProjectModuleGetAll,
    uiConfigNewBrowserObj,
    apiPutApiInfoType,
    apiCopyInfo,
  } from '@/api/url'
  import {
    usePagination,
    useRowKey,
    useRowSelection,
    useTable,
    useTableColumn,
  } from '@/hooks/table'
  import { FormItem, ModalDialogType } from '@/types/components'
  import { Message, Modal } from '@arco-design/web-vue'
  import { onMounted, ref, reactive, nextTick } from 'vue'
  import { useTestObj } from '@/store/modules/get-test-obj'
  import { getFormItems } from '@/utils/datacleaning'
  import { fieldNames } from '@/setting'
  import { useProject } from '@/store/modules/get-project'
  import { useProjectModule } from '@/store/modules/project_module'
  import { usePageData } from '@/store/page-data'
  import { useRouter } from 'vue-router'
  const router = useRouter()

  const projectModule = useProjectModule()

  const project = useProject()
  const testObj = useTestObj()
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const pagination = usePagination(doRefresh)
  const { selectedRowKeys, onSelectionChange, showCheckedAll } = useRowSelection()
  const table = useTable()
  const rowKey = useRowKey('id')
  const formModel = ref({})

  const apiInfoData = reactive({
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
  const conditionItems: Array<FormItem> = reactive([
    {
      key: 'id',
      label: 'ID',
      type: 'input',
      placeholder: '请输入接口ID',
      value: '',
      reset: function () {
        this.value = ''
      },
    },
    {
      key: 'name',
      label: '接口名称',
      type: 'input',
      placeholder: '请输入用例名称',
      value: '',
      reset: function () {
        this.value = ''
      },
    },
    {
      key: 'url',
      label: 'url',
      value: '',
      type: 'input',
      placeholder: '请先选择项目',
      reset: function () {},
    },
    {
      key: 'module_name',
      label: '模块',
      value: '',
      type: 'select',
      placeholder: '请先选择项目',
      optionItems: apiInfoData.moduleList,
      reset: function () {},
    },
    {
      key: 'client',
      label: '客户端类型',
      value: '',
      type: 'select',
      placeholder: '请选择客户端类型',
      optionItems: apiInfoData.moduleList,
      reset: function () {},
    },
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
      },
    },
    {
      label: '模块名称',
      key: 'module_name',
      value: '',
      type: 'select',
      required: true,
      placeholder: '请用例归属模块',
      validator: function () {
        if (!this.value && this.value !== 0) {
          Message.error(this.placeholder || '')
          return false
        }
        return true
      },
    },
    {
      label: '接口名称',
      key: 'name',
      value: '',
      type: 'input',
      required: true,
      placeholder: '请输入用例名称',
      validator: function () {
        if (!this.value && this.value !== '0') {
          Message.error(this.placeholder || '')
          return false
        }
        return true
      },
    },
    {
      label: '客户端类型',
      key: 'client',
      value: '',
      type: 'select',
      required: true,
      placeholder: '请设置客户端类型',
      validator: function () {
        if (!this.value && this.value !== 0) {
          Message.error(this.placeholder || '')
          return false
        }
        return true
      },
    },
    {
      label: 'url',
      key: 'url',
      value: '',
      type: 'input',
      required: true,
      placeholder: '请输入url',
    },
    {
      label: 'method',
      key: 'method',
      value: '',
      type: 'select',
      required: true,
      placeholder: '请选择接口方法',
      validator: function () {
        if (!this.value && this.value !== 0) {
          Message.error(this.placeholder || '')
          return false
        }
        return true
      },
    },
  ])

  const tableColumns = useTableColumn([
    table.indexColumn,
    {
      title: '模块名称',
      key: 'module_name',
      dataIndex: 'module_name',
      align: 'left',
      width: 100,
    },
    {
      title: '接口名称',
      key: 'name',
      dataIndex: 'name',
      align: 'left',
      width: 270,
    },

    {
      title: 'url',
      key: 'url',
      dataIndex: 'url',
      width: 500,
      align: 'left',
      ellipsis: true,
      tooltip: true,
    },
    {
      title: '端类型',
      key: 'client',
      dataIndex: 'client',
      width: 80,
    },
    {
      title: '方法',
      key: 'method',
      dataIndex: 'method',
      width: 80,
    },
    {
      title: '状态',
      key: 'status',
      dataIndex: 'status',
      width: 80,
    },
    {
      title: '操作',
      key: 'actions',
      dataIndex: 'actions',
      fixed: 'right',
      width: 170,
    },
  ])

  function switchType(key: any) {
    apiInfoData.apiType = key
    doRefresh()
  }

  function doRefresh() {
    get({
      url: apiInfo,
      data: () => {
        let value = getFormItems(conditionItems)
        value['page'] = pagination.page
        value['type'] = apiInfoData.apiType
        value['pageSize'] = pagination.pageSize
        return value
      },
    })
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
    apiInfoData.actionTitle = '新建接口'
    apiInfoData.isAdd = true
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
    apiInfoData.actionTitle = '编辑公共参数'
    apiInfoData.isAdd = false
    apiInfoData.updateId = item.id
    modalDialogRef.value?.toggle()
    getProjectModule(item.project.id)
    nextTick(() => {
      formItems.forEach((it) => {
        const propName = item[it.key]
        if (typeof propName === 'object' && propName !== null) {
          if (it.type === 'select') {
            it.value = propName.id
          } else {
            it.value = JSON.stringify(propName, null, '\t')
          }
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
        get({
          url: uiConfigNewBrowserObj,
          data: () => {
            return { is_recording: 1 }
          },
        })
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
        deleted({
          url: apiInfo,
          data: () => {
            return {
              id: '[' + data.id + ']',
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
          url: apiInfo,
          data: () => {
            return {
              id: JSON.stringify(selectedRowKeys.value),
            }
          },
        })
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
        put({
          url: apiPutApiInfoType,
          data: () => {
            return {
              id_list: selectedRowKeys.value,
              type: type,
            }
          },
        })
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
      value['type'] = apiInfoData.apiType
      if (apiInfoData.isAdd) {
        post({
          url: apiInfo,
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
          url: apiInfo,
          data: () => {
            value['id'] = apiInfoData.updateId
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

  // 获取所有项目
  function onRunCase(record: any) {
    if (testObj.selectValue == null) {
      Message.error('请先选择用例执行的环境')
      return
    }
    Message.loading('接口开始执行中~')
    get({
      url: apiCaseInfoRun,
      data: () => {
        return {
          id: record.id,
          test_obj_id: testObj.selectValue,
          project_id: record.project.id,
        }
      },
    })
      .then((res) => {
        apiInfoData.caseResult = res.data
        visible.value = true
      })
      .catch(console.log)
  }

  function onConcurrency() {
    Message.loading('调用了并发按钮')
  }

  function doEnd() {
    get({
      url: systemEnumEnd,
    })
      .then((res) => {
        apiInfoData.apiPublicEnd = res.data
      })
      .catch(console.log)
  }

  function doMethod() {
    get({
      url: systemEnumMethod,
    })
      .then((res) => {
        apiInfoData.apiMethodType = res.data
      })
      .catch(console.log)
  }

  function getProjectModule(projectId: number) {
    doRefresh()
    get({
      url: userProjectModuleGetAll,
      data: () => {
        return {
          project_id: projectId,
        }
      },
    })
      .then((res) => {
        apiInfoData.moduleList = res.data
      })
      .catch(console.log)
  }
  function apiInfoCopy(record: any) {
    post({
      url: apiCopyInfo,
      data: () => {
        return {
          id: record.id,
        }
      },
    })
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
        project: record.project.id,
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
