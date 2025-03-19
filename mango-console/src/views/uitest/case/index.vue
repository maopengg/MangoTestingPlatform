<template>
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
                <a-input v-model="item.value" :placeholder="item.placeholder" @blur="doRefresh" />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'project_product'">
                <a-select
                  style="width: 150px"
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="projectInfo.projectProductList"
                  :field-names="fieldNames"
                  value-key="key"
                  allow-clear
                  allow-search
                  @change="doRefresh(item.value, true)"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'module'">
                <a-select
                  style="width: 150px"
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="productModule.data"
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
                  :options="enumStore.task_status"
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
                >批量执行
              </a-button>
            </div>
            <div>
              <a-button status="warning" size="small" @click="handleClick">设为定时任务</a-button>
              <a-modal v-model:visible="data.visible" @ok="handleOk" @cancel="handleCancel">
                <template #title> 设为定时任务</template>
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
            :ellipsis="item.ellipsis"
            :tooltip="item.tooltip"
          >
            <template v-if="item.key === 'index'" #cell="{ record }">
              {{ record.id }}
            </template>
            <template v-else-if="item.key === 'project_product'" #cell="{ record }">
              {{ record?.project_product?.project?.name + '/' + record?.project_product?.name }}
            </template>
            <template v-else-if="item.key === 'module'" #cell="{ record }">
              {{ record?.module?.superior_module ? record?.module?.superior_module + '/' : ''
              }}{{ record?.module?.name }}
            </template>
            <template v-else-if="item.key === 'level'" #cell="{ record }">
              <a-tag :color="enumStore.colors[record?.level]" size="small"
                >{{ record.level !== null ? enumStore.case_level[record.level].title : '-' }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'case_people'" #cell="{ record }">
              {{ record.case_people.name }}
            </template>
            <template v-else-if="item.key === 'switch_step_open_url'" #cell="{ record }">
              <a-switch
                :default-checked="record.switch_step_open_url === 1"
                :beforeChange="(newValue) => onModifyStatus(newValue, record.id, item.key)"
              />
            </template>
            <template v-else-if="item.key === 'status'" #cell="{ record }">
              <a-tag :color="enumStore.status_colors[record.status]" size="small"
                >{{ enumStore.task_status[record.status].title }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <a-space>
                <a-button type="text" size="mini" @click="onCaseRun(record.id)">执行</a-button>
                <a-button type="text" size="mini" @click="onClick(record)">步骤</a-button>
                <a-button type="text" size="mini" @click="clickSuite(record)">套件</a-button>

                <a-dropdown trigger="hover">
                  <a-button type="text" size="mini">···</a-button>
                  <template #content>
                    <a-doption>
                      <a-button type="text" size="mini" @click="onUpdate(record)">编辑</a-button>
                    </a-doption>
                    <a-doption>
                      <a-button type="text" size="mini" @click="caseCody(record)">复制</a-button>
                    </a-doption>
                    <a-doption>
                      <a-button status="danger" type="text" size="mini" @click="onDelete(record)"
                        >删除
                      </a-button>
                    </a-doption>
                  </template>
                </a-dropdown>
              </a-space>
            </template>
          </a-table-column>
        </template>
      </a-table>
      <a-drawer
        :width="800"
        :visible="data.drawerVisible"
        @ok="drawerOk"
        @cancel="data.drawerVisible = false"
        unmountOnClose
      >
        <template #title> 用例套件</template>
        <div>
          <a-space>
            <a-button size="mini" @click.stop="data.row.parametrize.push([{ key: '', value: '' }])"
              >增加测试套
            </a-button>
          </a-space>
          <a-collapse :default-active-key="[0]" accordion :bordered="false">
            <!-- 遍历 row 数组，生成每一行 -->
            <a-collapse-item
              :header="'循环第 ' + (index + 1) + ' 次'"
              :key="index"
              v-for="(item, index) of data.row.parametrize"
            >
              <template #extra>
                <a-space>
                  <a-button
                    size="mini"
                    @click.stop="data.row.parametrize[index].push({ key: '', value: '' })"
                    >增加一行
                  </a-button>
                  <a-button
                    status="danger"
                    size="mini"
                    @click.stop="data.row.parametrize.splice(index, 1)"
                    >删除
                  </a-button>
                </a-space>
              </template>
              <a-space direction="vertical" fill>
                <a-space v-for="(items, index1) in item" :key="index1">
                  <span>key：</span>
                  <a-input placeholder="请输入key" v-model="items.key" />
                  <span>value：</span>
                  <a-input placeholder="请输入value" v-model="items.value" />
                  <a-button
                    type="text"
                    size="small"
                    status="danger"
                    @click="item.splice(index1, 1)"
                  >
                    移除
                  </a-button>
                </a-space>
              </a-space>
            </a-collapse-item>
          </a-collapse>
        </div>
      </a-drawer>
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
              @change="onModuleSelect(item.value)"
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
              :options="productModule.data"
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
              :options="enumStore.case_level"
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
  import { usePagination, useRowKey, useRowSelection, useTable } from '@/hooks/table'
  import { FormItem, ModalDialogType } from '@/types/components'
  import { Message, Modal } from '@arco-design/web-vue'
  import { onMounted, ref, nextTick, reactive } from 'vue'
  import { useProject } from '@/store/modules/get-project'
  import { fieldNames } from '@/setting'
  import { getFormItems } from '@/utils/datacleaning'
  import { useRouter } from 'vue-router'
  import { useProductModule } from '@/store/modules/project_module'
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
  } from '@/api/uitest/case'
  import { getSystemTasksName } from '@/api/system/tasks'
  import { postSystemTasksBatchSetCases } from '@/api/system/tasks_details'
  import { getUserName } from '@/api/user/user'
  import { useEnum } from '@/store/modules/get-enum'
  import useUserStore from '@/store/modules/user'
  import { putUiConfigPutStatus } from '@/api/uitest/config'

  const enumStore = useEnum()

  const productModule = useProductModule()
  const projectInfo = useProject()
  const userStore = useUserStore()
  const router = useRouter()

  const modalDialogRef = ref<ModalDialogType | null>(null)
  const pagination = usePagination(doRefresh)
  const { selectedRowKeys, onSelectionChange, showCheckedAll } = useRowSelection()
  const table = useTable()
  const rowKey = useRowKey('id')
  const formModel = ref({})

  const data: any = reactive({
    isAdd: false,
    updateId: 0,
    actionTitle: '添加用例',
    userList: [],
    moduleList: productModule.data,
    systemStatus: [],
    scheduledName: [],
    value: null,
    visible: false,
    drawerVisible: false,
    row: {},
  })

  function doRefresh(projectProductId: number | null = null, bool_ = false) {
    let value = getFormItems(conditionItems)
    value['page'] = pagination.page
    value['pageSize'] = pagination.pageSize
    if (projectProductId && bool_) {
      value['project_product'] = projectProductId
      productModule.getProjectModule(projectProductId)
    }
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
      content: '是否要删除此用例？',
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
    productModule.getProjectModule(item.project_product.id)
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
    if (userStore.selected_environment == null) {
      Message.error('请先选择用例执行的环境')
      return
    }
    getUiCaseRun(caseId, userStore.selected_environment)
      .then((res) => {
        Message.loading(res.msg)
      })
      .catch(console.log)
  }

  function onConcurrency(name: string) {
    if (userStore.selected_environment == null) {
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
        postUiRunCaseBatch(selectedRowKeys.value, userStore.selected_environment)
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
    getUserName()
      .then((res) => {
        data.userList = res.data
      })
      .catch(console.log)
  }

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

  function clickSuite(record: any) {
    data.drawerVisible = true
    data.row = record
  }

  function drawerOk() {
    data.drawerVisible = false
    let value = {
      id: data.row['id'],
      parametrize: data.row['parametrize'],
    }
    putUiCase(value)
      .then((res) => {
        Message.success(res.msg)
        doRefresh()
      })
      .catch(console.log)
  }

  function caseCody(record: any) {
    postUiCaseCopy(record.id)
      .then((res) => {
        Message.success(res.msg)
        doRefresh()
      })
      .catch(console.log)
  }

  function scheduledName() {
    getSystemTasksName()
      .then((res) => {
        data.scheduledName = res.data
      })
      .catch(console.log)
  }

  function onModuleSelect(projectProductId: number | string) {
    productModule.getProjectModule(projectProductId)
    formItems.forEach((item: FormItem) => {
      if (item.key === 'module') {
        item.value = ''
      }
    })
  }

  const onModifyStatus = async (newValue: any, id: number, key: string) => {
    let obj: any = {
      id: id,
    }
    if (key) {
      obj[key] = newValue ? 1 : 0
    }
    return new Promise<any>((resolve, reject) => {
      setTimeout(async () => {
        try {
          let value: any = false
          await putUiCase(obj)
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

  onMounted(() => {
    nextTick(async () => {
      await getNickName()
      await scheduledName()
      doRefresh()
      productModule.getProjectModule(null)
    })
  })
</script>
