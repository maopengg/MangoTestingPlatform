<template>
  <TableBody ref="tableBody" plain class="mango-detail-workbench-page">
    <template #header>
      <TableHeader title="测试文件" />
    </template>
    <template #default>
      <ProjectProductNavigationWorkbench
        ref="navigationCreateRef"
        contained-body
        :model-value="projectProductCondition?.value"
        :reset-key="sidebarResetKey"
        @filter-change="onNavigationFilterChange"
        @search="doRefresh"
        @reset-search="onResetSearch"
      >
        <template #search>
          <a-form layout="inline" :model="{}" @keyup.enter="doRefresh">
            <a-form-item v-for="item of headerConditionItems" :key="item.key" :label="item.label">
              <template v-if="item.type === 'input'">
                <a-input
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  allow-clear
                  @blur="doRefresh"
                  @clear="doRefresh"
                />
              </template>
              <template v-else-if="item.type === 'cascader' && item.key === 'project_product'">
                <ProjectProductSelect
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  @change="doRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :placeholder="item.placeholder"
                  :options="item.key === 'update_user' ? item.optionItems : project.data"
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
        <template #toolbar>
          <a-space>
            <div>
              <a-button  size="small" type="primary" @click="onOpenUploadModal" data-testid="qa-views-config-test-files-button-上传">上传</a-button>
            </div>
          </a-space>
        </template>
        <a-table
          :scroll="{ x: tableScrollX, y: '100%' }"
          class="full-width mango-native-scroll-table"
          :bordered="false"
          :columns="visibleTableColumns"
          :data="table.dataList"
          :loading="table.tableLoading.value"
          :pagination="false"
          :rowKey="rowKey"
          @selection-change="onSelectionChange"
        >
          <template #columns>
            <a-table-column
              v-for="item of visibleTableColumns"
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
              <template v-else-if="item.key === 'file_size'" #cell="{ record }">
                {{ record.file_size_display || formatFileSize(record.file_size) }}
              </template>
              <template v-else-if="item.key === 'allow_download'" #cell="{ record }">
                <a-tag :color="isAllowDownload(record) ? 'green' : 'orange'" size="small">
                  {{ isAllowDownload(record) ? '允许下载' : '限制下载' }}
                </a-tag>
              </template>
              <template v-else-if="item.key === 'project_product'" #cell="{ record }">
                {{ formatProjectProductPath(record.project_product) }}
              </template>
              <template v-else-if="item.key === 'update_user'" #cell="{ record }">
                {{ record.update_user?.name || record.update_user?.username || '-' }}
              </template>
              <template v-else-if="item.key === 'actions'" #cell="{ record }">
                <MangoTableActions
                  :actions="[
    {
        label: '下载',
        disabled: isDownloadDisabled(record),
        onClick: () => onDownload(record), },
    { label: '编辑', onClick: () => onUpdate(record) },
    { label: '删除', danger: true, onClick: () => onDelete(record) },
]"
                />
              </template>
            </a-table-column>
          </template>
        </a-table>
        <template #footer>
          <TableFooter :pagination="pagination" />
        </template>
      </ProjectProductNavigationWorkbench>
    </template>
  </TableBody>
  <ModalDialog ref="modalDialogRef" title="编辑" @confirm="onDataForm">
    <template #content>
      <a-form :model="formModel">
        <a-form-item
          :class="[item.required ? 'mango-form-item__require' : 'mango-form-item__no_require']"
          :label="item.label"
          v-for="item of formItems"
          :key="item.key"
        >
          <template v-if="item.type === 'input'">
            <a-input :placeholder="item.placeholder" v-model="item.value" />
          </template>
          <template v-else-if="item.type === 'cascader'">
            <ProjectProductSelect
              v-model="item.value"
              :placeholder="item.placeholder"
            />
          </template>
        </a-form-item>
      </a-form>
    </template>
  </ModalDialog>
  <a-modal v-model:visible="uploadModalVisible" title="上传文件" @cancel="onCancelUpload">
    <a-form :model="uploadForm">
      <a-form-item label="文件" required>
        <a-upload
          v-model:file-list="uploadFileList"
          :auto-upload="false"
          :limit="1"
          @change="onUploadFileChange"
          @before-remove="onRemoveUploadFile"
        />
      </a-form-item>
      <a-form-item label="项目/产品" required>
        <ProjectProductSelect
          v-model="uploadForm.project_product"
          :placeholder="'请选择项目产品'"
        />
      </a-form-item>
      <a-form-item label="允许下载">
        <a-switch v-model="uploadForm.allow_download" />
      </a-form-item>
    </a-form>
    <template #footer>
      <a-button @click="onCloseUploadModal" data-testid="qa-views-config-test-files-button-取消">取消</a-button>
      <a-button  type="primary" :loading="uploadLoading" @click="onUploadFile" data-testid="qa-views-config-test-files-button-上传-2">上传</a-button>
    </template>
  </a-modal>
</template>

<script lang="ts" setup>
  import { usePagination, useRowKey, useRowSelection, useTable } from '@/hooks/table'
  import { Message, Modal } from '@arco-design/web-vue'
  import { computed, nextTick, onMounted, reactive, ref } from 'vue'
  import { tableColumns, conditionItems, formItems, tableScrollX } from './config'
  import {
    deleteUserFile,
    getUserFile,
    getUserFileDownloadUrl,
    postUserFile,
    putUserFile,
  } from '@/api/system/file_data'
  import { fieldNames } from '@/setting'
  import { getFormItems } from '@/utils/datacleaning'
  import { ModalDialogType } from '@/types/components'
  import { useProject } from '@/store/modules/get-project'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import { formatProjectProductPath, getOptionId } from '@/utils/business-format'
  import { getUserName } from '@/api/user/user'
  import { setUpdateUserOptions } from '@/utils/update-user'
  import { prefillNavigationModel, NavigationCreateSource } from '@/utils/navigation-create-defaults'

  const navigationCreateRef = ref<NavigationCreateSource | null>(null)

  const pagination = usePagination(doRefresh, () => table.tableLoading)
  const { onSelectionChange } = useRowSelection()
  const table = useTable()
  const project = useProject()
  const rowKey = useRowKey('id')
  const sidebarResetKey = ref(0)
  const projectProductCondition = computed(() =>
    conditionItems.find((item) => item.key === 'project_product')
  )
  const headerConditionItems = computed(() =>
    conditionItems.filter((item) => item.key !== 'project_product')
  )
  const visibleTableColumns = tableColumns
  const formModel = ref({})
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const uploadModalVisible = ref(false)
  const uploadLoading = ref(false)
  const uploadFile = ref<File | null>(null)
  const uploadFileList = ref<any[]>([])
  const uploadForm = reactive({
    project_product: '' as string | number,
    allow_download: true,
  })
  const data = reactive({
    updateId: 0,
  })
  function doRefresh() {
    let value = getFormItems(conditionItems)
    value['project_product'] = getOptionId(value['project_product'])
    if (value['project_product'] === null || value['project_product'] === '') {
      delete value['project_product']
    }
    if (value.update_user === null || value.update_user === '') {
      delete value.update_user
    }
    value['page'] = pagination.page
    value['pageSize'] = pagination.pageSize
    value['type'] = 0
    getUserFile(value)
      .then((res) => {
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
      })
      .catch(console.log)
  }
  function onNavigationFilterChange({ projectProduct }: { projectProduct: any }) {
    if (projectProductCondition.value) projectProductCondition.value.value = projectProduct ?? ''
    pagination.page = 1
    doRefresh()
  }
  function onResetSearch() {
    conditionItems.forEach((it) => {
      it.value = it.multiple ? [] : ''
    })
    sidebarResetKey.value += 1
    doRefresh()
  }

  function onUpdate(item: any) {
    data.updateId = item.id
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

  function onDelete(record: any) {
    Modal.confirm({
      title: '提示',
      content: '是否要删除此数据？',
      cancelText: '取消',
      okText: '删除',
      onBeforeOk: () => {
        return deleteUserFile(record.id)
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

  function onDataForm() {
    if (formItems.every((it) => (it.validator ? it.validator() : true))) {
      let value = getFormItems(formItems)
      value['id'] = data.updateId
      putUserFile(value)
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
  }

  function onOpenUploadModal() {
    uploadFile.value = null
    uploadFileList.value = []
    uploadForm.project_product = ''
    uploadForm.allow_download = true
    void prefillNavigationModel(navigationCreateRef.value, uploadForm)
    uploadModalVisible.value = true
  }

  function onUploadFileChange(fileList: any[], fileItem: any) {
    uploadFileList.value = fileList.slice(-1)
    uploadFile.value = fileItem?.file || uploadFileList.value[0]?.file || null
  }

  function onRemoveUploadFile() {
    uploadFile.value = null
    uploadFileList.value = []
    return true
  }

  async function onUploadFile() {
    if (!uploadFile.value) {
      Message.error('请选择上传文件')
      return
    }
    if (!uploadForm.project_product && uploadForm.project_product !== '0') {
      Message.error('请选择项目产品')
      return
    }

    uploadLoading.value = true
    const formData = new FormData()
    formData.append('test_file', uploadFile.value)
    formData.append('type', '0')
    formData.append('name', uploadFile.value.name)
    formData.append('project_product', String(uploadForm.project_product))
    formData.append('allow_download', String(uploadForm.allow_download))
    try {
      const res = await postUserFile(formData)
      Message.success(res.msg)
      uploadModalVisible.value = false
      uploadFile.value = null
      uploadFileList.value = []
      uploadForm.project_product = ''
      uploadForm.allow_download = true
      doRefresh()
    } catch (error) {
      console.log(error)
    } finally {
      uploadLoading.value = false
    }
  }

  function onCancelUpload() {
    uploadFile.value = null
    uploadFileList.value = []
    uploadForm.project_product = ''
    uploadForm.allow_download = true
  }

  function onCloseUploadModal() {
    uploadModalVisible.value = false
    onCancelUpload()
  }

  async function onDownload(record: any) {
    if (isDownloadDisabled(record)) {
      Message.warning('当前文件不允许下载')
      return
    }
    const file_name = record.name
    try {
      const res = await getUserFileDownloadUrl(record.id)
      const file_path = res.data
      if (file_name.includes('jpg') || file_name.includes('png')) {
        window.open(file_path, '_blank')
      } else {
        let aLink = document.createElement('a')
        aLink.href = file_path
        aLink.download = file_name
        Message.loading('文件下载中，请到下载中心查看~')
        document.body.appendChild(aLink)
        aLink.click()
        document.body.removeChild(aLink)
      }
    } catch (error) {
      console.log(error)
    }
  }

  function isDownloadDisabled(record: any) {
    return !isAllowDownload(record)
  }

  function isAllowDownload(record: any) {
    const value = record?.allow_download
    if (typeof value === 'boolean') return value
    if (typeof value === 'number') return value === 1
    if (typeof value === 'string') return ['true', '1', 'yes', 'on'].includes(value.toLowerCase())
    return false
  }

  function formatFileSize(size: number | string | null | undefined) {
    const value = Number(size || 0)
    if (!value) return '-'
    const units = ['B', 'KB', 'MB', 'GB', 'TB']
    let current = value
    for (const unit of units) {
      if (current < 1024 || unit === units[units.length - 1]) {
        return unit === 'B' ? `${Math.round(current)} ${unit}` : `${current.toFixed(1)} ${unit}`
      }
      current /= 1024
    }
    return '-'
  }

  onMounted(() => {
    nextTick(async () => {
      project.getProject()
      getUserName().then((res) => setUpdateUserOptions(conditionItems, res.data || []))
      doRefresh()
    })
  })
</script>
<style scoped>
  .full-width {
    width: 100%;
  }
</style>
