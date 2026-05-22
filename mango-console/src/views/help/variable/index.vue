<template>
  <TableBody ref="tableBody">
    <template #header></template>
    <template #default>
      <section class="mango-section-card variable-shell">
        <div class="mango-section-title">
          <div>
            <h2>公共变量</h2>
            <p>调试随机数据、缓存变量和扩展变量表达式</p>
          </div>
        </div>
        <a-space class="variable-page" direction="vertical" fill :size="16">
          <div class="try-card mango-soft-panel">
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
          </div>

          <a-space direction="vertical" fill :size="12">
            <div class="section-tip">
              随机数据方法可直接生成测试数据；平台自定义方法属于扩展能力，部分方法会依赖上传文件或运行环境。
            </div>
            <div v-if="classGroups.length" class="method-layout">
              <div class="category-panel">
                <div class="category-title">方法分类</div>
                <div class="category-list">
                  <div
                    v-for="section of menuSections"
                    :key="section.value"
                    class="category-section"
                  >
                    <div class="category-section-title">{{ section.title }}</div>
                    <button
                      v-for="item of section.children"
                      :key="item.menuKey"
                      class="category-item"
                      :class="{ active: currentClassGroup?.menuKey === item.menuKey }"
                      type="button"
                      @click="activeGroupValue = item.menuKey"
                    >
                      <span class="category-label">
                        <span>{{ item.label }}</span>
                        <span v-if="getMenuRemark(item)" class="category-remark">
                          {{ getMenuRemark(item) }}
                        </span>
                      </span>
                      <span class="category-count">{{ item.children.length }}</span>
                    </button>
                  </div>
                </div>
              </div>
              <div class="method-content">
                <method-class-card
                  v-if="currentClassGroup"
                  :key="currentClassGroup.menuKey"
                  :group="currentClassGroup"
                  @test="obtain"
                />
              </div>
            </div>
            <div v-if="!classGroups.length" class="mango-empty-state">暂无方法数据</div>
          </a-space>
        </a-space>
      </section>
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
    parameter?:
      | Array<{
          f: string
          n?: string | null
          p?: string | null
          d?: boolean
          v?: string | number | boolean | null
        }>
      | Record<string, string | null>
  }

  type MethodClassGroup = {
    label: string
    value: string
    menuKey?: string
    typeValue?: string
    typeLabel?: string
    children: MethodItem[]
  }

  type MethodTypeGroup = {
    label: string
    value: string
    children: MethodClassGroup[]
  }

  const randomList = ref<MethodTypeGroup[]>([])
  const input = ref(wrapExpression('这里输入函数名称，注意加上英文括号()'))
  const activeGroupValue = ref('')

  const classGroups = computed(() =>
    randomList.value.flatMap((typeGroup) =>
      (typeGroup.children || [])
        .filter((classGroup) => classGroup.children?.length)
        .map((classGroup) => ({
          ...classGroup,
          menuKey: `${typeGroup.value}:${classGroup.value}`,
          typeValue: typeGroup.value,
          typeLabel: typeGroup.label,
        }))
    )
  )

  const menuSections = computed(() => {
    const testData = classGroups.value.filter((item) => item.typeValue === 'data')
    const tools = classGroups.value.filter((item) => item.typeValue !== 'data')
    return [
      { title: '测试数据', value: 'data', children: testData },
      { title: '工具', value: 'tools', children: tools },
    ].filter((item) => item.children.length)
  })

  const currentClassGroup = computed(
    () =>
      classGroups.value.find((item) => item.menuKey === activeGroupValue.value) ||
      classGroups.value[0]
  )

  onMounted(() => {
    getSystemRandomList()
      .then((res) => {
        randomList.value = res.data
        activeGroupValue.value = getDefaultGroupKey()
      })
      .catch(console.log)
  })

  function getDefaultGroupKey() {
    const defaultGroup = classGroups.value.find((item) => item.value === '人物信息测试数据')
    return defaultGroup?.menuKey || classGroups.value[0]?.menuKey || ''
  }

  function normalizeExpression(value: string) {
    return value
      .replace(/^\$\{\{/, '')
      .replace(/\}\}$/, '')
      .trim()
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
    const parameter = record.parameter || []
    const params = Array.isArray(parameter)
      ? parameter.map((item) => item.v ?? getExampleParameterValue(item.f)).join(', ')
      : Object.keys(parameter)
          .map((key) => parameter[key] ?? getExampleParameterValue(key))
          .join(', ')
    return `${record.value}(${params})`
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

  function getMenuRemark(item: MethodClassGroup) {
    return ['cache', 'json'].includes(item.typeValue || '') ? '不要使用，只做说明' : ''
  }

  function wrapExpression(expression: string) {
    return '${{' + expression + '}}'
  }

  const MethodClassCard = defineComponent({
    name: 'MethodClassCard',
    props: {
      group: {
        type: Object as () => MethodClassGroup,
        required: true,
      },
    },
    emits: ['test'],
    setup(props, { emit }) {
      const columns = [
        {
          title: '方法',
          dataIndex: 'value',
          width: 180,
          render: ({ record }: { record: MethodItem }) =>
            h('span', { class: 'method-name' }, record.value),
        },
        {
          title: '说明',
          dataIndex: 'label',
          ellipsis: true,
          tooltip: true,
        },
        {
          title: '参数',
          dataIndex: 'parameter',
          width: 220,
          render: ({ record }: { record: MethodItem }) => {
            const parameter = record.parameter || []
            const keys = Array.isArray(parameter)
              ? parameter.map((item) => item.n || item.f)
              : Object.keys(parameter)
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
        h('div', { class: 'method-group-card' }, [
          h(Table, {
            columns,
            data: props.group.children,
            pagination: false,
            bordered: false,
            rowKey: 'value',
          }),
        ])
    },
  })
</script>
<style lang="less" scoped>
  .variable-page {
    width: 100%;
  }

  .variable-shell {
    height: 100%;
    min-height: 0;
    overflow: auto;
  }

  .try-card {
    padding: 12px;
  }

  .try-title {
    font-size: 16px;
    font-weight: 600;
    color: var(--m-text);
  }

  .usage-panel {
    display: flex;
    gap: 18px;
    align-items: flex-start;
    padding: 12px 14px;
    border: 1px solid var(--m-border);
    border-radius: 6px;
    background: var(--m-surface);
  }

  .usage-title {
    flex: 0 0 auto;
    padding-top: 2px;
    font-size: 13px;
    font-weight: 600;
    color: var(--m-text);
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
    color: var(--m-text-2);
  }

  .section-tip {
    padding: 10px 12px;
    border-left: 3px solid var(--m-success);
    border-radius: 4px;
    background: color-mix(in srgb, var(--m-success) 12%, transparent);
    color: var(--m-text-2);
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
    border: 1px solid var(--m-border);
    border-radius: 6px;
    background: var(--m-surface);
  }

  .category-title {
    padding: 12px 14px;
    border-bottom: 1px solid var(--m-border);
    font-weight: 600;
    color: var(--m-text);
  }

  .category-list {
    display: flex;
    flex-direction: column;
    padding: 8px;
    gap: 12px;
  }

  .category-section {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .category-section-title {
    padding: 4px 8px;
    color: var(--m-muted);
    font-size: 12px;
    font-weight: 600;
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
    color: var(--m-text-2);
    text-align: left;
    cursor: pointer;
    transition: background-color 0.15s ease, color 0.15s ease;
  }

  .category-item:hover {
    background: var(--m-hover);
    color: var(--m-text);
  }

  .category-item.active {
    background: var(--m-hover);
    color: var(--m-text);
    font-weight: 600;
  }

  .category-item.active::before {
    position: absolute;
    top: 8px;
    bottom: 8px;
    left: 0;
    width: 3px;
    border-radius: 2px;
    background: var(--m-primary);
    content: '';
  }

  .category-label {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 2px;
  }

  .category-remark {
    color: var(--m-muted);
    font-size: 12px;
    font-weight: 400;
    line-height: 16px;
  }

  .category-count {
    flex: 0 0 auto;
    min-width: 24px;
    padding: 0 6px;
    border-radius: 10px;
    background: var(--m-primary-soft);
    color: var(--m-primary);
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
    border: 1px solid var(--m-border);
    border-radius: 6px;
    background: var(--m-surface);
  }

  .method-name,
  .expression,
  .inline-code {
    font-family: Consolas, 'Courier New', monospace;
  }

  .expression {
    color: var(--m-primary);
  }

  .inline-code {
    padding: 2px 7px;
    border-radius: 4px;
    border: 1px solid var(--m-border);
    background: var(--m-surface-soft);
    color: var(--m-primary);
  }

  .parameter-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .empty-text {
    color: var(--m-muted);
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
