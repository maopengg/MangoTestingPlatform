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
                  :options="data.userList"
                  :field-names="fieldNames"
                  value-key="key"
                  allow-clear
                  allow-search
                />
              </template>
              <template v-else-if="item.type === 'radio' && item.key === 'type'">
                <a-radio-group
                  @change="changeStatus"
                  v-model="data.type"
                  :options="data.driveType"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'type'">
                <a-select
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="data.driveType"
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
                  :options="data.browserType"
                  :field-names="fieldNames"
                  value-key="key"
                  allow-clear
                  allow-search
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'device'">
                <a-select
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="data.device"
                  value-key="key"
                  allow-clear
                  allow-search
                />
              </template>
              <template v-else-if="item.type === 'switch' && item.key === 'is_headless'">
                <a-switch v-model="item.value" :checked-value="1" :unchecked-value="0" />
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
  import { fieldNames } from '@/setting'
  import { getFormItems } from '@/utils/datacleaning'
  import useUserStore from '@/store/modules/user'
  import { tableColumns, formItems, webFormItems, androidFormItems } from './config'
  import { getUserNickname } from '@/api/user'
  import { getSystemEnumBrowser, getSystemEnumDrive, getSystemEnumUiDevice } from '@/api/system'
  import {
    deleteUiConfig,
    getUiConfig,
    getUiConfigNewBrowserObj,
    postUiConfig,
    putUiConfig,
    putUiConfigPutStatus,
  } from '@/api/uitest'
  const userStore = useUserStore()
  const data = reactive({
    userList: [],
    browserType: [],
    driveType: [],
    device: [],
    loading: false,
    actionTitle: '添加配置',
    updateId: 0,
    isAdd: true,
    type: 0,
  })
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const pagination = usePagination(doRefresh)
  const { onSelectionChange } = useRowSelection()
  const table = useTable()
  const rowKey = useRowKey('id')
  const formModel = ref({})

  function changeStatus(event: number) {
    for (let i = formItems.length - 1; i >= 0; i--) {
      if (formItems[i].key !== 'type') {
        formItems.splice(i, 1)
      }
    }
    if (event === 0) {
      if (
        !formItems.some(
          (item) =>
            item.key === 'browser_type' ||
            formItems.some(
              (item) =>
                item.key === 'browser_port' || formItems.some((item) => item.key === 'browser_path')
            )
        )
      ) {
        formItems.push(...webFormItems)
      }
    } else if (event === 1) {
      if (!formItems.some((item) => item.key === 'equipment')) {
        formItems.push(...androidFormItems)
      }
    } else if (event === 2) {
    } else {
    }
  }

  function doRefresh() {
    getUiConfig({
      page: pagination.page,
      pageSize: pagination.pageSize,
      user_id: userStore.userId,
    })
      .then((res) => {
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
      })
      .catch(console.log)
  }

  function onAddPage() {
    changeStatus(0)
    modalDialogRef.value?.toggle()
    data.isAdd = true
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
        deleteUiConfig(data.id)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      },
    })
  }

  function onUpdate(item: any) {
    changeStatus(item.type)
    data.actionTitle = '编辑配置'
    modalDialogRef.value?.toggle()
    data.isAdd = false
    data.updateId = item.id
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
    if (data.type === 3 || data.type === 2) {
      Message.error('暂不支持PC客户端和IOS的配置')

      return
    }
    if (formItems.every((it) => (it.validator ? it.validator() : true))) {
      modalDialogRef.value?.toggle()
      const value = getFormItems(formItems)
      if (data.isAdd) {
        value['type'] = data.type
        value['status'] = 0
        value['user_id'] = userStore.userId
        postUiConfig(value)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      } else {
        value['id'] = data.updateId
        putUiConfig(value)
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
          await putUiConfigPutStatus(obj)
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
    getUserNickname()
      .then((res) => {
        data.userList = res.data
      })
      .catch(console.log)
  }

  function getUiConfigGetBrowserType() {
    getSystemEnumBrowser()
      .then((res) => {
        data.browserType = res.data
      })
      .catch(console.log)
  }

  function getUiConfigGetDriveType() {
    getSystemEnumDrive()
      .then((res) => {
        data.driveType = res.data
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
    getUiConfigNewBrowserObj(id)
      .then((res) => {
        data.driveType = res.data
      })
      .catch(console.log)
  }
  function onEnumUiEquipment() {
    getSystemEnumUiDevice()
      .then((res) => {
        data.device = res.data
      })
      .catch(console.log)
  }

  onMounted(() => {
    nextTick(async () => {
      doRefresh()
      getUiConfigGetBrowserType()
      getUiConfigGetDriveType()
      getNickName()
      onEnumUiEquipment()
    })
  })
</script>
