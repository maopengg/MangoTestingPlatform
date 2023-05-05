<template>
  <div>
    <div class="main-container">
      <TableBody ref="tableBody">
        <template #header>
          <TableHeader :show-filter="true" title="Ui元素页面对象" @search="onSearch" @reset-search="onResetSearch">
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
          <a-tabs @tab-click="(key) => switchType(key)">
            <template #extra>
              <a-space>
                <a-button type="primary" size="small" @click="onAddPage">新增</a-button>
                <a-button status="danger" size="small" @click="onDeleteItems">批量删除</a-button>
              </a-space>
            </template>
            <a-tab-pane key="0" title="Web页面对象" />
            <a-tab-pane key="1" title="Android页面对象" />
            <a-tab-pane key="2" title="IOS页面对象" />
            <a-tab-pane key="3" title="桌面页面对象" />
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
                <template v-else-if="item.key === 'team'" #cell="{ record }">
                  {{ record.team.name }}
                </template>
                <template v-else-if="item.key === 'actions'" #cell="{ record }">
                  <a-space>
                    <a-button type="text" size="mini" @click="onUpdate(record)">编辑</a-button>
                    <a-button type="text" size="mini" @click="onClick(record)">添加元素</a-button>
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
              <template v-else-if="item.type === 'select'">
                <a-select v-model="item.value.value" :placeholder="item.placeholder">
                  <a-option v-for="optionItem of conditionItems[2].optionItems" :key="optionItem.key" :value="optionItem.title">
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
// import {Search} from '@/components/ListSearch.vue'
import { get, post, put, deleted } from '@/api/http'
import { uiPage, uiPageQuery } from '@/api/url'
import { usePagination, useRowKey, useRowSelection, useTable, useTableColumn } from '@/hooks/table'
import { FormItem, ModalDialogType } from '@/types/components'
import { Input, Message, Modal } from '@arco-design/web-vue'
import { defineComponent, h, onMounted, ref, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useProject } from '@/store/modules/get-project'
import { transformData, getKeyByTitle } from '@/utils/datacleaning'

const project = useProject()

interface TreeItem {
  title: string
  key: string
  children?: TreeItem[]
}

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
    key: 'team',
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
    label: '项目名称',
    key: 'team',
    value: ref(''),
    placeholder: '请选择项目名称',
    required: true,
    type: 'select'
  },
  {
    label: '页面名称',
    key: 'name',
    value: ref(''),
    type: 'input',
    required: true,
    placeholder: '请输入页面名称'
  },
  {
    label: '页面地址',
    key: 'url',
    value: ref(''),
    type: 'input',
    required: true,
    placeholder: '请输入页面名称'
  }
] as FormItem[]

export default defineComponent({
  name: 'TableWithSearch',
  setup() {
    const searchForm = ref()
    const actionTitle = ref('添加页面')
    const modalDialogRef = ref<ModalDialogType | null>(null)
    const pagination = usePagination(doRefresh)
    const { selectedRowKeys, onSelectionChange, showCheckedAll } = useRowSelection()
    const table = useTable()
    const rowKey = useRowKey('id')
    const tableColumns = useTableColumn([
      table.indexColumn,
      {
        title: '项目名称',
        key: 'team',
        dataIndex: 'team',
        width: 150
      },
      {
        title: '页面名称',
        key: 'name',
        dataIndex: 'name',
        width: 150
      },
      {
        title: '页面地址',
        key: 'url',
        dataIndex: 'url',
        align: 'left'
      },
      {
        title: '操作',
        key: 'actions',
        dataIndex: 'actions',
        fixed: 'right',
        width: 150
      }
    ])
    const pageType: any = ref('0')

    function switchType(key: any) {
      pageType.value = key
      doRefresh()
    }

    const formModel = ref({})

    function doRefresh() {
      get({
        url: uiPage,
        data: () => {
          return {
            page: pagination.page,
            pageSize: pagination.pageSize,
            type: pageType.value
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
      } else {
        get({
          url: uiPageQuery,
          data: () => {
            return {
              page: pagination.page,
              pageSize: pagination.pageSize,
              type: pageType.value,
              id: data.id,
              name: data.name,
              team: data.team
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
            url: uiPage,
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
            url: uiPage,
            data: () => {
              return {
                id: JSON.stringify(selectedRowKeys.value)
              }
            }
          })
            .then((res) => {
              Message.success(res.msg)
              selectedRowKeys.value = []
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
        let value = transformData(formItems)
        let teamId = getKeyByTitle(project.data, value.team)
        if (addUpdate.value === 1) {
          addUpdate.value = 0
          post({
            url: uiPage,
            data: () => {
              return {
                team: teamId,
                name: value.name,
                url: value.url,
                type: pageType.value
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
            url: uiPage,
            data: () => {
              return {
                id: value.id,
                team: teamId,
                name: value.name,
                url: value.url,
                type: pageType.value
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

    // 获取所有项目
    const treeData = ref<Array<TreeItem>>([])

    // function getItems() {
    //   get({
    //     url: getAllItems,
    //     data: {}
    //   })
    //     .then((res) => {
    //       for (let value of conditionItems) {
    //         if (value.key === 'project') {
    //           value.optionItems = res.data
    //         }
    //       }
    //       treeData.value = transformRoutes(res.data)
    //     })
    //     .catch(console.log)
    // }
    //
    // function transformRoutes(routes: any[], parentPath = '/'): TreeItem[] {
    //   const list: TreeItem[] = []
    //   routes
    //     .filter((it) => it.hidden !== true && it.fullPath !== parentPath)
    //     .forEach((it) => {
    //       const searchItem: TreeItem = {
    //         // 可以控制是取id还是取名称
    //         key: it.title,
    //         title: it.title
    //       }
    //       if (it.children && it.children.length > 0) {
    //         searchItem.children = transformRoutes(it.children, it.fullPath)
    //       }
    //       list.push(searchItem)
    //     })
    //   return list
    // }

    const router = useRouter()

    function onClick(record: any) {
      console.log(record)
      router.push({
        path: '/uitest/pageel',
        query: {
          id: record.id,
          name: record.name,
          team_id: record.team.id
        }
      })
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
      searchForm,
      tableColumns,
      conditionItems,
      selectedRowKeys,
      showCheckedAll,
      formItems,
      formModel,
      actionTitle,
      modalDialogRef,
      treeData,
      onClick,
      onSearch,
      onResetSearch,
      onSelectionChange,
      onDataForm,
      onAddPage,
      onUpdate,
      onDelete,
      onDeleteItems,
      switchType
    }
  }
})
</script>
