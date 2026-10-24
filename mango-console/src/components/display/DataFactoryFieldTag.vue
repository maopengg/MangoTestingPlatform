<template>
  <a-tooltip :content="tag.label">
    <a-tag :color="color" size="small" class="mango-field-rule-tag">
      <span class="mango-field-rule-tag-text">{{ tag.label }}</span>
    </a-tag>
  </a-tooltip>
</template>

<script setup lang="ts">
  import { computed } from 'vue'
  import type { DataFactoryFieldRule } from '@/types/data-factory'
  import { getFieldTag } from '@/components/DataFactory/fieldTags'
  import { useEnum } from '@/store/modules/get-enum'
  import { getEnumTagColor } from '@/utils/business-format'

  const props = defineProps<{ record: DataFactoryFieldRule; field: string }>()
  const enumStore = useEnum()
  const tag = computed(() => getFieldTag(props.record, props.field))
  const color = computed(() => getEnumTagColor(tag.value.options, tag.value.key, enumStore.colors))
</script>

<style scoped>
  .mango-field-rule-tag {
    max-width: 100%;
  }

  .mango-field-rule-tag-text {
    display: block;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
</style>
