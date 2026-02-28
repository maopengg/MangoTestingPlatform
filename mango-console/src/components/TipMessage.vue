<template>
  <div
    class="tip-message"
    :style="{
      marginBottom: marginBottom,
      padding: padding,
      backgroundColor: backgroundColor,
      border: border,
      borderRadius: borderRadius,
    }"
  >
    <span :style="{ color: iconColor, marginRight: iconMarginRight }">{{ icon }}</span>
    <span :style="{ color: textColor, fontSize: fontSize }">
      {{ message }}
    </span>
  </div>
</template>

<script setup>
  import { defineProps } from 'vue'

  const props = defineProps({
    // 提示文字
    message: {
      type: String,
      default: '从响应json中提取，请输入jsonpath语法的表达式，并点击测试按钮进行测试',
    },
    // 图标
    icon: {
      type: String,
      default: '🔔',
    },
    // 图标颜色
    iconColor: {
      type: String,
      default: '#1677ff',
    },
    // 文字颜色
    textColor: {
      type: String,
      default: 'rgba(0,0,0,0.88)',
    },
    // 背景色
    backgroundColor: {
      type: String,
      default: '#e6f4ff',
    },
    // 边框
    border: {
      type: String,
      default: '1px solid #91caff',
    },
    // 字体大小
    fontSize: {
      type: String,
      default: '13px',
    },
    // 内边距
    padding: {
      type: String,
      default: '8px 12px',
    },
    // 下边距
    marginBottom: {
      type: String,
      default: '16px',
    },
    // 边框圆角
    borderRadius: {
      type: String,
      default: '6px',
    },
    // 图标右边距
    iconMarginRight: {
      type: String,
      default: '8px',
    },
  })
</script>
