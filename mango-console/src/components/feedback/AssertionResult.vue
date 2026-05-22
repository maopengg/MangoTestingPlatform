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
          <span class="mango-assertion-method">{{ item.method }}</span>
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
            <span class="mango-assertion-value">{{ item.actual }}</span>
          </div>
          <div class="mango-assertion-row">
            <span class="mango-assertion-label">预期值:</span>
            <span class="mango-assertion-value">{{ item.expect }}</span>
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
  }

  interface Props {
    data: AssertionItem[]
  }

  const props = defineProps<Props>()

  const assertionData = computed(() => props.data || [])

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
    flex: 1;
    margin-right: 10px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
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
    word-break: break-all;
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
