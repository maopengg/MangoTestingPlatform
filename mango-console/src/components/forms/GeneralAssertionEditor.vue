<template>
  <div class="mango-general-assertion-editor">
    <a-space v-if="showActions && !editLocked" class="mango-general-assertion-toolbar">
      <a-button

        size="small"
        :disabled="modelValue.length >= 30"
        @click="add(false)"
        >增加断言</a-button
      >
      <a-button

        size="small"
        :disabled="modelValue.length > 28"
        @click="add(true)"
        >增加或关系组</a-button
      >
    </a-space>
    <KeyValueList
      layout="assertion"
      :data-list="modelValue"
      :field-config="fields"
      :disabled="editLocked"
      :on-delete-item="remove"
      :on-save="save"
      empty-text="暂无通用断言，请增加断言"
    >
      <template #extra="{ item }">
        <div v-if="item?.value?.parameter" class="mango-general-assertion-parameters">
          <div
            v-for="parameter in item.value.parameter"
            :key="parameter.f"
            class="mango-general-assertion-parameter"
          >
            <span class="mango-general-assertion-label">{{ parameter.n }}:</span>
            <a-textarea
              :model-value="
                callbackActual && parameter.f === 'actual'
                  ? '回调字段提取值（自动填充）'
                  : parameter.v
              "
              :disabled="editLocked || (callbackActual && parameter.f === 'actual')"
              :placeholder="parameter.p"
              :required="parameter.d"
              :auto-size="{ minRows: 1, maxRows: 2 }"
              @update:model-value="(value) => (parameter.v = value)"
              @blur="save"
            />
          </div>
        </div>
      </template>
    </KeyValueList>
  </div>
</template>

<script setup lang="ts">
  import { computed } from 'vue'
  import KeyValueList from './KeyValueList.vue'

  const props = withDefaults(
    defineProps<{
      modelValue: any[]
      methods: any[]
      editLocked: boolean
      showActions?: boolean
      callbackActual?: boolean
    }>(),
    { showActions: false, callbackActual: false }
  )
  const emit = defineEmits<{
    (event: 'update:modelValue', value: any[]): void
    (event: 'save'): void
  }>()
  function save() {
    if (props.editLocked) return
    emit('update:modelValue', [...props.modelValue])
    emit('save')
  }
  function remove(index: number) {
    if (props.editLocked) return
    props.modelValue.splice(index, 1)
    save()
  }
  function add(group: boolean) {
    if (props.editLocked || props.modelValue.length + (group ? 2 : 1) > 30) return
    const name = group ? `或关系${Date.now()}` : ''
    const entry = () => ({
      group_name: name,
      group_logic: group ? 'OR' : 'AND',
      method: '',
      value: {},
    })
    props.modelValue.push(entry())
    if (group) props.modelValue.push(entry())
    save()
  }
  function findMethod(items: any[], value: any): any {
    for (const item of items) {
      if (String(item.value) === String(value)) return item
      const child = item.children && findMethod(item.children, value)
      if (child) return child
    }
    return undefined
  }
  function updateMethod(value: any, list: any[], index: number) {
    if (props.editLocked) return
    const method = findMethod(props.methods, value)
    list[index].value = method
      ? {
          value: method.value || '',
          label: method.label || '',
          parameter: (method.parameter || []).map((parameter: any) => ({
            ...parameter,
            v:
              props.callbackActual && parameter.f === 'actual'
                ? '${{__callback_actual__}}'
                : typeof parameter.v === 'object'
                ? JSON.stringify(parameter.v)
                : parameter.v ?? '',
          })),
        }
      : { value: '', label: '', parameter: [] }
    save()
  }
  function updateGroup(value: any, list: any[], index: number) {
    if (props.editLocked) return
    const logic = value === 'OR' ? 'OR' : 'AND'
    const name = list[index].group_name
    list.forEach((item, itemIndex) => {
      if (name ? item.group_name === name : itemIndex === index) item.group_logic = logic
    })
    save()
  }
  const fields = computed(() => [
    {
      field: 'group_logic',
      label: '关系',
      type: 'select',
      options: [
        { label: '且', value: 'AND' },
        { label: '或', value: 'OR' },
      ],
      onChange: (value: any, _item: any, index: number) =>
        updateGroup(value, props.modelValue, index),
    },
    {
      field: 'method',
      label: '断言方法',
      type: 'cascader',
      options: props.methods,
      expandTrigger: 'hover',
      valueKey: 'key',
      onChange: updateMethod,
    },
  ])
</script>

<style scoped>
  .mango-general-assertion-editor {
    min-width: 0;
  }
  .mango-general-assertion-toolbar {
    margin-bottom: 8px;
  }
  .mango-general-assertion-parameters {
    display: flex;
    min-width: 280px;
    flex: 1;
    flex-wrap: wrap;
    gap: 8px;
  }
  .mango-general-assertion-parameter {
    display: flex;
    min-width: 220px;
    flex: 1;
    align-items: center;
    gap: 6px;
  }
  .mango-general-assertion-label {
    flex: none;
    color: var(--m-text-2);
    font-size: 12px;
  }
</style>
