<template>
  <section class="mango-module-manager">
    <div class="mango-module-manager__toolbar">
      <a-input-search
        v-model="keyword"
        allow-clear
        aria-label="搜索模块名称或 ID"
        placeholder="搜索模块名称或 ID"
      />
      <a-space wrap>
        <a-button size="small" @click="expandedKeys = moduleBranchKeys(tree)">全部展开</a-button>
        <a-button size="small" @click="expandedKeys = []">全部收起</a-button>
      </a-space>
    </div>
    <a-alert v-if="error" type="warning"
      >{{ error }}
      <a-button type="text" size="small" :loading="loading" @click="$emit('retry')"
        >重试</a-button
      ></a-alert
    >
    <MangoPanelSpin :loading="loading" class="mango-module-manager__panel">
      <a-tree
        v-if="visibleTree.length"
        v-model:expanded-keys="expandedKeys"
        :data="visibleTree"
        :selectable="false"
        block-node
        :show-line="false"
        size="small"
        class="mango-module-manager__tree"
      >
        <template #title="node">
          <div
            class="mango-module-manager__row"
            :class="{ 'mango-module-manager__row--root': Number(node.record.level) === 1 }"
          >
            <a-tooltip :content="formatModulePath(node.record)">
              <button
                type="button"
                class="mango-module-manager__name"
                @click.stop="$emit('detail', node.record)"
                ><svg
                  class="mango-module-manager__icon"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  aria-hidden="true"
                >
                  <line
                    v-for="y in moduleLevelIconLines[Number(node.record.level) - 1]"
                    :key="y"
                    x1="4"
                    x2="20"
                    :y1="y"
                    :y2="y"
                  />
                </svg>
                <span class="mango-module-manager__label">{{ node.title }}</span></button
              >
            </a-tooltip>
            <span
              class="mango-module-manager__children"
              :class="{ 'mango-module-manager__children--empty': !node.childCount }"
              >{{ node.childCount ? `${node.childCount} 个下级` : '' }}</span
            >
            <span class="mango-module-manager__id">ID {{ node.key }}</span>
            <div class="mango-module-manager__actions" @click.stop @keydown.stop>
              <MangoTableActions :actions="nodeActions(node.record)" />
            </div>
          </div>
        </template>
      </a-tree>
      <div v-else-if="!loading" class="mango-empty-state">
        {{
          keyword
            ? '没有匹配的模块，请调整搜索条件'
            : error
            ? '模块加载失败，请重试'
            : '暂无模块，点击“新增一级模块”开始配置'
        }}
      </div>
    </MangoPanelSpin>
  </section>
</template>

<script setup lang="ts">
  import { computed, ref, watch } from 'vue'
  import MangoPanelSpin from '@/components/feedback/MangoPanelSpin.vue'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import { formatModulePath } from '@/utils/business-format'
  import {
    buildModuleTree,
    filterModuleTree,
    moduleBranchKeys,
    moduleLevelIconLines,
  } from './config'

  const props = defineProps<{ modules: any[]; loading: boolean; error: string }>()
  const emit = defineEmits<{
    (event: 'retry'): void
    (event: 'add' | 'edit' | 'delete' | 'detail', record: any): void
  }>()
  const keyword = ref('')
  const expandedKeys = ref<number[]>([])
  const tree = computed(() => buildModuleTree(props.modules))
  const visibleTree = computed(() => filterModuleTree(tree.value, keyword.value))
  function nodeActions(record: any) {
    return [
      ...(Number(record.level) < 3
        ? [{ label: '新增下级', onClick: () => emit('add', record) }]
        : []),
      { label: '编辑', onClick: () => emit('edit', record) },
      { label: '删除', danger: true, onClick: () => emit('delete', record) },
    ].map((action) => ({ ...action, disabled: props.loading }))
  }
  watch(keyword, () => {
    if (keyword.value.trim()) expandedKeys.value = moduleBranchKeys(visibleTree.value)
  })
  watch(
    tree,
    (nodes, previous) => {
      const branches = moduleBranchKeys(nodes)
      const oldBranches = new Set(moduleBranchKeys(previous || []))
      const defaultBranches = new Set(moduleBranchKeys(nodes, 0))
      expandedKeys.value = [
        ...new Set([
          ...expandedKeys.value.filter((key) => branches.includes(key)),
          ...branches.filter((key) => !oldBranches.has(key) && defaultBranches.has(key)),
        ]),
      ]
    },
    { immediate: true }
  )
</script>

<style scoped>
  .mango-module-manager {
    display: flex;
    flex-direction: column;
    width: 100%;
    max-width: 1120px;
    margin-inline: auto;
    gap: var(--m-page-gap);
    min-height: 0;
    height: 100%;
    container: mango-module-manager / inline-size;
    background: var(--m-surface);
  }
  .mango-module-manager__toolbar {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: var(--m-page-gap);
    padding: var(--m-card-padding);
    border-bottom: 1px solid var(--m-border);
  }
  .mango-module-manager__toolbar :deep(.arco-input-search) {
    width: 280px;
    max-width: 100%;
  }
  .mango-module-manager__toolbar :deep(.arco-space) {
    margin-left: auto;
  }
  .mango-module-manager__panel {
    flex: 1;
    min-height: 0;
    overflow: auto;
    padding: 0 var(--m-card-padding) var(--m-card-padding);
  }
  .mango-module-manager__tree {
    width: 100%;
    max-width: 760px;
    margin-inline: auto;
  }
  .mango-module-manager__tree :deep(.arco-tree-node-title) {
    min-width: 0;
    padding: 0;
    border-radius: var(--m-radius-sm);
  }
  .mango-module-manager__tree :deep(.arco-tree-node) {
    padding-block: 1px;
  }
  .mango-module-manager__tree :deep(.arco-tree-node-switcher) {
    color: var(--m-text-2);
  }
  .mango-module-manager__tree :deep(.arco-tree-node-title-text) {
    flex: 1;
    min-width: 0;
  }
  .mango-module-manager__row {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: var(--m-space-md);
    min-height: 32px;
    width: 100%;
    padding: var(--m-space-xs) var(--m-space-sm);
    box-sizing: border-box;
    border-radius: var(--m-radius-sm);
  }
  .mango-module-manager__row--root {
    background: var(--m-surface);
  }
  .mango-module-manager__name {
    display: inline-flex;
    align-items: center;
    gap: var(--m-space-sm);
    flex: 1 1 0;
    min-width: 0;
    max-width: 100%;
    white-space: nowrap;
    border: 0;
    padding: 0;
    background: transparent;
    color: var(--m-text);
    font: inherit;
    font-size: var(--m-font-body);
    font-weight: 400;
    cursor: pointer;
    text-align: left;
  }
  .mango-module-manager__row--root .mango-module-manager__name {
    font-weight: 600;
  }
  .mango-module-manager__icon {
    width: 16px;
    height: 16px;
    flex-shrink: 0;
    color: var(--m-text-2);
    font-size: 16px;
  }
  .mango-module-manager__row--root .mango-module-manager__icon {
    color: var(--m-primary);
  }
  .mango-module-manager__label {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .mango-module-manager__name:hover {
    color: var(--m-primary);
  }
  .mango-module-manager__name:focus-visible {
    outline: 2px solid var(--m-primary);
    outline-offset: 2px;
  }
  .mango-module-manager__id,
  .mango-module-manager__children {
    color: var(--m-text-2);
    font-size: var(--m-font-caption);
    font-variant-numeric: tabular-nums;
  }
  .mango-module-manager__children {
    flex: 0 0 80px;
    box-sizing: border-box;
    text-align: left;
    padding: 1px var(--m-space-sm);
    border-radius: var(--m-radius-sm);
    background: var(--m-surface-soft);
  }
  .mango-module-manager__children--empty {
    visibility: hidden;
  }
  .mango-module-manager__row--root .mango-module-manager__children {
    background: var(--m-surface);
  }
  .mango-module-manager__id {
    margin-left: 24px;
    flex: 0 0 80px;
    text-align: left;
    font-weight: 400;
  }
  .mango-module-manager__actions {
    flex: 0 0 160px;
    margin-left: 48px;
  }
  .mango-module-manager__actions :deep(.mango-table-actions) {
    width: 100%;
    justify-content: flex-end;
  }
  @container mango-module-manager (max-width: 44rem) {
    .mango-module-manager__children {
      display: none;
    }
    .mango-module-manager__name {
      max-width: 100%;
    }
    .mango-module-manager__actions {
      flex-basis: 100%;
      margin-left: 0;
    }
  }
</style>
