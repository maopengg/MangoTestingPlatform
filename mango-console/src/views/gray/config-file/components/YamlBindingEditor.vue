<template>
  <a-modal
    modal-class="mango-simple-form-modal"
    :visible="visible"
    :title="recordId === null ? '新增仓库绑定' : '编辑仓库绑定'"
    :width="560"
    :ok-loading="saving"
    :on-before-ok="save"
    :on-before-cancel="canCancel"
    :mask-closable="!saving"
    :esc-to-close="!saving"
    @update:visible="onVisibleChange"
  >
    <a-alert v-if="saveError" type="error" class="mango-gray-binding-editor__error"
      >保存失败，输入已保留，请重试。</a-alert
    >
    
    
    <a-form auto-label-width class="mango-simple-form" :model="form" layout="horizontal" :disabled="saving">
      <a-form-item label="所属仓库" class="mango-form-item__require mango-simple-form-item"
        ><a-select
          v-model="form.repository"
          :options="repositoryOptions"
          :loading="repositoriesLoading"
          allow-search
          placeholder="请选择仓库"
          @change="onRepositoryChange"
      /></a-form-item>
      <a-form-item label="文件路径" class="mango-form-item__require mango-simple-form-item"
        ><a-cascader
          v-model="form.file_path"
          :options="fileOptions"
          :loading="filesLoading"
          allow-search
          expand-trigger="hover"
          placeholder="请选择仓库配置目录下的文件"
      /></a-form-item>
      <a-form-item class="mango-simple-form-item" label="启用状态"
        ><a-switch v-model="form.status" :checked-value="1" :unchecked-value="0"
      /></a-form-item>
    </a-form>
  </a-modal>
</template>
<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { computed, onActivated, onBeforeUnmount, onDeactivated, reactive, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { useEnum } from '@/store/modules/get-enum'
  import {
    getGrayRepository,
    getGrayYamlRepositoryFiles,
    postGrayYamlFileBinding,
    putGrayYamlFileBinding,
  } from '@/api/gray'
  import {
    createBindingForm,
    bindingPayload,
    normalizePath,
    pathTree,
    repositories,
    selectionId,
    object,
  } from '../forms'
  import type { BindingForm, BindingRecord, Repository } from '../forms'
  const props = defineProps<{ contextKey: string; blocked: boolean }>()
  const emit = defineEmits<{
    (event: 'saved', yamlId: number): void
    (event: 'busy', value: boolean): void
    (event: 'visible', value: boolean): void
  }>()
  const visible = ref(false),
    saving = ref(false),
    saveError = ref(false)
  const recordId = ref<number | null>(null),
    yamlId = ref<number | null>(null)
  const form: BindingForm = reactive(createBindingForm())
  const repositoryRows = ref<Repository[]>([]),
    files = ref<string[]>([])
  const repositoriesLoading = ref(false),
    repositoriesError = ref(false),
    filesLoading = ref(false),
    filesError = ref(false)
  const original = ref<BindingRecord | null>(null)
  const enums = useEnum()
  let active = true,
    generation = 0,
    repositorySequence = 0,
    fileSequence = 0,
    previousRepository: number | null = null
  const current = (version: number) => active && visible.value && version === generation
  const canCancel = () => !saving.value
  function repositoryLabel(row: Repository) {
    const environment =
      row.test_env === null
        ? '环境通用'
        : (enums.environment_type || []).find(
            (option) => String(option.key) === String(row.test_env)
          )?.title ?? String(row.test_env)
    return `${row.name || '-'} / ${environment} / ${row.branch || '-'}`
  }
  const repositoryOptions = computed(() => {
    const options = repositoryRows.value.map((row) => ({
        value: row.id,
        label: repositoryLabel(row),
      })),
      source = original.value?.repository
    const id = selectionId(source)
    if (id !== null && !options.some((item) => item.value === id))
      options.push({
        value: id,
        label: source && typeof source === 'object' ? repositoryLabel(source) : `ID ${id}`,
      })
    return options
  })
  const fileOptions = computed(() => {
    const selected = normalizePath(form.file_path)
    return pathTree([...files.value, ...(selected ? [selected] : [])])
  })
  function reset() {
    ++generation
    ++repositorySequence
    ++fileSequence
    visible.value = false
    yamlId.value = null
    recordId.value = null
    original.value = null
    repositoriesLoading.value = false
    repositoriesError.value = false
    filesLoading.value = false
    filesError.value = false
    saveError.value = false
    repositoryRows.value = []
    files.value = []
    previousRepository = null
    Object.assign(form, createBindingForm())
  }
  function onVisibleChange(value: boolean) {
    if (!value && canCancel()) reset()
  }
  function open(yaml: { id: number; name: string }, record?: BindingRecord) {
    if (
      !active ||
      saving.value ||
      props.blocked ||
      !selectionId(yaml.id) ||
      (record && (!selectionId(record.id) || record.yaml_file !== yaml.id))
    )
      return
    reset()
    yamlId.value = yaml.id
    recordId.value = record?.id ?? null
    original.value = record
      ? {
          id: record.id,
          yaml_file: record.yaml_file,
          file_path: record.file_path,
          status: record.status,
          repository:
            record.repository && typeof record.repository === 'object'
              ? {
                  id: record.repository.id,
                  name: record.repository.name,
                  branch: record.repository.branch,
                  test_env: record.repository.test_env,
                }
              : record.repository,
        }
      : null
    Object.assign(form, createBindingForm(record))
    previousRepository = selectionId(form.repository)
    visible.value = true
    void loadRepositories()
    void loadFiles()
  }
  async function loadRepositories() {
    if (!current(generation) || saving.value) return
    const version = generation,
      sequence = ++repositorySequence
    repositoriesLoading.value = true
    repositoriesError.value = false
    try {
      const response = await getGrayRepository({})
      if (current(version) && sequence === repositorySequence) {
        if (response.code !== 200) throw Error('Invalid repository response')
        repositoryRows.value = repositories(response.data)
      }
    } catch (loadFailure0) {
      if (current(version) && sequence === repositorySequence) (reportLoadError(loadFailure0, "加载失败，请重试", false), repositoriesError.value = true)
    } finally {
      if (current(version) && sequence === repositorySequence) repositoriesLoading.value = false
    }
  }
  async function loadFiles() {
    if (!current(generation) || saving.value) return
    const version = generation,
      sequence = ++fileSequence,
      repositoryId = selectionId(form.repository)
    files.value = []
    filesError.value = false
    if (repositoryId === null) {
      filesLoading.value = false
      return
    }
    filesLoading.value = true
    try {
      const response = await getGrayYamlRepositoryFiles({ repository_id: repositoryId })
      if (
        !current(version) ||
        sequence !== fileSequence ||
        repositoryId !== selectionId(form.repository)
      )
        return
      const value: unknown = response.data
      if (
        response.code !== 200 ||
        !Array.isArray(value) ||
        !value.every((path) => typeof path === 'string')
      )
        throw Error('Invalid repository file list')
      files.value = [...value]
    } catch (loadFailure1) {
      if (current(version) && sequence === fileSequence) (reportLoadError(loadFailure1, "加载失败，请重试", false), filesError.value = true)
    } finally {
      if (current(version) && sequence === fileSequence) filesLoading.value = false
    }
  }
  function onRepositoryChange(value: number | string | null) {
    const id = selectionId(value)
    if (id === previousRepository) return
    previousRepository = id
    form.file_path = ''
    void loadFiles()
  }
  async function save() {
    if (!current(generation) || saving.value || props.blocked || yamlId.value === null) return false
    if (!selectionId(form.repository)) {
      Message.warning('请选择所属仓库')
      return false
    }
    if (!normalizePath(form.file_path)) {
      Message.warning('请选择文件路径')
      return false
    }
    const version = generation,
      payload = bindingPayload(form, yamlId.value, recordId.value)
    saving.value = true
    saveError.value = false
    emit('busy', true)
    try {
      const response = await (recordId.value === null
        ? postGrayYamlFileBinding(payload)
        : putGrayYamlFileBinding(payload))
      if (!current(version)) return false
      const row = object(response.data),
        id = selectionId(row.id)
      if (
        response.code !== 200 ||
        !id ||
        ('id' in payload && payload.id !== id) ||
        row.yaml_file !== payload.yaml_file ||
        row.repository !== payload.repository
      )
        throw Error('Invalid saved binding')
      reset()
      Message.success('保存成功')
      emit('saved', payload.yaml_file)
    } catch {
      if (current(version)) saveError.value = true
    } finally {
      saving.value = false
      emit('busy', false)
    }
    return false
  }
  watch(visible, (value) => emit('visible', value), { flush: 'sync' })
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
  defineExpose({ open })
</script>
<style scoped>
  .mango-gray-binding-editor__error {
    margin-bottom: var(--m-page-gap);
  }
</style>
