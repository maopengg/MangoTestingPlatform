<template>
  <section class="mango-section-card">
    <div class="mango-section-title mango-requirement-tasks__heading">
      <span
        >子任务 <small>{{ completedCount }}/{{ persistedCount }}</small></span
      >
      <a-button size="small" type="primary" :disabled="!canEdit || loading" @click="addTask"
        >新增子任务</a-button
      >
    </div>
    
    <a-table
      :data="rows"
      :columns="taskColumns"
      :pagination="false"
      :loading="!parentLoading && loading"
      :scroll="{ x: 1480 }"
      row-key="key"
    >
      <template #task_sort="{ record }"
        ><a-input-number
          v-model="record.form.sort_order"
          :disabled="isBlocked(record)"
          size="mini"
          :min="0"
          @change="saveTask(record)"
      /></template>
      <template #task_name="{ record }"
        ><a-input
          v-model="record.form.name"
          :disabled="isBlocked(record)"
          size="small"
          :max-length="256"
          @blur="saveTask(record)"
        /><span v-if="record.error" class="mango-requirement-tasks__error"
          >保存失败，草稿已保留</span
        ></template
      >
      <template #task_type="{ record }"
        ><a-select
          v-model="record.form.task_type"
          :disabled="isBlocked(record)"
          size="small"
          :options="taskTypeOptions"
          :field-names="fieldNames"
          @change="saveTask(record)"
      /></template>
      <template #task_status="{ record }"
        ><a-select
          v-model="record.form.status"
          :disabled="isBlocked(record)"
          size="small"
          :options="taskStatusOptions"
          :field-names="fieldNames"
          @change="saveTask(record)"
      /></template>
      <template #task_owner="{ record }"
        ><a-select
          v-model="record.form.owner"
          :disabled="isBlocked(record)"
          size="small"
          :options="ownerOptions(record)"
          :loading="usersLoading"
          :field-names="fieldNames"
          allow-search
          allow-clear
          @change="saveTask(record)"
      /></template>
      <template #task_start="{ record }"
        ><a-date-picker
          v-model="record.form.planned_start_date"
          :disabled="isBlocked(record)"
          size="small"
          value-format="YYYY-MM-DD"
          @change="saveTask(record)"
      /></template>
      <template #task_end="{ record }"
        ><a-date-picker
          v-model="record.form.planned_end_date"
          :disabled="isBlocked(record)"
          size="small"
          value-format="YYYY-MM-DD"
          @change="saveTask(record)"
      /></template>
      <template #task_estimated="{ record }"
        ><a-input-number
          v-model="record.form.estimated_person_days"
          :disabled="isBlocked(record)"
          size="small"
          :min="0"
          :precision="2"
          @change="saveTask(record)"
      /></template>
      <template #task_actual="{ record }"
        ><a-input-number
          v-model="record.form.actual_person_days"
          :disabled="isBlocked(record)"
          size="small"
          :min="0"
          :precision="2"
          @change="saveTask(record)"
      /></template>
      <template #task_self_test="{ record }"
        ><a-select
          v-model="record.form.self_test_status"
          :disabled="isBlocked(record)"
          size="small"
          :options="selfTestOptions"
          :field-names="fieldNames"
          @change="saveTask(record)"
      /></template>
      <template #task_operations="{ record }"
        ><MangoTableActions
          :actions="[
            {
              label: record.error ? '重试' : '保存中',
              hidden: !record.error && !workers.has(record.key),
              loading: workers.has(record.key),
              disabled: isBlocked(record),
              onClick: () => saveTask(record),
            },
            {
              label: '删除',
              danger: true,
              loading: deletingKeys.has(record.key),
              disabled: isBlocked(record) || workers.has(record.key),
              onClick: () => removeTask(record),
            },
          ]"
      /></template>
    </a-table>
  </section>
</template>
<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import {
    computed,
    onActivated,
    onBeforeUnmount,
    onDeactivated,
    onMounted,
    reactive,
    ref,
    watch,
  } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import {
    getFunctionalRequirementTasks,
    postFunctionalRequirementTask,
    putFunctionalRequirementTask,
    deleteFunctionalRequirementTask,
  } from '@/api/functional-test'
  import { taskColumns, taskTypeOptions, taskStatusOptions, selfTestOptions } from '../config'
  import {
    createTaskForm,
    parseRequirementTask,
    positiveTaskId,
    sameTaskForm,
    taskPayload,
  } from '../task-form'
  import type { RequirementTaskForm, RequirementTaskRow } from '../types'

  const props = defineProps<{
    contextKey: string
    requirementId: number | null
    enabled: boolean
    blocked?: boolean
    users: Array<{ key: number | string; title: string }>
    usersLoading?: boolean
    parentLoading?: boolean
  }>()
  const rows = ref<RequirementTaskRow[]>([])
  const loading = ref(false),
    readError = ref(false)
  const workers = reactive(new Map<string, { generation: number; promise: Promise<boolean> }>())
  const deletingKeys = reactive(new Set<string>())
  const dialogs = reactive(new Map<string, ReturnType<typeof Modal.warning>>())
  const queued = new Map<string, RequirementTaskForm>()
  const fieldNames = { value: 'key', label: 'title' }
  let active = true,
    mounted = false,
    readSequence = 0,
    draftSequence = 0
  const generation = ref(0)
  const needsLoad = ref(false)
  const canEdit = computed(
    () =>
      props.enabled &&
      !props.blocked &&
      positiveTaskId(props.requirementId) &&
      ![...workers.values()].some((item) => item.generation !== generation.value) &&
      !deletingKeys.size
  )
  const current = (version: number) =>
    active && props.enabled && positiveTaskId(props.requirementId) && generation.value === version
  const owned = (row: RequirementTaskRow) => active && canEdit.value && rows.value.includes(row)
  const isSaving = () => workers.size > 0 || deletingKeys.size > 0
  const isBlocked = (row: RequirementTaskRow) =>
    !owned(row) || loading.value || dialogs.has(row.key)
  const persistedCount = computed(() => rows.value.filter((row) => row.confirmed !== null).length)
  const completedCount = computed(
    () => rows.value.filter((row) => row.confirmed?.status === 2).length
  )
  function ownerOptions(row: RequirementTaskRow) {
    const saved = row.confirmed
    return saved?.owner && !props.users.some((item) => Number(item.key) === saved.owner)
      ? [...props.users, { key: saved.owner, title: saved.owner_name || `ID ${saved.owner}` }]
      : props.users
  }
  function invalidateRead() {
    ++readSequence
    loading.value = false
  }
  function reset() {
    ++generation.value
    invalidateRead()
    rows.value = []
    queued.clear()
    readError.value = false
    needsLoad.value = false
    for (const dialog of dialogs.values()) dialog.close()
    dialogs.clear()
  }
  async function loadTasks() {
    if (!active || !props.enabled || !positiveTaskId(props.requirementId)) return false
    if (isSaving()) {
      needsLoad.value = true
      return false
    }
    if (rows.value.some((row) => row.confirmed === null || !sameTaskForm(row.form, row.confirmed)))
      return false
    const target = props.requirementId,
      version = generation.value,
      sequence = ++readSequence
    const valid = () => current(version) && readSequence === sequence
    needsLoad.value = false
    loading.value = true
    readError.value = false
    try {
      const data: unknown = (await getFunctionalRequirementTasks(target)).data
      if (!valid()) return false
      if (!Array.isArray(data)) throw Error('子任务列表格式错误')
      const parsed = data.map((item) => parseRequirementTask(item, target))
      if (new Set(parsed.map((item) => item.id)).size !== parsed.length)
        throw Error('子任务 ID 重复')
      rows.value = parsed.map((item) => ({
        key: `task-${item.id}`,
        id: item.id,
        form: createTaskForm(item),
        confirmed: item,
        error: false,
      }))
      return true
    } catch (loadFailure0) {
      if (valid()) (reportLoadError(loadFailure0, "加载失败，请重试", false), readError.value = true)
      return false
    } finally {
      if (valid()) loading.value = false
    }
  }
  function addTask() {
    if (!active || !canEdit.value || loading.value) return
    invalidateRead()
    const form = createTaskForm()
    form.sort_order = rows.value.length + 1
    rows.value.push({
      key: `draft-${++draftSequence}`,
      id: null,
      form,
      confirmed: null,
      error: false,
    })
  }
  function saveTask(row: RequirementTaskRow): Promise<boolean> {
    if (isBlocked(row) || !positiveTaskId(props.requirementId)) return Promise.resolve(false)
    const snapshot = createTaskForm(row.form)
    if (!workers.has(row.key) && row.confirmed && sameTaskForm(snapshot, row.confirmed)) {
      row.error = false
      return Promise.resolve(true)
    }
    queued.set(row.key, snapshot)
    const existing = workers.get(row.key)
    if (existing) return existing.promise
    invalidateRead()
    const version = generation.value,
      target = props.requirementId
    const worker = { generation: version, promise: Promise.resolve(false) }
    workers.set(row.key, worker)
    const promise = (async () => {
      try {
        while (current(version) && rows.value.includes(row) && queued.has(row.key)) {
          const sent = queued.get(row.key)!
          queued.delete(row.key)
          row.error = false
          const payload = taskPayload(sent, row.id, target)
          const data: unknown = (
            await (row.id === null
              ? postFunctionalRequirementTask(payload)
              : putFunctionalRequirementTask(payload))
          ).data
          if (!current(version) || !rows.value.includes(row)) return false
          const ack = parseRequirementTask(data, target)
          if (row.id !== null && ack.id !== row.id) throw Error('保存目标未确认')
          row.id = ack.id
          row.confirmed = ack
          for (const key of Object.keys(sent) as Array<keyof RequirementTaskForm>) {
            if (row.form[key] === sent[key]) Object.assign(row.form, { [key]: ack[key] })
          }
          const pending = queued.get(row.key)
          if (pending && sameTaskForm(pending, ack)) queued.delete(row.key)
        }
        return true
      } catch {
        queued.delete(row.key)
        if (current(version) && rows.value.includes(row)) row.error = true
        return false
      } finally {
        workers.delete(row.key)
      }
    })()
    worker.promise = promise
    return promise
  }
  function removeTask(row: RequirementTaskRow) {
    if (isBlocked(row) || workers.has(row.key)) return
    invalidateRead()
    if (row.id === null) {
      rows.value = rows.value.filter((item) => item !== row)
      return
    }
    const id = row.id,
      key = row.key,
      version = generation.value,
      name = row.form.name
    const release = () => dialogs.delete(key)
    const dialog = Modal.warning({
      title: '确认删除子任务',
      content: `确定删除「${name}」吗？`,
      hideCancel: false,
      onCancel: release,
      onBeforeCancel: () => !deletingKeys.has(key),
      onBeforeOk: async () => {
        if (
          !current(version) ||
          !rows.value.includes(row) ||
          workers.has(key) ||
          deletingKeys.has(key)
        )
          return false
        deletingKeys.add(key)
        try {
          await deleteFunctionalRequirementTask(id)
          if (!current(version)) return false
          rows.value = rows.value.filter((item) => item !== row)
          release()
          Message.success('已删除')
          return true
        } catch {
          if (current(version)) Message.error('删除失败，请重试')
          return false
        } finally {
          deletingKeys.delete(key)
        }
      },
    })
    dialogs.set(key, dialog)
  }
  watch(
    [() => props.contextKey, () => props.requirementId, () => props.enabled],
    () => {
      reset()
      if (mounted) void loadTasks()
    },
    { flush: 'sync' }
  )
  watch(
    () => workers.size + deletingKeys.size,
    () => {
      if (!isSaving() && needsLoad.value && active) void loadTasks()
    }
  )
  onMounted(() => {
    mounted = true
    void loadTasks()
  })
  onDeactivated(() => {
    active = false
    reset()
  })
  onActivated(() => {
    if (active) return
    active = true
    if (mounted) void loadTasks()
  })
  onBeforeUnmount(() => {
    active = false
    mounted = false
    reset()
  })
  defineExpose({ isSaving })
</script>
<style scoped>
  .mango-requirement-tasks__heading {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .mango-requirement-tasks__heading small {
    color: var(--m-muted);
    font-weight: 400;
  }
  .mango-requirement-tasks__notice {
    margin-bottom: var(--m-page-gap);
  }
  .mango-requirement-tasks__error {
    color: var(--m-danger);
    font-size: 12px;
  }
</style>
