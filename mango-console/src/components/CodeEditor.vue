<template>
  <Codemirror v-model="codeValue" :style="codeStyle" :extensions="extensions" v-bind="$attrs" />
</template>

<script setup lang="ts">
  import { CSSProperties, ref, defineProps, withDefaults, watch, defineEmits } from 'vue'
  import { Codemirror } from 'vue-codemirror'
  import { python } from '@codemirror/lang-python'
  import { oneDark } from '@codemirror/theme-one-dark'

  interface Props {
    codeStyle?: CSSProperties // 代码样式
    dark?: boolean // 是否暗黑主题
    modelValue?: string // 用于 v-model 的代码字符串
    indentWithTab?: boolean // 启用 tab 按键
    autoDestroy?: boolean // 组件销毁时是否自动销毁代码编辑器实例
  }

  // 定义组件的 props 和默认值
  const props = withDefaults(defineProps<Props>(), {
    codeStyle: () => ({}),
    dark: true,
    modelValue: '',
    indentWithTab: true,
    autoDestroy: true,
  })

  // 创建 emit 函数
  const emit = defineEmits<{
    (e: 'update:modelValue', value: string): void
  }>()

  // 根据主题设置扩展
  const extensions = props.dark ? [python(), oneDark] : [python()]

  // 使用 ref 来存储代码值
  const codeValue = ref(props.modelValue)

  // 监听 props.modelValue 的变化
  watch(
    () => props.modelValue,
    (newCode) => {
      codeValue.value = newCode
    }
  )

  // 监听 codeValue 的变化并发出更新事件
  watch(codeValue, (newCode) => {
    emit('update:modelValue', newCode)
  })
</script>

<style lang="less" scoped>
  @themeColor: #1890ff; // 定义主题颜色变量

  :deep(.cm-editor) {
    border-radius: 8px;
    outline: none;
    border: 1px solid transparent;
    .cm-scroller {
      border-radius: 8px;
    }
  }
  :deep(.cm-focused) {
    border: 1px solid fade(@themeColor, 48%);
  }
</style>
