<template>
  <EvaluationDrawer v-model:visible="visible" title="选择测评条目" :width="1000" contained :footer="true" :mask-closable="!saving" :closable="!saving" :esc-to-close="!saving" @before-cancel="() => !saving">
    <div class="mango-item-selection">
      <a-radio-group v-model="exclude" type="button" :disabled="disabled || saving">
        <a-radio :value="false">选择条目</a-radio>
        <a-radio :value="true">排除条目</a-radio>
      </a-radio-group>
      <p class="mango-item-selection__hint">{{ exclude ? '勾选不参与执行的条目，其余启用条目全部执行。' : '执行勾选的条目；未勾选时执行全部启用条目。' }} 已勾选 {{ selected.length }} 条。</p>
      <a-alert v-if="error" type="error">{{ error }} <a-button size="small" :loading="loading" @click="load">重试</a-button></a-alert>
      <a-table class="mango-native-scroll-table" row-key="id" :columns="columns" :data="items" :loading="loading" :selected-keys="selected"
        :row-selection="{ type: 'checkbox', showCheckedAll: !disabled && !saving, onlyCurrent: true }" :pagination="false" :scroll="{ x: 780, y: '100%' }"
        @update:selected-keys="select">
        <template #input="{ record }"><span :title="dataSummary(record.input_data)">{{ dataSummary(record.input_data) }}</span></template>
        <template #expected="{ record }"><span :title="dataSummary(record.expected_output)">{{ dataSummary(record.expected_output) }}</span></template>
        <template #enabled="{ record }"><a-tag :color="record.enabled ? 'green' : 'gray'">{{ record.enabled ? '启用' : '停用' }}</a-tag></template>
      </a-table>
      <a-pagination :current="page" :page-size="20" :total="total" size="small" show-total :disabled="loading || saving" @change="pageChanged" />
    </div>
    <template #footer>
      <a-space>
        <a-button size="small" :disabled="saving" @click="visible = false">取消</a-button>
        <a-button v-if="!disabled"  size="small" type="primary" :loading="saving" :disabled="loading || Boolean(error)" @click="save">保存</a-button>
      </a-space>
    </template>
  </EvaluationDrawer>
</template>
<script setup lang="ts">
  import { computed, onBeforeUnmount, ref, watch } from 'vue'
  import EvaluationDrawer from './EvaluationDrawer.vue'
  import { Message } from '@arco-design/web-vue'
  import { getEvaluationDatasetItems } from '@/api/evaluation'
  import { dataSummary } from './presentation'
  const props = defineProps<{ versionId?: number | null; modelValue: { exclude?: boolean; item_ids: number[] }; disabled?: boolean; saveSelection: (value: { exclude: boolean; item_ids: number[] }) => Promise<boolean> }>()
  const visible = ref(false), exclude = ref(false), selected = ref<number[]>([]), records = ref<any[]>([])
  const loading = ref(false), saving = ref(false), error = ref(''), page = ref(1), total = ref(0)
  let request = 0
  const columns = [
    { title: 'ID', dataIndex: 'id', width: 90, align: 'center' },
    { title: '输入', slotName: 'input', width: 260, ellipsis: true },
    { title: '期望输出', slotName: 'expected', width: 260, ellipsis: true },
    { title: '状态', slotName: 'enabled', width: 90, align: 'center' },
  ]
  const items = computed(() => records.value.map(row => ({ ...row, disabled: props.disabled || saving.value || (!row.enabled && !selected.value.includes(row.id)) })))
  async function load() {
    const current = ++request, version = props.versionId
    records.value = []; error.value = ''
    if (!version || !visible.value) return
    loading.value = true
    try {
      const response: any = await getEvaluationDatasetItems(version, { page: page.value, pageSize: 20 })
      if (current !== request) return
      records.value = response.data?.items || []
      total.value = response.data?.count || 0
    } catch {
      if (current === request) error.value = '条目加载失败，请确认数据集查看权限后重试'
    } finally { if (current === request) loading.value = false }
  }
  function open() {
    if (!props.versionId) return
    exclude.value = Boolean(props.modelValue.exclude)
    selected.value = [...props.modelValue.item_ids]
    page.value = 1; total.value = 0; visible.value = true
    load()
  }
  function select(keys: (string | number)[]) {
    if (!props.disabled && !saving.value && !loading.value) {
      const currentPage = new Set(records.value.map(row => row.id))
      selected.value = [...new Set([...selected.value.filter(key => !currentPage.has(key)), ...keys.map(Number)])]
    }
  }
  function pageChanged(value: number) { page.value = value; load() }
  async function save() {
    if (props.disabled || saving.value || loading.value || error.value) return
    saving.value = true
    try {
      if (await props.saveSelection({ exclude: exclude.value, item_ids: [...selected.value] })) visible.value = false
      else Message.error('保存未完成，请检查用例配置后重试')
    } catch { Message.error('条目范围保存失败，请重试') }
    finally { saving.value = false }
  }
  watch(() => props.versionId, () => { visible.value = false; request++; loading.value = false })
  watch(visible, value => { if (!value) { request++; loading.value = false } })
  onBeforeUnmount(() => { request++ })
  defineExpose({ open })
</script>
<style scoped>
  .mango-item-selection { display: flex; flex: 1; flex-direction: column; gap: var(--m-page-gap); height: 100%; min-width: 0; min-height: 0; }
  .mango-item-selection__hint { margin: 0; color: var(--m-muted); }
  .mango-item-selection :deep(.arco-table) { flex: 1; min-height: 0; }
</style>
