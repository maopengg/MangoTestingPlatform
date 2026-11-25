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
      <MangoSearchSelect
        v-else-if="item.type === 'select'"
        v-model="item.value"
        :field-names="fieldNames"
        :options="optionsFor(item)"
        :loading="
          (item.key === 'execution_configuration' && configurationOptionsLoading) ||
          (['case_people', 'update_user'].includes(item.key) && usersLoading)
        "
        :placeholder="item.placeholder"
        :multiple="item.multiple || item.key === 'scenario_tags'"
        :max-tag-count="item.multiple || item.key === 'scenario_tags' ? 1 : undefined"
        allow-clear
        allow-search
        value-key="key"
        @popup-visible-change="
          item.key === 'execution_configuration' && loadConfigurationSearchOptions($event)
        "
        @change="emit('search')"
      />
    </a-form-item>
  </a-form>
</template>

<script lang="ts" setup>
  import MangoSearchSelect from '@/components/business/MangoSearchSelect.vue'
  import { ref } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { resolveApiCaseSearchOptions } from '../api-case-search-filter-options'
  import type { FormItem } from '@/types/components'
  import type { UserOption } from '../types'
  import type { useEnum } from '@/store/modules/get-enum'

  const props = defineProps<{
    items: FormItem[]
    userList: UserOption[]
    usersLoading?: boolean
    enumStore: ReturnType<typeof useEnum>
    fieldNames: Record<string, string>
  }>()
  const emit = defineEmits(['search', 'reset'])
  const configurationOptionsLoading = ref(false)
  async function loadConfigurationSearchOptions(visible: boolean) {
    if (
      !visible ||
      configurationOptionsLoading.value ||
      props.enumStore.api_case_configuration_filter?.length
    )
      return
    configurationOptionsLoading.value = true
    try {
      await props.enumStore.getEnum(true)
      if (!props.enumStore.api_case_configuration_filter?.length) {
        Message.warning('执行配置选项尚未加载，请确认后端已更新后重新打开下拉框')
      }
    } catch {
      Message.error('执行配置选项加载失败，请重新打开下拉框重试')
    } finally {
      configurationOptionsLoading.value = false
    }
  }
  function optionsFor(item: FormItem) {
    return resolveApiCaseSearchOptions(item, props.userList, props.enumStore)
  }
</script>
