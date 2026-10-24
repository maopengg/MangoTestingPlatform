<template>
  <a-tooltip v-if="record.is_excluded || record.failure_reason || record.failure_description" :content="description">
    <a-tag size="small" :color="record.is_excluded ? 'orange' : 'blue'">
      {{ record.is_excluded ? '已排除' : '已排查' }}
    </a-tag>
  </a-tooltip>
  <span v-else>-</span>
</template>

<script setup lang="ts">
  import { computed } from 'vue'
  import { useEnum } from '@/store/modules/get-enum'

  const props = defineProps<{ record: any }>()
  const enumStore = useEnum()
  const description = computed(() => {
    const reason = enumStore.report_failure_reason.find((item: any) => item.key === props.record.failure_reason)?.title
    return `原因：${reason || '未填写'}；说明：${props.record.failure_description || '未填写'}`
  })
</script>
