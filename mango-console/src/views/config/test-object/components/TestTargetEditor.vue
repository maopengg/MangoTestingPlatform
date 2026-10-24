<template>
  <a-form-item label="默认地址">
    <a-input
      v-model="draft.default"
      :max-length="1024"
      placeholder="域名/包名/路径（可选）；未匹配时使用此地址"
      @input="emitConfig"
    />
  </a-form-item>
  <a-form-item label="条件变量">
    <a-input
      v-model="draft.selector"
      :max-length="128"
      placeholder="缓存键名，例如租户id；留空使用固定地址"
      @input="emitConfig"
    />
  </a-form-item>
  <template v-if="draft.selector">
    <a-form-item label="地址映射">
      <div class="mango-target-mapping">
        <div class="mango-target-mapping-toolbar">
          <span>已配置 {{ rows.length }} 项 · 按条件值精确匹配，未匹配时使用默认地址</span>
          <a-button size="small" :disabled="rows.length >= 200" @click="addRow">新增映射</a-button>
        </div>
        <div v-if="rows.length" class="mango-target-mapping-header" aria-hidden="true">
          <span>条件值</span><span>对应地址</span><span>操作</span>
        </div>
        <div v-for="(row, index) in rows" :key="row.id" class="mango-target-mapping-row">
          <a-input
            v-model="row.key"
            placeholder="租户 ID，例如 1001"
            :aria-label="`第 ${index + 1} 项条件值`"
            @input="emitConfig"
          />
          <a-input
            v-model="row.value"
            placeholder="对应域名/包名/路径"
            :max-length="1024"
            :aria-label="`第 ${index + 1} 项地址`"
            @input="emitConfig"
          />
          <a-button status="danger" size="small" @click="removeRow(index)">删除</a-button>
        </div>
        <div v-if="!rows.length" class="mango-target-mapping-empty"
          >点击「新增映射」，填写租户 ID 与对应地址</div
        >
        <div v-if="duplicateKey" class="mango-target-error">条件值不能重复</div>
      </div>
    </a-form-item>
  </template>
</template>

<script setup lang="ts">
  import { computed, reactive, ref, toRaw, watch } from 'vue'
  import type { TestTargetConfig } from '../target-config'
  const props = defineProps<{ modelValue: TestTargetConfig }>()
  const emit = defineEmits<{ 'update:modelValue': [value: TestTargetConfig] }>()
  const draft = reactive({ ...props.modelValue })
  let sequence = 0
  const rows = ref<{ id: number; key: string; value: string }[]>([])
  const duplicateKey = computed(
    () => new Set(rows.value.map((row) => row.key)).size !== rows.value.length
  )
  let lastEmission: TestTargetConfig | undefined
  watch(
    () => props.modelValue,
    (value) => {
      // 父级 ref 会把回传配置包装成代理，不能因此重建正在输入的行。
      if (toRaw(value) === lastEmission) return
      Object.assign(draft, value)
      rows.value = Object.entries(value.mapping || {}).map(([key, value]) => ({
        id: ++sequence,
        key,
        value,
      }))
    },
    { immediate: true }
  )
  function emitConfig() {
    const mapping = Object.fromEntries(rows.value.map((row) => [row.key, row.value]))
    // 重复 key 不能在转成对象时被悄悄覆盖；空 key 使提交校验明确失败。
    if (duplicateKey.value) mapping[''] = ''
    lastEmission = {
      default: draft.default,
      selector: draft.selector,
      mapping: draft.selector ? mapping : {},
    }
    emit('update:modelValue', lastEmission)
  }
  function addRow() {
    rows.value.push({ id: ++sequence, key: '', value: '' })
    emitConfig()
  }
  function removeRow(index: number) {
    rows.value.splice(index, 1)
    emitConfig()
  }
</script>

<style scoped>
  .mango-target-mapping {
    width: 100%;
    display: grid;
    gap: 8px;
  }
  .mango-target-mapping-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 8px;
    color: var(--m-muted);
    font-size: 13px;
  }
  .mango-target-mapping-row,
  .mango-target-mapping-header {
    display: grid;
    grid-template-columns: minmax(100px, 1fr) minmax(160px, 2fr) 56px;
    gap: 8px;
  }
  .mango-target-mapping-header {
    padding: 8px 0;
    color: var(--m-muted);
    font-size: 13px;
    border-bottom: 1px solid var(--m-border);
  }
  .mango-target-mapping-empty {
    padding: 32px 16px;
    border: 1px dashed var(--m-border);
    border-radius: var(--m-radius);
    color: var(--m-muted);
    text-align: center;
  }
  .mango-target-error {
    color: var(--m-danger);
  }
  @media (max-width: 760px) {
    .mango-target-mapping-row {
      grid-template-columns: minmax(0, 1fr);
      padding-bottom: 12px;
      border-bottom: 1px solid var(--m-border);
    }
    .mango-target-mapping-header {
      display: none;
    }
  }
</style>
