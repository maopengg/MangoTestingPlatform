<template>
  <TableBody ref="tableBody">
    <template #header>
      <TableHeader
        :show-filter="true"
        title="配置测试对象"
        @search="doRefresh"
        @reset-search="onResetSearch"
      >
        <template #search-content>
          <a-form layout="inline" :model="{}" @keyup.enter="doRefresh">
            <a-form-item v-for="item of conditionItems" :key="item.key" :label="item.label">
              <template v-if="item.type === 'input'">
                <a-input v-model="item.value" :placeholder="item.placeholder" @blur="doRefresh" />
              </template>
              <template v-else-if="item.type === 'select'">
                <a-select
                  style="width: 150px"
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  :options="project.data"
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
      </TableHeader>
    </template>
    <template #default>
      <a-tabs>
        <template #extra>
          <a-space>
            <div>
              <a-upload
                :before-upload="beforeUpload"
                :show-file-list="false"
                @before-upload="beforeUpload"
              />
            </div>
          </a-space>
        </template>
        <a-table
          style="width: 100%"
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
              <template v-else-if="item.key === 'project_product'" #cell="{ record }">
                {{
                  (record?.project_product?.project?.name || '无') +
                  '/' +
                  (record?.project_product?.name || '无')
                }}
              </template>
              <template v-else-if="item.key === 'actions'" #cell="{ record }">
                <a-button
                  size="mini"
                  type="text"
                  class="custom-mini-btn"
                  @click="onDownload(record)"
                  >下载
                </a-button>
                <a-button type="text" size="mini" class="custom-mini-btn" @click="onUpdate(record)"
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
              </template>
            </a-table-column>
          </template>
        </a-table>
      </a-tabs>
    </template>
    <template #footer>
      <TableFooter :pagination="pagination" />
    </template>
  </TableBody>
  <ModalDialog ref="modalDialogRef" title="编辑" @confirm="onDataForm">
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
          <template v-else-if="item.type === 'cascader'">
            <a-cascader
              v-model="item.value"
              :placeholder="item.placeholder"
              :options="projectInfo.projectProduct"
              allow-search
              allow-clear
            />
          </template>
        </a-form-item>
      </a-form>
    </template>
  </ModalDialog>
</template>

<script lang="ts" setup>
  import { usePagination, useRowKey, useRowSelection, useTable } from '@/hooks/table'
  import { Message, Modal } from '@arco-design/web-vue'
  import { nextTick, onMounted, reactive, ref } from 'vue'
  import { tableColumns, conditionItems, formItems } from './config'
  import { deleteUserFile, getUserFile, postUserFile, putUserFile } from '@/api/system/file_data'
  import { minioURL } from '@/api/axios.config'
  import { fieldNames } from '@/setting'
  import { getFormItems } from '@/utils/datacleaning'
  import { ModalDialogType } from '@/types/components'
  import { useProject } from '@/store/modules/get-project'

  const pagination = usePagination(doRefresh)
  const { onSelectionChange } = useRowSelection()
  const table = useTable()
  const projectInfo = useProject()
  const rowKey = useRowKey('id')
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const data = reactive({
    updateId: 0,
  })
  function doRefresh() {
    let value = getFormItems(conditionItems)
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
  function onResetSearch() {
    conditionItems.forEach((it) => {
      it.value = ''
    })
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
      onOk: () => {
        deleteUserFile(record.id)
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

  const beforeUpload = (file: any) => {
    return new Promise((resolve, reject) => {
      Modal.confirm({
        title: '上传文件',
        content: `确认上传：${file.name}`,
        onOk: () => {
          const formData = new FormData()
          formData.append('test_file', file)
          formData.append('type', '0')
          formData.append('name', file.name)
          postUserFile(formData)
            .then((res) => {
              Message.success(res.msg)
              doRefresh()
              // resolve(true)
            })
            .catch(console.log)
        },
        onCancel: () => reject('cancel'),
      })
    })
  }

  function onDownload(record: any) {
    let file_path = record.test_file

    if (file_path.startsWith('http://') || file_path.startsWith('https://')) {
      try {
        const urlObj = new URL(file_path)
        file_path = urlObj.pathname
      } catch (e) {
        console.error('URL解析失败:', e)
        Message.error('文件路径格式错误')
        return
      }
    } else if (!file_path.startsWith('/')) {
      file_path = '/' + file_path
    }
    file_path = minioURL + file_path
    const file_name = record.name
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
  }

  onMounted(() => {
    nextTick(async () => {
      doRefresh()
    })
  })
</script>
<style></style>
