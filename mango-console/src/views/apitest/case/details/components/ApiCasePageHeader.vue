<template>
  <div class="mango-detail-toolbar">
    <div class="mango-detail-heading">
      <div class="mango-detail-title">{{ title }}</div>
      <div class="mango-detail-subtitle">维护用例前后置、接口编排、断言和执行结果</div>
    </div>
    <a-space class="mango-detail-actions" wrap>
      <a-button
        size="small"
        status="success"
        :loading="running"
        :disabled="executionDisabled"
        data-testid="qa-views-apitest-case-details-button-执行"
        @click="$emit('execute')"
      >
        执行
      </a-button>
      <a-button
        v-if="caseId"
        size="small"
        :disabled="analysisDisabled"
        @click="$emit('analyze')"
      >
        AI 分析
      </a-button>
      <a-button
        v-if="caseId"
        size="small"
        data-testid="qa-views-apitest-case-details-button-搜索数据"
        @click="$emit('search')"
      >
        搜索数据
      </a-button>
      <a-button
        v-if="caseId"
        size="small"
        data-testid="qa-views-apitest-case-details-button-历史结果"
        @click="$emit('history')"
      >
        历史结果
      </a-button>
      <slot></slot>
      <a-button
        class="mango-back-button"
        size="small"
        data-testid="qa-views-apitest-case-details-button-返回"
        @click="$emit('back')"
      >
        返回
      </a-button>
    </a-space>
  </div>
</template>

<script setup lang="ts">
  defineProps<{
    title: string
    caseId?: string | number
    running?: boolean
    executionDisabled?: boolean
    analysisDisabled?: boolean
  }>()

  defineEmits<{
    (event: 'execute'): void
    (event: 'analyze'): void
    (event: 'search'): void
    (event: 'history'): void
    (event: 'back'): void
  }>()
</script>
