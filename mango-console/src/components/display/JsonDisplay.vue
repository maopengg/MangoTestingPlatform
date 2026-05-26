<template>
  <div class="mango-json-display-toolbar">
    <a-space v-if="showJsonpathButton" class="mango-json-display-toolbar__path">
      <a-input v-model="jsonpathInput" placeholder="请输入jsonpath语法，如: $.name" />
      <a-button type="outline" status="warning" @click="jsonpathTest">提取</a-button>
    </a-space>
    <a-space class="mango-json-display-toolbar__actions">
      <a-button type="outline" status="success" @click="copyToClipboard">复制</a-button>
      <a-button v-if="isLargeJson && !largePreviewEnabled" type="outline" @click="enableLargePreview">
        渲染预览
      </a-button>
      <a-button
        v-if="!isLargeJson && (isObjectOrArray || (isString && isValidJson))"
        type="outline"
        @click="toggleExpand"
      >
        {{ isExpanded ? '收起' : '展开' }}
      </a-button>
      <a-button v-if="canPreviewJson" type="outline" @click="openJsonDrawer">查看JSON</a-button>
    </a-space>
  </div>
  <div class="mango-json-display-content mango-code-panel">
    <div v-if="isLargeJson && !largePreviewEnabled" class="mango-json-large-placeholder">
      <div>
        <strong>JSON 数据较大，已暂停树渲染</strong>
        <span>{{ largeJsonSummary }}</span>
      </div>
      <a-space>
        <a-button size="small" type="primary" @click="openJsonDrawer">查看JSON</a-button>
        <a-button size="small" @click="enableLargePreview">渲染预览</a-button>
      </a-space>
    </div>
    <vue-json-pretty
      v-else-if="isObjectOrArray && showComponent"
      :data="parsedData"
      :deep="jsonTreeDeep"
      :show-length="true"
      :show-icon="true"
    />

    <pre v-else-if="isString && !isValidJson">{{ parsedData }}</pre>
    <vue-json-pretty
      v-else-if="isString && isValidJson && showComponent"
      :data="jsonFromString"
      :deep="jsonTreeDeep"
      :show-length="true"
      :show-icon="true"
    />

    <span v-else>{{ parsedData }}</span>
  </div>
  <a-drawer
    v-model:visible="jsonDrawerVisible"
    title="JSON数据"
    width="50%"
    :footer="false"
    unmount-on-close
  >
    <div class="mango-json-drawer">
      <div class="mango-json-drawer-toolbar mango-section-actions">
        <a-button type="primary" size="small" @click="toggleDrawerExpand">
          {{ drawerExpanded ? '收起' : '展开' }}
        </a-button>
      </div>
      <div class="mango-json-drawer-content mango-code-panel">
        <div v-if="showDrawerComponent" class="mango-json-drawer-render">
          <vue-json-pretty
            :data="drawerJsonData"
            :deep="drawerJsonTreeDeep"
            :show-length="true"
            :show-icon="true"
          />
        </div>
        <div v-else class="mango-json-large-placeholder">
          <strong>JSON 准备中...</strong>
        </div>
      </div>
    </div>
  </a-drawer>
</template>

<script setup>
  import { computed, ref, nextTick, onMounted, watch } from 'vue'
  import VueJsonPretty from 'vue-json-pretty'
  import 'vue-json-pretty/lib/styles.css'
  import { Message } from '@arco-design/web-vue'
  import { postCaseDetailedParameterTestExtractResponseAfter } from '@/api/apitest/case-detailed-parameter'

  const props = defineProps({
    data: {
      type: [Object, Array, String, Number, Boolean, Date],
      required: true,
    },
    jsonpath: {
      type: Boolean,
      default: false,
    },
    defaultExpanded: {
      type: [Boolean, String],
      default: 'auto',
    },
  })

  // JSONPath输入框的值
  const jsonpathInput = ref('')
  // 控制是否完全展开；默认只展示 JSON 第一层级
  const isExpanded = ref(false)
  // 控制是否显示组件
  const showComponent = ref(false)
  const jsonDrawerVisible = ref(false)
  const drawerExpanded = ref(false)
  const showDrawerComponent = ref(false)
  const largePreviewEnabled = ref(false)
  const collapsedDeep = 0
  const previewDeep = 1
  const expandedDeep = Number.MAX_SAFE_INTEGER
  const LARGE_JSON_STRING_LENGTH = 120000
  const LARGE_JSON_NODE_COUNT = 900

  const estimateNodeCount = (value, limit = LARGE_JSON_NODE_COUNT + 1) => {
    if (!value || typeof value !== 'object') {
      return 1
    }
    const stack = [value]
    let count = 0
    while (stack.length) {
      const current = stack.pop()
      count += 1
      if (count > limit) {
        return count
      }
      if (current && typeof current === 'object') {
        const children = Array.isArray(current) ? current : Object.values(current)
        for (const child of children) {
          if (child && typeof child === 'object') {
            stack.push(child)
          } else {
            count += 1
            if (count > limit) {
              return count
            }
          }
        }
      }
    }
    return count
  }

  /**
   * 判断是否是对象或数组
   */
  const isObjectOrArray = computed(() => {
    return typeof props.data === 'object' && props.data !== null && !(props.data instanceof Date)
  })

  /**
   * 判断是否是字符串
   */
  const isString = computed(() => {
    return typeof props.data === 'string'
  })

  /**
   * 检查字符串是否可能包含大数字
   */
  const mightContainLargeNumbers = (str) => {
    // 检查是否可能包含超出安全整数范围的数字
    const largeNumberPattern = /:\s*(\d{16,})/g
    return largeNumberPattern.test(str)
  }

  /**
   * 尝试解析字符串是否为 JSON
   */
  const isValidJson = computed(() => {
    if (!isString.value) return false
    try {
      if (props.data.length > LARGE_JSON_STRING_LENGTH) {
        const text = props.data.trim()
        return (
          (text.startsWith('{') && text.endsWith('}')) ||
          (text.startsWith('[') && text.endsWith(']'))
        )
      }
      // 对于可能包含大数字的 JSON 字符串，我们需要特殊处理
      if (isString.value && props.data.includes(':') && props.data.includes('{')) {
        // 检查是否可能包含大数字
        if (mightContainLargeNumbers(props.data)) {
          return true
        }
      }
      JSON.parse(props.data)
      return true
    } catch {
      return false
    }
  })

  /**
   * 如果是 JSON 字符串，解析成对象，并处理大数字问题
   */
  const jsonFromString = computed(() => {
    if (!isValidJson.value) return {}

    try {
      // 对于可能包含大数字的 JSON，使用特殊处理
      if (mightContainLargeNumbers(props.data)) {
        // 使用正则表达式查找可能的大数字并将其转换为字符串
        let processedData = props.data.replace(/(:\s*)(\d{16,})(\s*[,\}])/g, '$1"$2"$3')
        return JSON.parse(processedData)
      }

      // 使用 reviver 函数处理大数字，将其转换为字符串
      return JSON.parse(props.data, (key, value) => {
        // 检查是否为可能超出安全范围的数字
        if (typeof value === 'number' && !Number.isSafeInteger(value)) {
          return value.toString()
        }
        return value
      })
    } catch (e) {
      console.error('JSON解析错误:', e)
      return {}
    }
  })

  /**
   * 最终渲染的数据（处理 Date 等特殊情况）
   */
  const parsedData = computed(() => {
    if (props.data instanceof Date) {
      return props.data.toISOString()
    }
    // 如果是数字且超出安全范围，转换为字符串
    if (typeof props.data === 'number' && !Number.isSafeInteger(props.data)) {
      return props.data.toString()
    }
    return props.data
  })

  /**
   * 判断是否显示JSONPath按钮
   */
  const showJsonpathButton = computed(() => {
    return props.jsonpath && (isObjectOrArray.value || (isString.value && isValidJson.value))
  })

  const canPreviewJson = computed(() => {
    return isObjectOrArray.value || (isString.value && isValidJson.value)
  })

  const estimatedJsonSize = computed(() => {
    if (isString.value) {
      return props.data.length
    }
    if (isObjectOrArray.value) {
      return estimateNodeCount(props.data)
    }
    return 0
  })

  const isLargeJson = computed(() => {
    if (isString.value) {
      return props.data.length > LARGE_JSON_STRING_LENGTH
    }
    if (isObjectOrArray.value) {
      return estimatedJsonSize.value > LARGE_JSON_NODE_COUNT
    }
    return false
  })

  const largeJsonSummary = computed(() => {
    if (isString.value) {
      return `约 ${Math.ceil(props.data.length / 1024)} KB，点击后再渲染树结构。`
    }
    if (Array.isArray(props.data)) {
      return `${props.data.length} 个数组项，点击后再渲染树结构。`
    }
    if (isObjectOrArray.value) {
      return `${Object.keys(props.data).length} 个顶层字段，点击后再渲染树结构。`
    }
    return '点击后再渲染树结构。'
  })

  const drawerJsonData = computed(() => {
    if (isObjectOrArray.value) {
      return parsedData.value
    }
    if (isString.value && isValidJson.value) {
      return jsonFromString.value
    }
    return parsedData.value
  })

  const shouldExpandFullyByDefault = computed(() => {
    return props.defaultExpanded === true || props.defaultExpanded === 'true'
  })

  const defaultJsonTreeDeep = computed(() => {
    if (props.defaultExpanded === false || props.defaultExpanded === 'false') {
      return collapsedDeep
    }
    return previewDeep
  })

  const jsonTreeDeep = computed(() => {
    return isExpanded.value ? expandedDeep : defaultJsonTreeDeep.value
  })

  const drawerJsonTreeDeep = computed(() => {
    return drawerExpanded.value ? expandedDeep : defaultJsonTreeDeep.value
  })

  const formatCopyValue = (value) => {
    if (typeof value === 'object' && value !== null) {
      try {
        return JSON.stringify(value, null, 2)
      } catch {
        return String(value)
      }
    }
    if (value === undefined || value === null) {
      return ''
    }
    return String(value)
  }

  const fallbackCopy = (text) => {
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

  const copyToClipboard = async () => {
    const value = formatCopyValue(parsedData.value)
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(value)
      } else if (!fallbackCopy(value)) {
        throw new Error('copy failed')
      }
      Message.success('复制成功')
    } catch {
      Message.error('复制失败')
    }
  }

  const jsonpathTest = () => {
    if (!jsonpathInput.value.trim()) {
      Message.error('请输入JSONPath语法！')
      return
    }

    const jsonData = isObjectOrArray.value ? props.data : jsonFromString.value
    if (jsonData === null || (typeof jsonData !== 'object' && !Array.isArray(jsonData))) {
      Message.error('响应JSON是空或者不是JSON格式，无法进行测试！')
      return
    }

    postCaseDetailedParameterTestExtractResponseAfter(
      'jsonpath',
      jsonpathInput.value.trim(),
      jsonData
    )
      .then((res) => {
        Message.success('测试成功，提取的值：【' + res.data.value + '】')
      })
      .catch(console.log)
  }

  const toggleExpand = () => {
    isExpanded.value = !isExpanded.value
  }

  const openJsonDrawer = async () => {
    jsonDrawerVisible.value = true
    drawerExpanded.value = shouldExpandFullyByDefault.value
    showDrawerComponent.value = false
    window.setTimeout(() => {
      showDrawerComponent.value = true
    }, 80)
  }

  const toggleDrawerExpand = () => {
    drawerExpanded.value = !drawerExpanded.value
  }

  const enableLargePreview = () => {
    largePreviewEnabled.value = true
    showComponent.value = false
    window.setTimeout(() => {
      showComponent.value = true
    }, 80)
  }

  // 监听数据变化，确保组件正确渲染
  watch(
    () => props.data,
    async () => {
      showComponent.value = false
      showDrawerComponent.value = false
      largePreviewEnabled.value = false
      isExpanded.value = shouldExpandFullyByDefault.value
      drawerExpanded.value = shouldExpandFullyByDefault.value
      await nextTick()
      showComponent.value = !isLargeJson.value
      showDrawerComponent.value = jsonDrawerVisible.value
    }
    // 去掉 immediate: true，首次渲染由 onMounted 处理，避免挂载时触发两次重建
  )

  // 组件挂载后确保正确显示
  onMounted(async () => {
    isExpanded.value = shouldExpandFullyByDefault.value
    drawerExpanded.value = shouldExpandFullyByDefault.value
    await nextTick()
    showComponent.value = !isLargeJson.value
  })
</script>

<style scoped lang="less">
  .mango-json-display-toolbar {
    display: flex;
    flex-wrap: wrap;
    gap: 8px 12px;
    align-items: center;
    justify-content: space-between;
    margin: 8px 0;
  }

  .mango-json-display-toolbar__path {
    flex: 1;
    min-width: 260px;
  }

  .mango-json-display-toolbar__actions {
    flex: none;
  }

  .mango-json-display-content {
    position: relative;
    padding: 8px 10px;
    overflow: auto;
  }

  .mango-json-display-content pre,
  .mango-json-display-content span {
    margin: 0;
    color: var(--m-code-text);
    font-family: 'JetBrains Mono', 'Cascadia Code', Consolas, Monaco, Menlo, monospace;
    font-size: 13px;
    line-height: 21px;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .mango-json-display-content,
  .mango-json-drawer-content {
    :deep(.vjs-tree) {
      color: var(--m-code-text);
      font-size: 13px;
      line-height: 21px;
      font-family: 'JetBrains Mono', 'Cascadia Code', Consolas, Monaco, Menlo, monospace;
    }

    :deep(.vjs-tree-node) {
      border-radius: 4px;
      transition: background-color 0.15s ease;
    }

    :deep(.vjs-tree-node:hover),
    :deep(.vjs-tree-node.is-highlight) {
      background-color: var(--m-code-line-hover);
    }

    :deep(.vjs-key) {
      color: var(--m-code-key);
      font-weight: 500;
    }

    :deep(.vjs-colon) {
      color: var(--m-muted);
    }

    :deep(.vjs-value-string) {
      color: var(--m-code-string);
    }

    :deep(.vjs-value-number) {
      color: var(--m-code-number);
    }

    :deep(.vjs-value-boolean) {
      color: var(--m-code-boolean);
      font-weight: 500;
    }

    :deep(.vjs-value-null),
    :deep(.vjs-value-undefined) {
      color: var(--m-code-null);
      font-style: italic;
    }

    :deep(.vjs-comment) {
      color: var(--m-muted);
    }

    :deep(.vjs-tree-brackets),
    :deep(.vjs-carets) {
      color: var(--m-code-text);
    }

    :deep(.vjs-tree-brackets:hover),
    :deep(.vjs-carets:hover) {
      color: var(--m-primary);
    }

    :deep(.vjs-indent-unit.has-line) {
      border-left-color: var(--m-code-border);
    }
  }

  .mango-json-large-placeholder {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    min-height: 96px;
    padding: 12px;
    border: 1px dashed var(--m-code-border);
    border-radius: var(--m-radius-md);
    background: color-mix(in srgb, var(--m-code-bg) 82%, var(--m-surface));

    strong,
    span {
      display: block;
    }

    strong {
      color: var(--m-code-key);
      font-size: 13px;
      line-height: 20px;
    }

    span {
      margin-top: 4px;
      color: var(--m-code-text);
      font-size: 12px;
      line-height: 18px;
    }
  }

  .mango-json-drawer-render {
    min-width: 0;
  }

  .copy-button {
    position: absolute;
    top: 0;
    right: 0;
    z-index: 10;
    font-size: 12px;
    padding: 2px 8px;
    margin: 4px;
  }

  .jsonpath-container {
    position: absolute;
    top: 0;
    right: 100px;
    z-index: 10;
    display: flex;
    align-items: center;
  }

  .mango-json-drawer {
    height: 100%;
    display: flex;
    flex-direction: column;
  }

  .mango-json-drawer-toolbar {
    display: flex;
    justify-content: flex-end;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--m-border);
  }

  .mango-json-drawer-content {
    flex: 1;
    min-height: 0;
    overflow: auto;
    margin-top: 12px;
    padding: 12px 14px;
  }
</style>
