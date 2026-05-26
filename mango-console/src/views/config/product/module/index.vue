<template>
  <TableBody ref="tableBody" class="mango-detail-workbench-page">
    <template #header>
      <div class="mango-detail-toolbar">
        <div class="mango-detail-heading">
          <div class="mango-detail-title">{{ productModuleDetailTitle }}</div>
          <div class="mango-detail-subtitle">维护当前产品下的模块结构和模块名称</div>
        </div>
        <a-space class="mango-detail-actions" wrap>
          <a-button size="small" type="primary" @click="doAppend">增加</a-button>
          <a-button size="small" @click="doResetSearch">返回</a-button>
        </a-space>
      </div>
    </template>
    <template #default>
      <a-table
        :scroll="{ x: 1100 }"
        :bordered="false"
        :columns="columns"
        :data="data.data"
        :loading="tableLoading"
        :pagination="false"
      >
        <template #columns>
          <a-table-column
            v-for="item of columns"
            :key="item.key"
            :align="item.align"
            :data-index="item.dataIndex"
            :fixed="item.fixed"
            :title="item.title"
            :width="item.width"
          >
            <template v-if="item.dataIndex === 'actions'" #cell="{ record }">
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
        </a-form-item>
      </a-form>
    </template>
  </ModalDialog>
</template>
<script lang="ts" setup>
  import { computed, nextTick, onMounted, reactive, ref } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import { ModalDialogType } from '@/types/components'
  import { useRoute } from 'vue-router'
  import { getFormItems } from '@/utils/datacleaning'
  import { columns, formItems } from './config'
  import {
    deleteUserModule,
    getUserModule,
    postUserModule,
    putUserModule,
  } from '@/api/system/module'
  import { useProject } from '@/store/modules/get-project'
  const projectInfo = useProject()
  const route = useRoute()
  const productModuleDetailTitle = computed(() => {
    const id = route.query.id || '-'
    const name = route.query.name || '-'
    return `产品模块配置 / ${id} / ${name}`
  })
  const formModel = ref({})
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const tableLoading = ref(false)
  const data = reactive({
    isAdd: false,
    updateId: 0,
    actionTitle: '新增',
    data: [],
    caseList: [],
  })

  function doAppend() {
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
  }

  function onDelete(record: any) {
    Modal.confirm({
      title: '提示',
      content: '是否要删除此模块？',
      cancelText: '取消',
      okText: '删除',
      onBeforeOk: () => {
        return deleteUserModule(record.id)
          .then((res) => {
            Message.success(res.msg)
            doRefresh()
          })
          .catch(console.log)
      },
    })
  }

  function onUpdate(record: any) {
    data.actionTitle = '编辑'
    data.isAdd = false
    data.updateId = record.id
    modalDialogRef.value?.toggle()
    nextTick(() => {
      formItems.forEach((it) => {
        const propName = record[it.key]
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
      value['project_product'] = route.query.id
      if (data.isAdd) {
        postUserModule(value)
          .then((res) => {
            modalDialogRef.value?.toggle()
            Message.success(res.msg)
            projectInfo.projectPytestName()
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
        putUserModule(value)
          .then((res) => {
            modalDialogRef.value?.toggle()
            Message.success(res.msg)
            projectInfo.projectPytestName()
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

  function doResetSearch() {
    window.history.back()
  }

  function doRefresh() {
    tableLoading.value = true
    getUserModule({
      project_product: route.query.id,
    })
      .then((res) => {
        data.data = res.data
      })
      .catch(console.log)
      .finally(() => {
        tableLoading.value = false
      })
  }

  onMounted(() => {
    nextTick(async () => {
      doRefresh()
    })
  })
</script>
<style scoped>
  @media (max-width: 1px) {
  }
</style>
