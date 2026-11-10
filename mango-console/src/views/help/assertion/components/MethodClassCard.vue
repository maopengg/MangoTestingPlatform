<template>
  <div class="mango-assertion-method-card">
    <a-table
      :columns="methodColumns"
      :data="group.children"
      :scroll="{ x: METHOD_SCROLL_X }"
      :pagination="false"
      :bordered="false"
      row-key="value"
    >
      <template #columns>
        <a-table-column v-for="column in methodColumns" :key="column.key" v-bind="column">
          <template v-if="column.key === 'parameter'" #cell="{ record }">
            <div v-if="record.parameter?.length" class="mango-assertion-method-card__parameters"
              ><a-tag
                v-for="parameter in record.parameter"
                :key="parameter.f"
                size="small"
                :title="parameter.n || parameter.f"
                >{{ parameter.n || parameter.f }}</a-tag
              ></div
            >
            <span v-else class="mango-assertion-method-card__empty">无</span>
          </template>
          <template v-else-if="column.key === 'actions'" #cell="{ record }">
            <MangoTableActions
              :actions="[
                {
                  label: record.testable === false ? '配置' : '测试',
                  disabled,
                  onClick: () => select(record),
                },
              ]"
            />
          </template>
        </a-table-column>
      </template>
    </a-table>
  </div>
</template>
<script setup lang="ts">
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import { methodColumns, METHOD_SCROLL_X } from '../config'
  import type { AssertionMethodClassGroup, AssertionMethodItem } from '@/types/assertion'
  const props = defineProps<{ group: AssertionMethodClassGroup; disabled: boolean }>()
  const emit = defineEmits<{ (e: 'test', record: AssertionMethodItem): void }>()
  function select(record: AssertionMethodItem) {
    if (!props.disabled) emit('test', record)
  }
</script>
<style scoped lang="less">
  .mango-assertion-method-card {
    min-width: 0;
    overflow: hidden;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-lg);
    background: var(--m-surface);
  }
  .mango-assertion-method-card__parameters {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    min-width: 0;
  }
  .mango-assertion-method-card__parameters :deep(.arco-tag) {
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .mango-assertion-method-card__empty {
    color: var(--m-muted);
  }
</style>
