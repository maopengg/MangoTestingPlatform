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
      <a-select
        v-else-if="selectOptions(item)"
        v-model="item.value"
        :field-names="fieldNames"
        :options="selectOptions(item)"
        :placeholder="item.placeholder"
        :multiple="item.multiple || item.key === 'test_envs'"
        :max-tag-count="item.multiple || item.key === 'test_envs' ? 1 : undefined"
        allow-clear
        allow-search
        value-key="key"
        @change="emit('search')"
      />
    </a-form-item>
  </a-form>
</template>

<script lang="ts" setup>
  const props = defineProps<{
    items: any[]
    fieldNames: Record<string, string>
    enumStore: Record<string, any>
    userList: any[]
    environmentOptions?: any[]
  }>()
  const emit = defineEmits(['search', 'reset'])

  function selectOptions(item: { key: string; optionItems?: any[] }) {
    const options: Record<string, any[]> = {
      type: props.enumStore.api_public_type,
      test_envs: props.environmentOptions || [],
      test_env: props.enumStore.environment_type,
      auth_type: props.enumStore.api_auth_type,
      refresh_mode: props.enumStore.api_auth_refresh_mode,
      last_refresh_status: props.enumStore.api_auth_refresh_status,
      project_product__api_client_type: props.enumStore.api_client,
      update_user: props.userList,
    }
    return options[item.key] ?? item.optionItems
  }
</script>
