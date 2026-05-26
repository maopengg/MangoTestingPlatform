<template>
  <TableBody ref="tableBody">
    <template #header>
      <section class="mango-section-card pytest-bind-head">
        <div class="mango-section-title">
          <div>
            <h2>项目绑定</h2>
            <p>同步 Pytest 项目、初始化用例文件并提交代码变更</p>
          </div>
          <div class="mango-section-actions">
            <a-button size="small" type="primary" :loading="updateLoading" @click="clickUpdate"
              >更新项目</a-button
            >
            <a-button size="small" type="primary" :loading="pushLoading" @click="clickPush"
              >提交项目</a-button
            >
          </div>
        </div>
        <div class="mango-soft-panel pytest-bind-notes">
          <div>更新项目会执行 git pull 或 git clone。</div>
          <div>提交项目会执行 git push，冲突时默认接收远程最新内容。</div>
          <div>多人同时编辑同一文件时，以最后提交内容为准，建议各自维护自己的用例文件。</div>
        </div>
      </section>
    </template>

    <template #default>
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
              <span v-if="record?.project_product?.project && record?.project_product?.name">
                {{ record.project_product.project.name + '/' + record.project_product.name }}
              </span>
            </template>

            <template v-else-if="item.key === 'module'" #cell="{ record }">
              <span v-if="record?.module?.name">
                <span v-if="record.module.superior_module">
                  {{ record.module.superior_module + '/' }}
                </span>
                {{ record.module.name }}
              </span>
            </template>
            <template v-else-if="item.key === 'auto_type'" #cell="{ record }">
              <a-tag :color="enumStore.colors[record?.auto_type]" size="small"
                >{{ enumStore.test_case_type[record?.auto_type]?.title || '-' }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <MangoTableActions
                :actions="[
                  { label: '编辑', onClick: () => onUpdate(record) },
                  { label: '初始化文件', onClick: () => onEditFile(record) },
                  { label: '删除', danger: true, onClick: () => onDelete(record) },
                ]"
              />
            </template>
          </a-table-column>
        </template>
      </a-table>
      <BaseSidePanel
        :visible="data.drawerVisible"
        :title="'编辑代码'"
        :width="1000"
        @update:visible="
          (val) => {
            data.drawerVisible = val
          }
        "
        @cancel="
          () => {
            data.drawerVisible = false
          }
        "
      >
        <template #default>
          <div>
            <CodeEditor v-model="data.codeText" placeholder="输入python代码" />
          </div>
        </template>
        <template #extra-buttons>
          <a-button type="primary" :loading="drawerSaving" @click="drawerOk">保存</a-button>
        </template>
      </BaseSidePanel>
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
            <a-cascader
              v-model="item.value"
              :options="projectInfo.projectProduct"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
            />
          </template>

          <template v-else-if="item.type === 'select' && item.key === 'auto_type'">
            <a-select
              v-model="item.value"
              :field-names="fieldNames"
              :options="enumStore.test_case_type"
              :placeholder="item.placeholder"
              allow-clear
              allow-search
              value-key="key"
            />
          </template>
          <template v-else-if="item.type === 'input-tag'">
            <a-input-tag v-model="item.value" :placeholder="item.placeholder" allow-clear />
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
  import { nextTick, onMounted, reactive, ref } from 'vue'
  import { getFormItems } from '@/utils/datacleaning'
  import { fieldNames } from '@/setting'
  import { formItems, tableColumns } from './config'
  import { useProject } from '@/store/modules/get-project'
  import { useEnum } from '@/store/modules/get-enum'
  import {
    deletePytestProduct,
    getPytestProduct,
    getPytestProductRead,
    getPytestPush,
    getPytestUpdate,
    postPytestProduct,
    postPytestProductWrite,
    putPytestProduct,
  } from '@/api/pytest/product'
  import CodeEditor from '@/components/editors/CodeEditor.vue'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'

  const projectInfo = useProject()
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const pagination = usePagination(doRefresh)
  const { selectedRowKeys, onSelectionChange, showCheckedAll } = useRowSelection()
  const table = useTable()
  const rowKey = useRowKey('id')
  const formModel = ref({})
  const enumStore = useEnum()
  const updateLoading = ref(false)
  const pushLoading = ref(false)
  const drawerSaving = ref(false)

  const data: any = reactive({
    isAdd: false,
    updateId: 0,
    actionTitle: '新增',
    drawerVisible: false,
    codeText: '',
  })

  function onDelete(record: any) {
    Modal.confirm({
      title: '提示',
      content: '该删除只会删除数据库数据，不会影响git文件！是否要删除此数据？',
      cancelText: '取消',
      okText: '删除',
      onBeforeOk: () => {
        return deletePytestProduct(record.id)
          .then((res) => {
            Message.success(res.msg)
          })
          .catch(console.log)
          .finally(() => {
            doRefresh()
            projectInfo.projectPytestName()
          })
      },
    })
  }

  function clickUpdate() {
    if (updateLoading.value) return
    updateLoading.value = true
    Message.loading('项目更新中...')

    getPytestUpdate()
      .then((res) => {
        Message.success(res.msg)
        doRefresh()
      })
      .catch(console.log)
      .finally(() => {
        updateLoading.value = false
      })
  }

  function clickPush() {
    if (pushLoading.value) return
    pushLoading.value = true
    Message.loading('项目提交中...')
    getPytestPush()
      .then((res) => {
        Message.success(res.msg)
      })
      .catch(console.log)
      .finally(() => {
        pushLoading.value = false
      })
  }

  function onDataForm() {
    if (formItems.every((it) => (it.validator ? it.validator() : true))) {
      let value = getFormItems(formItems)
      if (data.isAdd) {
        postPytestProduct(value)
          .then((res) => {
            modalDialogRef.value?.toggle()
            Message.success(res.msg)
            doRefresh()
            projectInfo.projectPytestName()
          })
          .catch((error) => {
            console.log(error)
          })
          .finally(() => {
            modalDialogRef.value?.setConfirmLoading(false)
          })
      } else {
        value['id'] = data.updateId
        putPytestProduct(value)
          .then((res) => {
            modalDialogRef.value?.toggle()
            Message.success(res.msg)
            doRefresh()
            projectInfo.projectPytestName()
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

  function onUpdate(item: any) {
    data.actionTitle = '编辑'
    data.isAdd = false
    data.updateId = item.id
    modalDialogRef.value?.toggle()
    nextTick(() => {
      formItems.forEach((it) => {
        const propName = item[it.key]
        if (Array.isArray(propName)) {
          it.value = propName
        } else if (typeof propName === 'object' && propName !== null) {
          it.value = propName.id
        } else {
          it.value = propName
        }
      })
    })
  }

  function doRefresh() {
    const value = {}
    value['page'] = pagination.page
    value['pageSize'] = pagination.pageSize
    getPytestProduct(value)
      .then((res) => {
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
      })
      .catch(console.log)
  }

  function drawerOk() {
    if (drawerSaving.value) return
    drawerSaving.value = true
    postPytestProductWrite(data.updateId, data.codeText)
      .then((res) => {
        data.codeText = res.data
        Message.success(res.msg)
        data.drawerVisible = false
      })
      .catch(console.log)
      .finally(() => {
        drawerSaving.value = false
      })
  }

  function onEditFile(record: any) {
    data.drawerVisible = true
    data.updateId = record.id
    getPytestProductRead(record.id)
      .then((res) => {
        data.codeText = res.data
      })
      .catch(console.log)
  }

  onMounted(() => {
    nextTick(async () => {
      doRefresh()
    })
  })
</script>
<style lang="less" scoped>
  .pytest-bind-head {
    margin-bottom: 4px;
  }

  .pytest-bind-notes {
    display: grid;
    gap: 6px;
    color: var(--m-text-2);
    font-size: 13px;
    line-height: 20px;
  }
</style>
