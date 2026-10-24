<!-- eslint-disable vue/no-mutating-props -->
<template>
  <a-tabs :active-key="activeKey" @tab-click="emit('change', String($event))">
    <template #extra>
      <a-button v-if="canAdd" size="small" type="primary" :disabled="editLocked" @click="addItem"
        >增加</a-button
      >
    </template>
    <a-tab-pane key="40" title="响应JSON提取">
      <div class="m-2 mango-horizontal-scroll-region">
        <TipMessage message="从响应JSON中提取，请输入JSONPath表达式并点击测试" />
        <KeyValueList
          :data-list="item.posterior_response"
          :field-config="jsonFields"
          :on-delete-item="(index) => removeItem('posterior_response', index)"
          :on-save="() => saveField('posterior_response')"
          @update:item="(index, value) => updateItem('posterior_response', index, value)"
          empty-text='暂无响应结果提取，点击上方"增加"按钮添加'
        >
          <template #extra="{ index }">
            <a-button size="small" status="success" @click="testExtract('jsonpath', index)"
              >测试</a-button
            >
          </template>
        </KeyValueList>
      </div>
    </a-tab-pane>
    <a-tab-pane key="44" title="响应文本提取">
      <div class="m-2 mango-horizontal-scroll-region">
        <KeyValueList
          :data-list="item.posterior_response_text"
          :field-config="textFields"
          :on-delete-item="(index) => removeItem('posterior_response_text', index)"
          :on-save="() => saveField('posterior_response_text')"
          @update:item="(index, value) => updateItem('posterior_response_text', index, value)"
          empty-text='暂无响应结果提取，点击上方"增加"按钮添加'
        >
          <template #extra="{ index }">
            <a-button size="small" status="success" @click="testExtract('re', index)"
              >测试</a-button
            >
          </template>
        </KeyValueList>
      </div>
    </a-tab-pane>
    <a-tab-pane key="41" title="后置数据库">
      <div class="m-2">
        <DataSourceOperationList
          :data-list="item.posterior_sql"
          :datasource-options="datasourceOptions"
          :environment-options="environmentOptions"
          :project-product-id="projectProductId"
          :test-env="testEnv"
          :on-delete-item="(index) => removeItem('posterior_sql', index)"
          :on-save="() => saveField('posterior_sql')"
          @update:item="(index, value) => updateItem('posterior_sql', index, value)"
          empty-text="暂无数据库操作配置，点击上方“增加”按钮添加"
        />
      </div>
    </a-tab-pane>
    <a-tab-pane key="42" title="强制等待">
      <div class="mango-api-wait-config">
        <div class="mango-api-wait-config__field">
          <span class="mango-api-wait-config__label">等待时间</span>
          <a-input-number
            v-model="item.posterior_sleep"
            :disabled="editLocked"
            :min="0"
            :max="32767"
            :precision="0"
            placeholder="请输入等待时间"
            class="sleep-input"
            hide-button
            @blur="saveField('posterior_sleep')"
          >
            <template #suffix>秒</template>
          </a-input-number>
        </div>
        <div
          class="mango-api-wait-config__hint"
          :class="{ 'mango-api-wait-config__hint--warning': isLongWait }"
        >
          {{ waitHint }}
        </div>
      </div>
    </a-tab-pane>
    <a-tab-pane key="43" title="后置函数">
      <div class="m-2">
        <CodeEditor
          v-model="item.posterior_func"
          :readonly="editLocked"
          :line-height="280"
          :code-style="{ width: '100%' }"
          placeholder="根据帮助文档，输入自定义后置函数"
          @focus="codeSnapshot = item.posterior_func"
          @blur="saveCode"
        />
      </div>
    </a-tab-pane>
  </a-tabs>
</template>

<script setup lang="ts">
  /* eslint-disable vue/no-mutating-props */
  import { computed, ref } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import {
    postCaseDetailedParameterTestExtractResponseAfter,
    putApiCaseDetailedParameter,
  } from '@/api/apitest/case-detailed-parameter'
  import CodeEditor from '@/components/editors/CodeEditor.vue'
  import DataSourceOperationList from '@/components/forms/DataSourceOperationList.vue'
  import KeyValueList from '@/components/forms/KeyValueList.vue'
  import TipMessage from '@/components/feedback/TipMessage.vue'

  type PosteriorListField = 'posterior_response' | 'posterior_response_text' | 'posterior_sql'
  type PosteriorField = PosteriorListField | 'posterior_sleep' | 'posterior_func'
  const props = withDefaults(
    defineProps<{
      item: any
      activeKey: string
      editLocked: boolean
      datasourceOptions?: any[]
      environmentOptions?: any[]
      projectProductId?: string | number
      testEnv?: string | number
    }>(),
    {
      datasourceOptions: () => [],
      environmentOptions: () => [],
    }
  )
  const emit = defineEmits<{ (event: 'change', value: string): void }>()
  const codeSnapshot = ref<any>()
  const jsonFields = [
    { field: 'value', label: 'JSONPath语法', placeholder: '请输入JSONPath语法' },
    { field: 'key', label: 'Key', placeholder: '请输入缓存Key' },
  ]
  const textFields = [
    { field: 'value', label: '正则语法', placeholder: '请输入正则语法' },
    { field: 'key', label: 'Key', placeholder: '请输入缓存Key' },
  ]
  const canAdd = computed(() => ['40', '41', '44'].includes(props.activeKey))
  const isLongWait = computed(
    () =>
      Number.isFinite(Number(props.item.posterior_sleep)) &&
      Number(props.item.posterior_sleep) > 1800
  )
  const waitHint = computed(() => {
    const value = props.item.posterior_sleep
    if (value === null || value === undefined || value === '')
      return '接口响应后暂停执行，单位为秒，支持 0～32767 秒'
    const seconds = Number(value)
    if (!Number.isFinite(seconds)) return '请输入有效的等待秒数'
    if (seconds < 60) return `接口响应后等待 ${seconds} 秒再继续执行`
    const readable =
      seconds < 3600
        ? `${Number((seconds / 60).toFixed(1))} 分钟`
        : `${Number((seconds / 3600).toFixed(1))} 小时`
    return `当前为 ${seconds} 秒（约 ${readable}）${
      isLongWait.value ? '；超过 30 分钟可能触发任务超时重领' : ''
    }`
  })

  function addItem() {
    if (props.editLocked) return
    if (props.activeKey === '40') props.item.posterior_response.push({ key: '', value: '' })
    if (props.activeKey === '44') props.item.posterior_response_text.push({ key: '', value: '' })
    if (props.activeKey === '41')
      props.item.posterior_sql.push({ key: '', value: '', datasource_alias: null, test_envs: [] })
  }
  async function saveField(field: PosteriorField) {
    if (props.editLocked) return
    try {
      const response = await putApiCaseDetailedParameter({
        id: props.item.id,
        [field]: props.item[field],
      })
      Message.success(response.msg)
    } catch (error: any) {
      Message.error(error?.msg || '后置处理保存失败')
    }
  }
  function removeItem(field: PosteriorListField, index: number) {
    if (props.editLocked) return
    props.item[field].splice(index, 1)
    void saveField(field)
  }
  function updateItem(field: PosteriorListField, index: number, value: any) {
    if (props.editLocked) return
    props.item[field][index] = value
    void saveField(field)
  }
  function saveCode() {
    if (codeSnapshot.value !== props.item.posterior_func) void saveField('posterior_func')
  }
  async function testExtract(type: 'jsonpath' | 're', index: number) {
    const response = props.item.result_data?.response
    if (!response) return Message.error('暂无执行响应，无法测试提取')
    const source = type === 'jsonpath' ? response.json : response.text
    if (source === null || source === undefined || source === '')
      return Message.error(
        type === 'jsonpath' ? '响应JSON为空，无法测试' : '响应文本为空，无法测试'
      )
    const expression =
      type === 'jsonpath'
        ? props.item.posterior_response?.[index]
        : props.item.posterior_response_text?.[index]
    if (!expression) return Message.error('提取配置不存在')
    try {
      const result = await postCaseDetailedParameterTestExtractResponseAfter(
        type,
        expression,
        source
      )
      Message.success(`测试成功，Key：【${result.data.key}】，Value：【${result.data.value}】`)
    } catch (error: any) {
      Message.error(error?.msg || '提取测试失败')
    }
  }
</script>

<style scoped>
  .mango-horizontal-scroll-region {
    min-width: 0;
    overflow-x: auto;
  }
  .mango-api-wait-config {
    display: flex;
    margin: 8px;
    padding: 14px;
    flex-direction: column;
    gap: 10px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface-soft);
  }
  .mango-api-wait-config__field {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .mango-api-wait-config__label {
    width: 72px;
    flex: none;
    color: var(--m-text-2);
    font-size: 13px;
  }
  .sleep-input {
    width: 240px;
  }
  .mango-api-wait-config__hint {
    color: var(--m-muted);
    font-size: 12px;
    line-height: 20px;
  }
  .mango-api-wait-config__hint--warning {
    color: var(--m-warning);
  }
</style>
