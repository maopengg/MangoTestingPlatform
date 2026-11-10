<template>
  <BaseSidePanel v-model:visible="visible" :title="title" width="72%" @cancel="close">
    <div class="mango-step-reference-body">

      <div class="mango-step-reference-summary">当前步骤被 {{ rows.length }} 个用例引用</div>
      <a-table
        class="mango-native-scroll-table mango-step-reference-table"
        :loading="loading"
        :bordered="false"
        :data="rows"
        :pagination="false"
        :scroll="{ x: 1260, y: '100%' }"
        row-key="id"
      >
        <template #columns>
          <a-table-column
            v-for="column in referencedCaseColumns"
            :key="column.key"
            :title="column.title"
            :width="column.width"
            :align="column.align"
            :data-index="column.key"
            :fixed="column.fixed"
            :ellipsis="column.ellipsis"
            :tooltip="column.tooltip"
          >
            <template v-if="column.key === 'project_product'" #cell="{ record }">{{
              formatProjectProductPath(record.project_product)
            }}</template>
            <template v-else-if="column.key === 'module'" #cell="{ record }">{{
              formatModulePath(record.module)
            }}</template>
            <template v-else-if="column.key === 'case_people'" #cell="{ record }">{{
              record.case_people?.name || record.case_people?.username || '-'
            }}</template>
            <template v-else-if="column.key === 'status'" #cell="{ record }"
              ><a-tag :color="enumStore.status_colors[record.status]" size="small">{{
                enumStore.task_status[record.status]?.title || '-'
              }}</a-tag></template
            >
            <template v-else-if="column.key === 'actions'" #cell="{ record }"
              ><MangoTableActions :actions="[{ label: '步骤', onClick: () => openCase(record) }]"
            /></template>
          </a-table-column>
        </template>
      </a-table>
    </div>
  </BaseSidePanel>
  <BaseSidePanel
    v-model:visible="caseVisible"
    title="界面用例配置"
    width="80%"
    mode="page"
    @cancel="closeCase"
  >
    <UiCaseDetails
      v-if="caseVisible && selectedCase"
      :key="String(selectedCase.id)"
      embedded
      :case-id="selectedCase.id"
      :project-product-id="selectedCase.project_product?.id"
      @close="closeCase"
    />
  </BaseSidePanel>
</template>
<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { computed, ref } from 'vue'
  import { getUiPageStepReferencedCases } from '@/api/uitest/page-steps'
  import { useLiveWorkbenchScope } from '@/hooks/use-live-workbench-scope'
  import { useEnum } from '@/store/modules/get-enum'
  import { formatModulePath, formatProjectProductPath } from '@/utils/business-format'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import UiCaseDetails from '@/views/uitest/case/details/index.vue'
  import { referencedCaseColumns } from '../config'
  import {
    readStepListRow,
    readStepReferences,
    type StepListRow,
    type StepReference,
  } from '../step-list-records'
  const enumStore = useEnum(),
    visible = ref(false),
    loading = ref(false),
    error = ref('')
  const selectedStep = ref<StepListRow | null>(null),
    rows = ref<StepReference[]>([])
  const selectedCase = ref<StepReference | null>(null),
    caseVisible = ref(false)
  const title = computed(() => `引用用例 · ${selectedStep.value?.name || '页面步骤'}`)
  let sequence = 0
  function closeCase() {
    caseVisible.value = false
    selectedCase.value = null
  }
  function close() {
    sequence++
    visible.value = false
    selectedStep.value = null
    rows.value = []
    loading.value = false
    error.value = ''
    closeCase()
  }
  const scope = useLiveWorkbenchScope(() => null, { invalidate: close, resume: () => {} })
  async function loadReferences() {
    const id = selectedStep.value?.id,
      valid = scope.capture(),
      request = ++sequence
    const current = () =>
      valid() &&
      request === sequence &&
      visible.value &&
      String(selectedStep.value?.id) === String(id)
    if (id == null || !current()) return
    loading.value = true
    error.value = ''
    try {
      const result = readStepReferences(await getUiPageStepReferencedCases(id))
      if (current()) rows.value = result
    } catch (loadFailure0) {
      if (current()) (reportLoadError(loadFailure0, "引用用例加载失败，请重试", false), error.value = '引用用例加载失败，请重试')
    } finally {
      if (current()) loading.value = false
    }
  }
  function open(value: StepListRow) {
    if (!scope.available()) return
    close()
    selectedStep.value = readStepListRow(value)
    visible.value = true
    void loadReferences()
  }
  function openCase(value: StepReference) {
    if (!visible.value || !scope.available()) return
    const row = rows.value.find((row) => String(row.id) === String(value.id))
    if (!row) return
    selectedCase.value = row
    caseVisible.value = true
  }
  defineExpose({ open, close })
</script>
<style scoped>
  .mango-step-reference-body {
    display: flex;
    flex-direction: column;
    gap: var(--m-page-gap);
    height: 100%;
    min-height: 0;
  }
  .mango-step-reference-summary {
    color: var(--m-text-2);
  }
  .mango-step-reference-table {
    flex: 1;
    min-height: 0;
  }
</style>
