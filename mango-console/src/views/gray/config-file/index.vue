<template>
  <TableBody plain class="mango-detail-workbench-page">
    <template #header>
      <TableHeader title="配置文件" />
    </template>
    <template #default>
      <ProjectProductNavigationWorkbench
        ref="navigationCreateRef"
        contained-body
        :model-value="query.project_product"
        :reset-key="sidebarResetKey"
        @filter-change="onSidebarFilterChange"
        @search="onSearchRefresh"
        @reset-search="onReset"
      >
        <template #search>
          <a-form layout="inline" :model="query" @keyup.enter="onSearchRefresh">
            <a-form-item label="配置名称">
              <a-input
                v-model="query.name"
                allow-clear
                placeholder="请输入配置名称"
                @blur="onSearchRefresh"
                @clear="onSearchRefresh"
                data-testid="qa-views-gray-config-file-input-请输入配置名称"
              />
            </a-form-item>
            <a-form-item label="状态">
              <a-select
                v-model="query.status"
                multiple
                :max-tag-count="1"
                :options="enableStatusOptions"
                allow-clear
                placeholder="请选择状态"
                @change="onSearchRefresh"
                data-testid="qa-views-gray-config-file-select-请选择状态"
              />
            </a-form-item>
          </a-form>
        </template>
        <template #toolbar>
          <div class="mango-gray-toolbar">
            <a-button v-if="enumError" size="small" :loading="enumLoading" @click="loadEnums"
              >重试环境选项</a-button
            >
            <a-spin v-else-if="enumLoading" :loading="enumLoading" />
            <a-button
              size="small"
              type="primary"
              :disabled="actionBlocked() || bindingDrawer.visible"
              @click="onAdd"
              data-testid="qa-views-gray-config-file-button-新增配置文件"
              >新增配置文件</a-button
            >
          </div>
        </template>
        <a-table
          class="mango-native-scroll-table"
          :bordered="false"
          :columns="yamlColumns"
          :data="rows"
          :loading="listLoading"
          :pagination="false"
          :scroll="{ x: grayPageConfig.scrollX, y: '100%' }"
          row-key="id"
        >
          <template #columns>
            <a-table-column v-for="item in yamlColumns" :key="item.key" v-bind="item">
              <template v-if="item.key === 'index'" #cell="{ record }">{{ record.id }}</template>
              <template v-else-if="item.key === 'bindings'" #cell="{ record }">
                <a-space v-if="visibleBindings(record.bindings).length" size="mini" wrap>
                  <a-tag
                    v-for="binding of visibleBindings(record.bindings)"
                    :key="binding.id"
                    :color="environmentColor(binding?.repository?.test_env)"
                    size="small"
                  >
                    {{ bindingLabel(binding) }}
                  </a-tag>
                  <a-tag v-if="hiddenBindings(record.bindings).length" color="gray" size="small"
                    >+{{ hiddenBindings(record.bindings).length }}</a-tag
                  >
                </a-space>
                <span v-else>-</span>
              </template>
              <template v-else-if="item.key === 'status'" #cell="{ record }">
                <a-switch
                  :beforeChange="(newValue) => onModifyYamlStatus(newValue, record.id)"
                  :model-value="record.status === 1"
                  :loading="rowLoading('yaml', 'status', record.id)"
                  :disabled="actionBlocked()"
                />
              </template>
              <template v-else-if="item.key === 'project_product'" #cell="{ record }">
                {{ formatProjectProductPath(record.project_product) }}
              </template>
              <template v-else-if="item.key === 'actions'" #cell="{ record }">
                <MangoTableActions
                  :actions="[
                    { label: '绑定/查看', onClick: () => onBindingManage(record) },
                    { label: '编辑', onClick: () => onEdit(record) },
                    {
                      label: '删除',
                      danger: true,
                      loading: rowLoading('yaml', 'delete', record.id),
                      onClick: () => onDelete(record),
                    },
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

  <YamlFileEditor
    ref="yamlEditorRef"
    :context-key="editorScopeKey"
    :blocked="writeBusy || bindingSaving || bindingEditorVisible"
    @busy="yamlSaving = $event"
    @visible="yamlEditorVisible = $event"
    @saved="onYamlSaved"
  />
  <YamlBindingEditor
    ref="bindingEditorRef"
    :context-key="editorScopeKey"
    :blocked="writeBusy || yamlSaving || yamlEditorVisible"
    @busy="bindingSaving = $event"
    @visible="bindingEditorVisible = $event"
    @saved="onBindingSaved"
  />

  <YamlContentDrawer ref="contentDrawerRef" :context-key="contentScopeKey" />

  <a-drawer
    class="mango-gray-binding-panel"
    :visible="bindingDrawer.visible"
    :title="bindingDrawer.title"
    :width="900"
    :on-before-cancel="canCloseBindings"
    @update:visible="bindings.onVisibleChange"
  >
    <template #default>
      <div class="mango-gray-binding-drawer">
        <div class="mango-gray-toolbar">
          <a-button
            size="small"
            type="primary"
            :disabled="actionBlocked()"
            @click="onBindingAdd"
            data-testid="qa-views-gray-config-file-button-新增仓库绑定"
            >新增仓库绑定</a-button
          >
        </div>
        <a-table
          class="mango-native-scroll-table"
          :bordered="false"
          :columns="bindingColumns"
          :data="bindingDrawer.dataList"
          :loading="bindingDrawer.loading"
          :pagination="false"
          :scroll="{ x: grayPageConfig.bindingScrollX, y: '100%' }"
          row-key="id"
        >
          <template #columns>
            <a-table-column v-for="item in bindingColumns" :key="item.key" v-bind="item">
              <template v-if="item.key === 'index'" #cell="{ record }">{{ record.id }}</template>
              <template v-else-if="item.key === 'test_env'" #cell="{ record }">
                <a-tag :color="environmentColor(record.repository?.test_env)" size="small">{{
                  formatEnvironmentText(record.repository?.test_env)
                }}</a-tag>
              </template>
              <template v-else-if="item.key === 'repository'" #cell="{ record }">
                {{ record.repository ? repositoryLabel(record.repository) : '-' }}
              </template>
              <template v-else-if="item.key === 'status'" #cell="{ record }">
                <a-switch
                  :beforeChange="(newValue) => onModifyBindingStatus(newValue, record.id)"
                  :model-value="record.status === 1"
                  :loading="rowLoading('binding', 'status', record.id)"
                  :disabled="actionBlocked()"
                />
              </template>
              <template v-else-if="item.key === 'actions'" #cell="{ record }">
                <MangoTableActions
                  :actions="[
                    {
                      label: '查看',
                      onClick: () => onBindingContent(record),
                    },
                    { label: '编辑', onClick: () => onBindingEdit(record) },
                    {
                      label: '删除',
                      danger: true,
                      loading: rowLoading('binding', 'delete', record.id),
                      onClick: () => onDeleteBinding(record),
                    },
                  ]"
                />
              </template>
            </a-table-column>
          </template>
        </a-table>
      </div>
    </template>
    <template #footer>
      <a-button :disabled="!canCloseBindings()" @click="bindings.onVisibleChange(false)"
        >关闭</a-button
      >
    </template>
  </a-drawer>
</template>

<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import {
    computed,
    onActivated,
    onBeforeUnmount,
    onDeactivated,
    onMounted,
    reactive,
    ref,
    watch,
  } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import TableBody from '@/components/table/TableBody.vue'
  import TableHeader from '@/components/table/TableHeader.vue'
  import TableFooter from '@/components/table/TableFooter.vue'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import { useEnum } from '@/store/modules/get-enum'
  import { useRoute } from 'vue-router'
  import useUserStore from '@/store/modules/user'
  import { usePagination } from '@/hooks/table'
  import { formatProjectProductPath } from '@/utils/business-format'
  import type { NavigationCreateSource } from '@/utils/navigation-create-defaults'
  import { getGrayYamlFile } from '@/api/gray'
  import YamlFileEditor from './components/YamlFileEditor.vue'
  import YamlBindingEditor from './components/YamlBindingEditor.vue'
  import YamlContentDrawer from './components/YamlContentDrawer.vue'
  import { useYamlBindings } from './composables/useYamlBindings'
  import { useYamlMutations } from './composables/useYamlMutations'
  import type { MutationTarget } from './composables/useYamlMutations'
  import type { ContentDrawerHandle } from './content'
  import type {
    YamlEditorHandle,
    BindingEditorHandle,
    YamlRecord,
    BindingRecord,
    Repository,
    Selection,
  } from './forms'
  import { selectionId } from './forms'
  import { createQuery, queryParams, yamlPage } from './yaml-rows'
  import type { YamlRow } from './yaml-rows'
  import { enableStatusOptions, grayPageConfig } from './config'

  const user = useUserStore(),
    route = useRoute(),
    enumStore = useEnum()
  const navigationCreateRef = ref<NavigationCreateSource | null>(null)
  const yamlEditorRef = ref<YamlEditorHandle | null>(null)
  const bindingEditorRef = ref<BindingEditorHandle | null>(null)
  const contentDrawerRef = ref<ContentDrawerHandle | null>(null)
  const yamlSaving = ref(false),
    bindingSaving = ref(false)
  const yamlEditorVisible = ref(false),
    bindingEditorVisible = ref(false)
  const rows = ref<YamlRow[]>([]),
    listLoading = ref(false),
    listError = ref(false)
  const enumLoading = ref(false),
    enumError = ref(false)
  const query = reactive(createQuery())
  const pagination = usePagination(onSearch, listLoading)
  const sidebarResetKey = ref(0),
    viewEpoch = ref(0),
    contentEpoch = ref(0)
  let active = true,
    mounted = false,
    listSequence = 0,
    enumSequence = 0
  const isPageRoute = () => route.fullPath.split('?')[0] === '/gray/config-file/index'
  const identityScopeKey = computed(() =>
    JSON.stringify([
      route.fullPath,
      user.userId,
      user.roleId,
      user.token,
      user.selected_environment,
    ])
  )
  const bindingScopeKey = computed(() =>
    JSON.stringify([identityScopeKey.value, query.project_product, viewEpoch.value])
  )
  const canCloseBindings = () =>
    !yamlSaving.value &&
    !bindingSaving.value &&
    !mutations.pending.value &&
    !mutations.confirming.value &&
    !yamlEditorVisible.value &&
    !bindingEditorVisible.value
  const bindings = useYamlBindings({
    contextKey: () => bindingScopeKey.value,
    blocked: () => !canCloseBindings(),
  })
  const bindingDrawer = bindings.drawer,
    loadBindings = bindings.loadBindings
  const editorScopeKey = computed(() =>
    JSON.stringify([bindingScopeKey.value, bindingDrawer.record?.id])
  )
  const requestKey = computed(() => JSON.stringify(requestParams()))
  const writeScopeKey = computed(() =>
    JSON.stringify([editorScopeKey.value, bindingDrawer.visible, requestKey.value])
  )
  const mutations = useYamlMutations({
    contextKey: () => writeScopeKey.value,
    blocked: () =>
      !active ||
      !isPageRoute() ||
      yamlSaving.value ||
      bindingSaving.value ||
      yamlEditorVisible.value ||
      bindingEditorVisible.value,
    applied: onMutationApplied,
  })
  const writeBusy = computed(() => !!mutations.pending.value || mutations.confirming.value)
  const contentScopeKey = computed(() =>
    JSON.stringify([
      editorScopeKey.value,
      bindingDrawer.visible,
      yamlEditorVisible.value,
      bindingEditorVisible.value,
      contentEpoch.value,
    ])
  )
  const yamlColumns = grayPageConfig.columns,
    bindingColumns = grayPageConfig.yamlBindingColumns

  function requestParams() {
    return queryParams(query, pagination.page, pagination.pageSize)
  }
  function invalidateList(clear = true) {
    ++listSequence
    listLoading.value = false
    listError.value = false
    if (clear) {
      rows.value = []
      pagination.setTotalSize(0)
    }
  }
  async function onSearch(): Promise<boolean> {
    if (!active || !isPageRoute()) {
      listLoading.value = false
      return false
    }
    const sequence = ++listSequence,
      context = identityScopeKey.value,
      epoch = viewEpoch.value,
      params = requestParams(),
      key = JSON.stringify(params)
    const current = () =>
      active &&
      isPageRoute() &&
      sequence === listSequence &&
      context === identityScopeKey.value &&
      epoch === viewEpoch.value &&
      key === requestKey.value
    listLoading.value = true
    listError.value = false
    try {
      const response = await getGrayYamlFile(params)
      if (!current()) return false
      const result = yamlPage(response, params.project_product ?? null)
      if (result.rows.length > params.pageSize) throw Error('Invalid page length')
      const lastPage = Math.max(1, Math.ceil(result.total / params.pageSize))
      if (pagination.page > lastPage) {
        pagination.page = lastPage
        return await onSearch()
      }
      rows.value = result.rows
      pagination.setTotalSize(result.total)
      return true
    } catch (loadFailure0) {
      if (current()) (reportLoadError(loadFailure0, "加载失败，请重试", false), listError.value = true)
      return false
    } finally {
      if (current()) listLoading.value = false
    }
  }
  async function loadEnums() {
    if (!active || !isPageRoute()) return
    const sequence = ++enumSequence,
      context = identityScopeKey.value,
      epoch = viewEpoch.value
    const current = () =>
      active &&
      context === identityScopeKey.value &&
      epoch === viewEpoch.value &&
      sequence === enumSequence
    enumLoading.value = true
    enumError.value = false
    try {
      await enumStore.getEnum()
    } catch (loadFailure1) {
      if (current()) (reportLoadError(loadFailure1, "加载失败，请重试", false), enumError.value = true)
    } finally {
      if (current()) enumLoading.value = false
    }
  }
  function onSidebarFilterChange(filter: { projectProduct: Selection }) {
    const id = selectionId(filter.projectProduct)
    if (id === query.project_product) return
    query.project_product = id
    pagination.page = 1
    void onSearch()
  }
  function onSearchRefresh() {
    pagination.page = 1
    void onSearch()
  }
  function onReset() {
    Object.assign(query, createQuery())
    pagination.page = 1
    sidebarResetKey.value++
    void onSearch()
  }
  function actionBlocked() {
    return (
      !active ||
      !isPageRoute() ||
      yamlSaving.value ||
      bindingSaving.value ||
      writeBusy.value ||
      yamlEditorVisible.value ||
      bindingEditorVisible.value
    )
  }
  function onAdd() {
    if (actionBlocked() || bindingDrawer.visible) return
    const defaults = navigationCreateRef.value?.getCreateDefaults()
    yamlEditorRef.value?.open(undefined, defaults?.projectProduct)
  }
  function onEdit(record: YamlRecord) {
    if (actionBlocked() || bindingDrawer.visible || !rows.value.some((row) => row.id === record.id))
      return
    yamlEditorRef.value?.open(record)
  }
  async function onYamlSaved() {
    const context = identityScopeKey.value,
      epoch = viewEpoch.value,
      key = requestKey.value
    contentEpoch.value++
    if (
      !(await onSearch()) &&
      active &&
      epoch === viewEpoch.value &&
      context === identityScopeKey.value &&
      key === requestKey.value
    )
      Message.error('配置已保存，列表读取失败，请重试查询')
  }
  async function onBindingSaved(yamlId: number) {
    const context = editorScopeKey.value,
      epoch = viewEpoch.value,
      key = requestKey.value
    contentEpoch.value++
    const reads = [onSearch()]
    if (bindingDrawer.visible && bindingDrawer.record?.id === yamlId)
      reads.push(loadBindings(yamlId))
    const result = await Promise.all(reads)
    if (
      active &&
      context === editorScopeKey.value &&
      epoch === viewEpoch.value &&
      key === requestKey.value &&
      result.some((loaded) => !loaded)
    )
      Message.error('绑定已保存，列表读取失败，请重试查询')
  }
  function yamlTarget(id: number): MutationTarget | null {
    const row = rows.value.find((row) => row.id === id),
      ownerId = selectionId(row?.project_product)
    return row && ownerId ? { kind: 'yaml', id: row.id, ownerId, label: row.name } : null
  }
  function bindingTarget(id: number): MutationTarget | null {
    const row = bindingDrawer.visible && bindingDrawer.dataList.find((row) => row.id === id)
    return row && row.yaml_file === bindingDrawer.record?.id
      ? { kind: 'binding', id: row.id, ownerId: row.yaml_file, label: row.file_path }
      : null
  }
  function onModifyYamlStatus(checked: boolean, id: number) {
    const target = yamlTarget(id)
    return target ? mutations.changeStatus(target, checked) : Promise.resolve(false)
  }
  function onModifyBindingStatus(checked: boolean, id: number) {
    const target = bindingTarget(id)
    return target ? mutations.changeStatus(target, checked) : Promise.resolve(false)
  }
  function onDelete(record: YamlRecord) {
    const target = yamlTarget(record.id)
    if (target) mutations.confirmDelete(target)
  }
  function onDeleteBinding(record: BindingRecord) {
    const target = bindingTarget(record.id)
    if (target) mutations.confirmDelete(target)
  }
  async function onMutationApplied(target: MutationTarget, status?: number): Promise<boolean> {
    invalidateList(false)
    contentEpoch.value++
    if (target.kind === 'yaml') {
      if (status === undefined) {
        const last = rows.value.length === 1 && rows.value[0].id === target.id
        rows.value = rows.value.filter((row) => row.id !== target.id)
        if (last && pagination.page > 1) pagination.page--
      } else rows.value = rows.value.map((row) => (row.id === target.id ? { ...row, status } : row))
      return onSearch()
    }
    if (!bindingDrawer.visible || bindingDrawer.record?.id !== target.ownerId) return false
    bindings.applyMutation(target.id, status)
    const result = await Promise.all([onSearch(), loadBindings(target.ownerId)])
    return result.every(Boolean)
  }
  function rowLoading(kind: MutationTarget['kind'], action: 'status' | 'delete', id: number) {
    const pending = mutations.pending.value
    return pending?.kind === kind && pending.action === action && pending.id === id
  }
  function onBindingManage(record: YamlRecord) {
    if (actionBlocked() || !rows.value.some((row) => row.id === record.id)) return
    bindings.open(record)
  }
  function onBindingAdd() {
    if (actionBlocked() || !bindingDrawer.visible || !bindingDrawer.record) return
    bindingEditorRef.value?.open(bindingDrawer.record)
  }
  function onBindingEdit(record: BindingRecord) {
    if (actionBlocked() || !bindingTarget(record.id) || !bindingDrawer.record) return
    bindingEditorRef.value?.open(bindingDrawer.record, record)
  }
  function onBindingContent(record: BindingRecord) {
    if (actionBlocked() || !bindingTarget(record.id)) return
    const yamlId = selectionId(bindingDrawer.record?.id),
      bindingId = selectionId(record.id),
      repositoryId = selectionId(record.repository)
    if (!yamlId || !bindingId || !repositoryId || selectionId(record.yaml_file) !== yamlId) {
      Message.warning('绑定信息已变化，请重新查询后查看')
      return
    }
    contentDrawerRef.value?.open({
      yamlId,
      bindingId,
      repositoryId,
      title: bindingDrawer.record?.name || '配置文件',
      filePath: record.file_path,
    })
  }
  function formatEnvironmentText(value: number | null | undefined) {
    if (value == null) return '环境通用'
    return (
      enumStore.environment_type.find((option) => String(option.key) === String(value))?.title ??
      String(value)
    )
  }
  function environmentColor(value: number | null | undefined) {
    return value == null ? 'gray' : enumStore.colors[value] || 'gray'
  }
  function repositoryLabel(item: Repository | number | null) {
    return item && typeof item === 'object'
      ? `${item.name || '-'} / ${formatEnvironmentText(item.test_env)} / ${item.branch || '-'}`
      : item == null
      ? '-'
      : `ID ${item}`
  }
  function visibleBindings(bindings: BindingRecord[]) {
    return bindings.filter((row) => row.status !== 0).slice(0, 3)
  }
  function hiddenBindings(bindings: BindingRecord[]) {
    return bindings.filter((row) => row.status !== 0).slice(3)
  }
  function bindingLabel(binding: BindingRecord) {
    const repository =
      binding.repository && typeof binding.repository === 'object' ? binding.repository : null
    return `${formatEnvironmentText(repository?.test_env)} / ${repository?.name || '-'}`
  }
  function invalidatePage() {
    viewEpoch.value++
    ++enumSequence
    enumLoading.value = false
    enumError.value = false
    invalidateList()
  }
  watch(requestKey, () => invalidateList(), { flush: 'sync' })
  watch(
    identityScopeKey,
    () => {
      invalidatePage()
      pagination.page = 1
      if (mounted && active && isPageRoute()) {
        void onSearch()
        void loadEnums()
      }
    },
    { flush: 'sync' }
  )
  onMounted(() => {
    mounted = true
    void onSearch()
    void loadEnums()
  })
  onDeactivated(() => {
    active = false
    invalidatePage()
  })
  onActivated(() => {
    if (active) return
    active = true
    if (mounted) {
      void onSearch()
      void loadEnums()
    }
  })
  onBeforeUnmount(() => {
    active = false
    invalidatePage()
  })
</script>

<style scoped lang="less">
  .mango-gray-toolbar {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    gap: var(--m-page-gap);
  }
  .mango-gray-error {
    color: var(--m-danger);
  }

  :global(.mango-gray-binding-panel .arco-drawer-body) {
    padding: var(--m-page-gap);
    overflow: hidden;
  }
  :global(.mango-gray-binding-panel .arco-drawer-header),
  :global(.mango-gray-binding-panel .arco-drawer-footer) {
    padding-inline: var(--m-page-gap);
  }
  .mango-gray-binding-drawer {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
    gap: var(--m-page-gap);
  }
  .mango-gray-binding-drawer > .arco-table {
    flex: 1 1 auto;
    min-height: 0;
  }
</style>
