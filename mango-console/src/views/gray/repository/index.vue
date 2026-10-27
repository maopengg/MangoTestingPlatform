<template>
  <TableBody content-flush>
    <template #header>
      <TableHeader title="灰度仓库" :show-filter="true" @search="onSearchRefresh" @reset-search="onReset">
        <template #search-content>
          <a-form layout="inline" :model="query" @keyup.enter="onSearchRefresh">
            <a-form-item label="仓库名称">
              <a-input v-model="query.name" allow-clear placeholder="请输入仓库名称" @blur="onSearchRefresh" @clear="onSearchRefresh" data-testid="qa-views-gray-repository-input-请输入仓库名称" />
            </a-form-item>
            <a-form-item label="仓库地址">
              <a-input v-model="query.repo_url" allow-clear placeholder="请输入仓库地址" @blur="onSearchRefresh" @clear="onSearchRefresh" data-testid="qa-views-gray-repository-input-请输入仓库地址" />
            </a-form-item>
            <a-form-item label="平台">
              <a-select v-model="query.provider" multiple :max-tag-count="1" :options="providerOptions" allow-clear allow-search placeholder="请选择平台" @change="onSearchRefresh" data-testid="qa-views-gray-repository-select-请选择平台" />
            </a-form-item>
            <a-form-item label="测试环境">
              <a-select
                v-model="query.test_env"
                :field-names="{ value: 'key', label: 'title' }"
                :options="environmentOptions"
                allow-clear
                allow-search
                placeholder="请选择被测环境"
                @change="onSearchRefresh" data-testid="qa-views-gray-repository-select-请选择环境"
              />
            </a-form-item>
            <a-form-item label="分支">
              <a-input v-model="query.branch" allow-clear placeholder="请输入分支" @blur="onSearchRefresh" @clear="onSearchRefresh" data-testid="qa-views-gray-repository-input-请输入分支" />
            </a-form-item>
            <a-form-item label="状态">
              <a-select v-model="query.status" multiple :max-tag-count="1" :options="enableStatusOptions" allow-clear placeholder="请选择状态" @change="onSearchRefresh" data-testid="qa-views-gray-repository-select-请选择状态" />
            </a-form-item>
          </a-form>
        </template>
      </TableHeader>
    </template>

    <template #default>
      <TableTabs>
        <template #extra>
          <a-button v-permission="'gray.repository:create'"
            size="small"
            type="primary"
            @click="onAdd"
            data-testid="qa-views-gray-repository-button-新增仓库"
          >
            新增仓库
          </a-button>
        </template>
      </TableTabs>
      <a-table
        :bordered="false"
        :columns="repositoryColumns"
        :data="table.dataList"
        :loading="table.tableLoading.value"
        :pagination="false"
        :scroll="{ x: grayPageConfig.scrollX }"
        row-key="id"
      >
        <template #columns>
          <a-table-column v-for="item in repositoryColumns" :key="item.key" v-bind="item">
            <template v-if="item.key === 'index'" #cell="{ record }">{{ record.id }}</template>
            <template v-else-if="item.key === 'provider'" #cell="{ record }">
              <a-tag :color="providerColor(record.provider)" size="small">{{ providerText(record.provider) }}</a-tag>
            </template>
            <template v-else-if="item.key === 'config_dirs'" #cell="{ record }">
              <a-popover v-if="normalizeDirs(record.config_dirs).length" position="left" trigger="hover">
                <a-tag size="small">已配置 {{ normalizeDirs(record.config_dirs).length }} 个</a-tag>
                <template #content>
                  <div class="mango-gray-config-dir-popover">
                    <div v-for="dir of normalizeDirs(record.config_dirs)" :key="dir" class="mango-gray-config-dir-popover__item">
                      {{ dir }}
                    </div>
                  </div>
                </template>
              </a-popover>
              <span v-else>-</span>
            </template>
            <template v-else-if="item.key === 'test_env'" #cell="{ record }">
              <a-tag :color="environmentColor(record.test_env)" size="small">{{ formatEnvironmentText(record.test_env) }}</a-tag>
            </template>
            <template v-else-if="item.key === 'status'" #cell="{ record }">
              <a-switch v-permission="'gray.repository:status'"
                :beforeChange="(newValue) => onModifyStatus(newValue, record.id)"
                :default-checked="record.status === 1"
              />
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <MangoTableActions
                :actions="[
                  { permission: 'gray.repository:debug', label: '测试', loading: actionLoading === `test-${record.id}`, onClick: () => onTest(record) },
                  { permission: 'gray.repository:edit', label: '同步', loading: actionLoading === `sync-${record.id}`, onClick: () => onSync(record) },
                  { permission: 'gray.repository:edit', label: '编辑', onClick: () => onEdit(record) },
                  { permission: 'gray.repository:delete', label: '删除', danger: true, loading: actionLoading === `delete-${record.id}`, onClick: () => onDelete(record) },
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

  <ModalDialog ref="dialogRef" :title="form.id ? '编辑灰度仓库' : '新增灰度仓库'" width="560px" @confirm="onSubmit">
    <template #content>
      <a-form class="mango-gray-form" :model="form" layout="horizontal" :label-col-props="{ span: 4 }" :wrapper-col-props="{ span: 20 }">
        <a-form-item label="仓库名称" class="mango-form-item__require"><a-input v-model="form.name" placeholder="请输入仓库名称" data-testid="qa-views-gray-repository-input-请输入仓库名称-2" /></a-form-item>
        <a-form-item label="仓库地址" class="mango-form-item__require"><a-input v-model="form.repo_url" placeholder="请输入仓库地址" data-testid="qa-views-gray-repository-input-请输入仓库地址-2" /></a-form-item>
        <a-form-item label="平台类型" class="mango-form-item__require"><a-select v-model="form.provider" :options="providerOptions" placeholder="请选择平台类型" data-testid="qa-views-gray-repository-select-请选择平台类型" /></a-form-item>
        <a-form-item label="平台域名" class="mango-form-item__require"><a-input v-model="form.api_base_url" placeholder="请输入平台域名" data-testid="qa-views-gray-repository-input-请输入平台域名" /></a-form-item>
        <a-form-item label="访问令牌"><a-input-password v-model="form.access_token" placeholder="请输入访问令牌" data-testid="qa-views-gray-repository-input-password-请输入访问令牌" /></a-form-item>
        <a-form-item label="测试环境" class="mango-form-item__require">
          <a-select
            v-model="form.test_env"
            :field-names="{ value: 'key', label: 'title' }"
            :options="environmentOptions"
            allow-search
            placeholder="请选择测试环境" data-testid="qa-views-gray-repository-select-请选择测试环境"
          />
        </a-form-item>
        <a-form-item label="分支" class="mango-form-item__require"><a-input v-model="form.branch" placeholder="请输入分支" data-testid="qa-views-gray-repository-input-请输入分支-2" /></a-form-item>
        <a-form-item label="配置目录" class="mango-form-item__require">
          <a-input-tag v-model="form.config_dirs" allow-clear placeholder="输入仓库内相对目录后回车，例如 clm-api/nacos" data-testid="qa-views-gray-repository-input-tag-输入仓库内相对目录后回车-例如-clm-api-nacos" />
        </a-form-item>
        <a-form-item label="启用状态"><a-switch v-model="form.status" :checked-value="1" :unchecked-value="0" /></a-form-item>
      </a-form>
    </template>
  </ModalDialog>
</template>

<script setup lang="ts">
  import { computed, onMounted, reactive, ref } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import TableBody from '@/components/table/TableBody.vue'
  import TableHeader from '@/components/table/TableHeader.vue'
  import TableFooter from '@/components/table/TableFooter.vue'
  import TableTabs from '@/components/table/TableTabs.vue'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import ModalDialog from '@/components/overlays/ModalDialog.vue'
  import { useEnum } from '@/store/modules/get-enum'
  import { usePagination, useTable } from '@/hooks/table'
  import type { ModalDialogType } from '@/types/components'
  import {
    deleteGrayRepository,
    getGrayRepository,
    postGrayRepository,
    postGrayRepositorySync,
    postGrayRepositoryTest,
    putGrayRepository,
  } from '@/api/gray'
  import { enableStatusOptions, grayPageConfig, providerOptions } from './config'
  import { normalizeMultiSelectSearchParams } from '@/utils/search-condition'

  const COMMON_ENV_VALUE = '__common__'
  const table = useTable()
  const enumStore = useEnum()
  const pagination = usePagination(onSearch, () => table.tableLoading)
  const dialogRef = ref<ModalDialogType | null>(null)
  const query = reactive<any>({ provider: [], status: [] })
  const form = reactive<any>({})
  const actionLoading = ref('')
  const repositoryColumns = computed(() => grayPageConfig.columns)
  const environmentOptions = computed(() => [
    { key: COMMON_ENV_VALUE, title: '环境通用' },
    ...(Array.isArray(enumStore.environment_type) ? enumStore.environment_type : []),
  ])

  function cleanParams(params: Record<string, any>) {
    const result: Record<string, any> = {}
    Object.entries(params).forEach(([key, value]) => {
      if (value !== '' && value !== null && value !== undefined) {
        result[key] = value
      }
    })
    return result
  }

  function isCommonEnvironment(value: any) {
    return value === null || value === undefined || value === ''
  }

  function formatEnvironmentText(value: any) {
    if (isCommonEnvironment(value) || value === COMMON_ENV_VALUE) {
      return '环境通用'
    }
    return findEnvironmentOption(value)?.title || String(value)
  }

  function environmentColor(value: any) {
    if (isCommonEnvironment(value) || value === COMMON_ENV_VALUE) {
      return 'gray'
    }
    const optionIndex = findEnvironmentOptionIndex(value)
    if (optionIndex >= 0) {
      return enumStore.colors?.[optionIndex + 1] || enumStore.colors?.[optionIndex] || 'gray'
    }
    const numericValue = Number(value)
    if (Number.isFinite(numericValue)) {
      return enumStore.colors?.[numericValue] || 'gray'
    }
    return 'gray'
  }

  function findEnvironmentOption(value: any) {
    const index = findEnvironmentOptionIndex(value)
    return index >= 0 ? enumStore.environment_type?.[index] : undefined
  }

  function findEnvironmentOptionIndex(value: any) {
    const text = String(value)
    return (enumStore.environment_type || []).findIndex((item: any) => {
      return [item.key, item.value, item.title].some((itemValue) => String(itemValue) === text)
    })
  }

  function providerText(value: any) {
    return providerOptions.find((item) => item.value === value)?.label || value || '-'
  }

  function providerColor(value: any) {
    const index = providerOptions.findIndex((item) => item.value === value)
    return enumStore.colors?.[index + 1] || enumStore.colors?.[index] || 'gray'
  }

  function toEnvironmentSelectValue(value: any) {
    return isCommonEnvironment(value) ? COMMON_ENV_VALUE : Number(value)
  }

  function normalizeEnvironmentValue(value: any) {
    if (value === COMMON_ENV_VALUE || isCommonEnvironment(value)) {
      return null
    }
    return Number(value)
  }

  function normalizeDirs(value: any) {
    if (!Array.isArray(value)) {
      return []
    }
    const result: string[] = []
    value.forEach((item) => {
      const normalized = String(item || '').trim().replace(/\\/g, '/').replace(/^\/+|\/+$/g, '')
      if (normalized && !result.includes(normalized)) {
        result.push(normalized)
      }
    })
    return result
  }

  function requestParams() {
    return cleanParams(normalizeMultiSelectSearchParams({
      page: pagination.page,
      pageSize: pagination.pageSize,
      name: query.name,
      repo_url: query.repo_url,
      provider: query.provider,
      ...(query.test_env === COMMON_ENV_VALUE ? { test_env__isnull: true } : { test_env: normalizeEnvironmentValue(query.test_env) }),
      branch: query.branch,
      status: query.status,
    }, ['provider', 'status']))
  }

  async function onSearch() {
    table.tableLoading.value = true
    try {
      const res = await getGrayRepository(requestParams())
      table.handleSuccess(res)
      pagination.setTotalSize(res.totalSize || 0)
    } finally {
      table.tableLoading.value = false
    }
  }

  function onSearchRefresh() {
    pagination.page = 1
    onSearch()
  }

  function onReset() {
    Object.keys(query).forEach((key) => {
      query[key] = ['provider', 'status'].includes(key) ? [] : undefined
    })
    onSearchRefresh()
  }

  function openDialog(data: any) {
    Object.keys(form).forEach((key) => delete form[key])
    Object.assign(form, data)
    dialogRef.value?.show()
  }

  function onAdd() {
    openDialog({ provider: 'gitlab', test_env: COMMON_ENV_VALUE, config_dirs: [], status: 1 })
  }

  function onEdit(record: any) {
    openDialog({
      ...record,
      test_env: toEnvironmentSelectValue(record.test_env),
      config_dirs: normalizeDirs(record.config_dirs),
      access_token: '',
    })
  }

  async function onSubmit() {
    try {
      if (!validateRepositoryForm()) {
        return
      }
      const payload = {
        ...form,
        test_env: normalizeEnvironmentValue(form.test_env),
        config_dirs: normalizeDirs(form.config_dirs),
      }
      if (form.id && !payload.access_token) {
        delete payload.access_token
      }
      form.id ? await putGrayRepository(payload) : await postGrayRepository(payload)
      Message.success('保存成功')
      dialogRef.value?.close()
      await onSearch()
    } finally {
      dialogRef.value?.setConfirmLoading(false)
    }
  }

  function validateRepositoryForm() {
    const rules = [
      { value: form.name, message: '请输入仓库名称' },
      { value: form.repo_url, message: '请输入仓库地址' },
      { value: form.provider, message: '请选择平台类型' },
      { value: form.api_base_url, message: '请输入平台域名' },
      { value: form.test_env, message: '请选择测试环境' },
      { value: form.branch, message: '请输入分支' },
    ]
    const invalidRule = rules.find((rule) => isEmptyFormValue(rule.value))
    if (invalidRule) {
      Message.warning(invalidRule.message)
      return false
    }
    if (!normalizeDirs(form.config_dirs).length) {
      Message.warning('请输入配置目录，例如 clm-api/nacos')
      return false
    }
    return true
  }

  function isEmptyFormValue(value: any) {
    return value === undefined || value === null || (typeof value === 'string' && !value.trim())
  }

  async function onModifyStatus(newValue: boolean, id: number) {
    try {
      const res = await putGrayRepository({ id, status: newValue ? 1 : 0 })
      const success = res.code === 200
      if (success) {
        Message.success(res.msg || '状态更新成功')
        await onSearch()
      }
      return success
    } catch (error) {
      return false
    }
  }

  async function onTest(record: any) {
    actionLoading.value = `test-${record.id}`
    try {
      await postGrayRepositoryTest({ repository_id: record.id })
      Message.success('连接测试成功')
    } finally {
      actionLoading.value = ''
    }
  }

  async function onSync(record: any) {
    actionLoading.value = `sync-${record.id}`
    try {
      await postGrayRepositorySync({ repository_id: record.id })
      Message.success('同步成功')
      await onSearch()
    } finally {
      actionLoading.value = ''
    }
  }

  function onDelete(record: any) {
    Modal.confirm({
      title: '删除灰度仓库',
      content: `确认删除 ${record.name}？`,
      onOk: async () => {
        actionLoading.value = `delete-${record.id}`
        try {
          await deleteGrayRepository(record.id)
          await onSearch()
        } finally {
          actionLoading.value = ''
        }
      },
    })
  }

  onMounted(onSearch)
</script>

<style scoped lang="less">
  .mango-gray-form {
    :deep(.arco-form-item) {
      margin-bottom: 12px;
    }
  }

  .mango-gray-config-dir-popover {
    display: flex;
    flex-direction: column;
    gap: 6px;
    max-width: 360px;
  }

  .mango-gray-config-dir-popover__item {
    color: var(--m-text-2);
    font-size: 12px;
    line-height: 18px;
    word-break: break-all;
  }
</style>
