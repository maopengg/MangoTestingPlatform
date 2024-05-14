<template>
  <div>
    <div class="main-container">
      <TableBody ref="tableBody">
        <template #header>
          <TableHeader
            :show-filter="true"
            title="测试用例"
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
                  <template v-else-if="item.type === 'select' && item.key === 'case_people'">
                    <a-select
                      style="width: 150px"
                      v-model="item.value"
                      :placeholder="item.placeholder"
                      :options="data.userList"
                      :field-names="fieldNames"
                      value-key="key"
                      allow-clear
                      allow-search
                      @change="doRefresh"
                    />
                  </template>
                  <template v-else-if="item.type === 'select' && item.key === 'status'">
                    <a-select
                      style="width: 150px"
                      v-model="item.value"
                      :placeholder="item.placeholder"
                      :options="data.systemStatus"
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
                  <a-button status="success" size="small" @click="onConcurrency('批量执行')"
                    >批量执行</a-button
                  >
                </div>
                <div>
                  <a-button status="warning" size="small" @click="handleClick"
                    >设为定时任务</a-button
                  >
                  <a-modal v-model:visible="data.visible" @ok="handleOk" @cancel="handleCancel">
                    <template #title> 设为定时任务 </template>
                    <div>
                      <a-select
                        v-model="data.value"
                        placeholder="请选择定时任务进行绑定"
                        :options="data.scheduledName"
                        :field-names="fieldNames"
                        value-key="key"
                        allow-clear
                        allow-search
                      />
                    </div>
                  </a-modal>
                </div>
                <div>
                  <a-button type="primary" size="small" @click="onAdd">新增</a-button>
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
                <template v-else-if="item.key === 'project_product'" #cell="{ record }">
                  {{ record.project_product?.project?.name + '/' + record.project_product?.name }}
                </template>
                <template v-else-if="item.key === 'module'" #cell="{ record }">
                  {{ record.module?.superior_module ? record.module?.superior_module + '/' : ''
                  }}{{ record.module?.name }}
                </template>
                <template v-else-if="item.key === 'level'" #cell="{ record }">
                  <a-tag color="orange" size="small">
                    {{
                      record.level !== null ? data.enumCaseLevel[record.level].title : '-'
                    }}</a-tag
                  >
                </template>
                <template v-else-if="item.key === 'case_people'" #cell="{ record }">
                  {{ record.case_people.nickname }}
                </template>
                <template v-else-if="item.key === 'status'" #cell="{ record }">
                  <a-tag color="green" size="small" v-if="record.status === 1">通过</a-tag>
                  <a-tag color="red" size="small" v-else-if="record.status === 0">失败</a-tag>
                  <a-tag color="gray" size="small" v-else>未测试</a-tag>
                </template>
                <template v-else-if="item.key === 'actions'" #cell="{ record }">
                  <a-space>
                    <a-button type="text" size="mini" @click="onCaseRun(record.id)">执行</a-button>
                    <a-button type="text" size="mini" @click="onClick(record)">步骤</a-button>
                    <a-dropdown trigger="hover">
                      <a-button type="text" size="mini">···</a-button>
                      <template #content>
                        <a-doption>
                          <a-button type="text" size="mini" @click="onClick1(record)"
                            >结果</a-button
                          >
                        </a-doption>
                        <a-doption>
                          <a-button type="text" size="mini" @click="onUpdate(record)"
                            >编辑</a-button
                          >
                        </a-doption>
                        <a-doption>
                          <a-button type="text" size="mini" @click="caseCody(record)"
                            >复制</a-button
                          >
                        </a-doption>
                        <a-doption>
                          <a-button
                            status="danger"
                            type="text"
                            size="mini"
                            @click="onDelete(record)"
                            >删除</a-button
                          >
                        </a-doption>
                      </template>
                    </a-dropdown>
                  </a-space>
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
              <template v-else-if="item.type === 'select' && item.key === 'case_people'">
                <a-select
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="data.userList"
                  :field-names="fieldNames"
                  value-key="key"
                  allow-clear
                  allow-search
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'level'">
                <a-select
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="data.enumCaseLevel"
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
  import { onMounted, ref, nextTick, reactive } from 'vue'
  import { useProject } from '@/store/modules/get-project'
  import { fieldNames } from '@/setting'
  import { getFormItems } from '@/utils/datacleaning'
  import { useRouter } from 'vue-router'
  import { useTestObj } from '@/store/modules/get-test-obj'
  import { useProjectModule } from '@/store/modules/project_module'
  import { usePageData } from '@/store/page-data'
  import { conditionItems, formItems, tableColumns } from './config'
  import {
    deleteUiCase,
    getUiCase,
    getUiCaseRun,
    postUiCase,
    postUiCaseCopy,
    putUiCase,
    postUiRunCaseBatch,
  } from '@/api/uitest'
  import {
    getSystemEnumCaseLevel,
    getSystemEnumStatus,
    getSystemScheduledName,
    postSystemTasksBatchSetCases,
  } from '@/api/system'
  import { getUserModuleName, getUserNickname } from '@/api/user'
  const projectModule = useProjectModule()
  const projectInfo = useProject()
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const pagination = usePagination(doRefresh)
  const { selectedRowKeys, onSelectionChange, showCheckedAll } = useRowSelection()
  const table = useTable()
  const rowKey = useRowKey('id')
  const formModel = ref({})
  const testObj = useTestObj()

  const data = reactive({
    isAdd: false,
    updateId: 0,
    actionTitle: '添加用例',
    userList: [],
    moduleList: projectModule.data,
    systemStatus: [],
    scheduledName: [],
    enumCaseLevel: [],
    value: null,
    visible: false,
  })

  function doRefresh() {
    let value = getFormItems(conditionItems)
    value['page'] = pagination.page
    value['pageSize'] = pagination.pageSize
    getUiCase(value)
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

  function onAdd() {
    data.actionTitle = '添加用例'
    data.isAdd = true
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
        deleteUiCase(data.id)
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
        deleteUiCase(selectedRowKeys.value)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      },
    })
  }
  function onUpdate(item: any) {
    data.actionTitle = '编辑用例'
    data.isAdd = false
    data.updateId = item.id
    onProductModuleName(item.project_product.id)
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
  }

  function onCaseRun(caseId: number) {
    if (testObj.selectValue == null) {
      Message.error('请先选择用例执行的环境')
      return
    }
    getUiCaseRun(caseId, testObj.selectValue)
      .then((res) => {
        Message.loading(res.msg)
      })
      .catch(console.log)
  }

  function onConcurrency(name: string) {
    if (testObj.selectValue == null) {
      Message.error('请先选择用例执行的环境')
      return
    }
    if (selectedRowKeys.value.length === 0) {
      Message.error('请选择要' + name + '的用例数据')
      return
    }
    Modal.confirm({
      title: '提示',
      content: '确定要' + name + '这些用例吗？批量执行会生成多个浏览器来执行用例',
      cancelText: '取消',
      okText: '执行',
      onOk: () => {
        postUiRunCaseBatch(selectedRowKeys.value, testObj.selectValue)
          .then((res) => {
            Message.loading(res.msg)
            selectedRowKeys.value = []
            doRefresh()
          })
          .catch(console.log)
      },
    })
  }

  const handleClick = () => {
    if (selectedRowKeys.value.length === 0) {
      Message.error('请选择要添加定时任务的用例')
      return
    }
    data.visible = true
  }
  const handleOk = () => {
    postSystemTasksBatchSetCases(selectedRowKeys.value, data.value)
      .then((res) => {
        Message.success(res.msg)
        data.visible = false
      })
      .catch(console.log)
  }
  const handleCancel = () => {
    data.visible = false
  }
  function onDataForm() {
    if (formItems.every((it) => (it.validator ? it.validator() : true))) {
      modalDialogRef.value?.toggle()
      let value = getFormItems(formItems)
      if (data.isAdd) {
        value['front_custom'] = []
        value['front_sql'] = []
        value['posterior_sql'] = []
        postUiCase(value)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      } else {
        value['id'] = data.updateId
        putUiCase(value)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      }
    }
  }

  function getNickName() {
    getUserNickname()
      .then((res) => {
        data.userList = res.data
      })
      .catch(console.log)
  }

  function onProductModuleName(projectId: number | string) {
    getUserModuleName(projectId)
      .then((res) => {
        data.moduleList = res.data
      })
      .catch(console.log)
  }

  const router = useRouter()

  function onClick(record: any) {
    const pageData = usePageData()
    pageData.setRecord(record)
    router.push({
      path: '/uitest/case/details',
      query: {
        id: parseInt(record.id, 10),
      },
    })
  }

  function onClick1(record: any) {
    if (!record.test_suite_id) {
      Message.error(`用例：${record.name}最近无执行记录`)
      return
    }
    const pageData = usePageData()
    pageData.setRecord(record)
    router.push({
      path: '/uitest/report/details',
      query: {
        id: record.test_suite_id,
      },
    })
  }

  function caseCody(record: any) {
    postUiCaseCopy(record.id)
      .then((res) => {
        Message.success(res.msg)
        doRefresh()
      })
      .catch(console.log)
  }

  function status() {
    getSystemEnumStatus()
      .then((res) => {
        data.systemStatus = res.data
      })
      .catch(console.log)
  }
  function scheduledName() {
    getSystemScheduledName(0)
      .then((res) => {
        data.scheduledName = res.data
      })
      .catch(console.log)
  }
  function enumCaseLevel() {
    getSystemEnumCaseLevel()
      .then((res) => {
        data.enumCaseLevel = res.data
      })
      .catch(console.log)
  }

  onMounted(() => {
    nextTick(async () => {
      await getNickName()
      await status()
      await scheduledName()
      await enumCaseLevel()
      doRefresh()
    })
  })
</script>
