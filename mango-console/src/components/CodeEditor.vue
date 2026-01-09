<template>
  <Codemirror
    ref="cmRef"
    v-model="codeValue"
    :style="codeStyle"
    :extensions="extensions"
    v-bind="$attrs"
    :placeholder="placeholder"
  />
</template>

<script setup lang="ts">
  import { CSSProperties, ref, watch } from 'vue'
  import { Codemirror } from 'vue-codemirror'
  import { python } from '@codemirror/lang-python'
  import { oneDark } from '@codemirror/theme-one-dark'

  interface Props {
    codeStyle?: CSSProperties // 代码样式
    dark?: boolean // 是否暗黑主题
    modelValue?: string // 用于 v-model 的代码字符串
    indentWithTab?: boolean // 启用 tab 按键
    autoDestroy?: boolean // 组件销毁时是否自动销毁代码编辑器实例
    lineHeight?: number // 行数高度
    placeholder?: string // 占位符文本
  }

  // 定义组件的 props 和默认值
  const props = withDefaults(defineProps<Props>(), {
    codeStyle: () => ({}),
    dark: true,
    modelValue: '',
    indentWithTab: true,
    autoDestroy: true,
    placeholder: '', // 默认占位符文本
  })

  const emit = defineEmits<{
    (e: 'update:modelValue', value: string): void
  }>()

  const extensions = props.dark ? [python(), oneDark] : [python()]

  const codeValue = ref(props.modelValue)
  const cmRef = ref<any>(null)

  // 暴露方法给父组件
  defineExpose({
    codemirror: () => cmRef.value?.handle?.view,
    scrollToBottom: () => {
      // 方法1: 通过 handle.view 访问 scrollDOM
      if (cmRef.value?.handle?.view?.scrollDOM) {
        const scrollDOM = cmRef.value.handle.view.scrollDOM
        scrollDOM.scrollTop = scrollDOM.scrollHeight
        return
      }
      // 方法2: 通过 DOM 查询 .cm-scroller
      const editorEl = cmRef.value?.$el || document.querySelector('.cm-editor')
      if (editorEl) {
        const scrollContainer = editorEl.querySelector('.cm-scroller')
        if (scrollContainer) {
          scrollContainer.scrollTop = scrollContainer.scrollHeight
        }
      }
    },
  })

  watch(
    () => props.modelValue,
    (newCode) => {
      codeValue.value = newCode
    }
  )

  watch(codeValue, (newCode) => {
    emit('update:modelValue', newCode)
  })

  // 根据传入的 lineHeight 设置代码编辑器的高度
  const codeStyle = {
    ...props.codeStyle,
    height: `${props.lineHeight}px`,
  }
</script>

<style lang="less" scoped>
  @themeColor: #1890ff;

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
