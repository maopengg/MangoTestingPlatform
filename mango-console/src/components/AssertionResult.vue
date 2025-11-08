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
        :class="{ 'assertion-pass': isPass(item), 'assertion-fail': !isPass(item) }"
      >
        <div class="assertion-header">
          <span class="assertion-method">{{ item.method }}</span>
          <span
            class="assertion-status"
            :class="{ 'status-pass': isPass(item), 'status-fail': !isPass(item) }"
          >
            {{ isPass(item) ? '通过' : '失败' }}
          </span>
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
          <div class="assertion-message">
            {{ item.ass_msg }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { defineProps, computed } from 'vue'

  interface AssertionItem {
    actual: string
    expect: string
    method: string
    ass_msg: string
  }

  interface Props {
    data: AssertionItem[]
  }

  const props = defineProps<Props>()

  const assertionData = computed(() => props.data || [])

  // 判断断言是否通过
  const isPass = (item: AssertionItem) => {
    // 如果有明确的实际值和预期值，直接比较
    if (item.actual !== undefined && item.expect !== undefined) {
      // 检查ass_msg中是否包含失败或错误关键字
      if (item.ass_msg && (item.ass_msg.includes('失败') || item.ass_msg.includes('错误'))) {
        return false
      }
      return item.actual === item.expect
    }

    // 如果没有明确的值比较，检查ass_msg
    if (item.ass_msg) {
      return !(item.ass_msg.includes('失败') || item.ass_msg.includes('错误'))
    }

    // 默认返回true
    return true
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
  }
</style>
