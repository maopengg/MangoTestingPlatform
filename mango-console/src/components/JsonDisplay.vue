<template>
  <a-space class="m-2">
    <a-space v-if="showJsonpathButton">
      <a-input v-model="jsonpathInput" placeholder="请输入jsonpath语法，如: $.name" />
      <a-button type="dashed" status="warning" @click="jsonpathTest">提取</a-button>
    </a-space>
    <a-space>
      <a-button type="dashed" status="success" @click="copyToClipboard">复制</a-button>
      <a-button
        v-if="isObjectOrArray || (isString && isValidJson)"
        type="dashed"
        @click="toggleExpand"
      >
        {{ isExpanded ? '收起' : '展开' }}
      </a-button>
      <a-button v-if="canPreviewJson" type="dashed" @click="openJsonDrawer">查看JSON</a-button>
    </a-space>
  </a-space>
  <div class="json-display-content">
    <vue-json-pretty
      v-if="isObjectOrArray && showComponent"
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
    <div class="json-drawer">
      <div class="json-drawer-toolbar">
        <a-button type="primary" size="small" @click="toggleDrawerExpand">
          {{ drawerExpanded ? '收起' : '展开' }}
        </a-button>
      </div>
      <div class="json-drawer-content">
        <vue-json-pretty
          v-if="showDrawerComponent"
          :data="drawerJsonData"
          :deep="drawerJsonTreeDeep"
          :show-length="true"
          :show-icon="true"
        />
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
  })

  // JSONPath输入框的值
  const jsonpathInput = ref('')
  // 控制展开/收起状态，默认为收起状态
  const isExpanded = ref(false)
  // 控制是否显示组件
  const showComponent = ref(false)
  const jsonDrawerVisible = ref(false)
  const drawerExpanded = ref(false)
  const showDrawerComponent = ref(false)
  const collapsedDeep = 0
  const expandedDeep = Number.MAX_SAFE_INTEGER

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

  const drawerJsonData = computed(() => {
    if (isObjectOrArray.value) {
      return parsedData.value
    }
    if (isString.value && isValidJson.value) {
      return jsonFromString.value
    }
    return parsedData.value
  })

  const jsonTreeDeep = computed(() => {
    return isExpanded.value ? expandedDeep : collapsedDeep
  })

  const drawerJsonTreeDeep = computed(() => {
    return drawerExpanded.value ? expandedDeep : collapsedDeep
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
    drawerExpanded.value = false
    showDrawerComponent.value = false
    await nextTick()
    showDrawerComponent.value = true
  }

  const toggleDrawerExpand = () => {
    drawerExpanded.value = !drawerExpanded.value
  }

  // 监听数据变化，确保组件正确渲染
  watch(
    () => props.data,
    async () => {
      showComponent.value = false
      showDrawerComponent.value = false
      await nextTick()
      showComponent.value = true
      showDrawerComponent.value = jsonDrawerVisible.value
    }
    // 去掉 immediate: true，首次渲染由 onMounted 处理，避免挂载时触发两次重建
  )

  // 组件挂载后确保正确显示
  onMounted(async () => {
    await nextTick()
    showComponent.value = true
  })
</script>

<style scoped lang="less">
  .json-display-content {
    position: relative;
    padding: 8px 10px;
    background: #f7f8fa;
    border: 1px solid #e5e6eb;
    border-radius: 4px;
  }

  .json-display-content,
  .json-drawer-content {
    :deep(.vjs-tree) {
      color: #2b2d30;
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
      background-color: #edf3ff;
    }

    :deep(.vjs-key) {
      color: #871094;
      font-weight: 500;
    }

    :deep(.vjs-colon) {
      color: #6c707e;
    }

    :deep(.vjs-value-string) {
      color: #067d17;
    }

    :deep(.vjs-value-number) {
      color: #1750eb;
    }

    :deep(.vjs-value-boolean) {
      color: #0033b3;
      font-weight: 500;
    }

    :deep(.vjs-value-null),
    :deep(.vjs-value-undefined) {
      color: #9f6700;
      font-style: italic;
    }

    :deep(.vjs-comment) {
      color: #8c8c8c;
    }

    :deep(.vjs-tree-brackets),
    :deep(.vjs-carets) {
      color: #2b2d30;
    }

    :deep(.vjs-tree-brackets:hover),
    :deep(.vjs-carets:hover) {
      color: #0b6fcb;
    }

    :deep(.vjs-indent-unit.has-line) {
      border-left-color: #dcdfe6;
    }
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

  .json-drawer {
    height: 100%;
    display: flex;
    flex-direction: column;
  }

  .json-drawer-toolbar {
    display: flex;
    justify-content: flex-end;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--color-border-2);
  }

  .json-drawer-content {
    flex: 1;
    min-height: 0;
    overflow: auto;
    margin-top: 12px;
    padding: 12px 14px;
    background: #f7f8fa;
    border: 1px solid #e5e6eb;
    border-radius: 4px;
  }
</style>
