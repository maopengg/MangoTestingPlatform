<template>
  <div>
    <div class="main-container">
      <TableBody ref="tableBody">
        <template #header>
          <TableHeader :show-filter="true" title="Api自动化用例组" @search="onSearch" @reset-search="onResetSearch">
            <template #search-content>
              <a-form layout="inline" :model="{}">
                <a-form-item v-for="item of conditionItems" :key="item.key" :label="item.label">
                  <template v-if="item.render">
                    <FormRender :render="item.render" :formItem="item" />
                  </template>
                  <template v-else>
                    <template v-if="item.type === 'input'">
                      <a-input v-model="item.value.value" :placeholder="item.placeholder" />
                    </template>
                    <template v-if="item.type === 'select'">
                      <a-select v-model="item.value.value" style="width: 150px" :placeholder="item.placeholder">
                        <a-option v-for="optionItem of item.optionItems" :key="optionItem.value" :value="optionItem.title">
                          {{ optionItem.title }}
                        </a-option>
                      </a-select>
                    </template>
                    <template v-if="item.type === 'date'">
                      <a-date-picker v-model="item.value.value" />
                    </template>
                    <template v-if="item.type === 'time'">
                      <a-time-picker v-model="item.value.value" value-format="HH:mm:ss" />
                    </template>
                    <template v-if="item.type === 'check-group'">
                      <a-checkbox-group v-model="item.value.value">
                        <a-checkbox v-for="it of item.optionItems" :value="it.value" :key="it.value">
                          {{ item.label }}
                        </a-checkbox>
                      </a-checkbox-group>
                    </template>
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
            :row-selection="{ selectedRowKeys, showCheckedAll }"
            :loading="tableLoading"
            :data="dataList"
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
                  {{ record.project.name }}
                </template>
                <template v-else-if="item.key === 'environment'" #cell="{ record }">
                  <a-tag color="orangered" size="small" v-if="record.environment === 0">测试环境</a-tag>
                  <a-tag color="cyan" size="small" v-else-if="record.environment === 1">预发环境</a-tag>
                  <a-tag color="green" size="small" v-else-if="record.environment === 2">生产环境</a-tag>
                </template>
                <template v-else-if="item.key === 'actions'" #cell="{ record }">
                  <a-space>
                    <a-button type="text" size="mini" @click="onRunCase(record)">执行</a-button>
                    <a-button type="text" size="mini" @click="onUpdate(record)">编辑</a-button>
                    <a-button status="danger" type="text" size="mini" @click="onDelete(record)">删除</a-button>
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
      <ModalDialog ref="modalDialogRef" :title="actionTitle" @confirm="onDataForm">
        <template #content>
          <a-form :model="formModel">
            <a-form-item
              :class="[item.required ? 'form-item__require' : 'form-item__no_require']"
              :label="item.label"
              v-for="item of formItems"
              :key="item.key"
            >
              <template v-if="item.type === 'input'">
                <a-input :placeholder="item.placeholder" v-model="item.value.value" />
              </template>
              <template v-else-if="item.type === 'textarea'">
                <a-textarea v-model="item.value.value" :placeholder="item.placeholder" :auto-size="{ minRows: 3, maxRows: 5 }" />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'department'">
                <a-select v-model="item.value.value" :placeholder="item.placeholder">
                  <a-option v-for="optionItem of conditionItems[2].optionItems" :key="optionItem.value" :value="optionItem.title">
                    {{ optionItem.title }}
                  </a-option>
                </a-select>
              </template>
            </a-form-item>
          </a-form>
        </template>
      </ModalDialog>
    </div>
  </div>
</template>

<script lang="ts">
import { get, post, put, deleted } from '@/api/http'
import { ApiCaseGroup } from '@/api/url'
import { usePagination, useRowKey, useRowSelection, useTable, useTableColumn } from '@/hooks/table'
import { FormItem, ModalDialogType } from '@/types/components'
import { Input, Message, Modal } from '@arco-design/web-vue'
import { defineComponent, h, onMounted, ref, nextTick, reactive } from 'vue'
import { useProject } from '@/store/modules/get-project'

const project = useProject()

const conditionItems: Array<FormItem> = [
  {
    key: 'name',
    label: '页面名称',
    type: 'input',
    placeholder: '请输入页面名称',
    value: ref(''),
    reset: function () {
      this.value.value = ''
    },
    render: (formItem: FormItem) => {
      return h(Input, {
        placeholder: '请输入页面名称',
        modelValue: formItem.value.value,
        'onUpdate:modelValue': (value) => {
          formItem.value.value = value
        }
      })
    }
  },
  {
    key: 'caseid',
    label: '页面ID',
    type: 'input',
    placeholder: '请输入页面ID',
    value: ref(''),
    reset: function () {
      this.value.value = ''
    },
    render: (formItem: FormItem) => {
      return h(Input, {
        placeholder: '请输入页面ID',
        modelValue: formItem.value.value,
        'onUpdate:modelValue': (value) => {
          formItem.value.value = value
        }
      })
    }
  },
  {
    key: 'project',
    label: '筛选项目',
    value: ref(),
    type: 'select',
    placeholder: '请选择项目',
    optionItems: [],
    reset: function () {
      this.value.value = undefined
    }
  }
]
conditionItems[2].optionItems = project.data
const formItems = [
  {
    label: '项目',
    key: 'project',
    value: ref(''),
    placeholder: '请输入用户昵称',
    required: true,
    type: 'input'
  },
  {
    label: '账号',
    key: 'username',
    value: ref(''),
    type: 'input',
    required: true,
    placeholder: '请输入用户账号'
  },
  {
    label: '密码',
    key: 'password',
    value: ref(''),
    type: 'input',
    required: true,
    placeholder: '请输入用户密码'
  },
  {
    label: '归属项目',
    key: 'department',
    value: ref(''),
    type: 'select',
    required: true,
    placeholder: '请选择角色项目'
  },
  {
    label: '绑定角色',
    key: 'role',
    value: ref(''),
    type: 'select',
    required: true,
    placeholder: '请选择用户角色，角色不同权限不同'
  }
] as FormItem[]

export default defineComponent({
  name: 'TableWithSearch',
  setup() {
    const actionTitle = ref('添加页面')
    const modalDialogRef = ref<ModalDialogType | null>(null)
    const pagination = usePagination(doRefresh)
    const { selectedRowKeys, onSelectionChange, showCheckedAll } = useRowSelection()
    const table = useTable()
    const rowKey = useRowKey('id')
    const tableColumns = useTableColumn([
      table.indexColumn,
      {
        title: '项目',
        key: 'project',
        dataIndex: 'project',
        width: 100
      },
      {
        title: '用例组名称',
        key: 'name',
        dataIndex: 'name',
        align: 'left'
      },
      {
        title: '包含用例id',
        key: 'case_id',
        dataIndex: 'case_id',
        width: 150
      },
      {
        title: '包含用例名称',
        key: 'case_name',
        dataIndex: 'case_name'
      },
      {
        title: '定时任务',
        key: 'time_name',
        dataIndex: 'time_name'
      },
      {
        title: '操作',
        key: 'actions',
        dataIndex: 'actions',
        fixed: 'right',
        width: 150
      }
    ])

    const formModel = ref({})

    function doRefresh() {
      get({
        url: ApiCaseGroup,
        data: () => {
          return {
            page: pagination.page,
            pageSize: pagination.pageSize
          }
        }
      })
        .then((res) => {
          table.handleSuccess(res)
          pagination.setTotalSize((res as any).totalSize)
        })
        .catch(console.log)
    }

    function onSearch() {
      let data: { [key: string]: string } = {}
      conditionItems.forEach((it) => {
        if (it.value.value) {
          data[it.key] = it.value.value
        }
      })
      console.log(data)
      if (JSON.stringify(data) === '{}') {
        doRefresh()
      } else if (data.project) {
        get({
          url: ApiCaseGroup,
          data: () => {
            return {
              page: pagination.page,
              pageSize: pagination.pageSize,
              executor_name: data.executor_name
            }
          }
        })
          .then((res) => {
            table.handleSuccess(res)
            pagination.setTotalSize(res.totalSize || 10)
            Message.success(res.msg)
          })
          .catch(console.log)
      } else if (data) {
        get({
          url: ApiCaseGroup,
          data: () => {
            return {
              id: data.caseid,
              page: pagination.page,
              pageSize: pagination.pageSize,
              executor_name: data.executor_name
            }
          }
        })
          .then((res) => {
            table.handleSuccess(res)
            pagination.setTotalSize(res.totalSize || 10)
            Message.success(res.msg)
          })
          .catch(console.log)
      }
    }

    function onResetSearch() {
      conditionItems.forEach((it) => {
        it.reset ? it.reset() : (it.value.value = '')
      })
    }

    const addUpdate = ref(0)
    const updateId: any = ref('')

    function onAddPage() {
      actionTitle.value = '添加页面'
      modalDialogRef.value?.toggle()
      addUpdate.value = 1
      formItems.forEach((it) => {
        if (it.reset) {
          it.reset()
        } else {
          it.value.value = ''
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
            url: ApiCaseGroup,
            data: () => {
              return {
                id: '[' + data.id + ']'
              }
            }
          })
            .then((res) => {
              Message.success(res.msg)
              doRefresh()
            })
            .catch(console.log)
        }
      })
    }

    function onUpdate(item: any) {
      actionTitle.value = '编辑页面'
      modalDialogRef.value?.toggle()
      addUpdate.value = 0
      updateId.value = item.id
      nextTick(() => {
        formItems.forEach((it) => {
          const key = it.key
          const propName = item[key]
          if (propName) {
            it.value.value = propName
          }
        })
      })
    }

    function onDataForm() {
      if (formItems.every((it) => (it.validator ? it.validator() : true))) {
        modalDialogRef.value?.toggle()
        let value: { [key: string]: string } = {}
        formItems.forEach((it) => {
          value[it.key] = it.value.value
        })
        console.log(value)
        if (addUpdate.value === 1) {
          addUpdate.value = 0
          post({
            url: ApiCaseGroup,
            data: () => {
              return {
                nickname: value.nickname,
                username: value.username,
                password: value.password,
                role: value.role,
                department: value.department
              }
            }
          })
            .then((res) => {
              Message.success(res.msg)
              doRefresh()
            })
            .catch(console.log)
        } else if (addUpdate.value === 0) {
          addUpdate.value = 0
          value['id'] = updateId.value
          updateId.value = 0
          put({
            url: ApiCaseGroup,
            data: () => {
              return {
                id: value.id,
                nickname: value.nickname,
                username: value.username,
                password: value.password,
                role: value.role,
                department: value.department
              }
            }
          })
            .then((res) => {
              Message.success(res.msg)
              doRefresh()
            })
            .catch(console.log)
        }
      }
    }

    onMounted(() => {
      nextTick(async () => {
        doRefresh()
      })
    })
    return {
      ...table,
      rowKey,
      pagination,
      tableColumns,
      conditionItems,
      selectedRowKeys,
      showCheckedAll,
      formItems,
      formModel,
      actionTitle,
      modalDialogRef,
      onSearch,
      onResetSearch,
      onSelectionChange,
      onDataForm,
      onAddPage,
      onUpdate,
      onDelete
    }
  }
})
</script>
