<template>
  <vue-json-pretty v-if="isObjectOrArray" :data="parsedData" :deep="1" :show-length="true" />

  <pre v-else-if="isString && !isValidJson">{{ parsedData }}</pre>
  <vue-json-pretty v-else-if="isString && isValidJson" :data="jsonFromString" :deep="1" />

  <span v-else>{{ parsedData }}</span>
</template>

<script setup>
  import { computed } from 'vue'
  import VueJsonPretty from 'vue-json-pretty'
  import 'vue-json-pretty/lib/styles.css'

  const props = defineProps({
    data: {
      type: [Object, Array, String, Number, Boolean, Date],
      required: true,
    },
  })

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
</script>
