<template>
  <div>
    <div class="main-container">
      <TableBody ref="tableBody">
        <template #header>
          <TableHeader
            :show-filter="true"
            title="调试页面步骤"
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
                  <template v-else-if="item.type === 'select' && item.key === 'project'">
                    <a-select
                      style="width: 150px"
                      v-model="item.value"
                      :placeholder="item.placeholder"
                      :options="item.optionItems"
                      @change="getProjectModule(item.value, true)"
                      :field-names="fieldNames"
                      value-key="key"
                      allow-clear
                      allow-search
                    />
                  </template>
                  <template v-else-if="item.type === 'select' && item.key === 'module_name'">
                    <a-select
                      style="width: 150px"
                      v-model="item.value"
                      :placeholder="item.placeholder"
                      :options="pageStepsData.moduleList"
                      :field-names="fieldNames"
                      value-key="key"
                      allow-clear
                      allow-search
                      @change="onQueryProjectPage(item.value, true)"
                    />
                  </template>
                  <template v-else-if="item.type === 'select' && item.key === 'page'">
                    <a-select
                      style="width: 150px"
                      v-model="item.value"
                      :placeholder="item.placeholder"
                      :options="pageStepsData.pageName"
                      :field-names="fieldNames"
                      value-key="key"
                      allow-clear
                      allow-search
                      @change="doRefresh"
                    />
                  </template>
                  <template v-else-if="item.type === 'select' && item.key === 'type'">
                    <a-select
                      style="width: 150px"
                      v-model="item.value"
                      :placeholder="item.placeholder"
                      :options="pageStepsData.systemStatus"
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
          <a-tabs>
            <template #extra>
              <a-space>
                <div>
                  <a-button type="primary" size="small" @click="onAddPage">新增</a-button>
                </div>
                <div>
                  <a-button status="warning" size="small" @click="setCase">修改状态</a-button>
                </div>
                <div>
                  <a-button status="danger" size="small" @click="onDeleteItems">批量删除</a-button>
                </div>
              </a-space>
            </template>
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
              >
                <template v-if="item.key === 'index'" #cell="{ record }">
                  {{ record.id }}
                </template>
                <template v-else-if="item.key === 'project'" #cell="{ record }">
                  {{ record.project?.name }}
                </template>
                <template v-else-if="item.key === 'module_name'" #cell="{ record }">
                  {{
                    record.module_name?.superior_module
                      ? record.module_name?.superior_module + '/'
                      : ''
                  }}{{ record.module_name?.name }}
                </template>
                <template v-else-if="item.key === 'page'" #cell="{ record }">
                  {{ record.page.name }}
                </template>
                <template v-else-if="item.key === 'type'" #cell="{ record }">
                  <a-tag color="green" size="small" v-if="record.type === 1">通过</a-tag>
                  <a-tag color="red" size="small" v-else-if="record.type === 0">失败</a-tag>
                  <a-tag color="gray" size="small" v-else>未调试</a-tag>
                </template>
                <template v-else-if="item.key === 'actions'" #cell="{ record }">
                  <a-button type="text" size="mini" @click="onRunCase(record)">调试</a-button>
                  <a-button type="text" size="mini" @click="onClick(record)">步骤</a-button>
                  <a-dropdown trigger="hover">
                    <a-button type="text" size="mini">···</a-button>
                    <template #content>
                      <a-doption>
                        <a-button type="text" size="mini" @click="onUpdate(record)">编辑</a-button>
                      </a-doption>
                      <a-doption>
                        <a-button type="text" size="mini" @click="pageStepsCopy(record)"
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
                  @change="getProjectModule(item.value, false)"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'module_name'">
                <a-select
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="pageStepsData.moduleList"
                  :field-names="fieldNames"
                  value-key="key"
                  allow-clear
                  allow-search
                  @change="onQueryProjectPage(item.value, true)"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'page'">
                <a-select
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="pageStepsData.pageName"
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
    uiSteps,
    uiPageName,
    uiStepsRun,
    uiPageStepsCopy,
    userProjectModuleGetAll,
    uiStepsPutType,
    systemEnumStatus,
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
  import { onMounted, ref, nextTick, reactive } from 'vue'
  import { useRouter } from 'vue-router'
  import { useProject } from '@/store/modules/get-project'
  import { fieldNames } from '@/setting'
  import { useTestObj } from '@/store/modules/get-test-obj'
  import { getFormItems } from '@/utils/datacleaning'
  import { useProjectModule } from '@/store/modules/project_module'
  import { usePageData } from '@/store/page-data'

  const projectModule = useProjectModule()
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
    pageName: [],
    moduleList: projectModule.data,
    systemStatus: [],
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
    },
    {
      key: 'name',
      label: '步骤名称',
      type: 'input',
      placeholder: '请输入步骤名称',
      value: '',
      reset: function () {
        this.value = ''
      },
    },
    {
      key: 'project',
      label: '项目',
      value: '',
      type: 'select',
      placeholder: '请选择项目',
      optionItems: project.data,
      reset: function () {},
    },
    {
      key: 'module_name',
      label: '模块',
      value: '',
      type: 'select',
      placeholder: '请先选择项目',
      optionItems: pageStepsData.moduleList,
      reset: function () {},
    },
    {
      key: 'page',
      label: '所属页面',
      value: '',
      type: 'select',
      placeholder: '请选择所属页面',
      optionItems: pageStepsData.pageName,
      reset: function () {},
    },
    {
      key: 'type',
      label: '状态',
      value: '',
      type: 'select',
      placeholder: '请选择步骤状态',
      optionItems: pageStepsData.systemStatus,
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
        if (!this.value) {
          Message.error(this.placeholder || '')
          return false
        }
        return true
      },
    },
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
      },
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
      },
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
      },
    },
  ])

  const tableColumns = useTableColumn([
    table.indexColumn,
    {
      title: '项目',
      key: 'project',
      dataIndex: 'project',
      width: 130,
    },
    {
      title: '模块',
      key: 'module_name',
      dataIndex: 'module_name',
      width: 160,
    },
    {
      title: '所属页面',
      key: 'page',
      dataIndex: 'page',
      width: 150,
    },
    {
      title: '步骤名称',
      key: 'name',
      dataIndex: 'name',
      align: 'left',
      width: 170,
    },
    {
      title: '步骤顺序',
      key: 'run_flow',
      dataIndex: 'run_flow',
      align: 'left',
    },
    {
      title: '状态',
      key: 'type',
      dataIndex: 'type',
    },
    {
      title: '操作',
      key: 'actions',
      dataIndex: 'actions',
      fixed: 'right',
      width: 200,
    },
  ])

  function doRefresh() {
    get({
      url: uiSteps,
      data: () => {
        let value = getFormItems(conditionItems)
        value['page'] = pagination.page
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
          url: uiSteps,
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

  function onUpdate(item: any) {
    pageStepsData.actionTitle = '编辑页面步骤'
    pageStepsData.isAdd = false
    pageStepsData.updateId = item.id
    modalDialogRef.value?.toggle()
    getProjectModule(item.project.id, false)
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

  function setCase() {
    if (selectedRowKeys.value.length === 0) {
      Message.error('请选择要修改状态的步骤')
      return
    }
    Modal.confirm({
      title: '提示',
      content: '确定要翻转这些用例的状态吗？',
      cancelText: '取消',
      okText: '确定',
      onOk: () => {
        put({
          url: uiStepsPutType,
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
          },
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

  function onRunCase(record: any) {
    if (testObj.selectValue == null) {
      Message.error('请先选择用例执行的环境')
      return
    }
    get({
      url: uiStepsRun,
      data: () => {
        return {
          page_step_id: record.id,
          te: testObj.selectValue,
        }
      },
    })
      .then((res) => {
        Message.loading(res.msg)
      })
      .catch(console.log)
  }

  const router = useRouter()

  function onClick(record: any) {
    const pageData = usePageData()
    pageData.setRecord(record)
    router.push({
      path: '/uitest/page-steps-details',
      query: {
        id: parseInt(record.id, 10),
        pageId: record.page.id,
        pageType: record.page.type,
      },
    })
  }

  function onQueryProjectPage(moduleId: any, refresh: boolean) {
    if (refresh) {
      doRefresh()
    }
    get({
      url: uiPageName,
      data: () => {
        return {
          module_name: moduleId,
        }
      },
    })
      .then((res) => {
        pageStepsData.pageName = res.data
      })
      .catch(() => {
        pageStepsData.pageName = []
        formItems.forEach((obj: any) => {
          if (obj.key == 'page') {
            obj.value = null
          }
        })
      })
  }

  function pageStepsCopy(record: any) {
    post({
      url: uiPageStepsCopy,
      data: () => {
        return {
          page_id: record.id,
        }
      },
    })
      .then((res) => {
        Message.success(res.msg)
        doRefresh()
      })
      .catch(console.log)
  }

  function getProjectModule(projectId: number, isRefresh: boolean | null) {
    if (isRefresh) {
      doRefresh()
    }
    get({
      url: userProjectModuleGetAll,
      data: () => {
        return {
          project_id: projectId,
        }
      },
    })
      .then((res) => {
        pageStepsData.moduleList = res.data
      })
      .catch(console.log)
  }

  function status() {
    get({
      url: systemEnumStatus,
      data: () => {
        return {}
      },
    })
      .then((res) => {
        pageStepsData.systemStatus = res.data
      })
      .catch(console.log)
  }

  onMounted(() => {
    nextTick(async () => {
      doRefresh()
      onQueryProjectPage(null, false)
      status()
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
