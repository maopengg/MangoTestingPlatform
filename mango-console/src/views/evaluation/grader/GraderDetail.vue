<template>
  <div class="mango-grader-explanation">
    <div class="mango-grader-explanation-meta">
      <a-tag size="small">{{ formatVersion(detail.grader_version) }}</a-tag>
      <span>{{ isModel ? '使用用例中选择的评分 AI' : '按固定规则计算，无需评分 AI' }}</span>
    </div>
    <a-tabs v-model:active-key="activeTab" class="mango-grader-explanation-tabs" size="small">
      <a-tab-pane key="configuration" title="配置">
        <div class="mango-grader-guide-content">
        <section class="mango-grader-guide-section mango-grader-guide-purpose">
          <h3>用它测什么</h3>
          <p>{{ guide?.purpose || detail.description || '暂无适用说明' }}</p>
        </section>
        <template v-if="guide">
          <section class="mango-grader-guide-section">
            <h3>需要准备什么</h3>
            <dl class="mango-grader-guide-fields">
              <div v-for="field in requirements" :key="field.label"><dt>{{ field.label }}</dt><dd>{{ field.value }}</dd></div>
            </dl>
          </section>
          <section class="mango-grader-guide-section">
            <h3>平台如何评分</h3>
            <ol class="mango-grader-guide-steps"><li v-for="step in guide.steps" :key="step">{{ step }}</li></ol>
          </section>
          <section class="mango-grader-guide-section">
            <h3>分数与判定</h3>
            <p class="mango-grader-guide-scoring">{{ guide.scoring }}</p>
            <p class="mango-grader-guide-note"><strong>判定边界</strong>{{ guide.boundary }}</p>
            <p class="mango-grader-guide-note"><strong>通过设置</strong>通过阈值与权重在用例的评分项中设置；权重影响综合分，各项是否通过仍按对应规则判断。</p>
          </section>
        </template>
        <section class="mango-grader-guide-section">
          <h3>可调参数</h3>
          <p class="mango-grader-guide-note">在用例的评分项中点击“参数”设置；此处只说明作用。</p>
          <dl v-if="parameters.length" class="mango-grader-guide-fields">
            <div v-for="parameter in parameters" :key="parameter.key">
              <dt>{{ parameter.label }}</dt>
              <dd>{{ parameterHelp[parameter.path] || '按此项约束核对实际输出。' }}
                <span v-if="parameter.description !== '—'" class="mango-grader-guide-constraint">{{ parameter.description }}</span>
              </dd>
            </div>
          </dl>
          <p v-else>该评分器没有额外参数。</p>
        </section>
        </div>
      </a-tab-pane>
      <a-tab-pane key="example" title="示例说明">
        <div class="mango-grader-guide-content">
        <template v-if="guide && example">
          <p class="mango-grader-guide-note">以下为前端演示数据。切换情形可查看评分过程，不会调用接口或 AI。</p>
          <a-radio-group v-model="exampleIndex" type="button" size="small" class="mango-grader-example-switch" aria-label="选择评分示例">
            <a-radio v-for="(item, index) in guide.examples" :key="item.title" :value="index">{{ item.title }}</a-radio>
          </a-radio-group>
          <ol class="mango-grader-example-flow">
            <li>
              <h3>测评条目提供标准</h3>
              <dl class="mango-grader-guide-fields"><div v-for="field in fields" :key="field.label"><dt>{{ field.label }}</dt><dd>{{ field.value }}</dd></div></dl>
            </li>
            <li><h3>被测接口或脚本返回结果</h3><p class="mango-grader-example-actual">{{ example.actual }}</p></li>
            <li><h3>评分器核对：{{ detail.name }}</h3><p>{{ example.reason }}</p></li>
            <li>
              <h3>记录评分结果</h3>
              <div class="mango-grader-example-result" aria-live="polite" aria-atomic="true">
                <strong>{{ example.score == null ? '不计分' : `${example.score} 分` }}</strong>
                <a-tag size="small" :color="example.score == null ? 'orange' : example.score === 100 ? 'green' : 'orangered'">{{ example.outcome }}</a-tag>
              </div>
              <p class="mango-grader-guide-note">{{ example.score == null ? '本条记为无效，单独统计有效率，不作为能力零分。' : '实际执行时，本条结果参与本次执行的汇总。' }}</p>
            </li>
          </ol>
        </template>
        <div v-else class="mango-empty-state">该版本尚未提供前端演示，请查看“配置”中的适用说明与参数要求。</div>
        </div>
      </a-tab-pane>
    </a-tabs>
  </div>
</template>
<script setup lang="ts">
  import { computed, ref, watch } from 'vue'
  import { formatVersion, schemaRows } from '../components/presentation'
  import { exampleFields, getGraderGuide } from './guide'
  const props = defineProps<{ detail: Record<string, any> }>()
  const activeTab = ref('configuration')
  const exampleIndex = ref(0)
  const guide = computed(() => getGraderGuide(props.detail.grader_key, props.detail.grader_version))
  const isModel = computed(() => props.detail.category === 'model')
  const example = computed(() => guide.value?.examples[exampleIndex.value])
  const fields = computed(() => guide.value && example.value ? exampleFields(guide.value, example.value) : [])
  const parameters = computed(() => schemaRows(props.detail.parameters_schema).filter(row => row.path !== 'normalize'))
  const requirements = computed(() => {
    const key = props.detail.grader_key
    const memories: Record<string, string> = {
      memory_qa: '标准答案和来源原文；可以额外列出必须答到的事实。',
      memory_extraction: '应提取的标准记忆列表，以及原始对话或事实来源。',
      memory_update: '每个更新目标的旧事实、新事实，以及证明变化的原文。',
    }
    return [
      { label: '测评数据', value: memories[key] || '标准值、标准标签或结构要求，具体内容取决于本评分器。' },
      { label: '被测输出', value: key === 'memory_qa' ? '最终回答文本；只有召回片段时，先在用例中启用回答生成。' : ['memory_extraction', 'memory_update'].includes(key) ? '被测接口或脚本返回的记忆文本列表；必要时用响应提取选中该列表。' : '接口或脚本的实际结果；可在用例中通过响应提取选中需要评分的内容。' },
      ...(isModel.value ? [{ label: '评分 AI', value: '在用例中选择评分模型。回答 AI 负责生成答案，总结 AI 负责汇总结果，均不代替评分 AI。' }] : []),
    ]
  })
  const parameterHelp: Record<string, string> = {
    expected_path: '从标准输出中选取要比较的值；留空使用整个标准输出。',
    actual_path: '从实际输出中选取要比较的值；留空使用整个实际输出。',
    max_tokens: '限制评分 AI 输出核对过程与理由的长度，不是分数或通过阈值。',
    confidence_threshold: '低于此置信度的 AI 裁判结果将标为无效。',
    rubric: '描述评分要求、分数档位及判定依据，评分 AI 会按这些要求核对回答。',
    k: '只评估返回列表的前 K 项；留空按实际列表长度确定，实际为空时再参考标准列表长度。',
    absolute_tolerance: '允许的固定数值误差。', relative_tolerance: '允许的误差占标准数值绝对值的比例，例如 0.02 表示 2%。',
    schema: '指定必填字段、字段类型等结构要求。',
    'normalize.trim': '比较文本前去除首尾空格。', 'normalize.casefold': '比较文本前忽略大小写。',
  }
  watch(() => [props.detail.grader_key, props.detail.grader_version], () => {
    activeTab.value = 'configuration'
    exampleIndex.value = 0
  })
</script>
<style scoped>
  .mango-grader-explanation { display: flex; flex-direction: column; flex: 1; min-height: 0; min-width: 0; color: var(--m-text); font-size: var(--m-font-body); container-type: inline-size; }
  .mango-grader-explanation-meta { display: flex; align-items: center; gap: var(--m-space-sm); margin-bottom: var(--m-space-sm); color: var(--m-muted); flex-wrap: wrap; }
  .mango-grader-explanation-tabs { display: flex; flex-direction: column; flex: 1; min-height: 0; min-width: 0; }
  .mango-grader-explanation-tabs :deep(> .arco-tabs-nav) { flex-shrink: 0; }
  .mango-grader-explanation-tabs :deep(> .arco-tabs-content) { flex: 1; min-height: 0; overflow-y: auto; overflow-x: hidden; padding-top: var(--m-page-gap); }
  .mango-grader-guide-content { max-width: 960px; padding: var(--m-space-sm) var(--m-space-md) var(--m-space-lg); }
  .mango-grader-guide-section { margin-bottom: 24px; }
  h3 { color: var(--m-text); font-size: var(--m-font-subtitle); font-weight: 600; line-height: 1.5; margin: 0 0 var(--m-space-md); text-wrap: balance; }
  p { margin: 0; line-height: 1.8; overflow-wrap: anywhere; text-wrap: pretty; }
  .mango-grader-guide-purpose { padding-bottom: var(--m-space-lg); border-bottom: 1px solid var(--m-border); }
  .mango-grader-guide-purpose p { font-size: var(--m-font-subtitle); color: var(--m-text-2); }
  .mango-grader-guide-scoring { background: var(--m-surface-soft); padding: var(--m-space-md) var(--m-space-lg); border-radius: var(--m-radius-sm); font-weight: 500; }
  .mango-grader-guide-note { color: var(--m-text-2); margin-top: var(--m-space-md); font-size: var(--m-font-body); }
  .mango-grader-guide-note strong { font-weight: 600; margin-right: var(--m-space-sm); color: var(--m-text); }
  .mango-grader-guide-fields { margin: var(--m-space-sm) 0 0; }
  .mango-grader-guide-fields > div { display: grid; grid-template-columns: 112px minmax(0, 1fr); gap: var(--m-space-lg); padding: var(--m-space-md) 0; border-bottom: 1px solid var(--m-border); }
  .mango-grader-guide-fields dt { color: var(--m-text-2); font-weight: 500; line-height: 1.7; overflow-wrap: anywhere; }
  .mango-grader-guide-fields dd { margin: 0; line-height: 1.7; white-space: pre-wrap; overflow-wrap: anywhere; }
  .mango-grader-guide-constraint { display: block; margin-top: var(--m-space-xs); color: var(--m-text-2); font-size: var(--m-font-caption); }
  .mango-grader-guide-steps { margin: 0; padding-left: 24px; line-height: 1.8; list-style: decimal; }
  .mango-grader-guide-steps > li { padding-left: var(--m-space-xs); margin-bottom: var(--m-space-sm); overflow-wrap: anywhere; }
  .mango-grader-guide-steps > li::marker { color: var(--m-primary); font-weight: 600; font-variant-numeric: tabular-nums; }
  .mango-grader-example-switch { margin: var(--m-page-gap) 0; display: flex; flex-wrap: wrap; gap: var(--m-space-sm); }
  .mango-grader-example-flow { padding-left: 24px; margin: 0; list-style: decimal; }
  .mango-grader-example-flow > li { padding-left: var(--m-space-sm); margin-bottom: 24px; }
  .mango-grader-example-flow > li::marker { color: var(--m-primary); font-weight: 600; font-variant-numeric: tabular-nums; }
  .mango-grader-example-actual { white-space: pre-wrap; padding: var(--m-page-gap); border-radius: var(--m-radius-sm); background: var(--m-surface-soft); }
  .mango-grader-example-result { display: flex; align-items: center; flex-wrap: wrap; gap: var(--m-space-sm); font-variant-numeric: tabular-nums; }
  .mango-grader-example-result strong { font-size: var(--m-font-title); line-height: 1.5; color: var(--m-text); }
  @container (max-width: 440px) { .mango-grader-guide-fields > div { grid-template-columns: minmax(0, 1fr); gap: 4px; } }
</style>
