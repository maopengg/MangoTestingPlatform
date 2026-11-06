<template>
  <TableBody
    ref="tableBody"
    plain
    class="mango-detail-workbench-page"
    :sticky-horizontal-scroll="false"
  >
    <template #header>
      <TableHeader
        :show-filter="true"
        title="接口管理"
        @search="onSearchRefresh"
        @reset-search="onResetSearch"
      >
        <template v-if="false" #search-content>
          <a-form :model="{}" layout="inline" @keyup.enter="onSearchRefresh">
            <a-form-item v-for="item of headerConditionItems" :key="item.key" :label="item.label">
              <template v-if="item.type === 'input'">
                <a-input
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  allow-clear
                  @blur="onSearchRefresh"
                  @clear="onSearchRefresh"
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
              <template
                v-else-if="
                  item.type === 'select' && item.key === 'project_product__api_client_type'
                "
              >
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :field-names="fieldNames"
                  :options="enumStore.api_client"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="onSearchRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'method'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :field-names="fieldNames"
                  :options="enumStore.method"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="onSearchRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'protocol_type'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :options="item.optionItems"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  @change="onSearchRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'status'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :field-names="fieldNames"
                  :options="enumStore.task_status"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="onSearchRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'update_user'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :field-names="fieldNames"
                  :options="data.userList"
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
      <ProjectProductNavigationWorkbench
        ref="navigationCreateRef"
          contained-body
          show-modules
          :show-toolbar="false"
          :module-value="getConditionValue('module')"
          :reset-key="sidebarResetKey"
          @filter-change="onSidebarFilterChange"
          @search="onSearchRefresh"
          @reset-search="onResetSearch"
      >
        <template #search>
          <ApiInfoSearchFilters
            :items="headerConditionItems"
            :user-list="data.userList"
            :enum-store="enumStore"
            :field-names="fieldNames"
            :project-product-id="getConditionValue('project_product')"
            @search="onSearchRefresh"
          />
        </template>
        <template #tabs>
            <a-tabs
            class="mango-api-info-tabs mango-tabs-nav-only"
            :active-key="data.activeProtocol"
            @tab-click="(key) => switchProtocol(key)"
          >
            <template #extra>
              <a-space>
                <a-button
                  v-if="isStandardCreateProtocol"
                  size="small"
                  type="primary"
                  @click="onAdd(0)" data-testid="qa-views-apitest-info-button-新增"
                >
                  新增
                </a-button>
                <a-button
                  v-if="data.activeProtocol === 'grpc'"
                  size="small"
                  type="primary"
                  @click="openGrpcImport" data-testid="qa-views-apitest-info-button-导入grpc-method"
                >
                  导入gRPC Method
                </a-button>
                <a-button
                  v-if="data.activeProtocol === 'mcp'"
                  size="small"
                  type="primary"
                  @click="onAdd(0)" data-testid="qa-views-apitest-info-button-mcp工具"
                >
                  新增 MCP 接口
                </a-button>
                <a-button  v-if="isHttpProtocol" type="primary" size="small" @click="onAdd(1)" data-testid="qa-views-apitest-info-button-导入"
                  >导入</a-button
                >
                <a-button  v-if="isHttpProtocol" size="small" type="primary" @click="onBatchUpload" data-testid="qa-views-apitest-info-button-录制"
                  >录制</a-button
                >
                <a-button
                  v-if="isHttpProtocol"
                  size="small"
                  type="primary"
                  @click="showBatchImportModal" data-testid="qa-views-apitest-info-button-批量导入"
                  >批量导入</a-button
                >
                <a-button
                  size="small"
                  status="success"
                  :loading="caseRunning"
                  @click="onConcurrency" data-testid="qa-views-apitest-info-button-批量执行"
                  >批量执行
                </a-button>
                <a-button  size="small" status="danger" @click="onDelete(null)" data-testid="qa-views-apitest-info-button-批量删除">批量删除</a-button>
              </a-space>
            </template>
            <a-tab-pane key="all" title="全部" data-testid="qa-views-apitest-info-tab-pane-全部" />
            <a-tab-pane v-for="item in protocolTabs" :key="item.value" :title="item.label" />
          </a-tabs>
        </template>
          <StickyHorizontalTable :scroll-x="2090">
            <a-table
              :bordered="false"
              :columns="tableColumns"
              :data="table.dataList"
              :loading="table.tableLoading.value"
              :pagination="false"
              :row-selection="{ selectedRowKeys, showCheckedAll }"
              :rowKey="rowKey"
              :scroll="{ x: 2090, y: '100%' }"
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
                  <template v-else-if="item.key === 'client'" #cell="{ record }">
                    <a-tag
                      :color="enumStore.colors[record.project_product.api_client_type]"
                      size="small"
                      >{{ enumStore.api_client[record.project_product.api_client_type]?.title }}
                    </a-tag>
                  </template>
                  <template v-else-if="item.key === 'method'" #cell="{ record }">
                    <a-tag :color="enumStore.colors[record.method]" size="small">
                      {{ enumStore.method[record.method]?.title || '-' }}
                    </a-tag>
                  </template>
                  <template v-else-if="item.key === 'protocol_type'" #cell="{ record }">
                    <a-tag :color="protocolTagColor(record.protocol_type)" size="small">
                      {{ protocolTagText(record.protocol_type) }}
                    </a-tag>
                  </template>
                  <template v-else-if="item.key === 'status'" #cell="{ record }">
                    <a-tag :color="enumStore.status_colors[record.status]" size="small"
                      >{{ enumStore.task_status[record.status]?.title || '-' }}
                    </a-tag>
                  </template>
                  <template v-else-if="item.key === 'publication_status'" #cell="{ record }">
                    <a-tag
                      :color="
                        getApiInfoPublicationMeta(
                          record.publication_status,
                          record.published_version_label,
                          record.has_unpublished_changes
                        ).color
                      "
                      size="small"
                    >
                      {{
                        getApiInfoPublicationMeta(
                          record.publication_status,
                          record.published_version_label,
                          record.has_unpublished_changes
                        ).label
                      }}
                    </a-tag>
                  </template>
                  <template v-else-if="item.key === 'project_product'" #cell="{ record }">
                    {{ formatProjectProductPath(record.project_product) }}
                  </template>
                  <template v-else-if="item.key === 'module'" #cell="{ record }">
                    {{ formatModulePath(record.module) }}
                  </template>
                  <template v-else-if="item.key === 'update_user'" #cell="{ record }">
                    {{ record.update_user?.name || '-' }}
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
                              <pre>{{ strJson(responseBodyValue(data.caseResult)) }}</pre>
                            </a-space>
                          </a-space>
                        </div>
                      </a-modal>
                    </template>
                    <MangoTableActions
                      :actions="[
    {
        label: '执行',
        loading: caseRunning,
        onClick: () => onRunCase(record), },
    { label: '详情', onClick: () => onStep(record) },
    ...(canCopyApiInfoCurl(record)
        ? [{
                label: '复制 cURL',
                loading: copyingId === String(record.id),
                onClick: () => copyApiInfoCurl(record.id, userStore.selected_environment),
            }]
        : []),
    { label: '绑定Case', onClick: () => onBoundCases(record) },
    { label: '编辑', loading: editingId === String(record.id), onClick: () => onUpdate(record) },
    { label: '删除', danger: true, onClick: () => onDelete(record) },
]"
                    />
                  </template>
                </a-table-column>
              </template>
            </a-table>
          </StickyHorizontalTable>
          <template #footer>
            <TableFooter :pagination="pagination" />
          </template>
      </ProjectProductNavigationWorkbench>
    </template>
  </TableBody>
  <ApiInfoRuntimeParametersModal ref="runtimeParametersRef" />

  <BaseSidePanel
    :visible="boundCaseVisible"
    :title="boundCaseTitle"
    width="920px"
    cancel-button-text="关闭"
    @update:visible="handleBoundCaseVisibleChange"
    @cancel="handleBoundCaseCancel"
  >
    <div class="mango-bound-case-summary">共 {{ boundCaseTotal }} 个绑定 Case</div>
    <a-table
      :bordered="false"
      :data="boundCaseList"
      :loading="boundCaseLoading"
      :pagination="false"
      row-key="case_id"
      :scroll="{ x: 750 }"
      size="small"
    >
      <template #empty>
        <div class="mango-empty-state mango-bound-case-empty">暂无绑定用例</div>
      </template>
      <template #columns>
        <a-table-column title="Case ID" data-index="case_id" :width="70">
          <template #cell="{ record }">
            <a-link @click="openBoundCaseDetail(record)">{{ record.case_id }}</a-link>
          </template>
        </a-table-column>
        <a-table-column title="用例名称" data-index="case_name" :width="190" ellipsis tooltip />
        <a-table-column
          title="负责人"
          data-index="case_people_name"
          :width="100"
          ellipsis
          tooltip
        />
        <a-table-column
          title="最新更新人"
          data-index="update_user_name"
          :width="110"
          ellipsis
          tooltip
        >
          <template #cell="{ record }">
            {{ record.update_user_name || '-' }}
          </template>
        </a-table-column>
        <a-table-column title="更新时间" data-index="update_time" :width="180" />
        <a-table-column title="操作" data-index="actions" fixed="right" :width="60">
          <template #cell="{ record }">
            <MangoTableActions
              :actions="[{ label: '步骤', onClick: () => openBoundCaseDetail(record) }]"
            />
          </template>
        </a-table-column>
      </template>
    </a-table>
  </BaseSidePanel>

  <BaseSidePanel
    :visible="apiCaseDetailPanel.visible"
    :title="apiCaseDetailTitle"
    width="calc(92vw - 150px)"
    mode="page"
    @update:visible="
      (value) => {
        apiCaseDetailPanel.visible = value
      }
    "
    @cancel="apiCaseDetailPanel.visible = false"
  >
    <ApiCaseDetails
      v-if="apiCaseDetailPanel.visible && apiCaseDetailPanel.caseId"
      :key="apiCaseDetailPanel.caseId"
      embedded
      :case-id="apiCaseDetailPanel.caseId"
      :project-product-id="apiCaseDetailPanel.projectProductId"
      @close="apiCaseDetailPanel.visible = false"
    />
  </BaseSidePanel>

  <a-modal
    v-model:visible="batchImportVisible"
    title="批量导入"
    :ok-loading="batchImportLoading"
    @ok="handleBatchImportOk"
    @cancel="handleBatchImportCancel"
  >
    <a-space direction="vertical" class="batch-import-content">
      <a-button  type="primary" :loading="downloadLoading" @click="onDownload" data-testid="qa-views-apitest-info-button-下载模板">下载模板</a-button>
      <div class="batch-import-file">
        <a-button type="primary" @click="fileInputRef?.click()" data-testid="qa-views-apitest-info-button-选择文件">选择文件</a-button>
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

  <ModalDialog
    ref="grpcImportModalRef"
    title="导入 gRPC Method"
    width="760px"
    @confirm="handleGrpcImportOk"
    @cancel="handleGrpcImportCancel"
  >
    <template #content>
      <a-form :model="grpcImportForm">
        <div class="grpc-import-tip">
          <div class="grpc-import-tip__title">gRPC 自动化说明</div>
          <div
            >导入后页面使用 JSON 维护请求 Message，执行时按 proto/descriptor 转成 Protobuf
            发送，响应再转 JSON 用于断言和报告展示。</div
          >
          <div
            >导入后为编辑态；请先进入详情调试，成功后再生成修订并发布，发布后才能绑定到 API
            Case。</div
          >
          <div>当前仅支持 Unary RPC；流式 RPC 可登记和查看，但执行时会返回不支持提示。</div>
        </div>
        <a-form-item label="项目/产品" class="mango-form-item__no_require">
          <ProjectProductSelect
            v-model="grpcImportForm.project_product_id"
            placeholder="默认使用服务定义中的项目/产品"
            allow-clear
            @change="onGrpcImportProductChange" data-testid="qa-views-apitest-info-projectproductselect-默认使用服务定义中的项目-产品"
          />
        </a-form-item>
        <a-form-item label="模块" class="mango-form-item__no_require">
          <ProductModuleSelect
            v-model="grpcImportForm.module_id"
            :project-product-id="grpcImportForm.project_product_id"
            placeholder="默认使用服务定义中的模块"
            :auto-clear="false"
          />
        </a-form-item>
        <a-form-item label="gRPC服务" class="mango-form-item__require">
          <a-select
            v-model="grpcImportForm.service_id"
            :options="grpcServiceOptions"
            :loading="grpcServiceLoading"
            placeholder="请选择gRPC服务定义"
            allow-search
            @change="onGrpcServiceChange" data-testid="qa-views-apitest-info-select-请选择grpc服务定义"
          />
        </a-form-item>
        <a-form-item label="gRPC Method" class="mango-form-item__require">
          <a-space direction="vertical" fill>
            <a-button
              size="small"
              type="primary"
              :loading="grpcMethodSyncLoading"
              :disabled="!grpcImportForm.service_id"
              @click="syncGrpcMethods" data-testid="qa-views-apitest-info-button-同步-method"
            >
              同步 Method
            </a-button>
            <a-select
              v-model="grpcImportForm.method_id"
              :options="grpcMethodOptions"
              :loading="grpcMethodLoading"
              placeholder="请选择要导入的Method"
              allow-search data-testid="qa-views-apitest-info-select-请选择要导入的method"
            />
          </a-space>
        </a-form-item>
        <a-form-item label="gRPC地址" class="mango-form-item__no_require">
          <a-input
            v-model="grpcImportForm.grpc_target"
            allow-clear
            placeholder="可选，例如 127.0.0.1:50051；留空则使用测试对象地址" data-testid="qa-views-apitest-info-input-可选-例如-127-0-0-1-50051-留空则使用测试对象地址"
          />
        </a-form-item>
      </a-form>
    </template>
  </ModalDialog>

  <ModalDialog ref="modalDialogRef" :title="data.actionTitle" @confirm="onDataForm">
    <template #content>
      <a-form :model="formModel">
        <a-form-item v-if="getFormItemValue('protocol_type') === 'mcp'" label="工具名称" required>
          <a-input v-model="mcpToolName" placeholder="MCP 服务提供的工具名称" />
        </a-form-item>
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
              :multiple="item.multiple"
              :max-tag-count="item.multiple ? 1 : undefined"
              :field-names="fieldNames"
              :options="currentMethodOptions"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              value-key="key"
            />
          </template>
          <template v-else-if="item.key === 'protocol_type'">
            <a-select
              v-model="item.value"
              :multiple="item.multiple"
              :max-tag-count="item.multiple ? 1 : undefined"
              :options="item.optionItems"
              :placeholder="item.placeholder"
              allow-search
              @change="onProtocolTypeChange"
            />
          </template>
          <template v-else-if="item.key === 'body_type'">
            <a-select
              v-model="item.value"
              :multiple="item.multiple"
              :max-tag-count="item.multiple ? 1 : undefined"
              :options="item.optionItems"
              :placeholder="item.placeholder"
              :disabled="
                ['mcp', 'grpc', 'websocket'].includes(
                  normalizeProtocolType(getFormItemValue('protocol_type'))
                )
              "
              allow-search
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
  import { usePagePolling, isPendingExecution } from '@/hooks/use-page-polling'
  import ApiInfoRuntimeParametersModal from '@/components/business/ApiInfoRuntimeParametersModal.vue'
  import { usePagination, useRowKey, useRowSelection, useTable } from '@/hooks/table'
  import { useLatestRequest } from '@/hooks/use-latest-request'
  import { ModalDialogType } from '@/types/components'
  import { Message, Modal } from '@arco-design/web-vue'
  import { computed, onMounted, ref, reactive, nextTick, onUnmounted } from 'vue'
  import { getFormItems } from '@/utils/datacleaning'
  import { fieldNames } from '@/setting'
  import { usePageData } from '@/store/page-data'
  import { useRouter } from 'vue-router'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import ApiInfoSearchFilters from './ApiInfoSearchFilters.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import { getApiInfoPublicationMeta } from '@/utils/api-info-revision'
  import {
    formatProjectProductPath,
    formatModulePath,
    getItemValue,
    setItemValue,
  } from '@/utils/business-format'
  import {
    apiProtocolOptions,
    apiProtocolCreateOptions,
    apiProtocolTabOptions,
    tableColumns,
    formItems,
    conditionItems,
    formItemsImport,
  } from './config'
  import {
    deleteApiInfo,
    getApiCaseInfoRun,
    getApiInfo,
    getApiInfoBoundCases,
    getGrpcMethods,
    getGrpcServices,
    postApiInfoBatchRun,
    postApiImportUrl,
    postApiInfo,
    postApiUploadApi,
    postGrpcMethodImportApiInfo,
    postGrpcMethodSync,
    putApiInfo,
  } from '@/api/apitest/info'
  import { useEnum } from '@/store/modules/get-enum'
  import useUserStore from '@/store/modules/user'
  import { getUserName } from '@/api/user/user'
  import { strJson } from '@/utils/tools'
  import { getSystemSocketNewBrowser } from '@/api/system/socket_api'
  import ApiCaseDetails from '@/views/apitest/case/details/index.vue'
  import StickyHorizontalTable from '@/components/table/StickyHorizontalTable.vue'
  import { canCopyApiInfoCurl, useApiInfoCurl } from './useApiInfoCurl'
  import { prefillNavigationFormItems, NavigationCreateSource } from '@/utils/navigation-create-defaults'

  const navigationCreateRef = ref<NavigationCreateSource | null>(null)

  const router = useRouter()
  const enumStore = useEnum()

  const userStore = useUserStore()

  const modalDialogRef = ref<ModalDialogType | null>(null)
  const pagination = usePagination(doRefresh, () => table.tableLoading)
  const { selectedRowKeys, onSelectionChange, showCheckedAll } = useRowSelection()
  const table = useTable()
  const { beginRequest, isLatestRequest } = useLatestRequest()
  const rowKey = useRowKey('id')
  const editingId = ref('')
  let editRequest = 0
  const formModel = ref({})

  const data: any = reactive({
    actionTitle: '新增',
    isAdd: false,
    addType: 0,
    updateId: 0,
    activeProtocol: 'all',
    caseResult: {},
    apiPublicEnd: [],
    formItem: [],
    userList: [],
  })
  const caseRunning = ref(false)
  const runtimeParametersRef = ref<InstanceType<typeof ApiInfoRuntimeParametersModal> | null>(null)
  const { copyingId, copyApiInfoCurl } = useApiInfoCurl()
  const sidebarModuleIds = ref<Array<string | number>>([])
  const sidebarResetKey = ref(0)
  const downloadLoading = ref(false)
  const pagePolling = usePagePolling(() => doRefresh(null, false, false), () => {
    if (table.tableLoading.value) pagePolling.start()
    beginRequest()
    table.tableLoading.value = false
  })
  const httpMethodValues = new Set([0, 1, 2, 3, 4, 5, 6])
  const mcpMethodValue = 7
  const mcpToolName = ref('')
  const mcpBindingSnapshot = ref<Record<string, any>>({})
  const grpcMethodValue = 8
  const websocketMethodValue = 9
  const isStandardCreateProtocol = computed(
    () => !['grpc', 'mcp'].includes(String(data.activeProtocol || 'all'))
  )
  const isHttpProtocol = computed(() => normalizeProtocolType(data.activeProtocol) === 'http')

  function clearPollingTimer() { pagePolling.stop() }

  const visible = ref(false)
  const batchImportVisible = ref(false)
  const batchImportLoading = ref(false)
  const grpcImportModalRef = ref<ModalDialogType | null>(null)
  const grpcServiceLoading = ref(false)
  const grpcMethodLoading = ref(false)
  const grpcMethodSyncLoading = ref(false)
  const boundCaseVisible = ref(false)
  const boundCaseLoading = ref(false)
  const boundCaseTitle = ref('绑定Case')
  const boundCaseList = ref<any[]>([])
  const boundCaseTotal = ref(0)
  const apiCaseDetailPanel = reactive({
    visible: false,
    caseId: '' as number | string,
    caseName: '',
    projectProductId: '' as number | string,
  })
  const apiCaseDetailTitle = computed(() =>
    apiCaseDetailPanel.caseName ? `API 用例详情 / ${apiCaseDetailPanel.caseName}` : 'API 用例详情'
  )
  const fileInputRef = ref<HTMLInputElement | null>(null)
  const selectedFile = ref<File | null>(null) // 存储选中的文件
  const headerConditionItems = computed(() =>
    conditionItems.filter((item) => item.key !== 'project_product' && item.key !== 'module')
  )
  const protocolTabs = computed(() => apiProtocolTabOptions)
  const grpcServices = ref<any[]>([])
  const grpcMethods = ref<any[]>([])
  const grpcImportForm = reactive({
    project_product_id: null as number | string | null,
    module_id: null as number | string | null,
    service_id: null as number | string | null,
    method_id: null as number | string | null,
    grpc_target: '',
  })
  const grpcServiceOptions = computed(() =>
    grpcServices.value.map((item: any) => ({
      label: `${item.name || item.service_name || item.id} / ${item.service_name || '-'}`,
      value: item.id,
    }))
  )
  const grpcMethodOptions = computed(() =>
    grpcMethods.value.map((item: any) => {
      const streamingLabel = grpcStreamingLabel(item)
      return {
        label: `${item.full_method || item.name || item.id}${
          streamingLabel ? `（${streamingLabel}，暂不支持执行）` : ''
        }${item.imported_api_info_id ? '（已导入）' : ''}`,
        value: item.id,
        disabled: !!item.imported_api_info_id || Boolean(streamingLabel),
      }
    })
  )

  function responseBodyValue(result: any) {
    if (!result) return ''
    if (Object.prototype.hasOwnProperty.call(result, 'json')) {
      return result.json
    }
    return result.text
  }

  function protocolTagText(protocolType?: string) {
    return String(protocolType || 'http').toUpperCase()
  }

  function protocolTagColor(protocolType?: string) {
    const value = String(protocolType || 'http').toLowerCase()
    if (value === 'sse') return 'orange'
    if (value === 'http') return 'blue'
    if (value === 'grpc') return 'purple'
    if (value === 'mcp') return 'green'
    return 'gray'
  }

  function grpcStreamingLabel(item: any) {
    if (item?.client_streaming && item?.server_streaming) return '双向流'
    if (item?.client_streaming) return '客户端流'
    if (item?.server_streaming) return '服务端流'
    return ''
  }

  function normalizeProtocolType(protocolType?: string | null) {
    return String(protocolType || 'http').toLowerCase()
  }

  function methodKey(item: any) {
    return Number(item?.key ?? item?.value)
  }

  function getMethodOptionsByProtocol(protocolType?: string | null) {
    const methods = Array.isArray(enumStore.method) ? enumStore.method : []
    const protocol = normalizeProtocolType(protocolType)
    if (protocol === 'grpc') {
      const options = methods.filter((item: any) => methodKey(item) === grpcMethodValue)
      return options.length ? options : [{ key: grpcMethodValue, title: 'GRPC_CALL' }]
    }
    if (protocol === 'mcp') {
      const options = methods.filter((item: any) => methodKey(item) === mcpMethodValue)
      return options.length ? options : [{ key: mcpMethodValue, title: 'MCP_CALL' }]
    }
    if (protocol === 'websocket') {
      const options = methods.filter((item: any) => methodKey(item) === websocketMethodValue)
      return options.length ? options : [{ key: websocketMethodValue, title: 'WEBSOCKET_CONNECT' }]
    }
    return methods.filter((item: any) => httpMethodValues.has(methodKey(item)))
  }

  const currentMethodOptions = computed(() =>
    getMethodOptionsByProtocol(getFormItemValue('protocol_type'))
  )

  function syncMethodWithProtocol(protocolType?: string | null) {
    const protocol = normalizeProtocolType(protocolType)
    const targetValue =
      protocol === 'grpc'
        ? grpcMethodValue
        : protocol === 'mcp'
        ? mcpMethodValue
        : protocol === 'websocket'
        ? websocketMethodValue
        : null
    const currentMethod = getFormItemValue('method')
    const options = getMethodOptionsByProtocol(protocol)
    if (!options.length && targetValue === null) return
    const currentValid = options.some((item: any) => methodKey(item) === Number(currentMethod))
    if (targetValue !== null) {
      setItemValue(data.formItem, 'method', targetValue)
    } else if (!currentValid) {
      setItemValue(data.formItem, 'method', '')
    }
  }

  function syncBodyTypeWithProtocol(protocolType?: string | null) {
    if (normalizeProtocolType(protocolType) === 'websocket') {
      setItemValue(data.formItem, 'body_type', 'json')
    }
  }

  function onProtocolTypeChange(value: string) {
    syncMethodWithProtocol(value)
    syncBodyTypeWithProtocol(value)
  }

  function resetGrpcImportForm() {
    grpcImportForm.project_product_id = null
    grpcImportForm.module_id = null
    grpcImportForm.service_id = null
    grpcImportForm.method_id = null
    grpcImportForm.grpc_target = ''
    grpcMethods.value = []
  }

  async function openGrpcImport() {
    resetGrpcImportForm()
    await grpcImportModalRef.value?.show()
    await loadGrpcServices()
  }

  function handleGrpcImportCancel() {
    grpcImportModalRef.value?.close()
  }

  async function loadGrpcServices() {
    grpcServiceLoading.value = true
    try {
      const res: any = await getGrpcServices({ page: 1, pageSize: 200 })
      grpcServices.value = Array.isArray(res.data) ? res.data : []
    } finally {
      grpcServiceLoading.value = false
    }
  }

  function onGrpcImportProductChange() {
    grpcImportForm.module_id = null
  }

  async function onGrpcServiceChange(serviceId: number | string) {
    const service = grpcServices.value.find((item: any) => String(item.id) === String(serviceId))
    if (service) {
      grpcImportForm.project_product_id =
        service.project_product_id || grpcImportForm.project_product_id
      grpcImportForm.module_id = service.module_id || grpcImportForm.module_id
    }
    grpcImportForm.method_id = null
    await loadGrpcMethods()
  }

  async function loadGrpcMethods() {
    if (!grpcImportForm.service_id) {
      grpcMethods.value = []
      return
    }
    grpcMethodLoading.value = true
    try {
      const res: any = await getGrpcMethods({
        page: 1,
        pageSize: 500,
        service: grpcImportForm.service_id,
      })
      grpcMethods.value = Array.isArray(res.data) ? res.data : []
    } finally {
      grpcMethodLoading.value = false
    }
  }

  async function syncGrpcMethods() {
    if (!grpcImportForm.service_id) {
      Message.warning('请先选择gRPC服务')
      return
    }
    grpcMethodSyncLoading.value = true
    try {
      await postGrpcMethodSync({ grpc_service_id: grpcImportForm.service_id })
      Message.success('gRPC Method同步完成')
      await loadGrpcMethods()
    } finally {
      grpcMethodSyncLoading.value = false
    }
  }

  async function handleGrpcImportOk() {
    if (!grpcImportForm.method_id) {
      Message.warning('请选择要导入的gRPC Method')
      grpcImportModalRef.value?.setConfirmLoading(false)
      return
    }
    try {
      await postGrpcMethodImportApiInfo({
        grpc_method_id: grpcImportForm.method_id,
        project_product_id: grpcImportForm.project_product_id || undefined,
        module_id: grpcImportForm.module_id || undefined,
        grpc_target: grpcImportForm.grpc_target || undefined,
      })
      Message.success('gRPC Method已导入编辑态，请调试成功后再发布')
      grpcImportModalRef.value?.close()
      doRefresh(null, false, true)
    } finally {
      grpcImportModalRef.value?.setConfirmLoading(false)
    }
  }


  function setFormProtocolOptions(options: Array<{ label: string; value: string }>) {
    const protocolItem = data.formItem.find((item: any) => item.key === 'protocol_type')
    if (protocolItem) {
      protocolItem.optionItems = options
    }
  }

  const handleOk = () => {
    visible.value = false
  }
  const handleCancel = () => {
    visible.value = false
  }

  function switchProtocol(key: any) {
    data.activeProtocol = key || 'all'
    pagination.page = 1
    doRefresh(null, false, true)
  }

  function currentProtocolKey() {
    return String(data.activeProtocol || 'all')
  }

  function isLatestRefresh(requestId: number, protocolKey: string) {
    return isLatestRequest(requestId) && currentProtocolKey() === protocolKey
  }

  function getConditionValue(key: string) {
    return getItemValue(conditionItems, key)
  }

  function getFormItemValue(key: string) {
    return getItemValue(data.formItem, key)
  }

  function onSidebarFilterChange(filter: { projectProduct: any; module: any; moduleIds?: any[] }) {
    setItemValue(conditionItems, 'project_product', filter.projectProduct)
    setItemValue(conditionItems, 'module', filter.module)
    sidebarModuleIds.value = filter.moduleIds || []
    pagination.page = 1
    doRefresh(null, false, true)
  }

  function onFormProjectProductChange() {
    setItemValue(data.formItem, 'module', null)
  }

  function onSearchRefresh() {
    doRefresh(null, false, true)
  }

  function doRefresh(projectProductId: any = null, bool_ = false, showLoading = false) {
    const requestId = beginRequest()
    const protocolKey = currentProtocolKey()
    if (showLoading) {
      table.tableLoading.value = true
    }
    let value = getFormItems(conditionItems)
    if (sidebarModuleIds.value.length) {
      delete value['module']
      value['module__in'] = sidebarModuleIds.value.join(',')
    }
    clearEmptyFilter(value, 'module')
    clearEmptyFilter(value, 'project_product')
    value['page'] = pagination.page
    value['pageSize'] = pagination.pageSize
    value['summary'] = true
    if (data.activeProtocol && data.activeProtocol !== 'all') {
      value['protocol_type'] = data.activeProtocol
    }
    clearEmptyFilter(value, 'project_product__api_client_type')
    clearEmptyFilter(value, 'method')
    clearEmptyFilter(value, 'protocol_type')
    clearEmptyFilter(value, 'status')
    clearEmptyFilter(value, 'update_user')
    if (projectProductId && bool_) {
      value['project_product'] = projectProductId
    }
    return getApiInfo(value)
      .then((res) => {
        if (!isLatestRefresh(requestId, protocolKey)) return
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
        const hasRunningItem =
          res.data && Array.isArray(res.data) && res.data.some(isPendingExecution)

        if (hasRunningItem) pagePolling.start()
        else pagePolling.stop()
      })
      .catch((error) => {
        if (isLatestRefresh(requestId, protocolKey)) {
          console.log(error)
        }
      })
      .finally(() => {
        if (isLatestRefresh(requestId, protocolKey)) {
          table.tableLoading.value = false
        }
      })
  }

  function clearEmptyFilter(value: Record<string, any>, key: string) {
    if (value[key] === null || value[key] === '' || value[key] === undefined) {
      delete value[key]
    }
  }

  function getNickName() {
    getUserName()
      .then((res) => {
        data.userList = res.data
      })
      .catch(console.log)
  }

  function onResetSearch() {
    sidebarModuleIds.value = []
    sidebarResetKey.value += 1
    conditionItems.forEach((it) => {
      it.value = it.key === 'project_product' || it.key === 'module' ? null : it.multiple ? [] : ''
    })
    doRefresh(null, false, true)
  }

  function onAdd(type: number) {
    editRequest += 1
    editingId.value = ''
    mcpToolName.value = ''
    mcpBindingSnapshot.value = {}
    data.addType = type
    if (type === 0) {
      data.actionTitle = '新增'
      data.isAdd = true
      modalDialogRef.value?.toggle()
      data.formItem = formItems
      setFormProtocolOptions(apiProtocolCreateOptions)
      formItems.forEach((it) => {
        if (it.reset) {
          it.reset()
        } else {
          it.value = it.multiple ? [] : ''
        }
      })
      if (data.activeProtocol === 'mcp') {
        const protocol = formItems.find((item) => item.key === 'protocol_type')
        if (protocol) protocol.value = 'mcp'
      }
      syncMethodWithProtocol(getFormItemValue('protocol_type'))
      syncBodyTypeWithProtocol(getFormItemValue('protocol_type'))
    } else if (type === 1) {
      data.actionTitle = '导入接口'
      data.isAdd = true
      modalDialogRef.value?.toggle()
      data.formItem = formItemsImport
      formItemsImport.forEach((it) => {
        if (it.reset) {
          it.reset()
        } else {
          it.value = it.multiple ? [] : ''
        }
      })
    }
    void prefillNavigationFormItems(navigationCreateRef.value, data.formItem, () => data.isAdd)
  }

  async function onUpdate(record: any) {
    if (editingId.value) return
    const request = ++editRequest
    editingId.value = String(record.id)
    try {
      const response = await getApiInfo({ id: record.id })
      if (request !== editRequest) return
      const item = response.data?.[0]
      if (!item) return
      mcpBindingSnapshot.value = item.mcp_binding || {}
      mcpToolName.value = item.mcp_binding?.tool_name || ''
      data.actionTitle = '编辑'
      data.addType = 0
      data.isAdd = false
      data.updateId = item.id
      modalDialogRef.value?.toggle()
      nextTick(() => {
        if (request !== editRequest) return
        setFormProtocolOptions(apiProtocolOptions)
        formItems.forEach((it) => {
          const propName = item[it.key]
          if (typeof propName === 'object' && propName !== null) {
            it.value = propName.id
          } else {
            it.value = propName
          }
        })
        syncMethodWithProtocol(getFormItemValue('protocol_type'))
        syncBodyTypeWithProtocol(getFormItemValue('protocol_type'))
      })
      data.formItem = formItems
    } catch (error) {
      console.log(error)
    } finally {
      if (request === editRequest) editingId.value = ''
    }
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
    postApiUploadApi(selectedFile.value)
      .then((res) => {
        Message.success(res.msg)
        batchImportVisible.value = false
        doRefresh()
        // 重置状态
        if (fileInputRef.value) {
          fileInputRef.value.value = ''
        }
        selectedFile.value = null
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
  }

  function resetBoundCasePanel() {
    boundCaseList.value = []
    boundCaseTotal.value = 0
  }

  function handleBoundCaseVisibleChange(value: boolean) {
    boundCaseVisible.value = value
    if (!value) {
      resetBoundCasePanel()
    }
  }

  function handleBoundCaseCancel() {
    boundCaseVisible.value = false
    resetBoundCasePanel()
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

  function onDataForm() {
    if (data.addType == 0) {
      if (formItems.every((it) => (it.validator ? it.validator() : true))) {
        let value = getFormItems(formItems)
        if (value.protocol_type === 'mcp') {
          if (!mcpToolName.value.trim()) {
            Message.warning('请填写 MCP 工具名称')
            modalDialogRef.value?.setConfirmLoading(false)
            return
          }
          value.mcp_binding = { ...mcpBindingSnapshot.value, tool_name: mcpToolName.value.trim(), tool_type: 'tool', tool_enabled: true, transport_type: 0 }
        }
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
      const apiId = param.id
      const testEnv = userStore.selected_environment
      const parameters = await runtimeParametersRef.value?.prepare([{ id: apiId }])
      if (parameters == null) return
      const res = await getApiCaseInfoRun(apiId, testEnv, undefined, parameters)
      if (res.data?.status === 0) {
        Message.error(res.data.error_message || '接口调用失败，请查看执行结果')
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
    const selectedIds = new Set(selectedRowKeys.value.map(String))
    const selectedRows = table.dataList.filter((row: any) => selectedIds.has(String(row.id)))
    if (selectedRows.length !== selectedIds.size) {
      Message.warning('部分已选接口不在当前列表中，请刷新后重新选择')
      return
    }
    const unpublishedRows = selectedRows.filter((row: any) => !hasPublishedApiInfoVersion(row))
    if (unpublishedRows.length > 0) {
      Message.warning(`所选接口中有 ${unpublishedRows.length} 条尚未发布，请先发布后再执行`)
      return
    }
    if (caseRunning.value) return
    caseRunning.value = true
    try {
      const testEnv = userStore.selected_environment
      const targets = selectedRows.map((row: any) => ({ id: row.id, release_id: row.published_release_id }))
      const parameters = await runtimeParametersRef.value?.prepare(targets)
      if (parameters == null) return
      Message.loading('开始按已发布版本批量执行中~')
      const res = await postApiInfoBatchRun(
        selectedRows.map((row: any) => ({
          api_info_id: row.id,
          api_info_release_id: row.published_release_id,
        })),
        testEnv,
        parameters
      )
      const failedCount = Number(res.data?.fail_count || 0)
      if (failedCount > 0) {
        Message.warning(`批量执行完成，其中 ${failedCount} 条执行失败`)
      } else {
        Message.success(res.msg || '批量执行完成')
      }
    } catch (e) {
    } finally {
      caseRunning.value = false
      doRefresh()
    }
  }

  function hasPublishedApiInfoVersion(record: any) {
    return Boolean(record?.published_release_id && record?.published_revision_id)
  }

  function getPublishedApiInfoVersionParams(record: any) {
    if (!hasPublishedApiInfoVersion(record)) return null
    return {
      revision_id: record.published_revision_id,
      release_id: record.published_release_id,
    }
  }

  async function onBoundCases(record: any) {
    boundCaseTitle.value = `绑定Case - ${record.name || record.id}`
    boundCaseVisible.value = true
    boundCaseLoading.value = true
    boundCaseList.value = []
    boundCaseTotal.value = 0
    try {
      const res = await getApiInfoBoundCases(record.id)
      boundCaseList.value = Array.isArray(res.data) ? res.data : []
      boundCaseTotal.value = (res as any).totalSize || boundCaseList.value.length
    } finally {
      boundCaseLoading.value = false
    }
  }

  function openBoundCaseDetail(record?: any) {
    if (!record?.case_id) {
      Message.error('未找到API用例ID')
      return
    }
    apiCaseDetailPanel.caseId = record.case_id
    apiCaseDetailPanel.caseName = record.case_name || ''
    apiCaseDetailPanel.projectProductId = record.project_product_id || ''
    apiCaseDetailPanel.visible = true
  }

  function onStep(record: any) {
    const pageData = usePageData()
    pageData.setRecord(record)
    router.push({
      path: '/apitest/info/details',
      query: {
        id: record.id,
      },
    })
  }

  onMounted(() => {
    setItemValue(conditionItems, 'project_product', null)
    nextTick(async () => {
      doRefresh()
      getNickName()
    })
  })
  onUnmounted(() => {
    editRequest += 1
    clearPollingTimer()
  })
</script>

<style lang="less" scoped>
  .mango-api-info-tabs {
    overflow: hidden;
    flex: none;
  }

  .mango-api-info-tabs :deep(.arco-tabs-nav-extra) {
    margin-right: var(--m-page-gap);
  }

  .mango-api-info-table-region {
    min-width: 0;
    overflow: hidden;
  }

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

  .grpc-import-tip {
    display: grid;
    gap: 4px;
    padding: 10px 12px;
    margin-bottom: 12px;
    border: 1px solid var(--m-color-primary-light-3);
    border-radius: var(--m-radius-sm);
    background: var(--m-color-primary-light-1);
    color: var(--m-text-2);
    font-size: 13px;
    line-height: 20px;
  }

  .grpc-import-tip__title {
    color: var(--m-text);
    font-weight: 600;
  }

  .mango-bound-case-summary {
    margin-bottom: 12px;
    color: var(--m-muted);
    font-size: 13px;
  }

  .mango-bound-case-empty {
    padding: 28px 0;
  }
</style>
