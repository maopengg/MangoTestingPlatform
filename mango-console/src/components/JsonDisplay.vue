<template>
  <a-space class="m-2">
    <a-space v-if="showJsonpathButton">
      <a-input v-model="jsonpathInput" placeholder="请输入jsonpath语法，如: $.name" />
      <a-button type="dashed" status="warning" @click="jsonpathTest">提取</a-button>
    </a-space>
    <a-space>
      <a-button type="dashed" status="success" @click="copyToClipboard">复制</a-button></a-space
    ></a-space
  >
  <div style="position: relative">
    <vue-json-pretty v-if="isObjectOrArray" :data="parsedData" :show-length="true" />

    <pre v-else-if="isString && !isValidJson">{{ parsedData }}</pre>
    <vue-json-pretty v-else-if="isString && isValidJson" :data="jsonFromString" />

    <span v-else>{{ parsedData }}</span>
  </div>
</template>

<script setup>
  import { computed, ref } from 'vue'
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
   * 尝试解析字符串是否为 JSON
   */
  const isValidJson = computed(() => {
    if (!isString.value) return false
    try {
      JSON.parse(props.data)
      return true
    } catch {
      return false
    }
  })

  /**
   * 如果是 JSON 字符串，解析成对象
   */
  const jsonFromString = computed(() => {
    return isValidJson.value ? JSON.parse(props.data) : {}
  })

  /**
   * 最终渲染的数据（处理 Date 等特殊情况）
   */
  const parsedData = computed(() => {
    if (props.data instanceof Date) {
      return props.data.toISOString()
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

    postCaseDetailedParameterTestJsonpath(jsonpathInput.value.trim(), jsonData)
      .then((res) => {
        Message.success('测试成功，提取的值：【' + res.data.value + '】')
      })
      .catch(console.log)
  }
</script>

<style scoped>
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
