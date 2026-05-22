<template>
  <a-drawer :visible="visible" :width="800" unmountOnClose @cancel="handleCancel" @ok="handleOk">
    <template #title> 用例套件</template>
    <div>
      <a-space>
        <a-button size="mini" type="primary" @click.stop="addTestSuite"> 增加测试套</a-button>
      </a-space>
      <a-collapse :bordered="false" :default-active-key="[0]">
        <a-collapse-item
          v-for="(item, index) in parametrizeData"
          :key="index"
          :header="'循环第 ' + (index + 1) + ' 次 - ' + (item.name || '未命名')"
        >
          <template #extra>
            <a-space>
              <a-button size="mini" type="primary" @click.stop="addParametrizeRow(item)">
                增加一行
              </a-button>
              <a-button size="mini" status="danger" @click.stop="removeTestSuite(index)">
                删除
              </a-button>
            </a-space>
          </template>
          <a-space direction="vertical" fill>
            <a-space>
              <span>名称：</span>
              <a-input
                :model-value="item.name"
                placeholder="请输入套件名称"
                @update:model-value="
                  (val) => {
                    item.name = val
                    handleNameChange()
                  }
                "
              />
            </a-space>
            <a-space
              v-for="(items, index1) in item.parametrize"
              :key="index1"
              class="mango-parametrize-row"
            >
              <span>key：</span>
              <a-input
                :model-value="items.key"
                placeholder="请输入key"
                @update:model-value="
                  (val) => {
                    items.key = val
                    handleParamChange()
                  }
                "
              />
              <span>value：</span>
              <div class="mango-parametrize-value-editor">
                <a-input
                  :model-value="items.value === null ? '' : items.value"
                  :disabled="items.value === null"
                  :placeholder="items.value === null ? '当前保存为 null' : '请输入value'"
                  @update:model-value="
                    (val) => {
                      items.value = val
                      handleParamChange()
                    }
                  "
                />
                <a-radio-group
                  :model-value="items.value === null ? 'null' : 'string'"
                  type="button"
                  size="small"
                  class="mango-parametrize-value-type-switch"
                  @change="(value) => changeValueType(items, value)"
                >
                  <a-radio value="string">字符串</a-radio>
                  <a-radio value="null">Null</a-radio>
                </a-radio-group>
              </div>
              <a-button
                size="small"
                status="danger"
                type="text"
                @click="removeParametrizeRow(item, index1)"
              >
                移除
              </a-button>
            </a-space>
          </a-space>
        </a-collapse-item>
      </a-collapse>
    </div>
  </a-drawer>
</template>

<script setup>
  import { ref, watch } from 'vue'

  const props = defineProps({
    visible: {
      type: Boolean,
      default: false,
    },
    initialData: {
      type: Array,
      default: () => [],
    },
  })

  const emit = defineEmits(['ok', 'cancel', 'update:initialData'])

  const parametrizeData = ref([])

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
      parametrize: [{ key: '', value: '' }],
    })
  }

  const addParametrizeRow = (item) => {
    item.parametrize.push({ key: '', value: '' })
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
          parametrize: [{ key: '', value: '' }],
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
    align-items: flex-start;
  }

  .mango-parametrize-value-editor {
    display: flex;
    gap: 8px;
    align-items: center;
  }

  .mango-parametrize-value-editor :deep(.arco-input-wrapper) {
    width: 260px;
  }

  .mango-parametrize-value-type-switch {
    flex-shrink: 0;
  }
</style>
