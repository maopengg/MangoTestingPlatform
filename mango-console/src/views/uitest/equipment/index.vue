<template>
  <TableBody ref="tableBody" title="设备配置">
    <template #header></template>
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
              {{ record.user.name }}
            </template>
            <template v-else-if="item.key === 'type'" #cell="{ record }">
              <a-tag :color="enumStore.colors[record.tpye]" size="small"
                >{{ enumStore.drive_type[record.type].title }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'web_type'" #cell="{ record }">
              <a-tag :color="enumStore.colors[record.config?.web_type]" size="small">
                {{ enumStore.browser_type[record.config.web_type]?.title || '' }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'web_max'" #cell="{ record }">
              <a-switch
                :default-checked="record.config?.web_max === 1"
                :beforeChange="(newValue) => onModifyStatus(newValue, record.id, item.key)"
              />
            </template>
            <template v-else-if="item.key === 'web_recording'" #cell="{ record }">
              <a-switch
                :default-checked="record.config?.web_recording === 1"
                :beforeChange="(newValue) => onModifyStatus(newValue, record.id, item.key)"
              />
            </template>
            <template v-else-if="item.key === 'web_parallel'" #cell="{ record }">
              {{ record.config?.web_parallel }}
            </template>
            <template v-else-if="item.key === 'web_h5'" #cell="{ record }">
              {{ record.config?.web_h5 }}
            </template>
            <template v-else-if="item.key === 'web_path'" #cell="{ record }">
              {{ record.config?.web_path }}
            </template>
            <template v-else-if="item.key === 'and_equipment'" #cell="{ record }">
              {{ record.config?.and_equipment }}
            </template>
            <template v-else-if="item.key === 'status'" #cell="{ record }">
              <a-switch
                :default-checked="record.status === 1"
                :beforeChange="(newValue) => onModifyStatus(newValue, record.id, item.key)"
              />
            </template>
            <template v-else-if="item.key === 'web_headers'" #cell="{ record }">
              <a-switch
                :default-checked="record.config?.web_headers === 1"
                :beforeChange="(newValue) => onModifyStatus(newValue, record.id, item.key)"
              />
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <a-space>
                <template v-if="record.type === 0">
                  <a-button type="text" size="mini" @click="onTakeOver(record.id)" disabled
                    >接管端口
                  </a-button>
                  <a-button type="text" size="mini" @click="onDebugWEB(record.id)"
                    >启动浏览器
                  </a-button>
                </template>
                <template v-if="record.type === 1">
                  <a-button type="text" size="mini" @click="onDebugAndroid(record.id)"
                    >调试安卓
                  </a-button>
                  <a-button type="text" size="mini" @click="onUpdate(record)">编辑</a-button>
                </template>
                <a-dropdown trigger="hover">
                  <a-button type="text" size="mini">···</a-button>
                  <template #content>
                    <a-doption v-if="record.type !== 1">
                      <a-button type="text" size="mini" @click="onUpdate(record)">编辑 </a-button>
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
          <template v-else-if="item.type === 'select' && item.key === 'type'">
            <a-select
              v-model="item.value"
              :placeholder="item.placeholder"
              :options="enumStore.drive_type"
              :field-names="fieldNames"
              value-key="key"
              @change="changeStatus(item.value)"
              allow-clear
              allow-search
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'web_type'">
            <a-select
              v-model="item.value"
              :placeholder="item.placeholder"
              :options="enumStore.browser_type"
              :field-names="fieldNames"
              value-key="key"
              allow-clear
              allow-search
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'web_h5'">
            <a-select
              v-model="item.value"
              :placeholder="item.placeholder"
              :options="enumStore.device"
              value-key="key"
              allow-clear
              allow-search
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'web_parallel'">
            <a-select
              v-model="item.value"
              :placeholder="item.placeholder"
              :options="[
                { value: 1, label: '1' },
                { value: 2, label: '2' },
                { value: 3, label: '3' },
                { value: 5, label: '5' },
                { value: 10, label: '10' },
                { value: 15, label: '15' },
                { value: 20, label: '20' },
                { value: 30, label: '30' },
              ]"
              value-key="key"
              allow-clear
              allow-search
            />
          </template>
          <template v-else-if="item.type === 'switch' && item.key === 'web_headers'">
            <a-switch v-model="item.value" :checked-value="1" :unchecked-value="0" />
          </template>
          <template v-else-if="item.type === 'switch' && item.key === 'web_max'">
            <a-switch v-model="item.value" :checked-value="1" :unchecked-value="0" />
          </template>
          <template v-else-if="item.type === 'switch' && item.key === 'web_recording'">
            <a-switch v-model="item.value" :checked-value="1" :unchecked-value="0" />
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
  import { onMounted, ref, nextTick, reactive } from 'vue'
  import { fieldNames } from '@/setting'
  import { getFormItems } from '@/utils/datacleaning'
  import useUserStore from '@/store/modules/user'
  import { tableColumns, formItems, webFormItems, androidFormItems } from './config'
  import {
    deleteUiConfig,
    getUiConfig,
    getUiConfigNewBrowserObj,
    postUiConfig,
    putUiConfig,
    putUiConfigPutStatus,
  } from '@/api/uitest/config'
  import { useEnum } from '@/store/modules/get-enum'

  const userStore = useUserStore()
  const data = reactive({
    userList: [],
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
  const enumStore = useEnum()

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
            item.key === 'web_type' ||
            formItems.some(
              (item) => item.key === 'web_type' || formItems.some((item) => item.key === 'web_type')
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
      content: '是否要删除此设备配置？',
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
        if (it.key === 'user_id') {
          it.value = item[it.key].id
        } else if (it.key === 'type') {
          it.value = item[it.key]
        } else if (it.key === 'web_max') {
          it.value = item.config[it.key]
        } else if (it.key === 'web_recording') {
          it.value = item.config[it.key]
        } else if (it.key === 'web_parallel') {
          it.value = item.config[it.key]
        } else if (it.key === 'web_type') {
          it.value = item.config[it.key]
        } else if (it.key === 'web_h5') {
          it.value = item.config[it.key]
        } else if (it.key === 'web_path') {
          it.value = item.config[it.key]
        } else if (it.key === 'web_headers') {
          it.value = item.config[it.key]
        } else if (it.key === 'and_equipment') {
          it.value = item.config[it.key]
        }
      })
    })
  }

  function onDataForm() {
    if (formItems.every((it) => (it.validator ? it.validator() : true))) {
      modalDialogRef.value?.toggle()
      const value = getFormItems(formItems)
      const data1: any = {
        type: value.type,
        config: {
          web_max: value['web_max'] === null ? 0 : value['web_headers'],
          web_recording: value['web_recording'] === null ? 0 : value['web_headers'],
          web_parallel: value['web_parallel'],
          web_type: value['web_type'],
          web_h5: value['web_h5'],
          web_path: value['web_path'],
          web_headers: value['web_headers'] === null ? 0 : value['web_headers'],
          and_equipment: value['and_equipment'],
        },
      }
      if (data.isAdd) {
        data1['status'] = 0
        data1['user'] = userStore.userId
        postUiConfig(data1)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      } else {
        data1['id'] = data.updateId
        putUiConfig(data1)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      }
    }
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

  function onTakeOver(id: number) {
    Message.success('功能实现中' + id)
  }

  function onDebugAndroid(id: number) {
    Message.success('功能实现中' + id)
  }

  function onDebugWEB(id: number) {
    getUiConfigNewBrowserObj(id, 0)
      .then((res) => {
        Message.loading(res.msg)
      })
      .catch(console.log)
  }

  onMounted(() => {
    nextTick(async () => {
      doRefresh()
    })
  })
</script>
