<template>
  <div>
    <div v-if="!assertionData || assertionData.length === 0" class="empty-placeholder">
      暂无断言结果
    </div>
    <div v-else class="assertion-list">
      <div
        v-for="(item, index) in assertionData"
        :key="index"
        class="assertion-item"
        :class="{ 'assertion-pass': item.status === 1, 'assertion-fail': item.status !== 1 }"
      >
        <div class="assertion-header">
          <span class="assertion-method">{{ item.method }}</span>
          <div class="assertion-actions">
            <span
              class="assertion-status"
              :class="{ 'status-pass': item.status === 1, 'status-fail': item.status !== 1 }"
            >
              {{ item.status === 1 ? '通过' : '失败' }}
            </span>
            <a-tooltip content="复制实际值" position="top" mini>
              <a-button
                class="copy-button"
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
                class="copy-button"
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
        <div class="assertion-details">
          <div class="assertion-row">
            <span class="label">实际值:</span>
            <span class="value">{{ item.actual }}</span>
          </div>
          <div class="assertion-row">
            <span class="label">预期值:</span>
            <span class="value">{{ item.expect }}</span>
          </div>
          <a-tooltip :content="item.ass_msg" position="top" mini>
            <div class="assertion-message">
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
  .empty-placeholder {
    text-align: center;
    color: #999;
    font-size: 14px;
    padding: 20px;
  }

  .assertion-item {
    border-left: 4px solid #e0e0e0;
    padding: 8px 10px;
    margin-bottom: 8px;
    background-color: #fafafa;
    border-radius: 0 4px 4px 0;
    transition: all 0.3s;
  }

  .assertion-item:hover {
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
  }

  .assertion-pass {
    border-left-color: #52c41a;
  }

  .assertion-fail {
    border-left-color: #ff4d4f;
  }

  .assertion-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 6px;
    gap: 8px;
  }

  .assertion-method {
    font-size: 13px;
    font-weight: 500;
    color: #333;
    flex: 1;
    margin-right: 10px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .assertion-status {
    font-size: 12px;
    padding: 2px 8px;
    border-radius: 3px;
    font-weight: 500;
    flex-shrink: 0;
  }

  .assertion-actions {
    display: flex;
    align-items: center;
    gap: 4px;
    flex-shrink: 0;
  }

  .copy-button {
    width: 22px;
    height: 22px;
    padding: 0;
  }

  .status-pass {
    background-color: #f6ffed;
    color: #52c41a;
    border: 1px solid #b7eb8f;
  }

  .status-fail {
    background-color: #fff2f0;
    color: #ff4d4f;
    border: 1px solid #ffccc7;
  }

  .assertion-details {
    font-size: 12px;
  }

  .assertion-row {
    display: flex;
    margin-bottom: 4px;
    line-height: 1.5;
  }

  .label {
    font-weight: 500;
    color: #666;
    width: 60px;
    flex-shrink: 0;
  }

  .value {
    color: #333;
    flex: 1;
    word-break: break-all;
  }

  .assertion-message {
    margin-top: 4px;
    padding: 4px 8px;
    background-color: #f0f2f5;
    border-radius: 3px;
    color: #666;
    font-size: 11px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
</style>
