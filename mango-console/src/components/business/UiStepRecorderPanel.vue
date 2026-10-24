<template>
  <section class="mango-step-recorder">
    <header class="mango-step-recorder__header">
      <div>
        <strong
          ><span class="mango-step-recorder__dot"></span
          >{{ paused ? '录制已暂停' : '正在录制' }}</strong
        >
        <span>浏览器操作将按顺序生成当前页面步骤的画布节点，保存前不会写入业务表</span>
      </div>
      <a-space size="mini">
        <a-tag size="small">{{ actions.length }} 个节点</a-tag>
        <a-button size="mini" @click="emit('toggle-pause')">{{
          paused ? '继续' : '暂停'
        }}</a-button>
      </a-space>
    </header>

    <section class="mango-step-recorder__settings-card">
      <div class="mango-section-title">录制设置</div>
      <div class="mango-step-recorder__settings">
        <label
          ><span>合并连续输入</span><a-switch v-model="settings.mergeInput" size="small"
        /></label>
        <label
          ><span>记录页面滚动</span><a-switch v-model="settings.recordScroll" size="small"
        /></label>
        <label
          ><span>记录页面跳转</span><a-switch v-model="settings.recordNavigation" size="small"
        /></label>
      </div>
    </section>

    <div class="mango-step-recorder__content">
      <div class="mango-step-recorder__toolbar">
        <a-dropdown trigger="click">
          <a-button size="mini" data-testid="qa-components-business-uisteprecorderpanel-button-插入节点">插入节点</a-button>
          <template #content>
            <a-doption @click="insertNode(0)" data-testid="qa-components-business-uisteprecorderpanel-doption-元素操作">元素操作</a-doption>
            <a-doption @click="insertNode(1)" data-testid="qa-components-business-uisteprecorderpanel-doption-断言操作">断言操作</a-doption>
            <a-doption @click="insertNode(2)" data-testid="qa-components-business-uisteprecorderpanel-doption-sql-操作">SQL 操作</a-doption>
            <a-doption @click="insertNode(3)" data-testid="qa-components-business-uisteprecorderpanel-doption-自定义变量">自定义变量</a-doption>
            <a-doption @click="insertNode(5)" data-testid="qa-components-business-uisteprecorderpanel-doption-python-代码">Python 代码</a-doption>
            <a-doption @click="insertNode(6)" data-testid="qa-components-business-uisteprecorderpanel-doption-强制等待">强制等待</a-doption>
          </template>
        </a-dropdown>
        <a-popconfirm content="确认清空当前录制草稿吗？" @ok="emit('clear')">
          <a-button size="mini" status="danger" :disabled="!actions.length" data-testid="qa-components-business-uisteprecorderpanel-button-清空">清空</a-button>
        </a-popconfirm>
      </div>
      <div v-if="actions.length" class="mango-step-recorder__node-list">
        <article
          v-for="(item, index) in actions"
          :key="item.client_id"
          class="mango-step-recorder__node-card"
          :class="{ 'is-dragging': draggingIndex === index, 'is-review': item.status === 'review' }"
          @dragover.prevent
          @drop="onDrop(index)"
        >
          <header class="mango-step-recorder__node-head">
            <div class="mango-step-recorder__node-title">
              <span
                class="mango-step-recorder__handle"
                title="拖动排序"
                draggable="true"
                @dragstart.stop="onDragStart(index)"
                @dragend="onDragEnd"
                >⠿</span
              >
              <strong class="mango-step-recorder__node-index">{{
                String(index + 1).padStart(2, '0')
              }}</strong>
              <div>
                <strong>{{ nodeTypeName(item.detail?.type) }}</strong>
                <span>{{ nodeSummary(item) }}</span>
              </div>
            </div>
            <a-space size="mini">
              <a-tag :color="item.status === 'review' ? 'orange' : 'arcoblue'" size="small">
                {{ item.status === 'review' ? '待配置' : '已配置' }}
              </a-tag>
              <a-button
                v-if="item.element || item.element_id"
                type="text"
                size="mini"
                @click="emit('edit-element', item)" data-testid="qa-components-business-uisteprecorderpanel-button-元素"
                >元素</a-button
              >
              <a-button
                v-if="item.element || item.element_id"
                type="text"
                size="mini"
                :loading="checkLoading"
                :disabled="checkLoading"
                @click="emit('check-element', item)" data-testid="qa-components-business-uisteprecorderpanel-button-检测"
                >检测</a-button
              >
              <a-tag
                v-if="item._checkStatus"
                size="small"
                :color="item._checkStatus === 'passed' ? 'green' : 'red'"
              >
                {{ item._checkStatus === 'passed' ? '检测通过' : '检测失败' }}
              </a-tag>
              <a-button type="text" size="mini" status="danger" @click="emit('remove', index)" data-testid="qa-components-business-uisteprecorderpanel-button-删除"
                >删除</a-button
              >
            </a-space>
          </header>

          <UiStepNodeConfigForm
            v-if="item.detail?.type !== 2"
            :items="inlineEditorItems(item)"
            :operation-options="operationOptions"
            :assertion-options="assertionOptions"
            :element-cascader-options="elementCascaderOptions"
            :field-prefix="String(item.client_id)"
            compact
            class="mango-step-recorder__inline-editor"
            @method-change="onInlineMethodChange(item, $event)"
            @change="syncInlineConfig(item)"
          />
          <div v-else class="mango-step-recorder__sql-grid">
            <label>
              <span>逻辑数据源</span>
              <a-select
                size="small"
                :model-value="item.detail?.sql_execute?.[0]?.datasource_alias"
                :options="datasourceAliasOptions"
                placeholder="请选择逻辑数据源"
                allow-clear
                allow-search
                @update:model-value="updateSqlField(item, 'datasource_alias', $event)" data-testid="qa-components-business-uisteprecorderpanel-select-请选择逻辑数据源"
              />
            </label>
            <label>
              <span>缓存 Key</span>
              <a-input
                size="small"
                :model-value="item.detail?.sql_execute?.[0]?.key_list"
                placeholder="请输入缓存 Key"
                @update:model-value="updateSqlField(item, 'key_list', $event)" data-testid="qa-components-business-uisteprecorderpanel-input-请输入缓存-key"
              />
            </label>
            <label class="is-wide">
              <span>SQL</span>
              <a-textarea
                :model-value="item.detail?.sql_execute?.[0]?.sql"
                :auto-size="{ minRows: 2, maxRows: 6 }"
                placeholder="请输入数据库查询或操作内容"
                @update:model-value="updateSqlField(item, 'sql', $event)" data-testid="qa-components-business-uisteprecorderpanel-textarea-请输入数据库查询或操作内容"
              />
            </label>
          </div>
        </article>
      </div>
      <div v-else class="mango-empty-state mango-step-recorder__empty">
        <strong>暂无录制节点</strong>
        <span
          >在实时画面中操作，或通过“插入节点”增加元素操作、断言、SQL、自定义变量、Python
          和强制等待节点。</span
        >
      </div>
    </div>

    <footer class="mango-step-recorder__footer">
      <span>草稿已在当前浏览器会话中自动保存</span>
      <a-button
        type="primary"
        size="small"
        :loading="saving"
        :disabled="!actions.length"
        @click="saveVisible = true" data-testid="qa-components-business-uisteprecorderpanel-button-保存为页面步骤"
        >保存为页面步骤</a-button
      >
    </footer>

    <a-modal
      v-model:visible="saveVisible"
      title="保存页面步骤"
      width="560px"
      :ok-loading="saving"
      @ok="saveRecording"
    >
      <a-form layout="horizontal" :label-col-props="{ span: 5 }" :wrapper-col-props="{ span: 19 }">
        <a-form-item label="步骤名称" required
          ><a-input v-model="stepName" :max-length="64"
        /></a-form-item>
      </a-form>
    </a-modal>
  </section>
</template>

<script lang="ts" setup>
  import { computed, onMounted, reactive, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { postUiPageStepRecordingCommit } from '@/api/uitest/page-steps'
  import { useSelectValueStore } from '@/store/modules/get-ope-value'
  import UiStepNodeConfigForm from '@/components/business/UiStepNodeConfigForm.vue'
  import { getDataFactoryDatasourceAlias } from '@/api/data-factory'

  const props = withDefaults(
    defineProps<{
      actions: any[]
      pageId: string | number
      paused?: boolean
      pageType?: string | number
      elementOptions?: any[]
      projectProductId?: string | number
      testEnv?: string | number
      checkLoading?: boolean
    }>(),
    { pageType: 0, elementOptions: () => [], projectProductId: '', checkLoading: false }
  )
  const checkLoading = computed(() => props.checkLoading)
  const emit = defineEmits<{
    (event: 'reorder', from: number, to: number): void
    (event: 'remove', index: number): void
    (event: 'clear'): void
    (event: 'update-action', value: any): void
    (event: 'edit-element', value: any): void
    (event: 'check-element', value: any): void
    (event: 'toggle-pause'): void
    (event: 'saved', value: any): void
    (event: 'settings-change', value: Record<string, any>): void
  }>()

  const methodStore = useSelectValueStore()
  const draggingIndex = ref<number | null>(null)
  const saveVisible = ref(false)
  const saving = ref(false)
  const datasourceAliasOptions = ref<any[]>([])
  const inlineEditorCache = new Map<string, { signature: string; items: any[] }>()
  const stepName = ref('')
  const settings = reactive({
    mergeInput: true,
    recordScroll: false,
    recordNavigation: true,
  })
  const operationOptions = computed(() =>
    methodStore.getOperationOptions(props.pageType)
  )
  const assertionOptions = computed(() =>
    methodStore.getAssertionOptions(props.pageType)
  )
  const elementCascaderOptions = computed(() => {
    const groups = new Map<string, any[]>()
    props.elementOptions.forEach((element: any) => {
      const category = element.category || '未分类'
      if (!groups.has(category)) groups.set(category, [])
      groups.get(category)!.push({ label: element.name, value: element.id })
    })
    return Array.from(groups.entries()).map(([label, children]) => ({
      label,
      value: label,
      children,
    }))
  })

  onMounted(async () => {
    await methodStore.getSelectValue()
    await loadDatasourceAliases()
  })
  watch(
    () => props.projectProductId,
    () => {
      void loadDatasourceAliases()
    }
  )
  watch(settings, (value) => emit('settings-change', { ...value }), { deep: true, immediate: true })

  function onDragStart(index: number) {
    draggingIndex.value = index
  }
  function onDrop(index: number) {
    if (draggingIndex.value != null && draggingIndex.value !== index)
      emit('reorder', draggingIndex.value, index)
    draggingIndex.value = null
  }
  function onDragEnd() {
    draggingIndex.value = null
  }
  function nodeTypeName(type: any) {
    return (
      (
        {
          0: '元素操作',
          1: '断言操作',
          2: 'SQL 操作',
          3: '自定义变量',
          5: 'Python 代码',
          6: '强制等待',
        } as Record<number, string>
      )[Number(type)] || '未配置节点'
    )
  }
  function selectedElement(item: any) {
    const elementId = item.detail?.ele_name || item.element_id
    return props.elementOptions.find((element: any) => String(element.id) === String(elementId))
  }
  function elementDisplayName(item: any) {
    if (
      Object.prototype.hasOwnProperty.call(item || {}, 'name') &&
      item.name !== nodeTypeName(item.detail?.type)
    )
      return String(item.name || '')
    const fallbackName = item.name === nodeTypeName(item.detail?.type) ? '' : item.name
    return (
      fallbackName ||
      selectedElement(item)?.name ||
      item.element?.accessible_name ||
      item.element?.text ||
      item.element?.label ||
      item.element?.placeholder ||
      ''
    )
  }
  function nodeUsesElement(item: any) {
    if (item.element || item.element_id || item.detail?.ele_name) return true
    const method = methodStore.findItemByValue(item.detail?.ope_key)
    return (method?.parameter || []).some((parameter: any) =>
      ['locating', 'actual'].includes(parameter.f)
    )
  }
  function locatorCount(item: any) {
    const element = item.element || selectedElement(item) || {}
    if (Array.isArray(element.locators))
      return element.locators.filter((locator: any) => locator?.loc).length
    return ['loc', 'loc2', 'loc3'].filter((key) => element[key]).length
  }
  function nodeSummary(item: any) {
    const type = Number(item.detail?.type)
    const parts = [`元素 ${nodeUsesElement(item) ? 1 : 0} 个`]
    const locators = locatorCount(item)
    if (locators) parts.push(`定位 ${locators} 组`)
    if (type === 2) {
      parts.push(`SQL ${(item.detail?.sql_execute || []).length} 项`)
    } else if (type === 3) {
      parts.push(`变量 ${(item.detail?.custom || []).length} 项`)
    } else if (type === 5) {
      parts.push(String(item.detail?.func || '').trim() ? '代码已填写' : '代码未填写')
    } else if (type === 6) {
      const seconds = item.detail?.ope_value?.find((entry: any) => entry.f === 'seconds')?.v
      parts.push(`等待 ${seconds ?? 1} 秒`)
    }
    return parts.join(' · ')
  }
  function createNode(type: number) {
    const detailMap: Record<number, any> = {
      0: { type: 0, ope_key: '', ope_value: [], ele_name: null },
      1: { type: 1, ope_key: '', ope_value: [], ele_name: null },
      2: { type: 2, sql_execute: [{ datasource_alias: null, sql: '', key_list: '' }] },
      3: { type: 3, custom: [{ key: '', value: '' }] },
      5: { type: 5, func: 'def func(self):\n    pass' },
      6: { type: 6, ope_key: null, ope_value: [{ f: 'seconds', v: 1 }] },
    }
    return {
      client_id: crypto.randomUUID(),
      action: 'manual',
      name: nodeTypeName(type),
      status: 'review',
      category: '未分类',
      detail: detailMap[type],
    }
  }
  function insertNode(type: number) {
    const node = createNode(type)
    emit('update-action', node)
  }
  function clone<T>(value: T): T {
    return JSON.parse(JSON.stringify(value))
  }
  function elementCascaderValue(elementId: any) {
    if (!elementId) return ''
    const element = props.elementOptions.find((item: any) => String(item.id) === String(elementId))
    return element ? [element.category || '未分类', element.id] : elementId
  }
  function buildMethodItems(type: number, detail: any, node?: any) {
    const items: any[] = [
      {
        label: type === 0 ? '元素操作' : '断言操作',
        key: 'ope_key',
        value: detail.ope_key || '',
        type: 'cascader',
        required: true,
        placeholder: type === 0 ? '请选择元素操作' : '请选择断言方法',
      },
    ]
    if (nodeUsesElement(node))
      items.unshift(
        {
          label: '分类',
          key: 'recorded_element_category',
          value: node?.category || '未分类',
          type: 'input',
          compactHalf: true,
          compactNarrow: true,
          required: false,
          placeholder: '请输入元素分类',
        },
        {
          label: '元素名称',
          key: 'recorded_element_name',
          value: elementDisplayName(node),
          type: 'input',
          compactHalf: true,
          compactWideLabel: true,
          required: true,
          placeholder: '请输入元素名称',
        }
      )
    const method = methodStore.findItemByValue(detail.ope_key)
    const values = new Map((detail.ope_value || []).map((item: any) => [item.f, item.v]))
    const requiresElement = (method?.parameter || []).some((item: any) =>
      ['locating', 'actual'].includes(item.f)
    )
    if (requiresElement && !node?.element)
      items.push({
        label: '选择元素',
        key: 'ele_name',
        value: elementCascaderValue(detail.ele_name || node?.element_id),
        type: 'element-cascader',
        required: true,
        placeholder: '请选择页面元素',
      })
    ;(method?.parameter || []).forEach((parameter: any) => {
      if (['locating', 'actual'].includes(parameter.f)) return
      items.push({
        label: parameter.n || parameter.f,
        key: `${parameter.f}-ope_value`,
        field: parameter.f,
        value: values.has(parameter.f) ? values.get(parameter.f) : parameter.v,
        type: parameter.input_type === 'key_value' ? 'key-value' : 'textarea',
        required: parameter.d === true,
        placeholder: parameter.p,
      })
    })
    return items
  }
  function inlineEditorItems(item: any) {
    const key = String(item.client_id)
    const type = Number(item.detail?.type)
    const method = methodStore.findItemByValue(item.detail?.ope_key)
    const signature = `${type}:${item.detail?.ope_key || ''}:${method?.parameter?.length || 0}:${
      item.detail?.ele_name || item.element_id || ''
    }`
    const cached = inlineEditorCache.get(key)
    if (cached?.signature === signature) return cached.items
    let items: any[] = []
    if ([0, 1].includes(type)) items = buildMethodItems(type, item.detail || {}, item)
    else if (type === 3)
      items = [
        {
          label: '变量名称',
          key: 'key',
          value: item.detail?.custom?.[0]?.key || '',
          type: 'input',
          required: true,
          placeholder: '请输入变量名称',
        },
        {
          label: '变量值',
          key: 'value',
          value: item.detail?.custom?.[0]?.value || '',
          type: 'input',
          required: true,
          placeholder: '请输入变量值',
        },
      ]
    else if (type === 5)
      items = [
        {
          label: 'Python',
          key: 'func',
          value: item.detail?.func || '',
          type: 'code',
          required: true,
          placeholder: '请输入 Python 代码',
        },
      ]
    else if (type === 6)
      items = [
        {
          label: '等待时长',
          key: 'seconds-ope_value',
          field: 'seconds',
          value: item.detail?.ope_value?.find((entry: any) => entry.f === 'seconds')?.v ?? 1,
          type: 'input-number',
          required: true,
          min: 0,
          max: 3600,
          precision: 1,
          suffix: '秒',
          placeholder: '请输入等待秒数',
        },
      ]
    const reactiveItems = reactive(items) as any[]
    inlineEditorCache.set(key, { signature, items: reactiveItems })
    return reactiveItems
  }
  function onInlineMethodChange(item: any, value: any) {
    const next = clone(item)
    next.detail = { ...(next.detail || {}), ope_key: value, ope_value: [] }
    inlineEditorCache.delete(String(item.client_id))
    next.status = isNodeConfigured(next) ? 'ready' : 'review'
    emit('update-action', next)
  }
  function selectedElementId(value: any) {
    return Array.isArray(value) ? value[value.length - 1] : value || null
  }
  function syncInlineConfig(item: any) {
    const next = clone(item)
    const type = Number(next.detail?.type)
    const editorItems = inlineEditorItems(item)
    if ([0, 1].includes(type)) {
      const recordedElementName = editorItems.find(
        (field) => field.key === 'recorded_element_name'
      )?.value
      const recordedElementCategory = editorItems.find(
        (field) => field.key === 'recorded_element_category'
      )?.value
      if (recordedElementName !== undefined) next.name = recordedElementName
      if (recordedElementCategory !== undefined) next.category = recordedElementCategory || '未分类'
      next.detail.ope_key = editorItems.find((field) => field.key === 'ope_key')?.value
      next.detail.ele_name =
        selectedElementId(editorItems.find((field) => field.key === 'ele_name')?.value) ||
        next.detail.ele_name ||
        null
      const selected = selectedElement(next)
      if (selected && (!next.name || next.name === nodeTypeName(type))) next.name = selected.name
      next.detail.ope_value = editorItems
        .filter((field) => field.field)
        .map((field) => ({ f: field.field, v: field.value }))
    } else if (type === 3) {
      next.detail.custom = [
        {
          key: editorItems.find((field) => field.key === 'key')?.value || '',
          value: editorItems.find((field) => field.key === 'value')?.value || '',
        },
      ]
    } else if (type === 5) {
      next.detail.func = editorItems.find((field) => field.key === 'func')?.value || ''
    } else if (type === 6) {
      next.detail.ope_value = [
        {
          f: 'seconds',
          v: Number(editorItems.find((field) => field.key === 'seconds-ope_value')?.value),
        },
      ]
    }
    next.status = isNodeConfigured(next) ? 'ready' : 'review'
    emit('update-action', next)
  }
  function updateSqlField(item: any, field: string, value: any) {
    const next = clone(item)
    const row = { ...(next.detail?.sql_execute?.[0] || {}), [field]: value }
    next.detail.sql_execute = [row]
    next.status = isNodeConfigured(next) ? 'ready' : 'review'
    emit('update-action', next)
  }
  function isNodeConfigured(item: any) {
    const type = Number(item.detail?.type)
    if ([0, 1].includes(type)) {
      if (!item.detail?.ope_key) return false
      const method = methodStore.findItemByValue(item.detail.ope_key)
      const requiresElement = (method?.parameter || []).some((parameter: any) =>
        ['locating', 'actual'].includes(parameter.f)
      )
      if (requiresElement && !item.element && !item.element_id && !item.detail?.ele_name)
        return false
      if (requiresElement && !String(item.name || '').trim()) return false
      return (method?.parameter || [])
        .filter(
          (parameter: any) => parameter.d === true && !['locating', 'actual'].includes(parameter.f)
        )
        .every((parameter: any) => {
          const value = (item.detail?.ope_value || []).find(
            (entry: any) => entry.f === parameter.f
          )?.v
          return value !== undefined && value !== null && value !== ''
        })
    }
    if (type === 2)
      return Boolean(
        item.detail?.sql_execute?.[0]?.datasource_alias &&
          String(item.detail?.sql_execute?.[0]?.sql || '').trim()
      )
    if (type === 3) return Boolean(String(item.detail?.custom?.[0]?.key || '').trim())
    if (type === 5) return Boolean(String(item.detail?.func || '').trim())
    if (type === 6) {
      const seconds = Number(
        item.detail?.ope_value?.find((entry: any) => entry.f === 'seconds')?.v
      )
      return Number.isFinite(seconds) && seconds >= 0 && seconds <= 3600
    }
    return false
  }
  async function loadDatasourceAliases() {
    datasourceAliasOptions.value = []
    if (!props.projectProductId) return
    try {
      const res = await getDataFactoryDatasourceAlias({
        project_product: props.projectProductId,
        status: 1,
        page: 1,
        pageSize: 999,
      })
      datasourceAliasOptions.value = (res.data || []).map((item: any) => ({
        label: item.name,
        value: item.id,
        dbType: Number(item.db_type),
      }))
    } catch (_) {
      Message.warning('逻辑数据源加载失败，请稍后重试')
    }
  }
  async function saveRecording() {
    if (!stepName.value.trim()) {
      Message.warning('请输入步骤名称')
      return
    }
    const invalid = props.actions.some((item) => item.status === 'review' || !item.detail)
    if (invalid) {
      Message.warning('请先完成待确认节点的配置')
      return
    }
    saving.value = true
    try {
      const res = await postUiPageStepRecordingCommit({
        page_id: props.pageId,
        name: stepName.value.trim(),
        nodes: props.actions,
      })
      Message.success(res.msg || '页面步骤保存成功')
      saveVisible.value = false
      emit('saved', res.data || {})
    } catch (error: any) {
      Message.error(error?.msg || '保存页面步骤失败，录制草稿已保留')
    } finally {
      saving.value = false
    }
  }
</script>

<style scoped>
  .mango-step-recorder {
    display: flex;
    min-height: 0;
    flex: 1;
    flex-direction: column;
    border: 1px solid var(--m-border);
    border-radius: 6px;
    background: var(--m-surface);
  }
  .mango-step-recorder__header,
  .mango-step-recorder__footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    padding: 10px 12px;
    border-bottom: 1px solid var(--m-border);
  }
  .mango-step-recorder__header > div {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 3px;
  }
  .mango-step-recorder__header strong {
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .mango-step-recorder__header span,
  .mango-step-recorder__footer span {
    color: var(--m-muted);
    font-size: 12px;
  }
  .mango-step-recorder__dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--m-danger);
  }
  .mango-step-recorder__settings-card {
    margin: 10px;
    padding: 9px 10px;
    border: 1px solid var(--m-border);
    border-radius: 5px;
    background: var(--m-surface-soft);
  }
  .mango-step-recorder__settings {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    margin-top: 8px;
    white-space: nowrap;
  }
  .mango-step-recorder__settings label {
    display: flex;
    min-width: 0;
    align-items: center;
    gap: 6px;
    color: var(--m-text-2);
    font-size: 12px;
    white-space: nowrap;
  }
  .mango-step-recorder__content {
    min-height: 0;
    flex: 1;
    padding: 0 10px 10px;
  }
  .mango-step-recorder__toolbar {
    display: flex;
    gap: 6px;
    margin-bottom: 8px;
  }
  .mango-step-recorder__node-list {
    display: flex;
    max-height: calc(100vh - 470px);
    flex-direction: column;
    gap: 8px;
    overflow: auto;
    padding-right: 3px;
  }
  .mango-step-recorder__node-card {
    padding: 10px;
    border: 1px solid var(--m-border);
    border-left: 3px solid var(--m-primary-border);
    border-radius: 6px;
    background: var(--m-surface);
    transition: border-color 0.2s, box-shadow 0.2s;
  }
  .mango-step-recorder__node-card:hover {
    border-color: var(--m-primary-border);
    box-shadow: var(--m-shadow);
  }
  .mango-step-recorder__node-card.is-dragging {
    opacity: 0.55;
  }
  .mango-step-recorder__node-card.is-review {
    border-left-color: var(--m-warning);
  }
  .mango-step-recorder__node-head,
  .mango-step-recorder__node-title {
    display: flex;
    min-width: 0;
    align-items: center;
  }
  .mango-step-recorder__node-head {
    justify-content: space-between;
    gap: 8px;
  }
  .mango-step-recorder__node-title {
    flex: 1;
    gap: 8px;
  }
  .mango-step-recorder__node-title > div {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 2px;
  }
  .mango-step-recorder__node-title > div strong {
    color: var(--m-text);
    font-size: 13px;
  }
  .mango-step-recorder__node-title > div span {
    overflow: hidden;
    color: var(--m-muted);
    font-size: 12px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .mango-step-recorder__node-index {
    color: var(--m-primary);
    font-size: 13px;
  }
  .mango-step-recorder__handle {
    cursor: grab;
    color: var(--m-muted);
    font-size: 16px;
    line-height: 1;
  }
  .mango-step-recorder__sql-grid label {
    display: flex;
    min-width: 0;
    align-items: center;
    gap: 8px;
    color: var(--m-text-2);
    font-size: 12px;
  }
  .mango-step-recorder__sql-grid label > span {
    flex: 0 0 auto;
  }
  .mango-step-recorder__inline-editor :deep(.arco-form-item) {
    margin-bottom: 8px;
  }
  .mango-step-recorder__inline-editor :deep(.arco-form-item:last-child) {
    margin-bottom: 0;
  }
  .mango-step-recorder__sql-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
  }
  .mango-step-recorder__sql-grid label {
    align-items: flex-start;
    flex-direction: column;
    gap: 4px;
  }
  .mango-step-recorder__sql-grid label > :deep(.arco-select-view),
  .mango-step-recorder__sql-grid label > :deep(.arco-input-wrapper),
  .mango-step-recorder__sql-grid label > :deep(.arco-textarea-wrapper) {
    width: 100%;
  }
  .mango-step-recorder__sql-grid .is-wide {
    grid-column: 1 / -1;
  }
  .mango-step-recorder__empty {
    min-height: 180px;
  }
  .mango-step-recorder__footer {
    border-top: 1px solid var(--m-border);
    border-bottom: 0;
  }
  @media (max-width: 760px) {
    .mango-step-recorder__sql-grid {
      grid-template-columns: minmax(0, 1fr);
    }
    .mango-step-recorder__sql-grid .is-wide {
      grid-column: 1;
    }
    .mango-step-recorder__node-head {
      align-items: flex-start;
    }
  }
</style>
