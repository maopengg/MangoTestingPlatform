<template>
  <a-drawer
    v-model:visible="visible"
    :title="form.id ? '编辑用例' : '新增用例'"
    :width="760"
    :ok-loading="saving"
    :on-before-ok="saveCase"
    :on-before-cancel="canCancel"
    @cancel="invalidate"
  >
    <a-alert v-if="saveError" type="error" class="mango-library-case-editor__feedback"
      >保存失败，输入已保留，请重试。</a-alert
    >
    <a-spin :loading="categoryLoading" class="mango-library-case-editor__categories">
      <span v-if="categoryLoading">正在加载分类选项…</span>
      
    </a-spin>
    <a-form :model="form" layout="horizontal" :disabled="saving" class="mango-library-case-editor">
      <div class="mango-library-case-editor__fields">
        <div
          ><a-form-item label="用例编号" required><a-input v-model="form.case_no" /></a-form-item
        ></div>
        <div
          ><a-form-item label="优先级" required
            ><a-select
              v-model="form.priority"
              :options="enumStore.case_level"
              :field-names="fieldNames" /></a-form-item
        ></div>
        <div class="mango-library-case-editor__wide"
          ><a-form-item label="用例标题" required><a-input v-model="form.title" /></a-form-item
        ></div>
        <div
          ><a-form-item label="项目产品" required
            ><ProjectProductSelect
              v-model="form.project_product"
              @change="onProductChange" /></a-form-item
        ></div>
        <div
          ><a-form-item label="模块" required
            ><ProductModuleSelect
              v-model="form.module"
              :auto-clear="false"
              :project-product-id="caseProductId(form.project_product)"
              @change="loadCategoryOptions" /></a-form-item
        ></div>
        <div
          ><a-form-item label="分类一"
            ><a-auto-complete
              v-model="form.category_level_1"
              :data="categoryOptions.category_level_1"
              allow-clear
              @change="loadCategoryOptions" /></a-form-item
        ></div>
        <div
          ><a-form-item label="分类二"
            ><a-auto-complete
              v-model="form.category_level_2"
              :data="categoryOptions.category_level_2"
              allow-clear
              @change="loadCategoryOptions" /></a-form-item
        ></div>
        <div
          ><a-form-item label="分类三"
            ><a-auto-complete
              v-model="form.category_level_3"
              :data="categoryOptions.category_level_3"
              allow-clear /></a-form-item
        ></div>
        <div
          ><a-form-item label="负责人" required
            ><a-select
              v-model="form.owner"
              :options="users"
              :field-names="fieldNames"
              allow-search /></a-form-item
        ></div>
        <div
          ><a-form-item label="测试类型" required
            ><a-select
              v-model="form.test_types"
              :options="enumStore.manual_test_type"
              :field-names="fieldNames"
              multiple /></a-form-item
        ></div>
        <div
          ><a-form-item label="资产状态"
            ><a-select
              v-model="form.status"
              :options="enumStore.functional_case_status"
              :field-names="fieldNames" /></a-form-item
        ></div>
        <div
          ><a-form-item label="自动化状态"
            ><a-select
              v-model="form.automation_status"
              :options="AUTOMATION_STATUS_OPTIONS" /></a-form-item
        ></div>
        <div
          ><a-form-item label="测试层级" required
            ><a-select
              v-model="form.scenario_layer"
              :options="enumStore.api_case_scenario_layer"
              :field-names="fieldNames" /></a-form-item
        ></div>
        <div
          ><a-form-item label="验证类型" required
            ><a-select
              v-model="form.scenario_type"
              :options="enumStore.api_case_scenario_type"
              :field-names="fieldNames" /></a-form-item
        ></div>
        <div class="mango-library-case-editor__wide"
          ><a-form-item label="执行场景" required
            ><a-select
              v-model="form.scenario_tags"
              :options="enumStore.api_case_scenario_tag"
              :field-names="fieldNames"
              multiple /></a-form-item
        ></div>
        <div class="mango-library-case-editor__wide"
          ><a-form-item label="关联用户故事"
            ><a-select
              v-model="form.story_refs"
              multiple
              allow-create
              allow-search
              placeholder="输入故事或验收点编号后回车" /></a-form-item
        ></div>
        <div class="mango-library-case-editor__wide"
          ><a-form-item label="前置条件"
            ><a-textarea
              v-model="form.precondition"
              :auto-size="{ minRows: 2, maxRows: 4 }" /></a-form-item
        ></div>
        <div class="mango-library-case-editor__wide"
          ><a-form-item label="测试场景" required
            ><a-textarea
              v-model="form.test_point"
              :auto-size="{ minRows: 2, maxRows: 5 }" /></a-form-item
        ></div>
        <div class="mango-library-case-editor__wide">
          <a-form-item label="测试步骤">
            <div class="mango-case-library__steps">
              <div
                v-for="(step, index) in form.test_steps"
                :key="index"
                class="mango-case-library__step"
              >
                <span>{{ index + 1 }}</span>
                <a-input v-model="step.action" placeholder="操作" />
                <a-input v-model="step.expected" placeholder="步骤预期" />
                <a-button type="text" status="danger" @click="form.test_steps.splice(index, 1)"
                  ><icon-delete
                /></a-button>
              </div>
              <a-button size="small" @click="form.test_steps.push({ action: '', expected: '' })"
                >增加步骤</a-button
              >
            </div>
          </a-form-item>
        </div>
        <div class="mango-library-case-editor__wide"
          ><a-form-item label="预期结果"
            ><a-textarea
              v-model="form.expected_result"
              :auto-size="{ minRows: 2, maxRows: 5 }" /></a-form-item
        ></div>
        <div class="mango-library-case-editor__wide"
          ><a-form-item label="验收标准来源"
            ><a-textarea
              v-model="form.acceptance_source"
              :auto-size="{ minRows: 2, maxRows: 4 }" /></a-form-item
        ></div>
        <div class="mango-library-case-editor__wide"
          ><a-form-item label="测试数据"
            ><a-textarea
              v-model="form.test_data"
              :auto-size="{ minRows: 2, maxRows: 4 }" /></a-form-item
        ></div>
        <div class="mango-library-case-editor__wide"
          ><a-form-item label="备注"><a-textarea v-model="form.remark" /></a-form-item
        ></div>
      </div>
    </a-form>
  </a-drawer>
</template>

<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { nextTick, onActivated, onBeforeUnmount, onDeactivated, reactive, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ProductModuleSelect from '@/components/business/ProductModuleSelect.vue'
  import { useEnum } from '@/store/modules/get-enum'
  import {
    getFunctionalCaseCategoryOptions,
    postManualCase,
    putManualCase,
  } from '@/api/functional-test'
  import type { NavigationCreateSelection } from '@/utils/navigation-create-defaults'
  import { AUTOMATION_STATUS_OPTIONS } from '../config'
  import {
    caseProductId,
    createLibraryCaseForm,
    emptyCaseCategories,
    libraryCasePayload,
  } from '../form'
  import type { CaseUserOption, LibraryCaseEditorRecord } from '../types'

  const props = defineProps<{
    users: CaseUserOption[]
    contextKey: string
    defaults: NavigationCreateSelection
  }>()
  const emit = defineEmits<{ (event: 'saved'): void }>()
  const enumStore = useEnum()
  const fieldNames = { value: 'key', label: 'title' }
  const form = reactive(createLibraryCaseForm())
  const categoryOptions = reactive(emptyCaseCategories())
  const visible = ref(false)
  const saving = ref(false)
  const saveError = ref(false)
  const categoryLoading = ref(false)
  const categoryError = ref(false)
  let active = true
  let generation = 0
  let categoryRequest = 0

  const current = (version: number) => active && visible.value && version === generation

  function invalidate() {
    ++generation
    ++categoryRequest
    visible.value = false
    categoryLoading.value = false
    categoryError.value = false
    saveError.value = false
    Object.assign(form, createLibraryCaseForm())
    Object.assign(categoryOptions, emptyCaseCategories())
  }

  function canCancel() {
    return !saving.value
  }

  async function open(record?: LibraryCaseEditorRecord) {
    if (!active || saving.value) return
    invalidate()
    const version = generation
    Object.assign(form, createLibraryCaseForm(record))
    visible.value = true
    if (!record && props.defaults.projectProduct !== null) {
      form.project_product = props.defaults.projectProduct
      await nextTick()
      if (!current(version)) return
      if (
        String(caseProductId(form.project_product)) === String(props.defaults.projectProduct) &&
        form.module === null
      ) {
        form.module = props.defaults.module
      }
    }
    if (current(version)) await loadCategoryOptions()
  }

  async function loadCategoryOptions() {
    if (!active || !visible.value) return
    const version = generation
    const request = ++categoryRequest
    categoryLoading.value = true
    categoryError.value = false
    const owns = () => current(version) && request === categoryRequest
    try {
      const query = {
        project_product: caseProductId(form.project_product),
        module: form.module,
        category_level_1: form.category_level_1,
        category_level_2: form.category_level_2,
      }
      const response = await getFunctionalCaseCategoryOptions(
        Object.fromEntries(
          Object.entries(query).filter(([, value]) => value !== null && value !== '')
        )
      )
      if (owns()) Object.assign(categoryOptions, emptyCaseCategories(), response.data)
    } catch (loadFailure0) {
      if (owns()) {
        Object.assign(categoryOptions, emptyCaseCategories())
        void (reportLoadError(loadFailure0, "加载失败，请重试", false), categoryError.value = true)
      }
    } finally {
      if (owns()) categoryLoading.value = false
    }
  }

  function onProductChange() {
    form.module = null
    void loadCategoryOptions()
  }

  async function saveCase() {
    if (!active || !visible.value || saving.value) return false
    if (
      !form.case_no ||
      !form.title ||
      !caseProductId(form.project_product) ||
      !form.module ||
      !form.owner ||
      !form.test_point
    ) {
      Message.warning('请填写所有必填字段')
      return false
    }
    const version = generation
    const payload = libraryCasePayload(form)
    saving.value = true
    saveError.value = false
    try {
      if (form.id !== null) await putManualCase(payload)
      else await postManualCase(payload)
      if (current(version)) {
        Message.success('保存成功')
        invalidate()
        emit('saved')
      }
    } catch {
      if (current(version)) saveError.value = true
    } finally {
      // A context change invalidates UI ownership, but must not release an in-flight write lock.
      saving.value = false
    }
    // Closing is explicit above so a late write cannot close a subsequently opened draft.
    return false
  }

  watch(() => props.contextKey, invalidate, { flush: 'sync' })
  onDeactivated(() => {
    active = false
    invalidate()
  })
  onActivated(() => {
    active = true
  })
  onBeforeUnmount(() => {
    active = false
    invalidate()
  })
  defineExpose({ open })
</script>

<style scoped lang="less">
  .mango-library-case-editor__fields {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    column-gap: 16px;
  }
  .mango-library-case-editor__fields > div {
    min-width: 0;
  }
  .mango-library-case-editor__wide {
    grid-column: 1 / -1;
  }
  .mango-library-case-editor__feedback {
    margin-bottom: var(--m-page-gap);
  }
  .mango-library-case-editor__categories {
    width: 100%;
    color: var(--m-muted);
  }
  .mango-case-library__steps {
    display: flex;
    flex-direction: column;
    gap: 8px;
    width: 100%;
  }
  .mango-case-library__step {
    display: grid;
    grid-template-columns: 28px 1fr 1fr 32px;
    align-items: center;
    gap: 8px;
  }
</style>
