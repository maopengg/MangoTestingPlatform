<template>
  <div style="flex: 1; overflow: auto; margin-top: 10px;">
    <a-table
      :bordered="true"
      :columns="tableColumns"
      :data="dataList"
      :loading="loading"
      :pagination="false"
      :rowKey="rowKey"
      @selection-change="onSelectionChange"
      :scrollbar="true"
      :scroll="{
        y: 500
      }"
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
            <span style="width: 110px; display: inline-block">{{ record.id }}</span>
          </template>
          <template v-else-if="item.key === 'timing_strategy'" #cell="{ record }">
            {{ record.timing_strategy?.name }}
          </template>
          <template v-else-if="item.key === 'case_people'" #cell="{ record }">
            {{ record.case_people?.name }}
          </template>
          <template v-else-if="item.key === 'test_env'" #cell="{ record }">
            <a-tag :color="enumStore.colors[record.test_env]" size="small">
              {{
                record.test_env !== null
                  ? enumStore.environment_type[record.test_env].title
                  : ''
              }}
            </a-tag>
          </template>
          <template v-else-if="item.key === 'actions'" #cell="{ record }">
            <a-space>
              <a-button
                size="mini"
                type="text"
                class="custom-mini-btn"
                @click="onClick(record)"
                >查看结果
              </a-button>
            </a-space>
          </template>
        </a-table-column>
      </template>
    </a-table>
  </div>
</template>

<script lang="ts" setup>
  import { useRowKey, useRowSelection, useTableColumn } from '@/hooks/table'
  import { useEnum } from '@/store/modules/get-enum'
  import { useRouter } from 'vue-router'

  const props = defineProps({
    dataList: {
      type: Array,
      default: () => []
    },
    loading: {
      type: Boolean,
      default: false
    },
    tableColumns: {
      type: Array,
      default: () => []
    }
  })

  const emit = defineEmits(['selection-change', 'view-result'])

  const { onSelectionChange } = useRowSelection()
  const rowKey = useRowKey('id')
  const enumStore = useEnum()
  const router = useRouter()

  function onClick(record: any) {
    emit('view-result', record)
  }
</script>