<template>
  <div>
    <div v-if="!assertionData || assertionData.length === 0" class="mango-empty-placeholder">
      暂无断言结果
    </div>
    <div v-else class="mango-assertion-list">
      <div
        v-for="(item, index) in assertionData"
        :key="index"
        class="mango-assertion-item"
        :class="{ 'mango-assertion-pass': item.status === 1, 'mango-assertion-fail': item.status !== 1 }"
        >
        <div class="mango-assertion-header">
          <div class="mango-assertion-title">
            <span class="mango-assertion-method">{{ item.method }}</span>
            <span v-if="getGroupText(item)" class="mango-assertion-relation">
              {{ getGroupText(item) }}
            </span>
          </div>
          <div class="mango-assertion-actions">
            <span
              class="mango-assertion-status mango-status-badge"
              :class="
                item.status === 1 ? 'mango-status-badge--success' : 'mango-status-badge--danger'
              "
            >
              {{ item.status === 1 ? '通过' : '失败' }}
            </span>
            <a-tooltip content="复制实际值" position="top" mini>
              <a-button
                class="mango-copy-button"
                type="text"
                size="mini"
                @click="copyValue(item.actual, '实际值')"
              >
                <template #icon>
                  <icon-copy />
                </template>
              </a-button>
            </a-tooltip>
            <a-tooltip content="复制期望值" position="top" mini>
              <a-button
                class="mango-copy-button"
                type="text"
                size="mini"
                @click="copyValue(item.expect, '期望值')"
              >
                <template #icon>
                  <icon-copy />
                </template>
              </a-button>
            </a-tooltip>
          </div>
        </div>
        <div class="mango-assertion-details">
          <div class="mango-assertion-row">
            <span class="mango-assertion-label">实际值:</span>
            <a-tooltip :content="formatDisplayValue(item.actual)" position="top" mini>
              <span class="mango-assertion-value">{{ formatDisplayValue(item.actual) }}</span>
            </a-tooltip>
          </div>
          <div class="mango-assertion-row">
            <span class="mango-assertion-label">预期值:</span>
            <a-tooltip :content="formatDisplayValue(item.expect)" position="top" mini>
              <span class="mango-assertion-value">{{ formatDisplayValue(item.expect) }}</span>
            </a-tooltip>
          </div>
          <a-tooltip :content="item.ass_msg" position="top" mini>
            <div class="mango-assertion-message">
              {{ item.ass_msg }}
            </div>
          </a-tooltip>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { computed } from 'vue'
  import { Message } from '@arco-design/web-vue'

  interface AssertionItem {
    actual: unknown
    expect: unknown
    method: string
    ass_msg: string
    group_name?: string | null
    group_logic?: string | null
    group_result?: boolean | null
  }

  interface Props {
    data: AssertionItem[]
  }

  const props = defineProps<Props>()

  const assertionData = computed(() => props.data || [])

  const formatDisplayValue = (value: unknown) => formatCopyValue(value)

  const getGroupText = (item: AssertionItem) => {
    if (!item.group_name && !item.group_logic) return ''
    const logic = String(item.group_logic || 'AND').toUpperCase() === 'OR' ? '或' : '且'
    return item.group_name ? `${logic} / ${item.group_name}` : logic
  }

  const formatCopyValue = (value: unknown) => {
    if (value === undefined || value === null) {
      return ''
    }
    if (typeof value === 'object') {
      try {
        return JSON.stringify(value, null, 2)
      } catch {
        return String(value)
      }
    }
    return String(value)
  }

  const fallbackCopy = (text: string) => {
    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.setAttribute('readonly', 'readonly')
    textarea.style.position = 'fixed'
    textarea.style.left = '-9999px'
    textarea.style.top = '0'
    document.body.appendChild(textarea)
    textarea.select()
    textarea.setSelectionRange(0, textarea.value.length)
    const success = document.execCommand('copy')
    document.body.removeChild(textarea)
    return success
  }

  const copyValue = async (value: unknown, label: string) => {
    const text = formatCopyValue(value)
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text)
      } else if (!fallbackCopy(text)) {
        throw new Error('copy failed')
      }
      Message.success(`复制${label}成功`)
    } catch {
      Message.error(`复制${label}失败`)
    }
  }
</script>

<style scoped>
  .mango-empty-placeholder {
    text-align: center;
    color: var(--m-muted);
    font-size: 14px;
    padding: 20px;
    background: var(--m-surface-soft);
    border: 1px dashed var(--m-border);
    border-radius: var(--m-radius-md);
  }

  .mango-assertion-item {
    border-left: 4px solid var(--m-border-strong);
    padding: 8px 10px;
    margin-bottom: 8px;
    background-color: var(--m-surface);
    border-radius: 0 var(--m-radius-md) var(--m-radius-md) 0;
    transition: all 0.3s;
  }

  .mango-assertion-item:hover {
    box-shadow: var(--m-shadow);
  }

  .mango-assertion-pass {
    border-left-color: var(--m-success);
  }

  .mango-assertion-fail {
    border-left-color: var(--m-danger);
  }

  .mango-assertion-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 6px;
    gap: 8px;
  }

  .mango-assertion-method {
    font-size: 13px;
    font-weight: 500;
    color: var(--m-text);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-assertion-title {
    display: flex;
    align-items: center;
    gap: 6px;
    flex: 1;
    min-width: 0;
    margin-right: 10px;
  }

  .mango-assertion-relation {
    flex-shrink: 0;
    padding: 1px 6px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-sm);
    background: var(--m-surface-soft);
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .mango-assertion-status {
    flex-shrink: 0;
  }

  .mango-assertion-actions {
    display: flex;
    align-items: center;
    gap: 4px;
    flex-shrink: 0;
  }

  .mango-copy-button {
    width: 22px;
    height: 22px;
    padding: 0;
  }

  .mango-assertion-details {
    font-size: 12px;
  }

  .mango-assertion-row {
    display: flex;
    margin-bottom: 4px;
    line-height: 1.5;
  }

  .mango-assertion-label {
    font-weight: 500;
    color: var(--m-muted);
    width: 60px;
    flex-shrink: 0;
  }

  .mango-assertion-value {
    color: var(--m-text-2);
    flex: 1;
    display: -webkit-box;
    overflow: hidden;
    line-height: 18px;
    word-break: break-all;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 3;
  }

  .mango-assertion-message {
    margin-top: 4px;
    padding: 4px 8px;
    background-color: var(--m-surface);
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-sm);
    color: var(--m-muted);
    font-size: 11px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
</style>
