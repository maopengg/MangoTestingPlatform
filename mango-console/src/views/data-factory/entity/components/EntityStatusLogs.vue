<template>
  <BaseSidePanel
    :visible="visible"
    :title="`${entity?.name || ''} · 状态变更记录`"
    :width="1000"
    :show-footer="false"
    @update:visible="
      (value) => {
        if (!value) close()
      }
    "
  >
    <section class="mango-entity-log-panel">

      <a-table
        class="mango-native-scroll-table"
        :columns="entityStatusLogColumns"
        :data="rows"
        :loading="loading"
        :pagination="false"
        row-key="id"
        :scroll="{ x: 1030, y: '100%' }"
      >
        <template #columns>
          <a-table-column
            v-for="item of entityStatusLogColumns"
            :key="item.key"
            :align="item.align"
            :data-index="item.key"
            :ellipsis="item.ellipsis"
            :tooltip="item.tooltip"
            :title="item.title"
            :width="item.width"
          >
            <template v-if="item.key === 'create_time'" #cell="{ record }">{{
              formatStatusTime(record.create_time)
            }}</template>
            <template v-else-if="item.key === 'status_change'" #cell="{ record }"
              >{{ record.from_status_name }} → {{ record.to_status_name }}</template
            >
            <template v-else-if="item.key === 'source_name'" #cell="{ record }"
              ><a-tag :color="statusSourceColor(record.source)" size="small">{{
                record.source_name
              }}</a-tag></template
            >
            <template v-else-if="item.key === 'operator'" #cell="{ record }">{{
              record.operator?.name || record.operator?.username || '系统'
            }}</template>
            <template v-else-if="item.key === 'reference'" #cell="{ record }">{{
              formatStatusReference(record)
            }}</template>
          </a-table-column>
        </template>
      </a-table>
      <a-pagination
        v-model:current="pagination.current"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        show-total
        show-page-size
        @change="load"
        @page-size-change="onSizeChange"
      />
    </section>
  </BaseSidePanel>
</template>
<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { reactive, ref } from 'vue'
  import { getDataFactoryEntityStatusLog } from '@/api/data-factory'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import { entityStatusLogColumns } from '../config'
  import { formatStatusTime, formatStatusReference, statusSourceColor } from '../display'
  import { useEntityScope } from '../composables/useEntityScope'
  import type { EntityRecord, StatusLog } from '../types'
  const visible = ref(false),
    entity = ref<EntityRecord | null>(null),
    rows = ref<StatusLog[]>([]),
    loading = ref(false),
    loadError = ref(false)
  const pagination = reactive({ current: 1, pageSize: 10, total: 0 })
  let request = 0
  const scope = useEntityScope(close)
  function open(record: EntityRecord) {
    if (!scope.isActive()) return
    close()
    entity.value = { ...record }
    pagination.current = 1
    visible.value = true
    void load()
  }
  function close() {
    ++request
    visible.value = false
    entity.value = null
    rows.value = []
    pagination.total = 0
    loading.value = false
    loadError.value = false
  }
  async function load() {
    if (!visible.value || !entity.value || !scope.isActive()) return
    const current = ++request,
      version = scope.snapshot(),
      payload = {
        entity_id: entity.value.id,
        page: pagination.current,
        pageSize: pagination.pageSize,
      }
    loading.value = true
    loadError.value = false
    try {
      const response = await getDataFactoryEntityStatusLog(payload)
      if (current === request && scope.current(version)) {
        rows.value = response.data || []
        pagination.total = Number(response.totalSize || 0)
      }
    } catch (loadFailure0) {
      if (current === request && scope.current(version)) (reportLoadError(loadFailure0, "加载失败，请重试", false), loadError.value = true)
    } finally {
      if (current === request) loading.value = false
    }
  }
  function onSizeChange(size: number) {
    pagination.current = 1
    pagination.pageSize = size
    return load()
  }
  defineExpose({ open, close })
</script>
<style scoped>
  .mango-entity-log-panel {
    height: 100%;
    min-height: 0;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: var(--m-page-gap);
    overflow: hidden;
  }
</style>
