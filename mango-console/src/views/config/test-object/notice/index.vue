<template>
  <TableBody ref="tableBody">
    <template #header>
      <TableHeader
        :show-filter="true"
        title="自动化通知配置"
        @search="doRefresh"
        @reset-search="onResetSearch"
      >
        <template #search-content>
          <a-form :model="{}" layout="inline" @keyup.enter="doRefresh">
            <a-form-item v-for="item of conditionItems" :key="item.key" :label="item.label">
              <template v-if="item.type === 'input'">
                <a-input v-model="item.value" :placeholder="item.placeholder" @blur="doRefresh" />
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
      <a-tabs>
        <template #extra>
          <a-space>
            <div>
              <a-button size="small" type="primary" @click="onAdd">新增</a-button>
            </div>
          </a-space>
        </template>
      </a-tabs>
      <a-table
        :bordered="false"
        :columns="tableColumns"
        :data="table.dataList"
        :loading="table.tableLoading.value"
        :pagination="false"
        :rowKey="rowKey"
        @selection-change="onSelectionChange"
      >
        <template #columns>
          <a-table-column
            v-for="item of tableColumns"
            :key="item.key"
            :align="item.align"
            :data-index="item.key"
            :fixed="item.fixed"
            :title="item.title"
            :width="item.width"
          >
            <template v-if="item.key === 'index'" #cell="{ record }">
              {{ record.id }}
            </template>
            <template v-else-if="item.key === 'type'" #cell="{ record }">
              <a-tag :color="enumStore.colors[record.type]" size="small"
                >{{ enumStore.notice[record.type].title }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'config'" #cell="{ record }">
              {{ record.config }}
            </template>
            <template v-else-if="item.key === 'status'" #cell="{ record }">
              <a-switch
                :beforeChange="(newValue) => onModifyStatus(newValue, record.id)"
                :default-checked="record.status === 1"
              />
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <a-space>
                <a-button size="mini" type="text" class="custom-mini-btn" @click="onTest(record)"
                  >测试一下
                </a-button>
                <a-button size="mini" type="text" class="custom-mini-btn" @click="onUpdate(record)"
                  >编辑
                </a-button>
                <a-button
                  size="mini"
                  status="danger"
                  type="text"
                  class="custom-mini-btn"
                  @click="onDelete(record)"
                  >删除
                </a-button>
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
          v-for="item of data.formItems"
          :key="item.key"
          :class="[item.required ? 'form-item__require' : 'form-item__no_require']"
          :label="item.label"
        >
          <template v-if="item.type === 'input'">
            <a-input v-model="item.value" :placeholder="item.placeholder" />
          </template>
          <template v-else-if="item.type === 'textarea' && item.key === 'config'">
            <a-textarea
              v-model="item.value"
              :auto-size="{ minRows: 5, maxRows: 9 }"
              :placeholder="item.placeholder"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'type'">
            <a-select
              v-model="item.value"
              :field-names="fieldNames"
              :options="enumStore.notice"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              value-key="key"
              @change="onChange(item.value)"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'config'">
            <a-select
              v-model="item.value"
              :placeholder="item.placeholder"
              :scrollbar="true"
              multiple
            >
              <a-option v-for="user of data.userList" :key="user.key">{{ user.title }}</a-option>
            </a-select>
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
  import { conditionItems, formItems, tableColumns, mailboxForm, configForm } from './config'
  import {
    deleteSystemNotice,
    getSystemNotice,
    getSystemNoticeTest,
    postSystemNotice,
    putSystemNotice,
    putSystemNoticePutStatus,
  } from '@/api/system/notice_config'
  import { getUserName } from '@/api/user/user'
  import { useRoute } from 'vue-router'
  import { useEnum } from '@/store/modules/get-enum'

  const route = useRoute()
  const enumStore = useEnum()

  const modalDialogRef = ref<ModalDialogType | null>(null)
  const pagination = usePagination(doRefresh)
  const { onSelectionChange } = useRowSelection()
  const table = useTable()
  const rowKey = useRowKey('id')
  const formModel = ref({})

  const data: any = reactive({
    isAdd: false,
    updateId: 0,
    actionTitle: '新增',
    userList: [],
    formItems: [],
  })

  function doRefresh() {
    let value = getFormItems(conditionItems)
    value['test_object_id'] = route.query.id
    value['page'] = pagination.page
    value['pageSize'] = pagination.pageSize
    getSystemNotice(value)
      .then((res) => {
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
      })
      .catch(console.log)
  }

  function onChange(value: number) {
    data.formItems = []
    data.formItems.push(...formItems)
    if (value === 0) {
      mailboxForm[0].value = []
      data.formItems.push(...mailboxForm)
    } else if (value === 1) {
      mailboxForm[0].value = ''
      data.formItems.push(...configForm)
    }
  }

  function onResetSearch() {
    conditionItems.forEach((it) => {
      it.value = ''
    })
    doRefresh()
  }

  function onAdd() {
    data.formItems = []
    data.formItems.push(...formItems)
    data.actionTitle = '添加'
    modalDialogRef.value?.toggle()
    data.isAdd = true
    data.formItems.forEach((it: any) => {
      if (it.reset) {
        it.reset()
      } else {
        it.value = ''
      }
    })
  }

  function onDelete(record: any) {
    Modal.confirm({
      title: '提示',
      content: '是否要删除此配置？',
      cancelText: '取消',
      okText: '删除',
      onOk: () => {
        deleteSystemNotice(record.id)
          .then((res) => {
            Message.success(res.msg)
          })
          .catch(console.log)
          .finally(() => {
            doRefresh()
          })
      },
    })
  }

  function onUpdate(item: any) {
    data.formItems = []
    data.formItems.push(...formItems)
    data.actionTitle = '编辑'
    modalDialogRef.value?.toggle()
    data.isAdd = false
    data.updateId = item.id
    onChange(item.type)
    nextTick(() => {
      data.formItems.forEach((it: any) => {
        const propName = item[it.key]
        if (typeof propName === 'object' && propName !== null) {
          it.value = propName.id
        } else if (item.type === 0) {
          it.value = JSON.parse(propName)
        } else {
          it.value = propName
        }
      })
    })
  }

  function onDataForm() {
    if (data.formItems.every((it: any) => (it.validator ? it.validator() : true))) {
      let value = getFormItems(data.formItems)
      if (data.isAdd) {
        value['test_object'] = route.query.id
        value['status'] = 0
        postSystemNotice(value)
          .then((res) => {
            modalDialogRef.value?.toggle()
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      } else {
        value['id'] = data.updateId
        putSystemNotice(value)
          .then((res) => {
            modalDialogRef.value?.toggle()
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      }
    }
  }

  const onModifyStatus = async (newValue: boolean, id: number) => {
    return new Promise<any>((resolve, reject) => {
      setTimeout(async () => {
        try {
          let value: any = false
          await putSystemNoticePutStatus(id, newValue ? 1 : 0)
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
    getUserName()
      .then((res) => {
        data.userList = res.data
      })
      .catch(console.log)
  }

  function onTest(record: any) {
    getSystemNoticeTest(record.id)
      .then((res) => {
        Message.success(res.msg)
      })
      .catch(console.log)
  }

  onMounted(() => {
    nextTick(async () => {
      doRefresh()
      getNickName()
    })
  })
  onMounted(doRefresh)
</script>
