<template>
  <a-modal
    modal-class="mango-simple-form-modal"
    v-model:visible="visible"
    title="创建缺陷验证计划"
    :width="560"
    :ok-loading="saving"
    :ok-text="createdPlanId === null ? '确定' : '进入计划'"
    :on-before-ok="save"
    :on-before-cancel="canCancel"
    @cancel="reset"
  >
    
    
    <a-alert v-if="saveError" type="error" class="mango-defect-retest__error"
      >创建失败，输入已保留，请重试。</a-alert
    >
    <a-alert v-if="navigationError" type="warning" class="mango-defect-retest__error"
      >计划 {{ createdPlanId }} 已创建，进入失败，请重试进入。</a-alert
    >
    <a-form auto-label-width class="mango-simple-form" :model="form" layout="horizontal" :disabled="saving || createdPlanId !== null">
      <a-grid class="mango-simple-form-fields" :cols="2" :col-gap="16">
        <a-grid-item class="mango-simple-form-fields" :span="2"
          ><a-form-item class="mango-simple-form-item" label="计划名称" required><a-input v-model="form.name" /></a-form-item
        ></a-grid-item>
        <a-grid-item class="mango-simple-form-fields"
          ><a-form-item class="mango-simple-form-item" label="负责人" required
            ><a-select
              v-model="form.owner"
              :options="users"
              :loading="usersLoading"
              :field-names="fieldNames"
              allow-search /></a-form-item
        ></a-grid-item>
        <a-grid-item class="mango-simple-form-fields"
          ><a-form-item class="mango-simple-form-item" label="测试环境"><a-input v-model="form.environment" /></a-form-item
        ></a-grid-item>
        <a-grid-item class="mango-simple-form-fields"
          ><a-form-item class="mango-simple-form-item" label="构建版本"><a-input v-model="form.build_version" /></a-form-item
        ></a-grid-item>
        <a-grid-item :span="2"
          ><a-alert type="info"
            >将使用缺陷当前关联的用例创建一次新的测试计划，不会修改原计划和历史结果。</a-alert
          ></a-grid-item
        >
      </a-grid>
    </a-form>
  </a-modal>
</template>

<script setup lang="ts">
  import { onActivated, onBeforeUnmount, onDeactivated, reactive, ref, watch } from 'vue'
  import { useRouter } from 'vue-router'
  import { Message } from '@arco-design/web-vue'
  import { createFunctionalDefectRetestPlan } from '@/api/functional-test'
  import type { DefectActionSubject, DefectUserOption } from '../types'

  const props = defineProps<{
    users: DefectUserOption[]
    contextKey: string
    usersLoading?: boolean
    usersError?: boolean
    enumsLoading?: boolean
    enumsError?: boolean
  }>()
  const emit = defineEmits<{ (event: 'retry-users'): void; (event: 'retry-enums'): void }>()
  const router = useRouter()
  const fieldNames = { value: 'key', label: 'title' }
  const visible = ref(false),
    saving = ref(false),
    saveError = ref(false),
    navigationError = ref(false)
  const subjectId = ref<number | null>(null),
    createdPlanId = ref<number | null>(null)
  const form = reactive<{
    name: string
    owner: string | number | null
    environment: string
    build_version: string
  }>({ name: '', owner: null, environment: '', build_version: '' })
  let active = true,
    generation = 0
  const current = (version: number) => active && visible.value && generation === version
  const savingId = ref<number | null>(null)
  const isSaving = (id: number) => saving.value && savingId.value === id
  const canCancel = () => !saving.value
  function reset() {
    ++generation
    visible.value = false
    saveError.value = false
    navigationError.value = false
    subjectId.value = null
    createdPlanId.value = null
    Object.assign(form, { name: '', owner: null, environment: '', build_version: '' })
  }
  function open(record: DefectActionSubject) {
    if (!active || saving.value) return
    reset()
    subjectId.value = record.id
    Object.assign(form, {
      name: `${record.defect_no} 缺陷验证`,
      owner: record.assignee?.id ?? null,
      environment: record.environment ?? '',
      build_version: '',
    })
    visible.value = true
  }
  async function save() {
    if (!active || !visible.value || saving.value || subjectId.value === null) return false
    if (!form.name || form.owner === null) {
      Message.warning('请填写计划名称和负责人')
      return false
    }
    const version = generation
    const payload = {
      id: subjectId.value,
      name: form.name,
      owner: form.owner,
      environment: form.environment,
      build_version: form.build_version,
    }
    savingId.value = subjectId.value
    saving.value = true
    saveError.value = false
    navigationError.value = false
    try {
      if (createdPlanId.value === null) {
        const data: unknown = (await createFunctionalDefectRetestPlan(payload)).data
        if (!current(version)) return false
        const id: unknown =
          data && typeof data === 'object' && !Array.isArray(data) ? Reflect.get(data, 'id') : null
        if (typeof id !== 'number' || !Number.isSafeInteger(id) || id <= 0)
          throw Error('重测计划结果未确认')
        createdPlanId.value = id
        Message.success('重测计划已创建')
      }
      try {
        const failure = await router.push({
          path: '/functional-test/plan/details',
          query: { id: createdPlanId.value },
        })
        if (current(version)) {
          if (failure) navigationError.value = true
          else reset()
        }
      } catch {
        if (current(version)) navigationError.value = true
      }
    } catch {
      if (current(version)) saveError.value = true
    } finally {
      saving.value = false
      savingId.value = null
    }
    return false
  }
  watch(() => props.contextKey, reset, { flush: 'sync' })
  onDeactivated(() => {
    active = false
    reset()
  })
  onActivated(() => {
    active = true
  })
  onBeforeUnmount(() => {
    active = false
    reset()
  })
  defineExpose({ open, isSaving })
</script>

<style scoped>
  .mango-defect-retest__error {
    margin-bottom: var(--m-page-gap);
  }
</style>
