<template>
  <TableBody ref="tableBody">
    <template #header>
      <TableHeader
        :show-filter="true"
        title="公共方法"
        @search="onSearchRefresh"
        @reset-search="onResetSearch"
      >
        <template #search-content>
          <a-form :model="{}" layout="inline" @keyup.enter="onSearchRefresh">
            <a-form-item v-for="item of conditionItems" :key="item.key" :label="item.label">
              <template v-if="item.type === 'input'">
                <a-input
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  allow-clear
                  @blur="onSearchRefresh"
                  @clear="onSearchRefresh"
                />
              </template>
              <template v-else-if="item.type === 'cascader' && item.key === 'project_product'">
                <ProjectProductSelect
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  @change="onSearchRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select'">
                <a-select
                  v-model="item.value"
                  :field-names="fieldNames"
                  :options="item.key === 'test_env' ? enumStore.environment_type : item.optionItems"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="onSearchRefresh"
                />
              </template>
            </a-form-item>
          </a-form>
        </template>
      </TableHeader>
    </template>

    <template #default>
      <a-tabs default-active-key="0" @tab-click="(key) => switchType(key)">
        <template #extra>
          <div>
            <a-button size="small" type="primary" @click="onAdd">新增</a-button>
          </div>
        </template>
      </a-tabs>
      <a-table
        :scroll="{ x: 1100 }"
        :bordered="false"
        :columns="tableColumns"
        :data="table.dataList"
        :loading="table.tableLoading.value"
        :pagination="false"
        :row-selection="{ selectedRowKeys, showCheckedAll }"
        :rowKey="rowKey"
        @selection-change="onSelectionChange"
      >
        <template #columns>
          <a-table-column
            v-for="item of tableColumns"
            :key="item.key"
            :align="item.align"
            :data-index="item.key"
            :ellipsis="item.ellipsis"
            :fixed="item.fixed"
            :title="item.title"
            :tooltip="item.tooltip"
            :width="item.width"
          >
            <template v-if="item.key === 'index'" #cell="{ record }">
              {{ record.id }}
            </template>
            <template v-else-if="item.key === 'project_product'" #cell="{ record }">
              {{ formatProjectProductPath(record?.project_product) }}
            </template>
            <template v-else-if="item.key === 'test_env'" #cell="{ record }">
              <a-tag :color="enumStore.colors[record.test_env]" size="small">
                {{ enumStore.environment_type[record.test_env]?.title }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'type'" #cell="{ record }">
              <a-tag :color="enumStore.colors[record.type]" size="small"
                >{{ enumStore.ui_public[record.type]?.title || '-' }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'datasource_alias'" #cell="{ record }">
              <a-tag v-if="record.datasource_alias" size="small">
                {{ record.datasource_alias.name }}
              </a-tag>
              <span v-else>-</span>
            </template>
            <template v-else-if="item.key === 'status'" #cell="{ record }">
              <a-switch
                :beforeChange="(newValue) => onModifyStatus(newValue, record.id)"
                :default-checked="record.status === 1"
              />
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <MangoTableActions
                :actions="[
                  { label: '编辑', onClick: () => onUpdate(record) },
                  { label: '删除', danger: true, onClick: () => onDelete(record) },
                ]"
              />
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
          v-for="item of formItems"
          v-show="isFormItemVisible(item)"
          :key="item.key"
          :class="[item.required ? 'mango-form-item__require' : 'mango-form-item__no_require']"
          :label="item.label"
        >
          <template v-if="item.type === 'input'">
            <a-input v-model="item.value" :placeholder="item.placeholder" />
          </template>
          <template v-else-if="item.type === 'textarea'">
            <a-textarea
              v-model="item.value"
              :auto-size="{ minRows: 3, maxRows: 5 }"
              :placeholder="item.placeholder"
            />
          </template>

          <template v-else-if="item.type === 'cascader'">
            <ProjectProductSelect
              v-model="item.value"
              :placeholder="item.placeholder"
              @change="onProjectProductChange"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'type'">
            <a-select
              v-model="item.value"
              :field-names="fieldNames"
              :options="enumStore.ui_public"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              value-key="key"
              @change="onTypeChange"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'test_env'">
            <a-select
              v-model="item.value"
              :field-names="fieldNames"
              :options="enumStore.environment_type"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              value-key="key"
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'datasource_alias'">
            <a-select
              v-if="isSqlPublicType"
              v-model="item.value"
              :options="datasourceAliasOptions"
              :field-names="{ value: 'id', label: 'name' }"
              :placeholder="item.placeholder"
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
  import { ModalDialogType } from '@/types/components'
  import { Message, Modal } from '@arco-design/web-vue'
  import { computed, onMounted, ref, nextTick, reactive } from 'vue'
  import { fieldNames } from '@/setting'
  import { getFormItems } from '@/utils/datacleaning'
  import { conditionItems, tableColumns, formItems } from './config'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import { formatProjectProductPath } from '@/utils/business-format'
  import {
    deleteUiPublic,
    getUiPublic,
    postUiPublic,
    putUiPublic,
    putUiPublicPutStatus,
  } from '@/api/uitest/public'
  import { useEnum } from '@/store/modules/get-enum'
  import useUserStore from '@/store/modules/user'
  import { getDataFactoryDatasourceAlias } from '@/api/data-factory'

  const enumStore = useEnum()
  const userStore = useUserStore()

  const modalDialogRef = ref<ModalDialogType | null>(null)
  const pagination = usePagination(doRefresh)
  const { selectedRowKeys, onSelectionChange, showCheckedAll } = useRowSelection()
  const table = useTable()
  const rowKey = useRowKey('id')
  const formModel = ref({})
  const datasourceAliasOptions = ref<any[]>([])
  const data = reactive({
    type: 0,
    actionTitle: '新增',
    updateId: 0,
    isAdd: true,
  })

  const isSqlPublicType = computed(() => Number(getFormValue('type')) === 1)

  function getFormValue(key: string) {
    return formItems.find((it) => it.key === key)?.value
  }

  function setFormValue(key: string, value: any) {
    const item = formItems.find((it) => it.key === key)
    if (item) {
      item.value = value
    }
  }

  function getFormNumberValue(key: string) {
    const value = getFormValue(key)
    return value === '' || value == null ? null : Number(value)
  }

  function isFormItemVisible(item: any) {
    return item.key !== 'datasource_alias' || isSqlPublicType.value
  }

  function loadDatasourceAliasOptions(projectProductId?: any) {
    const productId = projectProductId ?? getFormValue('project_product')
    datasourceAliasOptions.value = []
    if (!productId && productId !== 0) {
      return Promise.resolve()
    }
    return getDataFactoryDatasourceAlias({
      project_product: productId,
      page: 1,
      pageSize: 999,
    }).then((res) => {
      datasourceAliasOptions.value = res.data || []
    })
  }

  function onProjectProductChange(value: any) {
    setFormValue('datasource_alias', '')
    loadDatasourceAliasOptions(value)
  }

  function onTypeChange(value: any) {
    if (Number(value) !== 1) {
      setFormValue('datasource_alias', '')
    } else {
      loadDatasourceAliasOptions()
    }
  }

  function switchType(key: any) {
    data.type = key
  }

  function onSearchRefresh() {
    doRefresh(true)
  }

  function doRefresh(showLoading = false) {
    if (showLoading) {
      table.tableLoading.value = true
    }
    let value = getFormItems(conditionItems)
    value['page'] = pagination.page
    value['pageSize'] = pagination.pageSize
    getUiPublic(value)
      .then((res) => {
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
      })
      .catch(console.log)
      .finally(() => {
        if (showLoading) {
          table.tableLoading.value = false
        }
      })
  }

  function onResetSearch() {
    conditionItems.forEach((it) => {
      it.value = ''
    })
    doRefresh(true)
  }

  const onModifyStatus = async (newValue: boolean, id: number) => {
    return new Promise<any>((resolve, reject) => {
      setTimeout(async () => {
        try {
          let value: any = false
          await putUiPublicPutStatus(id, newValue ? 1 : 0)
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

  function onAdd() {
    data.actionTitle = '新增'
    data.isAdd = true
    modalDialogRef.value?.toggle()
    formItems.forEach((it) => {
      if (it.reset) {
        it.reset()
      } else {
        it.value = ''
      }
    })
    const envItem = formItems.find((it) => it.key === 'test_env')
    if (envItem && userStore.selected_environment != null) {
      envItem.value = userStore.selected_environment
    }
    datasourceAliasOptions.value = []
  }

  function onDelete(record: any) {
    Modal.confirm({
      title: '提示',
      content: '是否要删除此参数？',
      cancelText: '取消',
      okText: '删除',
      onBeforeOk: () => {
        return deleteUiPublic(record.id)
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
    data.actionTitle = '编辑'
    data.isAdd = false
    data.updateId = item.id
    modalDialogRef.value?.toggle()
    nextTick(() => {
      loadDatasourceAliasOptions(item?.project_product?.id || item?.project_product)
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
      let value = getFormItems(formItems)
      if (Number(value.type) === 1 && !getFormNumberValue('datasource_alias')) {
        Message.error('SQL公共变量必须选择逻辑数据源')
        modalDialogRef.value?.setConfirmLoading(false)
        return
      }
      if (Number(value.type) !== 1) {
        value.datasource_alias = null
      }
      if (data.isAdd) {
        value['status'] = 1
        postUiPublic(value)
          .then((res) => {
            modalDialogRef.value?.toggle()
            Message.success(res.msg)
            doRefresh()
          })
          .catch((error) => {
            console.log(error)
          })
          .finally(() => {
            modalDialogRef.value?.setConfirmLoading(false)
          })
      } else {
        value['id'] = data.updateId
        putUiPublic(value)
          .then((res) => {
            modalDialogRef.value?.toggle()
            Message.success(res.msg)
            doRefresh()
          })
          .catch((error) => {
            console.log(error)
          })
          .finally(() => {
            modalDialogRef.value?.setConfirmLoading(false)
          })
      }
    } else {
      modalDialogRef.value?.setConfirmLoading(false)
    }
  }

  onMounted(() => {
    nextTick(async () => {
      doRefresh()
    })
  })
</script>
