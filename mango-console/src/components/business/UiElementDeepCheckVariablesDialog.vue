<template>
  <ModalDialog
    ref="dialogRef"
    title="深度检测临时变量"
    width="720px"
    @confirm="confirm"
    @cancel="cancel"
  >
    <template #content>
      <div class="mango-ui-deep-check-variables">
        <section class="mango-soft-panel mango-ui-deep-check-variables__element">
          <div>
            <span>元素名称</span>
            <strong>{{ element.name || '-' }}</strong>
          </div>
          <div>
            <span>元素分类</span>
            <strong>{{ element.category || '未分类' }}</strong>
          </div>
        </section>

        <section class="mango-ui-deep-check-variables__sources">
          <div class="mango-section-title">
            <div class="mango-section-title__main">
              <h3>包含变量的元素信息</h3>
              <p>以下内容包含 {{ variableSyntax }}，临时值仅用于本次深度检测。</p>
            </div>
          </div>
          <div
            v-for="item in sources"
            :key="item.field"
            class="mango-ui-deep-check-variables__source"
          >
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
          </div>
        </section>

        <section class="mango-ui-deep-check-variables__values">
          <div class="mango-section-title">
            <div class="mango-section-title__main">
              <h3>检测变量</h3>
              <p>
                自动识别的变量会预先带入，也可以手动新增多组；Value 留空时不替换。
              </p>
            </div>
            <a-button size="small" type="outline" @click="addVariable">新增变量</a-button>
          </div>
          <div
            v-for="(item, index) in variables"
            :key="item.id"
            class="mango-ui-deep-check-variables__row"
          >
            <a-input
              v-model="item.key"
              :input-attrs="{ name: `deep_check_variable_key_${index}` }"
              placeholder="请输入 Key"
            />
            <span>替换为</span>
            <a-input
              v-model="item.value"
              :input-attrs="{ name: `deep_check_variable_value_${index}` }"
              allow-clear
              placeholder="可不填；留空时不替换"
            />
            <a-button size="small" status="danger" type="text" @click="removeVariable(index)">
              删除
            </a-button>
          </div>
          <a-empty v-if="!variables.length" description="暂无检测变量，可点击新增变量手动添加" />
        </section>
      </div>
    </template>
  </ModalDialog>
</template>

<script lang="ts" setup>
  import { reactive, ref, watch } from 'vue'
  import ModalDialog from '@/components/overlays/ModalDialog.vue'

  type DeepCheckSource = {
    field: string
    label: string
    value: string
  }

  type DeepCheckVariable = {
    id: number
    key: string
    value: string
  }

  type DeepCheckVariables = Record<string, string>

  const dialogRef = ref<InstanceType<typeof ModalDialog> | null>(null)
  const variableSyntax = '${{...}}'
  const element = reactive<Record<string, any>>({})
  const sources = ref<DeepCheckSource[]>([])
  const variables = ref<DeepCheckVariable[]>([])
  let sequence = 0
  let resolver: ((value: DeepCheckVariables | null) => void) | null = null

  watch(
    () => dialogRef.value?.showModal,
    (visible, previous) => {
      if (previous === true && visible === false && resolver) {
        resolver(null)
        resolver = null
      }
    }
  )

  const sourceFields = [
    ['page_url', '页面 URL'],
    ['name', '元素名称'],
    ['prompt', 'AI 提示词'],
    ['loc', '第一组定位表达式'],
    ['loc2', '第二组定位表达式'],
    ['loc3', '第三组定位表达式'],
  ] as const

  function extract(record: Record<string, any>) {
    const matchedSources: DeepCheckSource[] = []
    const keys: string[] = []
    sourceFields.forEach(([field, label]) => {
      const value = String(record?.[field] || '')
      const matches = [...value.matchAll(/\$\{\{([\s\S]*?)\}\}/g)]
      if (!matches.length) return
      matchedSources.push({ field, label, value })
      matches.forEach((match) => {
        const key = String(match[1] ?? '').trim()
        if (!keys.includes(key)) keys.push(key)
      })
    })
    return { matchedSources, keys }
  }

  async function open(record: Record<string, any>): Promise<DeepCheckVariables | null> {
    const { matchedSources, keys } = extract(record || {})
    if (!matchedSources.length) return {}
    Object.keys(element).forEach((key) => delete element[key])
    Object.assign(element, record || {})
    sources.value = matchedSources
    variables.value = keys.map((key) => ({ id: ++sequence, key, value: '' }))
    return new Promise((resolve) => {
      resolver = resolve
      void dialogRef.value?.show()
    })
  }

  function addVariable() {
    variables.value.push({ id: ++sequence, key: '', value: '' })
  }

  function removeVariable(index: number) {
    variables.value.splice(index, 1)
  }

  function confirm() {
    const result = variables.value.reduce<DeepCheckVariables>((data, item) => {
      const key = item.key.trim()
      if (key && item.value !== '') data[key] = item.value
      return data
    }, {})
    dialogRef.value?.setConfirmLoading(false)
    void dialogRef.value?.close()
    resolver?.(result)
    resolver = null
  }

  function cancel() {
    resolver?.(null)
    resolver = null
  }

  defineExpose({ open })
</script>

<style scoped>
  .mango-ui-deep-check-variables {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .mango-ui-deep-check-variables__element {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
    padding: 12px;
  }

  .mango-ui-deep-check-variables__element > div,
  .mango-ui-deep-check-variables__source {
    display: flex;
    min-width: 0;
    gap: 10px;
  }

  .mango-ui-deep-check-variables__element span,
  .mango-ui-deep-check-variables__source span {
    flex: 0 0 118px;
    color: var(--m-muted);
  }

  .mango-ui-deep-check-variables__element strong,
  .mango-ui-deep-check-variables__source strong {
    min-width: 0;
    overflow-wrap: anywhere;
  }

  .mango-ui-deep-check-variables__sources,
  .mango-ui-deep-check-variables__values {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .mango-ui-deep-check-variables__source {
    padding: 8px 10px;
    background: var(--m-surface-soft);
  }

  .mango-ui-deep-check-variables__row {
    display: grid;
    grid-template-columns: minmax(180px, 0.8fr) auto minmax(240px, 1.2fr) auto;
    align-items: center;
    gap: 8px;
  }

  .mango-ui-deep-check-variables__row > span {
    color: var(--m-muted);
  }
</style>
