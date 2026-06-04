<template>
  <a-cascader
    :model-value="modelValue"
    :options="projectInfo.projectProduct"
    :placeholder="placeholder"
    :disabled="disabled"
    :allow-clear="allowClear"
    :allow-search="allowSearch"
    value-key="key"
    @update:model-value="onUpdate"
    @change="onChange"
  />
</template>

<script lang="ts" setup>
  import { onMounted } from 'vue'
  import { useProject } from '@/store/modules/get-project'

  defineProps({
    modelValue: {
      type: [String, Number, Array],
      default: null,
    },
    placeholder: {
      type: String,
      default: '请选择项目/产品',
    },
    disabled: {
      type: Boolean,
      default: false,
    },
    allowClear: {
      type: Boolean,
      default: true,
    },
    allowSearch: {
      type: Boolean,
      default: true,
    },
  })

  const emit = defineEmits(['update:modelValue', 'change'])
  const projectInfo = useProject()

  onMounted(() => {
    projectInfo.projectProductName()
  })

  function onUpdate(value: any) {
    emit('update:modelValue', value)
  }

  function onChange(value: any) {
    emit('change', value)
  }
</script>
