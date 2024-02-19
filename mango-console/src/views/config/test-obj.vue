<template>
  <div>
    <div class="main-container">
      <TableBody ref="tableBody">
        <template #header>
          <TableHeader
            :show-filter="true"
            title="配置测试对象"
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
                  <template v-else-if="item.type === 'select'">
                    <a-select
                      style="width: 150px"
                      v-model="item.value"
                      :placeholder="item.placeholder"
                      :options="project.data"
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
              </a-space>
            </template>
          </a-tabs>
          <a-table
            :bordered="false"
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
                <template v-else-if="item.key === 'executor_name'" #cell="{ record }">
                  {{ record.executor_name ? record.executor_name.nickname : '-' }}
                </template>
                <template v-else-if="item.key === 'db_status'" #cell="{ record }">
                  <a-switch
                    :default-checked="record.db_status === 1"
                    :beforeChange="(newValue) => onModifyStatus(newValue, record.id)"
                  />
                </template>
                <template v-else-if="item.key === 'environment'" #cell="{ record }">
                  <a-tag color="orangered" size="small" v-if="record.environment === 0"
                    >测试环境</a-tag
                  >
                  <a-tag color="cyan" size="small" v-else-if="record.environment === 1"
                    >预发环境</a-tag
                  >
                  <a-tag color="green" size="small" v-else-if="record.environment === 2"
                    >生产环境</a-tag
                  >
                </template>
                <template v-else-if="item.key === 'test_type'" #cell="{ record }">
                  <a-tag color="orangered" size="small" v-if="record.test_type === 0">WEB</a-tag>
                  <a-tag color="cyan" size="small" v-else-if="record.test_type === 1">安卓</a-tag>
                  <a-tag color="green" size="small" v-else-if="record.test_type === 2">IOS</a-tag>
                  <a-tag color="green" size="small" v-else-if="record.test_type === 3"
                    >PC桌面</a-tag
                  >
                </template>
                <template v-else-if="item.key === 'actions'" #cell="{ record }">
                  <a-space>
                    <a-button type="text" size="mini" @click="onUpdate(record)">编辑</a-button>
                    <a-button status="danger" type="text" size="mini" @click="onDelete(record)"
                      >删除</a-button
                    >
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
      <ModalDialog ref="modalDialogRef" :title="testObjData.actionTitle" @confirm="onDataForm">
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
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'environment'">
                <a-select
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="uEnvironment.data"
                  :field-names="fieldNames"
                  value-key="key"
                  allow-clear
                  allow-search
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'executor_name'">
                <a-select
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="testObjData.nickname"
                  :field-names="fieldNames"
                  value-key="key"
                  allow-clear
                  allow-search
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'test_type'">
                <a-select
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="testObjData.platformEnum"
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
  import { get, post, put, deleted } from '@/api/http'
  import {
    systemTestObject,
    userNickname,
    systemEnumPlatform,
    systemTestObjectPutStatus,
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
  import { useProject } from '@/store/modules/get-project'
  import { useEnvironment } from '@/store/modules/get-environment'
  import { getFormItems } from '@/utils/datacleaning'
  import { fieldNames } from '@/setting'
  import { useTestObj } from '@/store/modules/get-test-obj'

  const project = useProject()
  const uEnvironment = useEnvironment()
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const pagination = usePagination(doRefresh)
  const { onSelectionChange } = useRowSelection()
  const table = useTable()
  const rowKey = useRowKey('id')
  const formModel = ref({})
  const testObj = useTestObj()
  const testObjData = reactive({
    nickname: [],
    platformEnum: [],
    isAdd: false,
    updateId: 0,
    actionTitle: '添加测试对象',
  })
  const conditionItems: Array<FormItem> = reactive([
    {
      key: 'id',
      label: 'ID',
      type: 'input',
      placeholder: '请输入测试对象ID',
      value: '',
      reset: function () {
        this.value = ''
      },
    },
    {
      key: 'name',
      label: '环境名称',
      type: 'input',
      placeholder: '请输入环境名称',
      value: '',
      reset: function () {
        this.value = ''
      },
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
      label: '环境名称',
      key: 'name',
      value: '',
      type: 'input',
      required: true,
      placeholder: '请输入环境名称',
      validator: function () {
        if (!this.value) {
          Message.error(this.placeholder || '')
          return false
        }
        return true
      },
    },
    {
      label: '测试对象',
      key: 'value',
      value: '',
      type: 'input',
      required: true,
      placeholder: '请输入域名/名称/对象',
      validator: function () {
        if (!this.value) {
          Message.error(this.placeholder || '')
          return false
        }
        return true
      },
    },
    {
      label: '客户端类型',
      key: 'test_type',
      value: '',
      type: 'select',
      required: true,
      placeholder: '请选择客户端类型',
      validator: function () {
        if (this.value === null && this.value === '') {
          Message.error(this.placeholder || '')
          return false
        }
        return true
      },
    },
    {
      label: '绑定环境',
      key: 'environment',
      value: '',
      type: 'select',
      required: true,
      placeholder: '请选择绑定环境',
      validator: function () {
        if (this.value === null && this.value === '') {
          Message.error(this.placeholder || '')
          return false
        }
        return true
      },
    },
    {
      label: '负责人名称',
      key: 'executor_name',
      value: '',
      type: 'select',
      required: true,
      placeholder: '请输入负责人名称',
      validator: function () {
        if (this.value === null && this.value === '') {
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
      title: '项目名称',
      key: 'project',
      dataIndex: 'project',
      width: 150,
    },
    {
      title: '环境名称',
      key: 'name',
      dataIndex: 'name',
    },
    {
      title: '域名/包名',
      key: 'value',
      dataIndex: 'value',
      align: 'left',
    },
    {
      title: '客户端类型',
      key: 'test_type',
      dataIndex: 'test_type',
    },
    {
      title: '绑定环境',
      key: 'environment',
      dataIndex: 'environment',
      width: 150,
    },
    {
      title: '项目负责人',
      key: 'executor_name',
      dataIndex: 'executor_name',
    },
    {
      title: '数据库断言',
      key: 'db_status',
      dataIndex: 'db_status',
    },
    {
      title: '操作',
      key: 'actions',
      dataIndex: 'actions',
      fixed: 'right',
      width: 150,
    },
  ])

  function onResetSearch() {
    conditionItems.forEach((it) => {
      it.value = ''
    })
  }

  function onAddPage() {
    testObjData.actionTitle = '添加测试对象'
    testObjData.isAdd = true
    modalDialogRef.value?.toggle()
    formItems.forEach((it) => {
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
          url: systemTestObject,
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

  function onUpdate(item: any) {
    testObjData.actionTitle = '编辑测试对象'
    testObjData.isAdd = false
    testObjData.updateId = item.id
    modalDialogRef.value?.toggle()
    nextTick(() => {
      formItems.forEach((it) => {
        const propName = item[it.key]
        if (typeof propName === 'object' && propName !== null) {
          if (propName.name) {
            it.value = propName.id
          } else {
            it.value = propName.id
          }
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
      if (testObjData.isAdd) {
        post({
          url: systemTestObject,
          data: () => {
            value['db_status'] = 0
            return value
          },
        })
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
            testObj.getEnvironment()
          })
          .catch(console.log)
      } else {
        put({
          url: systemTestObject,
          data: () => {
            value['id'] = testObjData.updateId
            return value
          },
        })
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
            testObj.getEnvironment()
          })
          .catch(console.log)
      }
    }
  }

  function doRefresh() {
    get({
      url: systemTestObject,
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

  function getNickName() {
    get({
      url: userNickname,
      data: () => {
        return {}
      },
    })
      .then((res) => {
        testObjData.nickname = res.data
      })
      .catch(console.log)
  }

  function getPlatform() {
    get({
      url: systemEnumPlatform,
      data: () => {
        return {}
      },
    })
      .then((res) => {
        testObjData.platformEnum = res.data
      })
      .catch(console.log)
  }

  const onModifyStatus = async (newValue: boolean, id: number) => {
    return new Promise<any>((resolve, reject) => {
      setTimeout(async () => {
        try {
          let value: any = false
          await put({
            url: systemTestObjectPutStatus,
            data: () => {
              return {
                id: id,
                db_status: newValue ? 1 : 0,
              }
            },
          })
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
      doRefresh()
      getNickName()
      getPlatform()
      uEnvironment.getEnvironment()
    })
  })
</script>
