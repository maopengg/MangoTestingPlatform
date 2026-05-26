<template>
  <TableBody ref="tableBody">
    <template #header></template>
    <template #default>
      <section class="mango-section-card assertion-shell">
        <div class="mango-section-title">
          <div>
            <h2>断言方法</h2>
            <p>验证断言函数的入参、预期值和结果反馈</p>
          </div>
        </div>
        <a-space class="assertion-page" direction="vertical" fill :size="16">
          <div class="try-card mango-soft-panel">
            <a-space direction="vertical" fill :size="12">
              <div class="try-title">测试断言方法</div>
              <a-grid :cols="{ xs: 1, sm: 1, md: 2, lg: 3 }" :col-gap="12" :row-gap="12">
                <a-grid-item>
                  <a-cascader
                    v-model="selectedMethodValue"
                    :options="assertionList"
                    allow-search
                    expand-trigger="hover"
                    placeholder="请选择断言方法"
                    @change="handleMethodChange"
                  />
                </a-grid-item>
                <a-grid-item>
                  <a-textarea v-model="actualValue" auto-size placeholder="请输入实际值" />
                </a-grid-item>
                <a-grid-item>
                  <a-textarea
                    v-model="expectValue"
                    auto-size
                    :disabled="!currentMethodNeedsExpect"
                    :placeholder="currentMethodNeedsExpect ? '请输入预期值' : '无需预期值'"
                  />
                </a-grid-item>
              </a-grid>
              <div class="try-actions">
                <a-button @click="fillSelectedMethodExample">填入示例</a-button>
                <a-button @click="clearTestForm">清空</a-button>
                <a-button type="primary" :loading="testing" @click="testAssertion">
                  测试断言
                </a-button>
              </div>
              <a-alert
                v-if="testResult"
                :type="testResult.status ? 'success' : 'error'"
                :title="testResult.status ? '断言通过' : '断言失败'"
              >
                {{ testResult.message }}
              </a-alert>
            </a-space>
          </div>

          <a-space direction="vertical" fill :size="12">
            <div class="section-tip">
              断言方法用于比较实际值和预期值，测试结果仅用于验证当前输入是否满足断言条件。
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
                      <span>{{ item.label }}</span>
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
                  @test="selectMethodForTest"
                />
              </div>
            </div>
            <div v-if="!classGroups.length" class="mango-empty-state">暂无断言方法</div>
          </a-space>
        </a-space>
      </section>
    </template>
  </TableBody>
</template>

<script lang="ts" setup>
  import { computed, defineComponent, h, onMounted, ref } from 'vue'
  import { Button, Message, Table, Tag } from '@arco-design/web-vue'
  import { getSystemAssertionList, postSystemAssertionTest } from '@/api/system/system'

  type MethodParameter = {
    f: string
    n?: string | null
    p?: string | null
    d?: boolean
    v?: string | number | boolean | null
  }

  type MethodItem = {
    label: string
    value: string
    parameter?: MethodParameter[]
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

  const assertionList = ref<MethodTypeGroup[]>([])
  const activeGroupValue = ref('')
  const selectedMethodValue = ref('')
  const actualValue = ref('')
  const expectValue = ref('')
  const testing = ref(false)
  const testResult = ref<{ status: boolean; message: string } | null>(null)

  const classGroups = computed(() =>
    assertionList.value.flatMap((typeGroup) =>
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

  const menuSections = computed(() =>
    assertionList.value
      .map((typeGroup) => ({
        title: typeGroup.label,
        value: typeGroup.value,
        children: classGroups.value.filter((item) => item.typeValue === typeGroup.value),
      }))
      .filter((item) => item.children.length)
  )

  const currentClassGroup = computed(
    () =>
      classGroups.value.find((item) => item.menuKey === activeGroupValue.value) ||
      classGroups.value[0]
  )

  const flatMethods = computed(() =>
    classGroups.value.flatMap((classGroup) =>
      classGroup.children.map((method) => ({
        ...method,
        classLabel: classGroup.label,
        typeLabel: classGroup.typeLabel,
      }))
    )
  )

  const selectedMethod = computed(
    () => flatMethods.value.find((item) => item.value === selectedMethodValue.value) || null
  )

  const currentMethodNeedsExpect = computed(() =>
    Boolean(selectedMethod.value?.parameter?.some((item) => item.f === 'expect'))
  )

  onMounted(() => {
    getSystemAssertionList()
      .then((res) => {
        assertionList.value = sortAssertionGroups(res.data)
        activeGroupValue.value = classGroups.value[0]?.menuKey || ''
        selectedMethodValue.value = flatMethods.value[0]?.value || ''
        fillSelectedMethodExample()
      })
      .catch(console.log)
  })

  function sortAssertionGroups(groups: MethodTypeGroup[]) {
    return [...(groups || [])].sort((left, right) => {
      if (left.value === '函数断言') {
        return 1
      }
      if (right.value === '函数断言') {
        return -1
      }
      return 0
    })
  }

  function handleMethodChange() {
    testResult.value = null
    fillSelectedMethodExample()
  }

  function selectMethodForTest(record: MethodItem) {
    selectedMethodValue.value = record.value
    fillMethodExample(record)
    testResult.value = null
  }

  function fillSelectedMethodExample() {
    if (!selectedMethod.value) {
      return
    }
    fillMethodExample(selectedMethod.value)
  }

  function fillMethodExample(record: MethodItem) {
    actualValue.value = String(getParameterExample(record, 'actual') ?? '')
    expectValue.value = String(getParameterExample(record, 'expect') ?? '')
  }

  function clearTestForm() {
    actualValue.value = ''
    expectValue.value = ''
    testResult.value = null
  }

  function testAssertion() {
    if (!selectedMethodValue.value) {
      Message.warning('请先选择断言方法')
      return
    }
    testing.value = true
    testResult.value = null
    postSystemAssertionTest({
      method: selectedMethodValue.value,
      actual: actualValue.value,
      expect: currentMethodNeedsExpect.value ? expectValue.value : null,
    })
      .then((res) => {
        testResult.value = res.data
      })
      .catch(console.log)
      .finally(() => {
        testing.value = false
      })
  }

  function getParameterExample(record: MethodItem, key: string) {
    const parameter = record.parameter || []
    const item = parameter.find((option) => option.f === key)
    if (item?.v !== undefined && item.v !== null) {
      return item.v
    }
    const exampleValueMap: Record<string, string> = {
      actual: 'mango',
      expect: 'mango',
    }
    return exampleValueMap[key] || ''
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
          width: 220,
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
          width: 260,
          render: ({ record }: { record: MethodItem }) => {
            const parameter = record.parameter || []
            if (!parameter.length) {
              return h('span', { class: 'empty-text' }, '无')
            }
            return h(
              'div',
              { class: 'parameter-tags' },
              parameter.map((item) =>
                h(Tag, { size: 'small', bordered: true }, () => item.n || item.f)
              )
            )
          },
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
                onClick: () => emit('test', record),
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
  .assertion-page {
    width: 100%;
  }

  .assertion-shell {
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

  .try-actions {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
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

  .method-name {
    font-family: Consolas, 'Courier New', monospace;
  }

  .parameter-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .empty-text {
    color: var(--m-muted);
  }

  @media (max-width: 1px) {
    .method-layout {
      grid-template-columns: 1fr;
    }

    .category-panel {
      position: static;
    }
  }
</style>
