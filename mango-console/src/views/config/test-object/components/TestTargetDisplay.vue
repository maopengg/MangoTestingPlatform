<template>
  <div class="mango-target-preview-summary">
    <div class="mango-target-preview-field">
      <span class="mango-target-preview-label">默认地址</span>
      <span class="mango-target-preview-default" :title="defaultAddress">{{ defaultAddress }}</span>
    </div>
    <template v-if="!value && config?.selector">
      <div class="mango-target-preview-field">
        <span class="mango-target-preview-label">条件变量</span>
        <span>{{ config.selector }}</span>
      </div>
      <div class="mango-target-preview-field">
        <span class="mango-target-preview-label">地址映射</span>
        <div class="mango-target-preview-list">
          <div
            v-for="[key, address] in entries.slice(0, 2)"
            :key="key"
            class="mango-target-preview-line"
            :title="`${key} → ${address}`"
            >{{ key }} → {{ address }}</div
          >
          <a-popover v-if="entries.length > 2" position="bottom" trigger="click">
            <a-button type="text" size="small">查看全部 {{ entries.length }} 项映射</a-button>
            <template #content>
              <div class="mango-target-preview">
                <div>条件变量：{{ config.selector }}</div>
                <div v-if="config.default">默认地址：{{ config.default }}</div>
                <dl class="mango-target-preview-mappings">
                  <template v-for="[key, address] in entries" :key="key">
                    <dt>{{ key }}</dt
                    ><dd>{{ address }}</dd>
                  </template>
                </dl>
              </div>
            </template>
          </a-popover>
        </div>
      </div>
    </template>
  </div>
</template>
<script setup lang="ts">
  import { computed } from 'vue'
  import type { TestTargetConfig } from '../target-config'
  const props = defineProps<{ value?: string; config?: TestTargetConfig }>()
  const defaultAddress = computed(() => props.value || props.config?.default || '未设置')
  const entries = computed(() => Object.entries(props.config?.mapping || {}))
</script>
<style scoped>
  .mango-target-preview {
    max-width: min(560px, 70vw);
    overflow-wrap: anywhere;
  }
  .mango-target-preview-summary {
    min-width: 0;
    display: grid;
    gap: 4px;
    color: var(--m-text);
    text-align: left;
  }
  .mango-target-preview-field {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    gap: 12px;
    align-items: baseline;
  }
  .mango-target-preview-label {
    color: var(--m-muted);
    white-space: nowrap;
  }
  .mango-target-preview-list {
    min-width: 0;
    display: grid;
    gap: 4px;
  }
  .mango-target-preview-default {
    color: var(--m-text);
    overflow-wrap: anywhere;
  }
  .mango-target-preview-line {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--m-text);
  }
  .mango-target-preview-mappings {
    display: grid;
    grid-template-columns: minmax(80px, 1fr) minmax(0, 3fr);
    gap: 8px 16px;
    max-height: 320px;
    overflow: auto;
  }
  .mango-target-preview-mappings dd {
    margin: 0;
  }
</style>
