<template>
  <a-modal :visible="visible" title="生成数据预览" width="920px" @update:visible="emitVisible">
    <a-space class="data-factory-preview-content" direction="vertical">
      <a-alert v-if="result.missing_fields?.length" type="warning">
        当前还有 {{ result.missing_fields.length }} 个字段需要配置，建议补齐后再调试运行。
      </a-alert>
      <a-alert v-else-if="result.payload" type="success">当前模板字段已能生成 payload，可以继续调试运行。</a-alert>
      <a-textarea
        v-if="Object.keys(result.output || {}).length"
        :model-value="JSON.stringify(result.output, null, 2)"
        :auto-size="{ minRows: 3, maxRows: 8 }"
        readonly
      />
      <a-table
        v-if="flattenDependencyTree(result.dependency_tree).length"
        :columns="dependencyTreeColumns"
        :data="flattenDependencyTree(result.dependency_tree)"
        :pagination="false"
        :row-key="'path'"
        :scroll="{ x: 900, y: 220 }"
        size="small"
      >
        <template #columns>
          <a-table-column
            v-for="item of dependencyTreeColumns"
            :key="item.key"
            :data-index="item.key"
            :title="item.title"
            :width="item.width"
          >
            <template v-if="item.key === 'node'" #cell="{ record }">
              <span :style="{ paddingLeft: `${record.level * 18}px` }">{{ record.template_name }}</span>
              <a-tag v-if="record.level === 0" size="small" color="arcoblue" style="margin-left: 8px">根节点</a-tag>
              <a-tag v-else-if="record.reused" size="small" color="green" style="margin-left: 8px">复用</a-tag>
              <a-tag v-else size="small" color="orange" style="margin-left: 8px">创建</a-tag>
            </template>
            <template v-else-if="item.key === 'action'" #cell="{ record }">
              <a-tag :color="getDependencyActionColor(record.action)" size="small">{{ getDependencyActionText(record.action) }}</a-tag>
            </template>
          </a-table-column>
        </template>
      </a-table>
      <a-table
        v-if="result.fields?.length"
        :columns="previewFieldColumns"
        :data="result.fields"
        :pagination="false"
        :row-key="'name'"
        :scroll="{ x: 1040, y: 360 }"
        size="small"
      >
        <template #columns>
          <a-table-column
            v-for="item of previewFieldColumns"
            :key="item.key"
            :data-index="item.key"
            :title="item.title"
            :width="item.width"
          >
            <template v-if="item.key === 'value'" #cell="{ record }">
              {{ formatPreviewValue(record.value) }}
            </template>
            <template v-else-if="item.key === 'label'" #cell="{ record }">
              {{ record.label || '-' }}
            </template>
            <template v-else-if="item.key === 'valid'" #cell="{ record }">
              <a-tag :color="record.valid ? 'green' : 'red'">{{ record.valid ? '正常' : '需配置' }}</a-tag>
            </template>
          </a-table-column>
        </template>
      </a-table>
    </a-space>
    <template #footer>
      <a-space class="data-factory-preview-footer">
        <a-button @click="emitVisible(false)">关闭</a-button>
        <a-button
          v-if="showDebug"
          type="primary"
          :disabled="!result.can_debug_run"
          :loading="debugLoading"
          @click="$emit('debug')"
        >
          调试运行
        </a-button>
      </a-space>
    </template>
  </a-modal>
</template>

<script lang="ts" setup>
  import { useTableColumn } from '@/hooks/table'

  defineProps({
    visible: {
      type: Boolean,
      required: true,
    },
    result: {
      type: Object as () => any,
      default: () => ({}),
    },
    showDebug: {
      type: Boolean,
      default: false,
    },
    debugLoading: {
      type: Boolean,
      default: false,
    },
  })

  const emit = defineEmits(['update:visible', 'debug'])

  const previewFieldColumns = useTableColumn([
    { title: '字段', key: 'name', dataIndex: 'name', width: 150 },
    { title: '字段说明', key: 'label', dataIndex: 'label', width: 180 },
    { title: '生成值', key: 'value', dataIndex: 'value' },
    { title: '状态', key: 'valid', dataIndex: 'valid', width: 110 },
    { title: '结果说明', key: 'message', dataIndex: 'message', width: 260 },
  ])

  const dependencyTreeColumns = useTableColumn([
    { title: '依赖节点', key: 'node', dataIndex: 'node', width: 260 },
    { title: '来源字段', key: 'field', dataIndex: 'field', width: 140 },
    { title: '取值字段', key: 'target_field', dataIndex: 'target_field', width: 100 },
    { title: '策略', key: 'strategy', dataIndex: 'strategy', width: 140 },
    { title: '动作', key: 'action', dataIndex: 'action', width: 100 },
    { title: '说明', key: 'message', dataIndex: 'message' },
  ])

  function emitVisible(value: boolean) {
    emit('update:visible', value)
  }

  function formatPreviewValue(value: any) {
    if (value === null || value === undefined || value === '') {
      return '空'
    }
    if (typeof value === 'object') {
      return JSON.stringify(value)
    }
    return String(value)
  }

  function flattenDependencyTree(tree: any, level = 0, path = '0'): any[] {
    if (!tree) {
      return []
    }
    const current = {
      ...tree,
      level,
      path,
      node: tree.template_name,
      message: tree.message || (tree.reused ? '复用上下文已有数据' : ''),
    }
    const children = (tree.children || []).flatMap((child: any, index: number) =>
      flattenDependencyTree(child, level + 1, `${path}-${index}`)
    )
    return [current, ...children]
  }

  function getDependencyActionText(action: string) {
    const map: Record<string, string> = {
      root: '根节点',
      create: '创建',
      reuse: '复用',
    }
    return map[action] || action || '-'
  }

  function getDependencyActionColor(action: string) {
    const map: Record<string, string> = {
      root: 'arcoblue',
      create: 'orange',
      reuse: 'green',
    }
    return map[action] || 'gray'
  }
</script>

<style scoped>
  .data-factory-preview-content {
    max-height: 70vh;
    overflow-y: auto;
    padding-right: 8px;
    width: 100%;
  }

  .data-factory-preview-footer {
    justify-content: flex-end;
    width: 100%;
  }
</style>
