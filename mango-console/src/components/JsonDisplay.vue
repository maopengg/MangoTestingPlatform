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
    </a-space>
  </a-space>
  <div style="position: relative">
    <vue-json-pretty
      v-if="isObjectOrArray && showComponent"
      :key="`json-${isExpanded}-${forceRerender}`"
      :data="parsedData"
      :deep="isExpanded ? undefined : 1"
      :show-length="true"
    />

    <pre v-else-if="isString && !isValidJson">{{ parsedData }}</pre>
    <vue-json-pretty
      v-else-if="isString && isValidJson && showComponent"
      :key="`json-string-${isExpanded}-${forceRerender}`"
      :data="jsonFromString"
      :deep="isExpanded ? undefined : 1"
    />

    <span v-else>{{ parsedData }}</span>
  </div>
</template>

<script setup>
  import { computed, ref, nextTick, onMounted, watch } from 'vue'
  import VueJsonPretty from 'vue-json-pretty'
  import 'vue-json-pretty/lib/styles.css'
  import { Message } from '@arco-design/web-vue'
  import { postCaseDetailedParameterTestJsonpath } from '@/api/apitest/case-detailed-parameter'

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
  // 强制重新渲染的标记
  const forceRerender = ref(0)
  // 控制是否显示组件
  const showComponent = ref(false)

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

  const copyToClipboard = async () => {
    let value = parsedData.value
    if (typeof value === 'object') {
      try {
        value = JSON.stringify(value, null, 2)
      } catch {
        value = String(value)
      }
    } else if (value === undefined || value === null) {
      value = ''
    } else {
      value = String(value)
    }
    try {
      await navigator.clipboard.writeText(value)
      Message.success('复制成功')
    } catch (error) {
      Message.error('复制失败: 需要使用HTTPS协议才能进行复制')
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

    postCaseDetailedParameterTestJsonpath(jsonpathInput.value.trim(), jsonData)
      .then((res) => {
        Message.success('测试成功，提取的值：【' + res.data.value + '】')
      })
      .catch(console.log)
  }

  const toggleExpand = async () => {
    isExpanded.value = !isExpanded.value
    // 强制重新渲染组件
    forceRerender.value++
    await nextTick()
  }

  // 监听数据变化，确保组件正确渲染
  watch(
    () => props.data,
    async () => {
      showComponent.value = false
      await nextTick()
      showComponent.value = true
      forceRerender.value++
    },
    { immediate: true }
  )

  // 监听展开状态变化
  watch(
    () => isExpanded.value,
    async () => {
      await nextTick()
      forceRerender.value++
    }
  )

  // 组件挂载后确保正确显示
  onMounted(async () => {
    await nextTick()
    showComponent.value = true
    // 确保初始状态正确
    forceRerender.value++
  })
</script>

<style scoped lang="less">
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
</style>
