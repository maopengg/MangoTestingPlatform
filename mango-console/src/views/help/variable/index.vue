<template>
  <TableBody ref="tableBody">
    <template #header></template>
    <template #default>
      <a-card :bordered="false" title="公共变量">
        <a-space class="variable-page" direction="vertical" fill :size="16">
          <a-card class="try-card" :bordered="false">
            <a-space direction="vertical" fill :size="12">
              <div class="try-title">测试变量表达式</div>
              <a-input-search
                v-model="input"
                search-button
                button-text="测试一下"
                placeholder="请输入变量表达式"
                @search="obtain(input)"
              />
              <div class="usage-panel">
                <div class="usage-title">用法说明</div>
                <div class="usage-list">
                  <div class="usage-item">
                    <span class="usage-label">直接生成</span>
                    <span class="inline-code">{{ wrapExpression('方法名(参数)') }}</span>
                  </div>
                  <div class="usage-item">
                    <span class="usage-label">生成并缓存</span>
                    <span class="inline-code">{{ wrapExpression('方法名()|缓存key') }}</span>
                  </div>
                </div>
              </div>
            </a-space>
          </a-card>

          <a-space direction="vertical" fill :size="12">
            <div class="section-tip">
              随机数据方法可直接生成测试数据；平台自定义方法属于扩展能力，部分方法会依赖上传文件或运行环境。
            </div>
            <div v-if="methodGroups.length" class="method-layout">
              <div class="category-panel">
                <div class="category-title">方法分类</div>
                <div class="category-list">
                  <button
                    v-for="item of methodGroups"
                    :key="item.value"
                    class="category-item"
                    :class="{ active: currentMethodGroup?.value === item.value }"
                    type="button"
                    @click="activeGroupValue = item.value"
                  >
                    <span>{{ item.label }}</span>
                    <span class="category-count">{{ item.children.length }}</span>
                  </button>
                </div>
              </div>
              <div class="method-content">
                <method-group-card
                  v-if="currentMethodGroup"
                  :key="currentMethodGroup.value"
                  :group="currentMethodGroup"
                  @test="obtain"
                />
              </div>
            </div>
            <a-empty v-if="!methodGroups.length" description="暂无方法数据" />
          </a-space>
        </a-space>
      </a-card>
    </template>
  </TableBody>
</template>

<script lang="ts" setup>
  import { computed, defineComponent, h, onMounted, ref } from 'vue'
  import { Button, Message, Notification, Table, Tag } from '@arco-design/web-vue'
  import { getSystemRandomData, getSystemRandomList } from '@/api/system/system'

  type MethodItem = {
    label: string
    value: string
    parameter?: Record<string, string | null>
  }

  type MethodGroup = {
    label: string
    value: string
    children: MethodItem[]
  }

  const hiddenCustomMethods = new Set([
    'get_cache()',
    'set_data_factory_cache()',
    'get_data_factory_all()',
    'to_frontend_safe_value()',
  ])

  const randomList = ref<MethodGroup[]>([])
  const input = ref(wrapExpression('这里输入函数名称'))
  const activeGroupValue = ref('')

  const customGroups = computed(() =>
    randomList.value
      .filter((item) => item.value === 'ObtainTestData')
      .map((item) => ({
        ...item,
        label: '平台自定义方法',
        children: item.children.filter((child) => !hiddenCustomMethods.has(child.label)),
      }))
      .filter((item) => item.children.length)
  )

  const randomGroups = computed(() =>
    randomList.value.filter((item) => item.value !== 'ObtainTestData')
  )

  const methodGroups = computed(() => [...randomGroups.value, ...customGroups.value])

  const currentMethodGroup = computed(
    () =>
      methodGroups.value.find((item) => item.value === activeGroupValue.value) ||
      methodGroups.value[0]
  )

  onMounted(() => {
    getSystemRandomList()
      .then((res) => {
        randomList.value = res.data
        activeGroupValue.value = methodGroups.value[0]?.value || ''
      })
      .catch(console.log)
  })

  function normalizeExpression(value: string) {
    return value.replace(/^\$\{\{/, '').replace(/\}\}$/, '').trim()
  }

  function obtain(value?: string) {
    const expression = normalizeExpression(value || input.value)
    if (!expression) {
      Message.warning('请输入需要测试的方法')
      return
    }
    getSystemRandomData('${{' + expression + '}}')
      .then((res) => {
        Notification.success({
          title: '${{' + expression + '}}',
          content: String(res.data),
        })
      })
      .catch(console.log)
  }

  function buildExample(record: MethodItem) {
    const parameter = record.parameter || {}
    const params = Object.keys(parameter)
      .map((key) => parameter[key] || getExampleParameterValue(key))
      .join(',')
    return record.label.replace('()', `(${params})`)
  }

  function getExampleParameterValue(key: string) {
    const exampleValueMap: Record<string, string> = {
      length: '8',
      left: '1',
      right: '100',
      digits: '3',
      count: '3',
      days: '0',
      day: '0',
      hours: '0',
      hour: '0',
      minutes: '0',
      minute: '0',
      seconds: '0',
      second: '0',
      extension: 'txt',
      file_name: '文件名称',
      time_parts: '12:30:00',
      demo1: 'demo1',
      demo2: 'demo2',
    }
    return exampleValueMap[key] || key
  }

  function wrapExpression(expression: string) {
    return '${{' + expression + '}}'
  }

  const MethodGroupCard = defineComponent({
    name: 'MethodGroupCard',
    props: {
      group: {
        type: Object as () => MethodGroup,
        required: true,
      },
    },
    emits: ['test'],
    setup(props, { emit }) {
      const columns = [
        {
          title: '方法',
          dataIndex: 'label',
          width: 240,
          render: ({ record }: { record: MethodItem }) =>
            h('span', { class: 'method-name' }, record.label),
        },
        {
          title: '说明',
          dataIndex: 'value',
          ellipsis: true,
          tooltip: true,
        },
        {
          title: '参数',
          dataIndex: 'parameter',
          width: 220,
          render: ({ record }: { record: MethodItem }) => {
            const keys = Object.keys(record.parameter || {})
            if (!keys.length) {
              return h('span', { class: 'empty-text' }, '无')
            }
            return h(
              'div',
              { class: 'parameter-tags' },
              keys.map((key) => h(Tag, { size: 'small', bordered: true }, () => key))
            )
          },
        },
        {
          title: '示例',
          width: 260,
          render: ({ record }: { record: MethodItem }) =>
            h('span', { class: 'expression' }, wrapExpression(buildExample(record))),
        },
        {
          title: '操作',
          width: 110,
          align: 'center' as const,
          render: ({ record }: { record: MethodItem }) =>
            h(
              Button,
              {
                size: 'mini',
                type: 'text',
                onClick: () => emit('test', buildExample(record)),
              },
              () => '测试'
            ),
        },
      ]

      return () =>
        h(
          'div',
          { class: 'method-group-card' },
          [
            h(Table, {
              columns,
              data: props.group.children,
              pagination: false,
              bordered: false,
              rowKey: 'label',
            }),
          ]
        )
    },
  })
</script>
<style lang="less" scoped>
  .variable-page {
    width: 100%;
  }

  .try-card {
    background: var(--color-fill-1);
  }

  .try-title {
    font-size: 16px;
    font-weight: 600;
    color: var(--color-text-1);
  }

  .usage-panel {
    display: flex;
    gap: 18px;
    align-items: flex-start;
    padding: 12px 14px;
    border: 1px solid var(--color-border-2);
    border-radius: 6px;
    background: var(--color-bg-2);
  }

  .usage-title {
    flex: 0 0 auto;
    padding-top: 2px;
    font-size: 13px;
    font-weight: 600;
    color: var(--color-text-1);
  }

  .usage-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
    min-width: 0;
  }

  .usage-item {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
  }

  .usage-label {
    width: 72px;
    color: var(--color-text-2);
  }

  .section-tip {
    padding: 10px 12px;
    border-left: 3px solid rgb(var(--success-6));
    border-radius: 4px;
    background: rgb(var(--success-1));
    color: var(--color-text-2);
  }

  .method-layout {
    display: grid;
    grid-template-columns: 220px minmax(0, 1fr);
    gap: 14px;
    align-items: flex-start;
  }

  .category-panel {
    position: sticky;
    top: 12px;
    overflow: hidden;
    border: 1px solid var(--color-border-2);
    border-radius: 6px;
    background: var(--color-bg-2);
  }

  .category-title {
    padding: 12px 14px;
    border-bottom: 1px solid var(--color-border-2);
    font-weight: 600;
    color: var(--color-text-1);
  }

  .category-list {
    display: flex;
    flex-direction: column;
    padding: 8px;
    gap: 4px;
  }

  .category-item {
    position: relative;
    display: flex;
    gap: 8px;
    align-items: center;
    justify-content: space-between;
    width: 100%;
    min-width: 0;
    padding: 8px 10px;
    border: 0;
    border-radius: 4px;
    background: transparent;
    color: var(--color-text-2);
    text-align: left;
    cursor: pointer;
    transition: background-color 0.15s ease, color 0.15s ease;
  }

  .category-item:hover {
    background: var(--color-fill-2);
    color: var(--color-text-1);
  }

  .category-item.active {
    background: var(--color-fill-2);
    color: var(--color-text-1);
    font-weight: 600;
  }

  .category-item.active::before {
    position: absolute;
    top: 8px;
    bottom: 8px;
    left: 0;
    width: 3px;
    border-radius: 2px;
    background: var(--color-text-2);
    content: '';
  }

  .category-count {
    flex: 0 0 auto;
    min-width: 24px;
    padding: 0 6px;
    border-radius: 10px;
    background: var(--color-fill-2);
    color: var(--color-text-2);
    text-align: center;
    font-size: 12px;
    line-height: 18px;
  }

  .method-content {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 14px;
  }

  .method-group-card {
    overflow: hidden;
    border: 1px solid var(--color-border-2);
    border-radius: 6px;
    background: var(--color-bg-2);
  }

  .method-name,
  .expression,
  .inline-code {
    font-family: Consolas, 'Courier New', monospace;
  }

  .expression {
    color: rgb(var(--primary-6));
  }

  .inline-code {
    padding: 2px 7px;
    border-radius: 4px;
    border: 1px solid var(--color-border-2);
    background: var(--color-fill-1);
    color: #0f5cad;
  }

  .parameter-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .empty-text {
    color: var(--color-text-3);
  }

  @media (max-width: 900px) {
    .method-layout {
      grid-template-columns: 1fr;
    }

    .category-panel {
      position: static;
    }
  }
</style>
