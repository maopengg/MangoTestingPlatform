<template>
  <div class="mango-tip-message" :style="tipStyle">
    <span class="mango-tip-message__icon">{{ icon }}</span>
    <span class="mango-tip-message__text">
      {{ message }}
    </span>
  </div>
</template>

<script setup>
  import { computed } from 'vue'

  const props = defineProps({
    // 提示文字
    message: {
      type: String,
      default: '从响应json中提取，请输入jsonpath语法的表达式，并点击测试按钮进行测试',
    },
    // 图标
    icon: {
      type: String,
      default: 'i',
    },
    // 图标颜色
    iconColor: {
      type: String,
      default: 'var(--m-primary)',
    },
    // 文字颜色
    textColor: {
      type: String,
      default: 'var(--m-text-2)',
    },
    // 背景色
    backgroundColor: {
      type: String,
      default: 'var(--m-surface-soft)',
    },
    // 边框
    border: {
      type: String,
      default: '1px solid var(--m-primary-border)',
    },
    // 字体大小
    fontSize: {
      type: String,
      default: '13px',
    },
    // 内边距
    padding: {
      type: String,
      default: '8px 10px',
    },
    // 下边距
    marginBottom: {
      type: String,
      default: '12px',
    },
    // 边框圆角
    borderRadius: {
      type: String,
      default: 'var(--m-radius-lg)',
    },
    // 图标右边距
    iconMarginRight: {
      type: String,
      default: '8px',
    },
  })

  const tipStyle = computed(() => ({
    '--tip-margin-bottom': props.marginBottom,
    '--tip-padding': props.padding,
    '--tip-bg': props.backgroundColor,
    '--tip-border': props.border,
    '--tip-radius': props.borderRadius,
    '--tip-icon-color': props.iconColor,
    '--tip-icon-margin-right': props.iconMarginRight,
    '--tip-text-color': props.textColor,
    '--tip-font-size': props.fontSize,
  }))
</script>

<style scoped>
  .mango-tip-message {
    display: flex;
    align-items: flex-start;
    margin-bottom: var(--tip-margin-bottom);
    padding: var(--tip-padding);
    color: var(--tip-text-color);
    background: var(--tip-bg);
    border: var(--tip-border);
    border-radius: var(--tip-radius);
  }

  .mango-tip-message__icon {
    display: inline-flex;
    flex: 0 0 18px;
    align-items: center;
    justify-content: center;
    width: 18px;
    height: 18px;
    margin-top: 1px;
    margin-right: var(--tip-icon-margin-right);
    border: 1px solid color-mix(in srgb, var(--tip-icon-color) 34%, transparent);
    border-radius: 50%;
    background: color-mix(in srgb, var(--tip-icon-color) 8%, transparent);
    color: var(--tip-icon-color);
    font-size: 12px;
    font-weight: 700;
    font-style: normal;
    line-height: 16px;
  }

  .mango-tip-message__text {
    min-width: 0;
    color: var(--tip-text-color);
    font-size: var(--tip-font-size);
    line-height: 20px;
  }
</style>
