<template>
  <a-cascader
    :model-value="modelValue"
    :options="productOptions"
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
  import { computed, onMounted } from 'vue'
  import { useProject } from '@/store/modules/get-project'

  const props = defineProps({
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
    currentProjectOnly: {
      type: Boolean,
      default: false,
    },
  })

  const emit = defineEmits(['update:modelValue', 'change'])
  const projectInfo = useProject()
  const productOptions = computed(() => {
    if (!props.currentProjectOnly || !projectInfo.selectValue) {
      return projectInfo.projectProduct
    }
    return projectInfo.projectProduct.filter(
      (item: any) => String(item.value) === String(projectInfo.selectValue)
    )
  })

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
