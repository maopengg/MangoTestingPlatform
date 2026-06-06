<template>
  <TableBody ref="tableBody">
    <template #header>
      <TableHeader
        :show-filter="true"
        title="接口信息收集"
        @search="onSearchRefresh"
        @reset-search="onResetSearch"
      >
        <template #search-content>
          <a-form :model="{}" layout="inline" @keyup.enter="onSearchRefresh">
            <a-form-item v-for="item of conditionItems" :key="item.key" :label="item.label">
              <template v-if="item.type === 'input'">
                <a-input
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  allow-clear
                  @blur="onSearchRefresh"
                  @clear="onSearchRefresh"
                />
              </template>
              <template v-else-if="item.type === 'cascader' && item.key === 'project_product'">
                <ProjectProductSelect
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  @change="onSearchProjectProductChange"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'module'">
                <ProductModuleSelect
                  v-model="item.value"
                  :project-product-id="getConditionValue('project_product')"
                  :placeholder="item.placeholder"
                  :auto-clear="false"
                  @change="onSearchRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'status'">
                <a-select
                  v-model="item.value"
                  :field-names="fieldNames"
                  :options="enumStore.task_status"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="onSearchRefresh"
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
                  <a-checkbox v-for="it of item.optionItems" :key="it.value" :value="it.value">
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
      <a-tabs default-active-key="1" @tab-click="(key) => switchType(key)">
        <template #extra>
          <a-space v-if="data.apiType === '0'">
            <a-button size="small" type="primary" @click="onBatchUpload">录制</a-button>
            <a-button size="small" type="primary" @click="showBatchImportModal">批量导入</a-button>
            <a-button size="small" status="success" :loading="caseRunning" @click="onConcurrency"
              >批量执行
            </a-button>
            <a-button
              size="small"
              status="success"
              :loading="setDebugLoading"
              @click="setCase('设为调试')"
              >设为调试</a-button
            >
            <a-button size="small" status="danger" @click="onDelete(null)">批量删除</a-button>
          </a-space>
          <a-space v-else-if="data.apiType === '1'">
            <a-button size="small" type="primary" @click="onAdd(0)">新增</a-button>
            <a-button type="primary" size="small" @click="onAdd(1)">导入</a-button>
            <a-button size="small" status="success" :loading="caseRunning" @click="onConcurrency"
              >批量执行
            </a-button>
            <a-button size="small" status="danger" @click="onDelete(null)">批量删除</a-button>
          </a-space>
        </template>
        <a-tab-pane key="0" title="批量生成" />
        <a-tab-pane key="1" title="调试接口" />
      </a-tabs>
      <a-table
        :bordered="false"
        :columns="tableColumns"
        :data="table.dataList"
        :loading="table.tableLoading.value"
        :pagination="false"
        :row-selection="{ selectedRowKeys, showCheckedAll }"
        :rowKey="rowKey"
        :scroll="{ x: 1380 }"
        @selection-change="onSelectionChange"
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
            <template v-else-if="item.key === 'project_product'" #cell="{ record }">
              {{ formatProjectProductPath(record?.project_product) }}
            </template>
            <template v-else-if="item.key === 'module'" #cell="{ record }">
              {{ formatModulePath(record?.module) }}
            </template>
            <template v-else-if="item.key === 'client'" #cell="{ record }">
              <a-tag :color="enumStore.colors[record.project_product.api_client_type]" size="small"
                >{{ enumStore.api_client[record.project_product.api_client_type]?.title }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'method'" #cell="{ record }">
              <a-tag :color="enumStore.colors[record.method]" size="small"
                >{{ enumStore.method[record.method]?.title || '-' }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'status'" #cell="{ record }">
              <a-tag :color="enumStore.status_colors[record.status]" size="small"
                >{{ enumStore.task_status[record.status]?.title || '-' }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'is_schema'" #cell="{ record }">
              <a-switch
                :beforeChange="(newValue) => onModifyStatus(newValue, record.id, 'is_schema')"
                :default-checked="record.is_schema === 1"
              />
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <template>
                <a-modal
                  v-model:visible="visible"
                  width="55%"
                  @cancel="handleCancel"
                  @ok="handleOk"
                >
                  <template #title>
                    {{ data.caseResult.name ? data.caseResult.name : '' }}接口-测试结果
                  </template>

                  <div class="case-result-scroll">
                    <a-space direction="vertical">
                      <a-space>
                        <a-tag color="orange">响 应 码</a-tag>
                        <span>{{ data.caseResult.code }}</span>
                      </a-space>
                      <a-space>
                        <a-tag color="orange">响应时间</a-tag>
                        <span>{{ data.caseResult.time }}</span>
                      </a-space>
                      <a-space>
                        <a-tag color="orange">响 应 体</a-tag>
                        <pre>{{
                          strJson(
                            data.caseResult.json ? data.caseResult.json : data.caseResult.text
                          )
                        }}</pre>
                      </a-space>
                    </a-space>
                  </div>
                </a-modal>
              </template>
              <MangoTableActions
                :actions="[
                  { label: '执行', loading: caseRunning, onClick: () => onRunCase(record) },
                  { label: '详情', onClick: () => onStep(record) },
                  { label: '编辑', onClick: () => onUpdate(record) },
                  { label: '复制', onClick: () => apiInfoCopy(record) },
                  { label: '删除', danger: true, onClick: () => onDelete(record) },
                ]"
              />
            </template>
          </a-table-column>
        </template>
      </a-table>
    </template>
    <template #footer>
      <TableFooter :pagination="pagination" />
    </template>
  </TableBody>

  <a-modal
    v-model:visible="batchImportVisible"
    title="批量导入"
    :ok-loading="batchImportLoading"
    @ok="handleBatchImportOk"
    @cancel="handleBatchImportCancel"
  >
    <a-space direction="vertical" class="batch-import-content">
      <a-button type="primary" :loading="downloadLoading" @click="onDownload">下载模板</a-button>
      <a-space>
        <a-switch
          v-model="debugInterface"
          :checked-value="1"
          :unchecked-value="0"
          checked-text="调试接口"
          unchecked-text="批量生成" />
        <TipMessage message="如果需要直接上传到调试接口Tab里面，请点击开关打开"
      /></a-space>
      <div class="batch-import-file">
        <a-button type="primary" @click="fileInputRef?.click()">选择文件</a-button>
        <span v-if="selectedFile" class="batch-import-filename"
          >已选择: {{ selectedFile.name }}</span
        >
        <input
          ref="fileInputRef"
          type="file"
          accept=".xlsx,.xls"
          class="batch-import-input"
          @change="handleFileSelect"
        />
      </div>
    </a-space>
  </a-modal>

  <ModalDialog ref="modalDialogRef" :title="data.actionTitle" @confirm="onDataForm">
    <template #content>
      <a-form :model="formModel">
        <a-form-item
          v-for="item of data.formItem"
          :key="item.key"
          :class="[item.required ? 'mango-form-item__require' : 'mango-form-item__no_require']"
          :label="item.label"
        >
          <template v-if="item.type === 'input'">
            <a-input v-model="item.value" :placeholder="item.placeholder" />
          </template>
          <template v-else-if="item.type === 'cascader'">
            <ProjectProductSelect
              v-model="item.value"
              :placeholder="item.placeholder"
              @change="onFormProjectProductChange"
            />
          </template>
          <template v-else-if="item.key === 'module'">
            <ProductModuleSelect
              v-model="item.value"
              :project-product-id="getFormItemValue('project_product')"
              :placeholder="item.placeholder"
              :auto-clear="false"
            />
          </template>
          <template v-else-if="item.key === 'method'">
            <a-select
              v-model="item.value"
              :field-names="fieldNames"
              :options="enumStore.method"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              value-key="key"
            />
          </template>
          <template v-else-if="item.key === 'curl_command'">
            <a-textarea
              v-model="item.value"
              :placeholder="item.placeholder"
              allow-clear
              :auto-size="{ minRows: 3, maxRows: 5 }"
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
  import { onMounted, ref, reactive, nextTick, onUnmounted } from 'vue'
  import { getFormItems } from '@/utils/datacleaning'
  import { fieldNames } from '@/setting'
  import { usePageData } from '@/store/page-data'
  import { useRouter } from 'vue-router'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import {
    formatModulePath,
    formatProjectProductPath,
    getItemValue,
    setItemValue,
  } from '@/utils/business-format'
  import { tableColumns, formItems, conditionItems, formItemsImport } from './config'
  import {
    deleteApiInfo,
    getApiCaseInfoRun,
    getApiInfo,
    postApiCopyInfo,
    postApiImportUrl,
    postApiInfo,
    postApiUploadApi,
    putApiInfo,
    putApiPutApiInfoType,
  } from '@/api/apitest/info'
  import { useEnum } from '@/store/modules/get-enum'
  import useUserStore from '@/store/modules/user'
  import { strJson } from '@/utils/tools'
  import { getSystemSocketNewBrowser } from '@/api/system/socket_api'
  import TipMessage from '@/components/feedback/TipMessage.vue'

  const router = useRouter()
  const enumStore = useEnum()

  const userStore = useUserStore()

  const modalDialogRef = ref<ModalDialogType | null>(null)
  const pagination = usePagination(doRefresh)
  const { selectedRowKeys, onSelectionChange, showCheckedAll } = useRowSelection()
  const table = useTable()
  const rowKey = useRowKey('id')
  const formModel = ref({})

  const data: any = reactive({
    actionTitle: '新增',
    isAdd: false,
    addType: 0,
    updateId: 0,
    apiType: '1',
    caseResult: {},
    apiPublicEnd: [],
    formItem: [],
  })
  const caseRunning = ref(false)
  const setDebugLoading = ref(false)
  const downloadLoading = ref(false)
  const pollingTimer = ref<NodeJS.Timeout | null>(null)

  function clearPollingTimer() {
    if (pollingTimer.value) {
      clearInterval(pollingTimer.value)
      pollingTimer.value = null
    }
  }

  const visible = ref(false)
  const batchImportVisible = ref(false)
  const batchImportLoading = ref(false)
  const debugInterface = ref(0) // 调试接口开关，默认为0
  const fileInputRef = ref<HTMLInputElement | null>(null)
  const selectedFile = ref<File | null>(null) // 存储选中的文件

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

  function getConditionValue(key: string) {
    return getItemValue(conditionItems, key)
  }

  function getFormItemValue(key: string) {
    return getItemValue(data.formItem, key)
  }

  function onSearchProjectProductChange(value: any) {
    setItemValue(conditionItems, 'module', null)
    doRefresh(value, true, true)
  }

  function onFormProjectProductChange() {
    setItemValue(data.formItem, 'module', null)
  }

  function onSearchRefresh() {
    doRefresh(null, false, true)
  }

  function doRefresh(projectProductId: any = null, bool_ = false, showLoading = false) {
    clearPollingTimer()
    if (showLoading) {
      table.tableLoading.value = true
    }
    let value = getFormItems(conditionItems)
    value['page'] = pagination.page
    value['type'] = data.apiType
    value['pageSize'] = pagination.pageSize
    if (projectProductId && bool_) {
      value['project_product'] = projectProductId
    }
    getApiInfo(value)
      .then((res) => {
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
        const hasRunningItem =
          res.data && Array.isArray(res.data) && res.data.some((item: any) => item.status === 3)

        if (hasRunningItem) {
          // 5秒后再次刷新
          pollingTimer.value = setInterval(() => {
            doRefresh()
          }, 5000)
        }
      })
      .catch(console.log)
      .finally(() => {
        if (showLoading) {
          table.tableLoading.value = false
        }
      })
  }

  function onResetSearch() {
    conditionItems.forEach((it) => {
      it.value = it.key === 'project_product' || it.key === 'module' ? null : ''
    })
    doRefresh(null, false, true)
  }

  function onAdd(type: number) {
    data.addType = type
    if (type === 0) {
      data.actionTitle = '新增'
      data.isAdd = true
      modalDialogRef.value?.toggle()
      data.formItem = formItems
      formItems.forEach((it) => {
        if (it.reset) {
          it.reset()
        } else {
          it.value = ''
        }
      })
    } else if (type === 1) {
      data.actionTitle = '导入接口'
      data.isAdd = true
      modalDialogRef.value?.toggle()
      data.formItem = formItemsImport
      formItemsImport.forEach((it) => {
        if (it.reset) {
          it.reset()
        } else {
          it.value = ''
        }
      })
    }
  }

  function onUpdate(item: any) {
    data.actionTitle = '编辑'
    data.addType = 0
    data.isAdd = false
    data.updateId = item.id
    modalDialogRef.value?.toggle()
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
    data.formItem = formItems
  }

  function onDownload() {
    if (downloadLoading.value) return
    downloadLoading.value = true
    const file_name = '接口批量上传模版.xlsx'
    const file_path = `/api/download?file_name=${encodeURIComponent(file_name)}`
    let aLink = document.createElement('a')
    aLink.href = file_path
    aLink.download = file_name
    Message.loading('文件下载中~')
    document.body.appendChild(aLink)
    aLink.click()
    document.body.removeChild(aLink)
    window.setTimeout(() => {
      downloadLoading.value = false
    }, 500)
  }

  // 新增的批量导入弹窗功能
  function showBatchImportModal() {
    batchImportVisible.value = true
    // 重置文件和开关状态
    if (fileInputRef.value) {
      fileInputRef.value.value = ''
    }
    debugInterface.value = 0
    selectedFile.value = null
  }

  function handleBatchImportOk() {
    // 点击确定时才进行上传
    if (!selectedFile.value) {
      Message.warning('请先选择要上传的文件')
      return
    }

    if (batchImportLoading.value) return
    batchImportLoading.value = true
    postApiUploadApi(debugInterface.value, selectedFile.value)
      .then((res) => {
        Message.success(res.msg)
        batchImportVisible.value = false
        doRefresh()
        // 重置状态
        if (fileInputRef.value) {
          fileInputRef.value.value = ''
        }
        selectedFile.value = null
        debugInterface.value = 0
      })
      .catch((error) => {
        Message.error('上传失败')
      })
      .finally(() => {
        batchImportLoading.value = false
      })
  }

  function handleBatchImportCancel() {
    batchImportVisible.value = false
    // 重置状态
    if (fileInputRef.value) {
      fileInputRef.value.value = ''
    }
    selectedFile.value = null
    debugInterface.value = 0
  }

  function handleFileSelect(event: Event) {
    const target = event.target as HTMLInputElement
    const files = target.files
    if (files && files.length > 0) {
      selectedFile.value = files[0]
      // 仅选择文件，不立即上传
      Message.info(`已选择文件: ${selectedFile.value.name}`)
    } else {
      selectedFile.value = null
    }
  }

  const onModifyStatus = async (newValue: boolean, id: number, is_schema: number) => {
    return new Promise<any>((resolve, reject) => {
      setTimeout(async () => {
        try {
          let value: any = false
          await putApiInfo({ id: id, [is_schema]: newValue ? 1 : 0 })
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

  function onBatchUpload() {
    Modal.confirm({
      title: '注意事项',
      content:
        '录制接口只支持web端，开始时会结合执行器启动一个浏览器，用例会自动绑定给所选择的项目，请确认是否已选择项目；使用所选择测试环境的域名进行进行过滤请求，请确认是否准备完成！',
      cancelText: '取消',
      okText: '确定',
      onBeforeOk: () => {
        return getSystemSocketNewBrowser(null, 1)
          .then((res) => {
            Message.success(res.msg)
          })
          .catch(console.log)
      },
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
      content: '是否要删除此接口？',
      cancelText: '取消',
      okText: '删除',
      onBeforeOk: () => {
        return deleteApiInfo(batch ? selectedRowKeys.value : record.id)
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

  function setCase(name: any) {
    if (selectedRowKeys.value.length === 0) {
      Message.error('请选择要设为' + name + '的数据')
      return
    }
    let type: any = 1
    Modal.confirm({
      title: '提示',
      content: '确定要把这些设为' + name + '的吗？',
      cancelText: '取消',
      okText: '确定',
      onBeforeOk: () => {
        setDebugLoading.value = true
        return putApiPutApiInfoType(selectedRowKeys.value, type)
          .then((res) => {
            Message.success(res.msg)
            selectedRowKeys.value = []
            doRefresh()
          })
          .catch(console.log)
          .finally(() => {
            setDebugLoading.value = false
          })
      },
    })
  }

  function onDataForm() {
    if (data.addType == 0) {
      if (formItems.every((it) => (it.validator ? it.validator() : true))) {
        let value = getFormItems(formItems)
        value['type'] = data.apiType
        value['front_json_path'] = []
        value['front_re'] = []
        if (data.isAdd) {
          postApiInfo(value)
            .then((res) => {
              Message.success(res.msg)
              modalDialogRef.value?.toggle()
              doRefresh()
            })
            .catch((error) => {
              console.log(error)
            })
            .finally(() => {
              modalDialogRef.value?.setConfirmLoading(false)
            })
        } else {
          value['id'] = data.updateId
          putApiInfo(value)
            .then((res) => {
              Message.success(res.msg)
              modalDialogRef.value?.toggle()
              doRefresh()
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
    } else if (data.addType === 1) {
      if (formItemsImport.every((it) => (it.validator ? it.validator() : true))) {
        let value = getFormItems(formItemsImport)
        value['type'] = data.apiType
        postApiImportUrl(value)
          .then((res) => {
            Message.success(res.msg)
            modalDialogRef.value?.toggle()
            doRefresh()
          })
          .catch((error) => {
            console.log(error)
          })
          .finally(() => {
            modalDialogRef.value?.setConfirmLoading(false)
          })
      } else {
        modalDialogRef.value?.setConfirmLoading(false)
      }
    } else {
      modalDialogRef.value?.setConfirmLoading(false)
    }
  }

  const onRunCase = async (param) => {
    if (userStore.selected_environment == null) {
      Message.error('请先选择用例执行的环境')
      return
    }
    if (caseRunning.value) return
    caseRunning.value = true
    try {
      const res = await getApiCaseInfoRun(param.id, userStore.selected_environment)
      if (res.data.error_msg) {
        Message.error(res.data.error_msg)
      } else {
        Message.success(res.msg)
      }
    } catch (e) {
    } finally {
      caseRunning.value = false
      doRefresh()
    }
  }

  const onConcurrency = async () => {
    if (userStore.selected_environment == null) {
      Message.error('请先选择测试环境')
      return
    }
    if (selectedRowKeys.value.length === 0) {
      Message.error('请选择要执行的接口')
      return
    }
    Message.loading('开始批量执行中~')
    if (caseRunning.value) return
    caseRunning.value = true
    try {
      const res = await getApiCaseInfoRun(selectedRowKeys.value, userStore.selected_environment)
      Message.success(res.msg)
    } catch (e) {
    } finally {
      caseRunning.value = false
      doRefresh()
    }
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
    })
  })
  onUnmounted(() => {
    clearPollingTimer()
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
      border: 2px solid var(--m-warning);
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

  .case-result-scroll {
    max-height: 400px;
    overflow-y: auto;
  }

  .batch-import-content {
    width: 100%;
  }

  .batch-import-file {
    margin-top: 10px;
  }

  .batch-import-filename {
    margin-left: 10px;
  }

  .batch-import-input {
    display: none;
  }
</style>
