<template>
  <Codemirror
    ref="cmRef"
    v-model="codeValue"
    :class="editorClass"
    :style="codeStyle"
    :extensions="extensions"
    v-bind="$attrs"
    :placeholder="placeholder"
  />
</template>

<script setup lang="ts">
  import { CSSProperties, computed, ref, watch } from 'vue'
  import { Codemirror } from 'vue-codemirror'
  import { python } from '@codemirror/lang-python'
  import { HighlightStyle, syntaxHighlighting } from '@codemirror/language'
  import { Prec } from '@codemirror/state'
  import { EditorView } from '@codemirror/view'
  import { tags } from '@lezer/highlight'

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

  const pythonHighlightStyle = HighlightStyle.define([
    { tag: tags.keyword, color: 'var(--m-code-keyword)', fontWeight: '600' },
    {
      tag: [tags.definitionKeyword, tags.modifier],
      color: 'var(--m-code-keyword)',
      fontWeight: '600',
    },
    { tag: [tags.name, tags.variableName], color: 'var(--m-code-text)' },
    { tag: tags.definition(tags.variableName), color: 'var(--m-code-function)' },
    {
      tag: [tags.function(tags.variableName), tags.function(tags.propertyName)],
      color: 'var(--m-code-function)',
    },
    { tag: [tags.className, tags.typeName], color: 'var(--m-code-key)' },
    { tag: [tags.string, tags.special(tags.string)], color: 'var(--m-code-string)' },
    { tag: tags.number, color: 'var(--m-code-number)' },
    { tag: [tags.bool, tags.null], color: 'var(--m-code-boolean)' },
    { tag: tags.comment, color: 'var(--m-code-comment)', fontStyle: 'italic' },
    { tag: tags.atom, color: 'var(--m-code-builtin)' },
    { tag: [tags.meta, tags.documentMeta, tags.annotation], color: 'var(--m-code-decorator)' },
    { tag: tags.labelName, color: 'var(--m-code-key)' },
    {
      tag: [tags.operator, tags.arithmeticOperator, tags.compareOperator, tags.logicOperator],
      color: 'var(--m-code-operator)',
    },
    { tag: [tags.punctuation, tags.bracket], color: 'var(--m-code-bracket)' },
  ])

  const editorClass = computed(() => ({
    'code-editor': true,
    'code-editor--dark': props.dark,
  }))

  const editorTheme = computed(() =>
    EditorView.theme(
      {
        '&': {
          color: 'var(--m-code-text)',
          backgroundColor: 'var(--m-code-bg)',
          borderColor: 'var(--m-code-border)',
        },
        '.cm-content': {
          color: 'var(--m-code-text)',
          caretColor: 'var(--m-code-text)',
        },
        '.cm-line': {
          color: 'var(--m-code-text)',
        },
        '.cm-gutters': {
          color: 'var(--m-muted)',
          backgroundColor: 'var(--m-code-bg)',
          borderRightColor: 'var(--m-code-border)',
        },
        '.cm-activeLine, .cm-activeLineGutter': {
          backgroundColor: 'var(--m-code-line-hover)',
        },
        '.cm-selectionBackground, &.cm-focused .cm-selectionBackground': {
          backgroundColor: 'color-mix(in srgb, var(--m-primary) 22%, transparent)',
        },
      },
      { dark: props.dark }
    )
  )

  const extensions = computed(() => [
    python(),
    editorTheme.value,
    Prec.highest(syntaxHighlighting(pythonHighlightStyle, { fallback: false })),
  ])

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
  const codeStyle = computed(() => ({
    ...props.codeStyle,
    ...(props.lineHeight ? { height: `${props.lineHeight}px` } : {}),
  }))
</script>

<style lang="less" scoped>
  :deep(.cm-editor) {
    color: var(--m-code-text);
    background: var(--m-code-bg);
    border-radius: var(--m-radius-lg);
    outline: none;
    border: 1px solid var(--m-code-border);

    .cm-scroller {
      border-radius: var(--m-radius-lg);
      background: var(--m-code-bg);
    }

    .cm-content {
      color: var(--m-code-text);
      caret-color: var(--m-code-text);
    }

    .cm-gutters {
      color: var(--m-muted);
      background: var(--m-code-bg);
      border-right-color: var(--m-code-border);
    }

    .cm-activeLine,
    .cm-activeLineGutter {
      background: var(--m-code-line-hover);
    }
  }

  :deep(.cm-focused) {
    border: 1px solid var(--m-primary-border);
    box-shadow: var(--m-form-focus-shadow);
  }
</style>
