<template>
  <BaseSidePanel
    :visible="visible"
    :title="`${alias?.name || ''} / 环境绑定`"
    :width="1000"
    :show-footer="false"
    @update:visible="onVisibilityChange"
    @cancel="close"
  >
    <section class="mango-datasource-bindings">
      <a-space class="mango-datasource-bindings__toolbar">
        <a-button size="small" type="primary" :disabled="bindingSaving" @click="openEditor()"
          >新增绑定</a-button
        >
        <a-button size="small" :loading="loading" @click="loadBindings">刷新</a-button>
      </a-space>
      
      <a-table
        class="mango-native-scroll-table"
        :scroll="{ x: bindingScrollX, y: '100%' }"
        :columns="datasourceBindingColumns"
        :data="rows"
        :loading="loading"
        :pagination="false"
        :bordered="false"
        row-key="id"
      >
        <template #columns>
          <a-table-column
            v-for="item of datasourceBindingColumns"
            :key="item.key"
            :align="item.align"
            :fixed="item.fixed"
            :data-index="item.key"
            :ellipsis="item.ellipsis"
            :tooltip="item.tooltip"
            :title="item.title"
            :width="item.width"
          >
            <template v-if="item.key === 'index'" #cell="{ record }">{{ record.id }}</template>
            <template v-else-if="item.key === 'environment'" #cell="{ record }">
              <a-tag :color="enumStore.colors[record.environment]" size="small">{{
                enumStore.environment_type.find(
                  (item) => String(item.key) === String(record.environment)
                )?.title ?? record.environment
              }}</a-tag>
            </template>
            <template v-else-if="item.key === 'data_source'" #cell="{ record }">{{
              displayDataSource(record.data_source ?? record.database)
            }}</template>
            <template v-else-if="item.key === 'update_user'" #cell="{ record }">{{
              record.update_user?.name || record.update_user?.username || '-'
            }}</template>
            <template
              v-else-if="item.key === 'db_c_status' || item.key === 'db_rud_status'"
              #cell="{ record }"
            >
              <a-tag :color="record[item.key] === 1 ? 'green' : 'orange'" size="small">{{
                record[item.key] === 1 ? '允许' : '禁止'
              }}</a-tag>
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <MangoTableActions
                :actions="[
                  {
                    label: '编辑',
                    disabled: bindingSaving || deletingIds.has(record.id),
                    onClick: () => openEditor(record),
                  },
                  {
                    label: '删除',
                    danger: true,
                    loading: deletingIds.has(record.id),
                    disabled: editingIds.has(record.id),
                    onClick: () => removeBinding(record),
                  },
                ]"
              />
            </template>
          </a-table-column>
        </template>
      </a-table>
    </section>
  </BaseSidePanel>
  <DatasourceBindingEditor ref="editorRef" @saved="onSaved" @saving-change="onEditorSaving" />
</template>
<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { reactive, ref } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import {
    getDataFactoryDatasourceBinding,
    deleteDataFactoryDatasourceBinding,
  } from '@/api/data-factory'
  import { useEnum } from '@/store/modules/get-enum'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import DatasourceBindingEditor from './DatasourceBindingEditor.vue'
  import { datasourceBindingColumns, bindingScrollX } from '../config'
  import { displayDataSource } from '../form'
  import { useDatasourceScope } from '../composables/useDatasourceScope'
  import type { LogicalSource, LogicalBinding, BindingEditorHandle } from '../types'
  const emit = defineEmits<{ (event: 'writing-change', aliasId: number, pending: boolean): void }>()
  const enumStore = useEnum()
  const visible = ref(false),
    alias = ref<LogicalSource | null>(null),
    rows = ref<LogicalBinding[]>([])
  const loading = ref(false),
    loadError = ref(false),
    bindingSaving = ref(false)
  const editorRef = ref<BindingEditorHandle | null>(null)
  const deletingIds = reactive(new Set<number>()),
    editingIds = reactive(new Set<number>())
  const writers = new Map<number, number>()
  let session = 0,
    request = 0
  let confirmation: ReturnType<typeof Modal.confirm> | null = null
  const scope = useDatasourceScope(close)
  function changeWriting(id: number, pending: boolean) {
    const count = writers.get(id) ?? 0,
      next = Math.max(0, count + (pending ? 1 : -1))
    if (next) writers.set(id, next)
    else writers.delete(id)
    if (!count && next) emit('writing-change', id, true)
    if (count && !next) emit('writing-change', id, false)
  }
  function open(source: LogicalSource) {
    if (!scope.isActive()) return
    close()
    alias.value = { ...source }
    visible.value = true
    void loadBindings()
  }
  function close() {
    ++session
    ++request
    visible.value = false
    alias.value = null
    rows.value = []
    loading.value = false
    loadError.value = false
    editorRef.value?.close()
    confirmation?.close()
    confirmation = null
  }
  function onVisibilityChange(value: boolean) {
    if (!value) close()
  }
  async function loadBindings() {
    if (!visible.value || !alias.value || !scope.isActive()) return
    const current = ++request,
      version = scope.snapshot(),
      id = alias.value.id
    loading.value = true
    loadError.value = false
    try {
      const response = await getDataFactoryDatasourceBinding({ datasource_alias: id })
      if (current === request && scope.current(version)) rows.value = response.data || []
    } catch (loadFailure0) {
      if (current === request && scope.current(version)) (reportLoadError(loadFailure0, "加载失败，请重试", false), loadError.value = true)
    } finally {
      if (current === request) loading.value = false
    }
  }
  function openEditor(record?: LogicalBinding) {
    if (
      !visible.value ||
      !alias.value ||
      !scope.isActive() ||
      bindingSaving.value ||
      (record && deletingIds.has(record.id))
    )
      return
    editorRef.value?.open(alias.value, record)
  }
  function onSaved(id: number) {
    if (visible.value && alias.value?.id === id) void loadBindings()
  }
  function onEditorSaving(aliasId: number, id: number | null, pending: boolean) {
    bindingSaving.value = pending
    if (id !== null) {
      if (pending) editingIds.add(id)
      else editingIds.delete(id)
    }
    changeWriting(aliasId, pending)
  }
  function removeBinding(record: LogicalBinding) {
    if (
      !visible.value ||
      !alias.value ||
      !scope.isActive() ||
      confirmation ||
      deletingIds.has(record.id) ||
      editingIds.has(record.id)
    )
      return
    const id = record.id,
      aliasId = alias.value.id,
      current = session,
      version = scope.snapshot()
    const dialog = Modal.confirm({
      title: '删除绑定',
      content: '确认删除该环境绑定？',
      okText: '删除',
      cancelText: '取消',
      okButtonProps: { status: 'danger' },
      async onBeforeOk() {
        if (
          current !== session ||
          !scope.current(version) ||
          deletingIds.has(id) ||
          editingIds.has(id)
        )
          return false
        deletingIds.add(id)
        changeWriting(aliasId, true)
        try {
          const response = await deleteDataFactoryDatasourceBinding(id)
          if (current === session && scope.current(version)) {
            Message.success(response.msg)
            await loadBindings()
          }
          return true
        } catch {
          return false
        } finally {
          deletingIds.delete(id)
          changeWriting(aliasId, false)
        }
      },
      onClose() {
        if (confirmation === dialog) confirmation = null
      },
    })
    confirmation = dialog
  }
  defineExpose({ open, close })
</script>
<style scoped>
  .mango-datasource-bindings {
    display: flex;
    height: 100%;
    min-height: 0;
    min-width: 0;
    flex-direction: column;
    gap: var(--m-page-gap);
    overflow: hidden;
  }
  .mango-datasource-bindings__toolbar {
    flex: none;
  }
</style>
