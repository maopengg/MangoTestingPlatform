<template>
  <a-form :model="{}" layout="inline" @keyup.enter="emit('search')">
    <a-form-item v-for="item of items" :key="item.key" :label="item.label">
      <a-input
        v-if="item.type === 'input'"
        v-model="item.value"
        :placeholder="item.placeholder"
        allow-clear
        @blur="emit('search')"
        @clear="emit('search')"
      />
      <ProductModuleSelect
        v-else-if="item.key === 'module'"
        v-model="item.value"
        :project-product-id="projectProductId"
        :placeholder="item.placeholder"
        :auto-clear="false"
        @change="emit('search')"
      />
      <a-select
        v-else-if="item.type === 'select'"
        v-model="item.value"
        :multiple="item.multiple"
        :max-tag-count="item.multiple ? 1 : undefined"
        :field-names="item.key === 'protocol_type' ? undefined : fieldNames"
        :options="optionsFor(item)"
        :placeholder="item.placeholder"
        allow-clear
        allow-search
        value-key="key"
        @change="emit('search')"
      />
    </a-form-item>
  </a-form>
</template>
<script lang="ts" setup>
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import { resolveSearchFilterOptions } from '../search-filter-options'

  const enumKeys: Record<string, string> = {
    project_product__api_client_type: 'api_client',
    method: 'method',
    status: 'task_status',
  }
  const props = defineProps<{
    items: any[]
    userList: any[]
    enumStore: Record<string, any>
    fieldNames: Record<string, string>
    projectProductId?: string | number | null
  }>()
  const emit = defineEmits(['search', 'reset'])
  function optionsFor(item: any) {
    return resolveSearchFilterOptions(item, props.userList, props.enumStore, enumKeys, [
      'update_user',
    ])
  }
</script>
