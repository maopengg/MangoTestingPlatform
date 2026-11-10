<template>
  <section v-if="sequence !== 'independent'" class="mango-scenario-editor">
    <div class="mango-section-title"
      ><h3 class="mango-scenario-heading">{{
        sequence === 'timeline' ? '时序步骤' : '多轮对话'
      }}</h3
      ><a-button v-if="!disabled" size="small" @click="addTurn">添加轮次</a-button></div
    >
    <div class="mango-scenario-body">
      <a-form-item label="用户／会话组"
        ><a-input
          :model-value="modelValue?.group_key || ''"
          :disabled="disabled"
          placeholder="相同组共享准备数据和会话；留空表示本条独立"
          @update:model-value="update({ group_key: $event })"
      /></a-form-item>
      <a-form-item label="组内顺序"
        ><a-input-number
          :model-value="modelValue?.order || 0"
          :min="0"
          :disabled="disabled"
          @change="update({ order: $event })"
      /></a-form-item>
      <article
        v-for="(turn, index) in modelValue?.turns || []"
        :key="index"
        class="mango-scenario-turn"
      >
        <div class="mango-section-title"
          ><h4 class="mango-scenario-subheading">第 {{ index + 1 }} 轮</h4
          ><MangoTableActions
            :actions="
              disabled
                ? []
                : [
                    { label: '上移', disabled: index === 0, onClick: () => move(index) },
                    { label: '移除', danger: true, onClick: () => remove(index) },
                  ]
            "
        /></div>
        <div class="mango-scenario-body">
          <a-form-item label="轮次名称"
            ><a-input
              :model-value="turn.name"
              :disabled="disabled"
              @update:model-value="setTurn(index, { name: $event })"
          /></a-form-item>
          <a-form-item v-if="sequence === 'timeline'" label="步骤类型"
            ><a-select
              :model-value="turn.kind || 'test'"
              :options="turnKinds"
              :disabled="disabled"
              @change="setTurn(index, { kind: $event, score: $event !== 'material' })"
          /></a-form-item>
          <a-form-item label="本轮输入"
            ><DataFieldsEditor
              :model-value="turn.input_data"
              :disabled="disabled"
              @update:model-value="setTurn(index, { input_data: $event })"
          /></a-form-item>
          <a-form-item v-if="turn.kind !== 'material'" label="参与评分"
            ><a-switch
              :model-value="turn.score !== false"
              :disabled="disabled"
              size="small"
              @change="setTurn(index, { score: Boolean($event) })"
          /></a-form-item>
          <template v-if="turn.score !== false">
            <a-form-item label="预期输出"
              ><DataFieldsEditor
                :model-value="turn.expected_output"
                :disabled="disabled"
                @update:model-value="setTurn(index, { expected_output: $event })"
            /></a-form-item>
            <a-form-item label="原文证据"
              ><DataFieldsEditor
                :model-value="turn.context"
                :disabled="disabled"
                @update:model-value="setTurn(index, { context: $event })"
            /></a-form-item>
          </template>
        </div>
      </article>
    </div>
  </section>
</template>
<script setup lang="ts">
  import DataFieldsEditor from './DataFieldsEditor.vue'
  import { computed } from 'vue'
  import { useEvaluationEnums } from './useEvaluationEnums'
  import type { DatasetItemScenario, DatasetScenarioTurn } from '../dataset/types'
  const { options } = useEvaluationEnums()
  const turnKinds = computed(() => options('evaluation_turn_kind'))
  const props = withDefaults(
    defineProps<{ modelValue: DatasetItemScenario; sequence: string; disabled?: boolean }>(),
    { disabled: false }
  )
  const emit = defineEmits<{ (event: 'update:modelValue', value: DatasetItemScenario): void }>()
  const update = (value: Partial<DatasetItemScenario>) => {
    if (props.disabled) return
    emit('update:modelValue', { group_key: '', order: 0, turns: [], ...props.modelValue, ...value })
  }
  function addTurn() {
    update({
      turns: [
        ...(props.modelValue?.turns || []),
        { name: '', input_data: {}, expected_output: {}, context: {}, score: true },
      ],
    })
  }
  function setTurn(index: number, value: Partial<DatasetScenarioTurn>) {
    if (!props.modelValue.turns[index]) return
    update({
      turns: props.modelValue.turns.map((turn, i) => (i === index ? { ...turn, ...value } : turn)),
    })
  }
  function remove(index: number) {
    if (!props.modelValue.turns[index]) return
    update({ turns: props.modelValue.turns.filter((_, i) => i !== index) })
  }
  function move(index: number) {
    if (index <= 0 || index >= props.modelValue.turns.length) return
    const turns = [...props.modelValue.turns]
    ;[turns[index], turns[index - 1]] = [turns[index - 1], turns[index]]
    update({ turns })
  }
</script>
<style scoped>
  .mango-scenario-editor {
    min-width: 0;
  }
  .mango-scenario-heading {
    margin: 0;
    font-size: 15px;
    font-weight: 600;
    line-height: 24px;
  }
  .mango-scenario-subheading {
    margin: 0;
    font-size: 13px;
    font-weight: 500;
    line-height: 20px;
  }
  .mango-scenario-body {
    padding-inline-start: 16px;
    margin-top: var(--m-page-gap);
    min-width: 0;
  }
  .mango-scenario-editor .mango-section-title {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--m-page-gap);
  }
  .mango-scenario-turn {
    padding-block: var(--m-card-padding);
    border-top: 1px solid var(--m-border);
    margin-top: var(--m-page-gap);
  }
</style>
