<template>
  <a-drawer :visible="visible" :width="1080" unmountOnClose @cancel="handleCancel" @ok="handleOk">
    <template #title> 用例套件</template>
    <div>
      <a-space>
        <a-button size="mini" type="primary" @click.stop="addTestSuite" data-testid="qa-components-forms-parametrizedrawer-button-增加测试套"> 增加测试套</a-button>
      </a-space>
      <a-collapse :bordered="false" :default-active-key="[0]">
        <a-collapse-item
          v-for="(item, index) in parametrizeData"
          :key="index"
          :header="'循环第 ' + (index + 1) + ' 次 - ' + (item.name || '未命名')"
        >
          <template #extra>
            <a-space>
              <a-button size="mini" type="primary" @click.stop="addParametrizeRow(item)" data-testid="qa-components-forms-parametrizedrawer-button-增加一行">
                增加一行
              </a-button>
              <a-button size="mini" status="danger" @click.stop="removeTestSuite(index)" data-testid="qa-components-forms-parametrizedrawer-button-删除">
                删除
              </a-button>
            </a-space>
          </template>
          <a-space direction="vertical" fill>
            <a-space>
              <span>名称：</span>
              <a-tooltip
                :content="getTextTitle(item.name)"
                :disabled="!getTextTitle(item.name)"
                class="mango-parametrize-name-tooltip"
              >
                <a-input
                  :model-value="item.name"
                  class="mango-parametrize-name-input"
                  placeholder="请输入套件名称"
                  data-testid="qa-components-forms-parametrizedrawer-input-请输入套件名称"
                  @update:model-value="
                    (val) => {
                      item.name = val
                      handleNameChange()
                    }
                  "
                />
              </a-tooltip>
            </a-space>
            <div
              v-for="(items, index1) in item.parametrize"
              :key="index1"
              class="mango-parametrize-row"
              :class="{ 'mango-parametrize-row--with-env': showEnvironment }"
            >
              <label v-if="showEnvironment" class="mango-parametrize-env-editor">
                <span class="mango-parametrize-label">适用环境：</span>
                <a-tooltip
                  :content="getParamEnvironmentTitle(items)"
                  :disabled="!getParamEnvironmentTitle(items)"
                  class="mango-parametrize-control-tooltip"
                >
                  <a-select
                    :model-value="getParamEnvironmentValue(items)"
                    :options="environmentOptions"
                    :field-names="fieldNames"
                    multiple
                    placeholder="请选择被测环境"
                    @change="(value) => changeParamEnvironment(items, value)"
                  />
                </a-tooltip>
              </label>
              <label class="mango-parametrize-key-editor">
                <span class="mango-parametrize-label">key：</span>
                <a-tooltip
                  :content="getTextTitle(items.key)"
                  :disabled="!getTextTitle(items.key)"
                  class="mango-parametrize-control-tooltip"
                >
                  <a-input
                    :model-value="items.key"
                    placeholder="请输入key"
                    data-testid="qa-components-forms-parametrizedrawer-input-请输入key"
                    @update:model-value="
                      (val) => {
                        items.key = val
                        handleParamChange()
                      }
                    "
                  />
                </a-tooltip>
              </label>
              <label class="mango-parametrize-value-editor">
                <span class="mango-parametrize-label">value：</span>
                <a-tooltip
                  :content="getTextTitle(items.value)"
                  :disabled="!getTextTitle(items.value)"
                  class="mango-parametrize-control-tooltip"
                >
                  <a-input
                    :model-value="items.value === null ? '' : items.value"
                    :disabled="items.value === null"
                    :placeholder="items.value === null ? '当前值为空值 null' : '请输入value'"
                    @update:model-value="
                      (val) => {
                        items.value = val
                        handleParamChange()
                      }
                    "
                  />
                </a-tooltip>
              </label>
              <a-radio-group
                :model-value="items.value === null ? 'null' : 'string'"
                type="button"
                size="small"
                class="mango-parametrize-value-type-switch"
                @change="(value) => changeValueType(items, value)"
              >
                <a-radio value="string" data-testid="qa-components-forms-parametrizedrawer-radio-字符串">文本值</a-radio>
                <a-radio value="null" data-testid="qa-components-forms-parametrizedrawer-radio-null">空值 null</a-radio>
              </a-radio-group>
              <a-button
                size="small"
                status="danger"
                type="text"
                data-testid="qa-components-forms-parametrizedrawer-button-移除"
                @click="removeParametrizeRow(item, index1)"
              >
                移除
              </a-button>
            </div>
          </a-space>
        </a-collapse-item>
      </a-collapse>
    </div>
  </a-drawer>
</template>

<script setup>
  import { computed, ref, watch } from 'vue'
  import { fieldNames } from '@/setting'
  import { useEnum } from '@/store/modules/get-enum'
  import {
    COMMON_ENV_VALUE,
    normalizeEnvironmentSelectChange,
    normalizeEnvironmentValues,
    toEnvironmentSelectValue,
  } from '@/utils/environment-scope'

  const props = defineProps({
    visible: {
      type: Boolean,
      default: false,
    },
    initialData: {
      type: Array,
      default: () => [],
    },
    showEnvironment: {
      type: Boolean,
      default: false,
    },
  })

  const emit = defineEmits(['ok', 'cancel', 'update:initialData'])

  const enumStore = useEnum()
  const parametrizeData = ref([])
  const showEnvironment = computed(() => props.showEnvironment)
  const environmentOptions = computed(() => [
    { key: COMMON_ENV_VALUE, title: '环境通用' },
    ...enumStore.environment_type,
  ])

  watch(
    () => props.initialData,
    (newVal) => {
      if (newVal && newVal.length > 0) {
        parametrizeData.value = JSON.parse(JSON.stringify(newVal))
      } else {
        parametrizeData.value = []
      }
    },
    { immediate: true }
  )

  const addTestSuite = () => {
    parametrizeData.value.push({
      name: '',
      parametrize: [{ key: '', value: '', test_envs: [] }],
    })
  }

  const addParametrizeRow = (item) => {
    item.parametrize.push({ key: '', value: '', test_envs: [] })
  }
  const removeTestSuite = (index) => {
    parametrizeData.value.splice(index, 1)
  }

  const removeParametrizeRow = (item, index) => {
    item.parametrize.splice(index, 1)
  }

  const changeValueType = (item, value) => {
    item.value = value === 'null' ? null : ''
    handleParamChange()
  }

  const getParamEnvironmentValue = (item) => toEnvironmentSelectValue(item?.test_envs)

  const getTextTitle = (value) => {
    if (value === undefined || value === null) return ''
    return String(value)
  }

  const getParamEnvironmentTitle = (item) => {
    const values = normalizeEnvironmentValues(toEnvironmentSelectValue(item?.test_envs))
    if (!values.length || values.includes(COMMON_ENV_VALUE)) return '环境通用'
    const optionMap = new Map(
      environmentOptions.value.map((option) => [String(option.key), option.title])
    )
    return values.map((value) => optionMap.get(String(value)) || value).join('、')
  }

  const changeParamEnvironment = (item, value) => {
    item.test_envs = normalizeEnvironmentValues(normalizeEnvironmentSelectChange(value))
    handleParamChange()
  }

  const handleNameChange = () => {
    parametrizeData.value = [...parametrizeData.value]
    emit('update:initialData', JSON.parse(JSON.stringify(parametrizeData.value)))
  }

  const handleParamChange = () => {
    parametrizeData.value = [...parametrizeData.value]
    emit('update:initialData', JSON.parse(JSON.stringify(parametrizeData.value)))
  }

  const hasParamValue = (param) => Boolean(param.key)

  const handleOk = () => {
    let hasValidData = false

    for (const suite of parametrizeData.value) {
      if (suite.name || suite.parametrize.some(hasParamValue)) {
        hasValidData = true
        break
      }
    }

    if (parametrizeData.value.length === 0 || !hasValidData) {
      parametrizeData.value = [
        {
          name: '',
          parametrize: [{ key: '', value: '', test_envs: [] }],
        },
      ]
    }

    emit('ok', JSON.parse(JSON.stringify(parametrizeData.value)))
  }

  const handleCancel = () => {
    emit('cancel')
  }
</script>

<style scoped>
  .mango-parametrize-row {
    display: grid;
    width: 100%;
    grid-template-columns: 212px 228px 156px 44px;
    gap: 8px;
    align-items: center;
  }

  .mango-parametrize-row--with-env {
    grid-template-columns: 252px 212px 228px 156px 44px;
  }

  .mango-parametrize-key-editor,
  .mango-parametrize-value-editor,
  .mango-parametrize-env-editor {
    display: grid;
    grid-template-columns: 28px 176px;
    column-gap: 8px;
    align-items: center;
    min-width: 0;
  }

  .mango-parametrize-env-editor {
    grid-template-columns: 68px 176px;
  }

  .mango-parametrize-value-editor {
    grid-template-columns: 48px 176px;
  }

  .mango-parametrize-control-tooltip {
    width: 176px;
    min-width: 0;
  }

  .mango-parametrize-control-tooltip :deep(.arco-trigger),
  .mango-parametrize-control-tooltip :deep(.arco-input-wrapper),
  .mango-parametrize-control-tooltip :deep(.arco-select),
  .mango-parametrize-key-editor :deep(.arco-input-wrapper),
  .mango-parametrize-value-editor :deep(.arco-input-wrapper) {
    width: 100%;
    min-width: 0;
  }

  .mango-parametrize-name-tooltip {
    display: inline-flex;
    width: 180px;
  }

  .mango-parametrize-name-input {
    width: 100%;
  }

  .mango-parametrize-name-input :deep(.arco-input),
  .mango-parametrize-key-editor :deep(.arco-input),
  .mango-parametrize-value-editor :deep(.arco-input) {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-parametrize-value-type-switch {
    display: inline-flex;
    width: 156px;
    min-width: 156px;
    padding: 2px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-sm);
    background: var(--m-surface);
  }

  .mango-parametrize-value-type-switch :deep(.arco-radio-button) {
    flex: 1;
    min-width: 0;
    border: 0;
    border-radius: calc(var(--m-radius-sm) - 1px);
    text-align: center;
    white-space: nowrap;
  }

  .mango-parametrize-value-type-switch :deep(.arco-radio-button-content) {
    display: block;
    overflow: hidden;
    padding: 0 8px;
    text-overflow: ellipsis;
  }

  .mango-parametrize-value-type-switch :deep(.arco-radio-button:not(.arco-radio-checked)) {
    color: var(--m-text-2);
    background: transparent;
  }

  .mango-parametrize-value-type-switch :deep(.arco-radio-button.arco-radio-checked) {
    color: var(--m-primary);
    background: var(--m-primary-soft);
    box-shadow: inset 0 0 0 1px var(--m-primary-border);
  }

  .mango-parametrize-env-editor :deep(.arco-select) {
    width: 100%;
    min-width: 0;
  }

  .mango-parametrize-env-editor :deep(.arco-select-view-single),
  .mango-parametrize-env-editor :deep(.arco-select-view-multiple) {
    min-height: 32px;
    overflow: hidden;
  }

  .mango-parametrize-env-editor :deep(.arco-select-view-tag),
  .mango-parametrize-env-editor :deep(.arco-tag) {
    max-width: 96px;
  }

  .mango-parametrize-env-editor :deep(.arco-tag-content) {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-parametrize-label {
    color: var(--m-text-2);
    text-align: right;
    white-space: nowrap;
  }

  @media (max-width: 860px) {
    .mango-parametrize-row,
    .mango-parametrize-row--with-env {
      grid-template-columns: minmax(270px, 1fr) 144px 44px;
      align-items: flex-start;
    }

    .mango-parametrize-value-editor,
    .mango-parametrize-row--with-env .mango-parametrize-env-editor,
    .mango-parametrize-row--with-env .mango-parametrize-key-editor,
    .mango-parametrize-row--with-env .mango-parametrize-value-editor {
      grid-column: 1 / 2;
    }
  }
</style>
