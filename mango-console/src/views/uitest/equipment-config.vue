<template>
  <div>
    <div class="main-container">
      <TableBody ref="tableBody" title="设备配置">
        <template #header> </template>
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
                <template v-else-if="item.key === 'user_id'" #cell="{ record }">
                  {{ record.user_id.nickname }}
                </template>
                <template v-else-if="item.key === 'type'" #cell="{ record }">
                  <a-tag color="green" size="small" v-if="record.type === 0">WEB</a-tag>
                  <a-tag color="red" size="small" v-else-if="record.type === 1">安卓</a-tag>
                </template>
                <template v-else-if="item.key === 'browser_type'" #cell="{ record }">
                  <a-tag color="green" size="small" v-if="record.browser_type === 0"
                    >谷歌浏览器</a-tag
                  >
                  <a-tag color="red" size="small" v-else-if="record.browser_type === 1">EDGE</a-tag>
                  <a-tag color="red" size="small" v-else-if="record.browser_type === 2">火狐</a-tag>
                  <a-tag color="red" size="small" v-else-if="record.browser_type === 3"
                    >WEBKIT</a-tag
                  >
                </template>
                <template v-else-if="item.key === 'status'" #cell="{ record }">
                  <a-switch
                    :default-checked="record.status === 1"
                    :beforeChange="(newValue) => onModifyStatus(newValue, record.id, item.key)"
                  />
                </template>
                <template v-else-if="item.key === 'is_headless'" #cell="{ record }">
                  <a-switch
                    :default-checked="record.is_headless === 1"
                    :beforeChange="(newValue) => onModifyStatus(newValue, record.id, item.key)"
                  />
                </template>
                <template v-else-if="item.key === 'actions'" #cell="{ record }">
                  <a-space>
                    <template v-if="record.type === 0">
                      <a-button type="text" size="mini" @click="onTakeOver(record.id)"
                        >接管端口</a-button
                      >
                      <a-button type="text" size="mini" @click="onDebugWEB(record.id)"
                        >调试WEB</a-button
                      >
                    </template>
                    <template v-if="record.type === 1">
                      <a-button type="text" size="mini" @click="onDebugAndroid(record.id)"
                        >调试安卓</a-button
                      >
                      <a-button type="text" size="mini" @click="onUpdate(record)">编辑</a-button>
                    </template>
                    <a-dropdown trigger="hover">
                      <a-button type="text" size="mini">···</a-button>
                      <template #content>
                        <a-doption v-if="record.type !== 1">
                          <a-button type="text" size="mini" @click="onUpdate(record)"
                            >编辑</a-button
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
      <ModalDialog ref="modalDialogRef" :title="uiConfigData.actionTitle" @confirm="onDataForm">
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
              <template v-else-if="item.type === 'select' && item.key === 'user_id'">
                <a-select
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="uiConfigData.userList"
                  :field-names="fieldNames"
                  value-key="key"
                  allow-clear
                  allow-search
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'type'">
                <a-select
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="uiConfigData.driveType"
                  :field-names="fieldNames"
                  value-key="key"
                  allow-clear
                  allow-search
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'browser_type'">
                <a-select
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="uiConfigData.browserType"
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
    userNickname,
    uiConfig,
    systemEnumDrive,
    systemEnumBrowser,
    uiConfigNewBrowserObj,
    uiConfigPutStatus,
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
  import { fieldNames } from '@/setting'
  import { getFormItems } from '@/utils/datacleaning'
  import useUserStore from '@/store/modules/user'

  const userStore = useUserStore()
  const uiConfigData = reactive({
    userList: [],
    browserType: [],
    driveType: [],
    loading: false,
    actionTitle: '添加配置',
    updateId: 0,
    isAdd: true,
  })
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const pagination = usePagination(doRefresh)
  const { onSelectionChange } = useRowSelection()
  const table = useTable()
  const rowKey = useRowKey('id')
  const formModel = ref({})
  const formItems: FormItem[] = reactive([
    {
      label: '驱动类型',
      key: 'type',
      value: '',
      type: 'select',
      required: true,
      placeholder: '请选择驱动类型',
      validator: function () {
        if (!this.value && this.value !== 0) {
          Message.error(this.placeholder || '')
          return false
        }
        return true
      },
    },
    {
      label: '浏览器',
      key: 'browser_type',
      value: '',
      type: 'select',
      required: false,
      placeholder: '请选择浏览器',
      validator: function () {
        return true
      },
    },
    {
      label: '浏览器端口',
      key: 'browser_port',
      value: '',
      placeholder: '请输入浏览器调试端口',
      required: false,
      type: 'input',
      validator: function () {
        return true
      },
    },
    {
      label: '浏览器路径',
      key: 'browser_path',
      value: '',
      type: 'textarea',
      required: false,
      placeholder: '请输入浏览器路径',
      validator: function () {
        return true
      },
    },
    {
      label: '安卓设备号',
      key: 'equipment',
      value: '',
      placeholder: '请输入安卓设备号或IP+端口',
      required: false,
      type: 'input',
      validator: function () {
        return true
      },
    },
  ])

  const tableColumns = useTableColumn([
    table.indexColumn,
    {
      title: '驱动类型',
      key: 'type',
      dataIndex: 'type',
    },
    {
      title: '浏览器',
      key: 'browser_type',
      dataIndex: 'browser_type',
    },
    {
      title: '浏览器端口',
      key: 'browser_port',
      dataIndex: 'browser_port',
    },
    {
      title: '浏览器地址',
      key: 'browser_path',
      dataIndex: 'browser_path',
      align: 'left',
    },
    {
      title: '安卓设备号',
      key: 'equipment',
      dataIndex: 'equipment',
      align: 'left',
    },
    {
      title: '所属用户',
      key: 'user_id',
      dataIndex: 'user_id',
    },
    {
      title: '是否开启无头',
      key: 'is_headless',
      dataIndex: 'is_headless',
    },
    {
      title: '状态',
      key: 'status',
      dataIndex: 'status',
    },
    {
      title: '操作',
      key: 'actions',
      dataIndex: 'actions',
      fixed: 'right',
      width: 150,
    },
  ])

  function doRefresh() {
    get({
      url: uiConfig,
      data: () => {
        return {
          page: pagination.page,
          pageSize: pagination.pageSize,
          user_id: userStore.userId,
        }
      },
    })
      .then((res) => {
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
      })
      .catch(console.log)
  }

  function onAddPage() {
    modalDialogRef.value?.toggle()
    uiConfigData.isAdd = true
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
          url: uiConfig,
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
    uiConfigData.actionTitle = '编辑配置'
    modalDialogRef.value?.toggle()
    uiConfigData.isAdd = false
    uiConfigData.updateId = item.id
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

  function onDataForm() {
    if (formItems.every((it) => (it.validator ? it.validator() : true))) {
      modalDialogRef.value?.toggle()
      const value = getFormItems(formItems)
      if (uiConfigData.isAdd) {
        post({
          url: uiConfig,
          data: () => {
            value['status'] = 0
            value['is_headless'] = 0
            value['user_id'] = userStore.userId
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
          url: uiConfig,
          data: () => {
            value['id'] = uiConfigData.updateId
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

  const onModifyStatus = async (newValue: number, id: number, key: string) => {
    let obj: any = {
      id: id,
    }
    if (key === 'is_headless') {
      obj['is_headless'] = newValue ? 1 : 0
    } else {
      obj['status'] = newValue ? 1 : 0
    }
    return new Promise<any>((resolve, reject) => {
      setTimeout(async () => {
        try {
          let value: any = false
          await put({
            url: uiConfigPutStatus,
            data: () => {
              return obj
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

  function getNickName() {
    get({
      url: userNickname,
      data: () => {
        return {}
      },
    })
      .then((res) => {
        uiConfigData.userList = res.data
      })
      .catch(console.log)
  }

  function getUiConfigGetBrowserType() {
    get({
      url: systemEnumBrowser,
      data: () => {
        return {}
      },
    })
      .then((res) => {
        uiConfigData.browserType = res.data
      })
      .catch(console.log)
  }

  function getUiConfigGetDriveType() {
    get({
      url: systemEnumDrive,
      data: () => {
        return {}
      },
    })
      .then((res) => {
        uiConfigData.driveType = res.data
      })
      .catch(console.log)
  }

  function onTakeOver(id: number) {
    Message.success('功能实现中' + id)
  }

  function onDebugAndroid(id: number) {
    Message.success('功能实现中' + id)
  }

  function onDebugWEB(id: number) {
    get({
      url: uiConfigNewBrowserObj,
      data: () => {
        return { id: id }
      },
    })
      .then((res) => {
        uiConfigData.driveType = res.data
      })
      .catch(console.log)
  }

  const handleChangeIntercept = async (newValue: any) => {
    await new Promise((resolve) => setTimeout(resolve, 1000))
    return true
  }
  onMounted(() => {
    nextTick(async () => {
      doRefresh()
      getUiConfigGetBrowserType()
      getUiConfigGetDriveType()
      getNickName()
    })
  })
</script>
