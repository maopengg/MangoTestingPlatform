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
  import { json } from '@codemirror/lang-json'
  import { javascript } from '@codemirror/lang-javascript'
  import { syntaxHighlighting } from '@codemirror/language'
  import { EditorState, Prec, RangeSet } from '@codemirror/state'
  import { EditorView, GutterMarker, gutter } from '@codemirror/view'
  import { classHighlighter } from '@lezer/highlight'

  interface Props {
    codeStyle?: CSSProperties // 代码样式
    dark?: boolean // 是否暗黑主题
    modelValue?: string // 用于 v-model 的代码字符串
    indentWithTab?: boolean // 启用 tab 按键
    autoDestroy?: boolean // 组件销毁时是否自动销毁代码编辑器实例
    lineHeight?: number // 行数高度
    placeholder?: string // 占位符文本
    readonly?: boolean // 是否只读
    language?: 'python' | 'json' | 'javascript'
    lineActions?: CodeLineAction[]
  }

  interface CodeLineAction {
    id: string
    line: number
    label: string
    loading?: boolean
    disabled?: boolean
    payload?: unknown
  }

  // 定义组件的 props 和默认值
  const props = withDefaults(defineProps<Props>(), {
    codeStyle: () => ({}),
    dark: true,
    modelValue: '',
    indentWithTab: true,
    autoDestroy: true,
    placeholder: '', // 默认占位符文本
    readonly: false,
    language: 'python',
    lineActions: () => [],
  })

  const emit = defineEmits<{
    (e: 'update:modelValue', value: string): void
    (e: 'line-action', payload: unknown): void
  }>()

  const normalizedLineActions = computed<CodeLineAction[]>(() =>
    Array.isArray(props.lineActions) ? props.lineActions : []
  )

  class LineActionMarker extends GutterMarker {
    elementClass = 'mango-code-line-action-cell'

    constructor(private readonly action: CodeLineAction) {
      super()
    }

    eq(other: LineActionMarker) {
      return (
        this.action.id === other.action.id &&
        this.action.label === other.action.label &&
        this.action.loading === other.action.loading &&
        this.action.disabled === other.action.disabled
      )
    }

    toDOM() {
      const button = document.createElement('button')
      button.type = 'button'
      button.className = 'mango-code-line-action'
      button.title = this.action.label
      button.setAttribute('aria-label', this.action.label)
      button.disabled = Boolean(this.action.disabled || this.action.loading)
      if (this.action.loading) {
        button.classList.add('mango-code-line-action--loading')
      } else {
        const icon = document.createElement('span')
        icon.className = 'mango-code-line-action__play'
        button.appendChild(icon)
      }
      button.addEventListener('mousedown', (event) => {
        event.preventDefault()
        event.stopPropagation()
      })
      button.addEventListener('click', (event) => {
        event.preventDefault()
        event.stopPropagation()
        if (!button.disabled) emit('line-action', this.action.payload)
      })
      return button
    }
  }

  const lineActionExtension = computed(() =>
    gutter({
      class: 'mango-code-line-action-gutter',
      markers: (view) => {
        const markers = normalizedLineActions.value
          .filter((action) => action.line > 0 && action.line <= view.state.doc.lines)
          .map((action) =>
            new LineActionMarker(action).range(view.state.doc.line(action.line).from)
          )
        return RangeSet.of(markers, true)
      },
    })
  )

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
          backgroundColor: 'color-mix(in srgb, var(--m-primary) 52%, transparent)',
        },
        '.cm-content ::selection': {
          backgroundColor: 'color-mix(in srgb, var(--m-primary) 58%, transparent)',
        },
      },
      { dark: props.dark }
    )
  )

  const extensions = computed(() => [
    props.language === 'json' ? json() : props.language === 'javascript' ? javascript() : python(),
    ...(normalizedLineActions.value.length ? [Prec.highest(lineActionExtension.value)] : []),
    editorTheme.value,
    EditorState.readOnly.of(props.readonly),
    EditorView.editable.of(!props.readonly),
    Prec.highest(syntaxHighlighting(classHighlighter)),
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

    .cm-selectionBackground,
    &.cm-focused .cm-selectionBackground {
      background: color-mix(in srgb, var(--m-primary) 52%, transparent);
    }

    .cm-content ::selection {
      background: color-mix(in srgb, var(--m-primary) 58%, transparent);
    }
  }

  :deep(.cm-focused) {
    border: 1px solid var(--m-primary-border);
    box-shadow: var(--m-form-focus-shadow);
  }

  :deep(.tok-keyword),
  :deep(.tok-modifier) {
    color: var(--m-code-keyword);
    font-weight: 600;
  }

  :deep(.tok-string),
  :deep(.tok-string2) {
    color: var(--m-code-string);
  }

  :deep(.tok-number) {
    color: var(--m-code-number);
  }

  :deep(.tok-bool),
  :deep(.tok-null) {
    color: var(--m-code-boolean);
  }

  :deep(.tok-comment) {
    color: var(--m-code-comment);
    font-style: italic;
  }

  :deep(.tok-className),
  :deep(.tok-typeName),
  :deep(.tok-labelName) {
    color: var(--m-code-key);
  }

  :deep(.tok-definition) {
    color: var(--m-code-function);
  }

  :deep(.tok-atom) {
    color: var(--m-code-builtin);
  }

  :deep(.tok-meta),
  :deep(.tok-annotation) {
    color: var(--m-code-decorator);
  }

  :deep(.tok-operator) {
    color: var(--m-code-operator);
  }

  :deep(.tok-punctuation),
  :deep(.tok-bracket) {
    color: var(--m-code-bracket);
  }

  :deep(.mango-code-line-action-gutter) {
    min-width: 28px;
    padding: 0 3px;
    border-right: 0;
    background: var(--m-code-bg);
  }

  :deep(.mango-code-line-action-cell) {
    display: flex;
    min-width: 22px;
    align-items: center;
    justify-content: center;
  }

  :deep(.mango-code-line-action) {
    position: relative;
    display: inline-flex;
    width: 20px;
    height: 20px;
    align-items: center;
    justify-content: center;
    padding: 0;
    border: 1px solid color-mix(in srgb, var(--m-code-function) 68%, transparent);
    border-radius: var(--m-radius-sm);
    color: var(--m-code-function);
    background: color-mix(in srgb, var(--m-code-function) 22%, var(--m-code-bg));
    box-shadow: 0 0 0 1px color-mix(in srgb, var(--m-code-function) 10%, transparent);
    cursor: pointer;
    transition: color 0.16s ease, background-color 0.16s ease, border-color 0.16s ease;
  }

  :deep(.mango-code-line-action:hover:not(:disabled)) {
    border-color: var(--m-code-function);
    color: var(--m-code-bg);
    background: var(--m-code-function);
  }

  :deep(.mango-code-line-action:focus-visible) {
    outline: 2px solid var(--m-code-function);
    outline-offset: 1px;
  }

  :deep(.mango-code-line-action:disabled) {
    cursor: default;
    opacity: 0.72;
  }

  :deep(.mango-code-line-action__play) {
    width: 0;
    height: 0;
    margin-left: 2px;
    border-top: 4px solid transparent;
    border-bottom: 4px solid transparent;
    border-left: 6px solid currentColor;
  }

  :deep(.mango-code-line-action--loading::before) {
    width: 10px;
    height: 10px;
    border: 2px solid color-mix(in srgb, var(--m-code-function) 35%, transparent);
    border-top-color: var(--m-code-function);
    border-radius: 50%;
    animation: mango-code-line-action-spin 0.75s linear infinite;
    content: '';
  }

  @keyframes mango-code-line-action-spin {
    to {
      transform: rotate(360deg);
    }
  }
</style>
