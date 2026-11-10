<template>
  <a-modal
    modal-class="mango-simple-form-modal"
    :visible="visible"
    :title="record ? '编辑项目绑定' : '导入项目'"
    :width="560"
    :ok-loading="saving"
    :on-before-ok="save"
    @cancel="close"
    @update:visible="onVisibleChange"
  >
    <a-form
      :model="draft"
      layout="horizontal"
      auto-label-width
      :disabled="saving"
      class="mango-pytest-binding-form mango-simple-form"
    >
      <a-form-item label="项目/产品" class="mango-form-item__require mango-simple-form-item">
        <a-cascader
          v-model="draft.project_product"
          :options="projects.projectProduct"
          :loading="projectLoading"
          allow-search
          allow-clear
          placeholder="请选择项目/产品"
        />
        <template v-if="projectFailed" #extra
          ><a-button size="small" :loading="projectLoading" @click="loadProjects"
            >重试</a-button
          ></template
        >
      </a-form-item>
      <a-form-item label="仓库管理" class="mango-form-item__require mango-simple-form-item">
        <a-select
          v-model="draft.repository"
          :options="repositoryOptions"
          :disabled="!!record || saving"
          :loading="repositoryLoading"
          allow-search
          placeholder="请选择代码仓库"
        />
        <template v-if="repositoryFailed" #extra
          ><a-button size="small" :loading="repositoryLoading" @click="loadRepositories"
            >重试</a-button
          ></template
        >
      </a-form-item>
      <a-form-item label="项目目录" class="mango-form-item__require mango-simple-form-item">
        <a-cascader
          v-model="draft.file_name"
          :options="repositoryDirectoryOptions"
          :disabled="!!record || saving || draft.repository === null"
          :loading="directoryLoading"
          allow-search
          allow-clear
          check-strictly
          placeholder="请选择项目目录"
        />
        <template v-if="directoryFailed" #extra
          ><a-button size="small" :loading="directoryLoading" @click="loadRepositoryDirectories"
            >重试</a-button
          ></template
        >
      </a-form-item>
      <a-form-item label="名称" class="mango-form-item__require mango-simple-form-item"
        ><a-input v-model="draft.name" placeholder="请输入绑定名称"
      /></a-form-item>
      <a-form-item label="自动化类型" class="mango-form-item__require mango-simple-form-item">
        <a-select
          v-model="draft.auto_type"
          :options="enumStore.test_case_type"
          :field-names="fieldNames"
          allow-search
          allow-clear
          placeholder="请选择自动化类型"
        />
      </a-form-item>
      <a-form-item label="测试目录" class="mango-form-item__require mango-simple-form-item">
        <a-cascader
          v-model="draft.test_dir"
          :options="testDirectoryOptions"
          :disabled="saving || !draft.file_name"
          :loading="testLoading"
          multiple
          :max-tag-count="2"
          allow-search
          allow-clear
          check-strictly
          placeholder="请选择测试目录"
        />
        <template v-if="testFailed" #extra
          ><span></span
          ><a-button size="small" :loading="testLoading" @click="loadTestDirectories"
            >重试</a-button
          ></template
        >
      </a-form-item>
      <a-form-item label="配置文件" class="mango-pytest-binding-form__wide mango-simple-form-item"
        ><a-input v-model="draft.pytest_config_path" placeholder="例如 pytest.ini"
      /></a-form-item>
    </a-form>
  </a-modal>
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
  import { useRoute } from 'vue-router'
  import { Message } from '@arco-design/web-vue'
  import { useProject } from '@/store/modules/get-project'
  import { useEnum } from '@/store/modules/get-enum'
  import useUserStore from '@/store/modules/user'
  import { fieldNames } from '@/setting'
  import {
    getPytestProductTestDirectories,
    postPytestProductImport,
    putPytestProduct,
  } from '@/api/pytest/product'
  import { getPytestRepositories, getPytestRepositoryDirectories } from '@/api/pytest/repository'
  import {
    bindingDraft,
    bindingPayload,
    checkBindingResponse,
    directoryTree,
    emptyBindingDraft,
    readBinding,
    readDirectories,
    readRepositories,
  } from '../binding'
  import type { BindingRecord, DirectoryOption } from '../binding'

  const emit = defineEmits<{ (event: 'saved'): void }>()
  const projects = useProject(),
    enumStore = useEnum(),
    user = useUserStore(),
    route = useRoute()
  const visible = ref(false),
    saving = ref(false),
    record = ref<BindingRecord | null>(null)
  const draft = reactive(emptyBindingDraft())
  const projectLoading = ref(false),
    projectFailed = ref(false),
    repositoryLoading = ref(false),
    repositoryFailed = ref(false)
  const directoryLoading = ref(false),
    directoryFailed = ref(false),
    testLoading = ref(false),
    testFailed = ref(false)
  const repositories = ref<Array<{ value: number; label: string }>>([])
  const repositoryDirectoryOptions = ref<DirectoryOption[]>([]),
    testDirectoryOptions = ref<DirectoryOption[]>([])
  const repositoryOptions = computed(() =>
    record.value?.repository
      ? [{ value: record.value.repository.id, label: record.value.repository.name }]
      : repositories.value
  )
  let version = 0,
    projectRequest = 0,
    repositoryRequest = 0,
    directoryRequest = 0,
    testRequest = 0
  let active = true,
    disposed = false,
    initializing = false
  const available = () =>
    !disposed && active && (typeof document === 'undefined' || !document.hidden)
  const current = (window: number) => available() && visible.value && window === version
  function close(): void {
    version++
    projectRequest++
    repositoryRequest++
    directoryRequest++
    testRequest++
    visible.value = false
    initializing = true
    record.value = null
    Object.assign(draft, emptyBindingDraft())
    initializing = false
    repositories.value = []
    repositoryDirectoryOptions.value = []
    testDirectoryOptions.value = []
    projectLoading.value =
      repositoryLoading.value =
      directoryLoading.value =
      testLoading.value =
        false
    projectFailed.value = repositoryFailed.value = directoryFailed.value = testFailed.value = false
  }
  function onVisibleChange(value: boolean): void {
    if (!value) close()
  }
  function open(value?: unknown): void {
    if (!available() || saving.value) return
    let row: BindingRecord | null
    try {
      row = value == null ? null : readBinding(value)
    } catch {
      Message.error('项目绑定格式不正确，请刷新列表')
      return
    }
    close()
    initializing = true
    record.value = row
    Object.assign(draft, row ? bindingDraft(row) : emptyBindingDraft())
    initializing = false
    visible.value = true
    void loadProjects()
    if (row) {
      repositoryDirectoryOptions.value = directoryTree([], [row.file_name])
      testDirectoryOptions.value = directoryTree([], row.test_dir, true)
      void loadTestDirectories()
    } else void loadRepositories()
  }
  async function loadProjects(): Promise<void> {
    if (!current(version) || projectLoading.value) return
    const window = version,
      request = ++projectRequest
    projectLoading.value = true
    projectFailed.value = false
    try {
      await projects.projectProductName()
      if (projects.optionErrors.products) throw new Error('项目加载失败')
    } catch (loadFailure0) {
      if (current(window) && request === projectRequest) (reportLoadError(loadFailure0, "加载失败，请重试", false), projectFailed.value = true)
    } finally {
      if (current(window) && request === projectRequest) projectLoading.value = false
    }
  }
  async function loadRepositories(): Promise<void> {
    if (!current(version) || record.value || repositoryLoading.value) return
    const window = version,
      request = ++repositoryRequest
    repositoryLoading.value = true
    repositoryFailed.value = false
    try {
      const rows = readRepositories(await getPytestRepositories())
      if (!current(window) || request !== repositoryRequest) return
      repositories.value = rows
      if (draft.repository === null && rows.length) draft.repository = rows[0].value
    } catch (loadFailure0) {
      if (current(window) && request === repositoryRequest) (reportLoadError(loadFailure0, "加载失败，请重试", false), repositoryFailed.value = true)
    } finally {
      if (current(window) && request === repositoryRequest) repositoryLoading.value = false
    }
  }
  async function loadRepositoryDirectories(): Promise<void> {
    if (!current(version) || record.value || draft.repository === null || directoryLoading.value)
      return
    const window = version,
      request = ++directoryRequest,
      repositoryId = draft.repository
    directoryLoading.value = true
    directoryFailed.value = false
    try {
      const options = directoryTree(
        readDirectories(await getPytestRepositoryDirectories(repositoryId))
      )
      if (current(window) && request === directoryRequest)
        repositoryDirectoryOptions.value = options
    } catch (loadFailure1) {
      if (current(window) && request === directoryRequest) (reportLoadError(loadFailure1, "加载失败，请重试", false), directoryFailed.value = true)
    } finally {
      if (current(window) && request === directoryRequest) directoryLoading.value = false
    }
  }
  async function loadTestDirectories(): Promise<void> {
    if (!current(version) || !draft.file_name || draft.repository === null || testLoading.value)
      return
    const window = version,
      request = ++testRequest,
      configured = [...draft.test_dir]
    testLoading.value = true
    testFailed.value = false
    try {
      const entries = readDirectories(
        await getPytestProductTestDirectories(record.value?.id, draft.file_name, draft.repository)
      )
      if (current(window) && request === testRequest)
        testDirectoryOptions.value = directoryTree(entries, configured, true)
    } catch (loadFailure1) {
      if (current(window) && request === testRequest) (reportLoadError(loadFailure1, "加载失败，请重试", false), testFailed.value = true)
    } finally {
      if (current(window) && request === testRequest) testLoading.value = false
    }
  }
  watch(
    () => draft.repository,
    () => {
      if (initializing || !visible.value || record.value) return
      directoryRequest++
      testRequest++
      directoryLoading.value = testLoading.value = false
      directoryFailed.value = testFailed.value = false
      repositoryDirectoryOptions.value = []
      testDirectoryOptions.value = []
      draft.file_name = ''
      draft.test_dir = []
      void loadRepositoryDirectories()
    },
    { flush: 'sync' }
  )
  watch(
    () => draft.file_name,
    (path) => {
      if (initializing || !visible.value || record.value) return
      testRequest++
      testLoading.value = false
      testFailed.value = false
      testDirectoryOptions.value = []
      draft.test_dir = []
      if (path) {
        draft.name = path.split('/').at(-1) || path
        void loadTestDirectories()
      }
    },
    { flush: 'sync' }
  )
  async function save(): Promise<boolean> {
    if (
      !current(version) ||
      saving.value ||
      projectLoading.value ||
      projectFailed.value ||
      directoryLoading.value ||
      testLoading.value ||
      repositoryLoading.value
    )
      return false
    let payload: ReturnType<typeof bindingPayload>
    try {
      payload = bindingPayload(draft, projects.projectProduct, record.value?.id ?? null)
    } catch (error) {
      Message.warning(error instanceof Error ? error.message : '请检查必填项')
      return false
    }
    const window = version,
      editing = record.value !== null
    saving.value = true
    try {
      checkBindingResponse(
        await (editing ? putPytestProduct(payload) : postPytestProductImport(payload))
      )
      if (!current(window)) return false
      close()
      Message.success(editing ? '保存成功' : '导入成功')
      emit('saved')
      return true
    } catch {
      if (current(window)) Message.error('保存失败，请重试')
      return false
    } finally {
      saving.value = false
    }
  }
  watch(
    () => [user.userId, user.roleId, user.token, user.selected_environment, route.fullPath],
    close,
    { flush: 'sync' }
  )
  function visibilityChanged(): void {
    if (typeof document !== 'undefined' && document.hidden) close()
  }
  onMounted(() => {
    if (typeof document !== 'undefined')
      document.addEventListener('visibilitychange', visibilityChanged)
  })
  onActivated(() => {
    active = true
  })
  onDeactivated(() => {
    active = false
    close()
  })
  onBeforeUnmount(() => {
    disposed = true
    close()
    if (typeof document !== 'undefined')
      document.removeEventListener('visibilitychange', visibilityChanged)
  })
  defineExpose({ open, close })
</script>

<style scoped>
  .mango-pytest-binding-form {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    column-gap: 16px;
  }
  .mango-pytest-binding-form__wide {
    grid-column: 1 / -1;
  }
</style>
