<template>
  <a-cascader
    :model-value="modelValue"
    :field-names="fieldNames"
    :options="cascaderOptions"
    :placeholder="placeholder"
    :disabled="disabled"
    :allow-clear="allowClear"
    :allow-search="allowSearch"
    :loading="loading"
    value-key="key"
    @update:model-value="onUpdate"
    @change="onChange"
  />
</template>

<script lang="ts" setup>
  import { computed, onMounted, ref, watch } from 'vue'
  import { fieldNames } from '@/setting'
  import { getUserModuleName } from '@/api/system/module'

  type ModuleOption = {
    key: string | number
    title: string
    superior_module_1?: string | null
    superior_module_2?: string | null
  }

  type ModuleCascaderOption = {
    key: string | number
    title: string
    children?: ModuleCascaderOption[]
  }

  const props = defineProps({
    modelValue: {
      type: [String, Number],
      default: null,
    },
    projectProductId: {
      type: [String, Number, Array],
      default: null,
    },
    placeholder: {
      type: String,
      default: '请选择模块',
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
    autoClear: {
      type: Boolean,
      default: true,
    },
  })

  const emit = defineEmits(['update:modelValue', 'change', 'loaded'])
  const options = ref<ModuleOption[]>([])
  const loading = ref(false)
  const cascaderOptions = computed(() => buildModuleTree(options.value))

  onMounted(() => {
    loadOptions()
  })

  watch(
    () => props.projectProductId,
    (value, oldValue) => {
      if (value === oldValue) {
        return
      }
      if (props.autoClear) {
        emit('update:modelValue', '')
      }
      loadOptions()
    }
  )

  function getLeafValue(value: any) {
    if (Array.isArray(value)) {
      return value[value.length - 1] ?? null
    }
    return value ?? null
  }

  function normalizeName(value: string | null | undefined) {
    return value?.trim() || ''
  }

  function getGroupOption(
    nodes: ModuleCascaderOption[],
    title: string,
    path: string
  ): ModuleCascaderOption {
    const key = `module_group:${path}`
    let option = nodes.find((item) => item.key === key)
    if (!option) {
      option = {
        key,
        title,
        children: [],
      }
      nodes.push(option)
    }
    return option
  }

  function buildModuleTree(list: ModuleOption[]) {
    const tree: ModuleCascaderOption[] = []
    list.forEach((item) => {
      const level1 = normalizeName(item.superior_module_1)
      const level2 = normalizeName(item.superior_module_2)
      const level3 = normalizeName(item.title)
      if (!level3) {
        return
      }

      const leaf = {
        key: item.key,
        title: level3,
      }

      if (!level1 && !level2) {
        tree.push(leaf)
        return
      }

      if (level1 && level2) {
        const first = getGroupOption(tree, level1, level1)
        const second = getGroupOption(first.children || [], level2, `${level1}/${level2}`)
        second.children?.push(leaf)
        return
      }

      const groupTitle = level1 || level2
      const group = getGroupOption(tree, groupTitle, groupTitle)
      group.children?.push(leaf)
    })
    return tree
  }

  function loadOptions() {
    loading.value = true
    return getUserModuleName(getLeafValue(props.projectProductId))
      .then((res) => {
        options.value = Array.isArray(res.data) ? res.data : []
        emit('loaded', cascaderOptions.value)
      })
      .catch(console.log)
      .finally(() => {
        loading.value = false
      })
  }

  function onUpdate(value: any) {
    emit('update:modelValue', value)
  }

  function onChange(value: any) {
    emit('change', value)
  }
</script>
