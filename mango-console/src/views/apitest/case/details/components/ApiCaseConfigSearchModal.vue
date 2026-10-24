<template>
  <a-modal
    :visible="visible"
    title="当前 Case 数据搜索"
    :width="760"
    :footer="false"
    unmount-on-close
    @update:visible="$emit('update:visible', $event)"
  >
    <div class="mango-api-case-config-search">
      <a-input-search
        :model-value="keyword"
        search-button
        button-text="搜索"
        allow-clear
        :loading="loading"
        :disabled="loading"
        placeholder="输入 App ID、变量名、URL、请求或响应内容"
        data-testid="qa-views-apitest-case-details-input-search-当前case配置"
        @update:model-value="$emit('update:keyword', String($event || ''))"
        @search="$emit('search')"
      />
      <div class="mango-api-case-config-search__hint">
        搜索当前正在查看的 Case、版本配置及最近一次执行结果。
        <span v-if="loading && total"> 正在加载 {{ completed }}/{{ total }} 个配置区域… </span>
      </div>
      <a-spin :loading="loading" class="mango-api-case-config-search__spin">
        <div v-if="searched" class="mango-api-case-config-search__summary">
          找到 {{ matches.length }} 个配置位置
          <span v-if="truncated">，仅展示前 {{ limit }} 个</span>
        </div>
        <div v-if="matches.length" class="mango-api-case-config-search__results">
          <button
            v-for="(item, index) in matches"
            :key="`${item.location}-${index}`"
            type="button"
            class="mango-api-case-config-search__result"
            @click="$emit('select', item)"
          >
            <span class="mango-api-case-config-search__location">{{ item.location }}</span>
            <span class="mango-api-case-config-search__path">{{ item.path }}</span>
            <span class="mango-api-case-config-search__preview">{{ item.preview }}</span>
          </button>
        </div>
        <div v-else-if="searched && !loading" class="mango-empty-state">
          当前 Case 数据中未找到匹配内容
        </div>
        <div v-else-if="!loading" class="mango-empty-state">
          输入内容后搜索当前 Case 的配置和最近执行结果
        </div>
      </a-spin>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
  import type { ConfigSearchMatch } from '../types'

  defineProps<{
    visible: boolean
    keyword: string
    loading: boolean
    searched: boolean
    truncated: boolean
    completed: number
    total: number
    matches: ConfigSearchMatch[]
    limit: number
  }>()

  defineEmits<{
    (event: 'update:visible', value: boolean): void
    (event: 'update:keyword', value: string): void
    (event: 'search'): void
    (event: 'select', value: ConfigSearchMatch): void
  }>()
</script>

<style scoped>
  .mango-api-case-config-search {
    display: flex;
    min-height: 420px;
    flex-direction: column;
    gap: 8px;
  }

  .mango-api-case-config-search__hint,
  .mango-api-case-config-search__summary {
    color: var(--m-muted);
    font-size: 12px;
    line-height: 20px;
  }

  .mango-api-case-config-search__spin {
    min-height: 350px;
  }

  .mango-api-case-config-search__results {
    display: flex;
    max-height: 470px;
    flex-direction: column;
    overflow-y: auto;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
  }

  .mango-api-case-config-search__result {
    display: grid;
    grid-template-columns: minmax(180px, 0.8fr) minmax(160px, 0.7fr) minmax(260px, 1.5fr);
    gap: 12px;
    width: 100%;
    padding: 10px 12px;
    border: 0;
    border-bottom: 1px solid var(--m-border);
    background: transparent;
    color: var(--m-text);
    text-align: left;
    cursor: pointer;
  }

  .mango-api-case-config-search__result:last-child {
    border-bottom: 0;
  }

  .mango-api-case-config-search__result:hover {
    background: var(--m-fill-1);
  }

  .mango-api-case-config-search__location,
  .mango-api-case-config-search__path,
  .mango-api-case-config-search__preview {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-api-case-config-search__location {
    font-weight: 600;
  }

  .mango-api-case-config-search__path {
    color: var(--m-primary);
  }

  .mango-api-case-config-search__preview {
    color: var(--m-text-2);
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  }
</style>
