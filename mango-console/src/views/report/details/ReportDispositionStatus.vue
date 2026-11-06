<template>
  <a-tooltip v-if="record.execution_control?.phase === 'infrastructure_blocked'" :content="record.failure_description || '回归尚未完成，请核查平台、执行记录和清理责任'">
    <a-tag size="small" color="orange">{{ record.execution_control.requires_review === false ? '已核查待重试' : record.failure_reason === 'environment' ? '待环境核查' : '待平台核查' }}</a-tag>
  </a-tooltip>
  <a-tooltip v-else-if="record.is_excluded || record.failure_reason || record.failure_description" :content="description">
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
