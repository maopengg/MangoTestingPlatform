<template>
  <TableBody>
    <template #header></template>
    <template #default>
      <section class="mango-section-card assertion-shell">
        <div class="mango-section-title">
          <div>
            <h2>断言方法</h2>
            <p>验证断言函数的入参、预期值和结果反馈</p>
          </div>
        </div>
        
        <MangoPanelSpin
          class="mango-assertion-panel"
          :loading="catalogLoading && !assertionList.length"
        >
          <a-space class="assertion-page" direction="vertical" fill :size="16">
            <div ref="tryPanel" class="try-card">
              <AssertionGroupEditor
                :key="editorEpoch"
                ref="assertionEditorRef"
                v-model="assertionGroups"
                :methods="assertionList"
                :method-scopes="assertionMethodScopes"
                :disabled="editorBlocked"
                @testability-change="testAvailability = $event"
              />
              <div class="try-actions">
                <a-button
                  size="small"
                  :disabled="editorBlocked"
                  @click="fillExamples"
                  data-testid="qa-views-help-assertion-button-填入示例"
                  >填入示例</a-button
                >
                <a-button
                  size="small"
                  :disabled="editorBlocked"
                  @click="clearValues"
                  data-testid="qa-views-help-assertion-button-清空参数"
                  >清空参数</a-button
                >
                <a-tooltip :content="testAvailability.reason" :disabled="testAvailability.allowed">
                  <span>
                    <a-button
                      type="primary"
                      :loading="testing"
                      :disabled="editorBlocked || !testAvailability.allowed"
                      size="small"
                      status="success"
                      @click="testAssertion"
                      data-testid="qa-views-help-assertion-button-测试全部断言"
                    >
                      测试全部断言
                    </a-button>
                  </span>
                </a-tooltip>
              </div>
              <MangoRequestFeedback v-if="testError" :message="(testError)" />
              <a-alert
                v-if="testResult"
                :type="testResult.status ? 'success' : 'error'"
                :title="testResult.status ? '断言通过' : '断言失败'"
              >
                {{ testResult.message }}
              </a-alert>
              <div v-if="testResult?.groups?.length" class="assertion-test-results">
                <div
                  v-for="(group, groupIndex) in testResult.groups"
                  :key="`${groupIndex}-${group.name}-${group.logic}`"
                  class="assertion-test-result-group"
                >
                  <div class="assertion-test-result-group__header">
                    <div>
                      <strong>{{ group.name }}</strong>
                      <a-tag size="small">{{ group.logic === 'AND' ? '且' : '或' }}</a-tag>
                    </div>
                    <a-tag size="small" :color="group.status ? 'green' : 'red'">
                      {{ group.status ? '通过' : '失败' }}
                    </a-tag>
                  </div>
                  <div class="assertion-test-result-group__items">
                    <div
                      v-for="(item, itemIndex) in group.items"
                      :key="`${item.method}-${itemIndex}`"
                      class="assertion-test-result-item"
                    >
                      <span>{{ itemIndex + 1 }}. {{ item.label || item.method }}</span>
                      <span :class="item.status ? 'is-success' : 'is-error'">
                        {{ item.status ? '通过' : '失败' }}
                      </span>
                      <span>{{ item.message }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <a-space direction="vertical" fill :size="12">
              <div class="section-tip">
                断言方法用于比较实际值和预期值，测试结果仅用于验证当前输入是否满足断言条件。
              </div>
              <div
                v-if="classGroups.length"
                class="mango-workbench-scroll-x mango-assertion-catalog"
              >
                <div class="method-layout">
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
                          :title="item.label"
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
                      :disabled="editorBlocked"
                      @test="selectMethodForTest"
                    />
                  </div>
                </div>
              </div>
              
            </a-space>
          </a-space>
        </MangoPanelSpin>
      </section>
    </template>
  </TableBody>
</template>

<script lang="ts" setup>
  import { requestFailureMessage, reportLoadError } from '@/utils/load-error'
  import {
    computed,
    nextTick,
    onActivated,
    onBeforeUnmount,
    onDeactivated,
    onMounted,
    ref,
    watch,
  } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { useRoute } from 'vue-router'
  import useUserStore from '@/store/modules/user'
  import TableBody from '@/components/table/TableBody.vue'
  import MangoPanelSpin from '@/components/feedback/MangoPanelSpin.vue'
  import MethodClassCard from './components/MethodClassCard.vue'
  import { getSystemAssertionList, postSystemAssertionTest } from '@/api/system/system'
  import AssertionGroupEditor from '@/components/forms/AssertionGroupEditor.vue'
  import { stringifyLosslessJson } from '@/utils/lossless-json'
  import { assertionMethodScopes } from './config'
  import {
    catalog,
    testPayload,
    testResult as parseTestResult,
    type AssertionTestResult,
  } from './records'
  import type {
    AssertionEditorGroup,
    AssertionMethodItem,
    AssertionMethodTypeGroup,
    AssertionTestAvailability,
  } from '@/types/assertion'

  const assertionList = ref<AssertionMethodTypeGroup[]>([]),
    activeGroupValue = ref('')
  const assertionEditorRef = ref<InstanceType<typeof AssertionGroupEditor> | null>(null)
  const assertionGroups = ref<AssertionEditorGroup[]>([]),
    editorEpoch = ref(0),
    tryPanel = ref<HTMLElement | null>(null)
  const testing = ref(false),
    catalogLoading = ref(true),
    catalogError = ref(''),
    testError = ref('')
  const testAvailability = ref<AssertionTestAvailability>({ allowed: true, reason: '' })
  const testResult = ref<AssertionTestResult | null>(null)
  const editorBlocked = computed(
    () => testing.value || catalogLoading.value || !!catalogError.value
  )
  const user = useUserStore(),
    route = useRoute()
  const contextKey = computed(() =>
    JSON.stringify([
      route.fullPath,
      user.userId,
      user.roleId,
      user.token,
      user.selected_environment,
    ])
  )
  let active = true,
    mounted = false,
    generation = 0,
    catalogSequence = 0,
    draftVersion = 0,
    groupSequence = 0

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

  async function loadCatalog(): Promise<boolean> {
    if (!active) return false
    const version = generation,
      sequence = ++catalogSequence,
      context = contextKey.value
    const current = () =>
      active &&
      version === generation &&
      sequence === catalogSequence &&
      context === contextKey.value
    catalogLoading.value = true
    catalogError.value = ''
    try {
      const methods = catalog(await getSystemAssertionList())
      if (!current()) return false
      assertionList.value = methods
      if (!classGroups.value.some((group) => group.menuKey === activeGroupValue.value))
        activeGroupValue.value = classGroups.value[0]?.menuKey || ''
      const initialize = !assertionGroups.value.length
      if (initialize) assertionGroups.value = createInitialGroups(flatMethods.value[0]?.value || '')
      ++editorEpoch.value
      const inputVersion = draftVersion
      await nextTick()
      if (!current()) return false
      if (initialize && inputVersion === draftVersion) assertionEditorRef.value?.fillExamples()
      return true
    } catch (loadFailure0) {
      if (current()) (reportLoadError(loadFailure0, "断言方法加载失败，请重试", false), catalogError.value = '断言方法加载失败，请重试')
      return false
    } finally {
      if (current()) catalogLoading.value = false
    }
  }
  function fillExamples() {
    if (!editorBlocked.value) assertionEditorRef.value?.fillExamples()
  }
  function clearValues() {
    if (!editorBlocked.value) assertionEditorRef.value?.clearValues()
  }
  function selectMethodForTest(record: AssertionMethodItem) {
    if (editorBlocked.value || !flatMethods.value.some((method) => method.value === record.value))
      return
    assertionEditorRef.value?.setSingleMethod(record.value)
    testResult.value = null
    tryPanel.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
  function createInitialGroups(method: string): AssertionEditorGroup[] {
    const id = ++groupSequence
    return [
      {
        id: `group-${id}`,
        name: '断言组1',
        logic: 'AND',
        assertions: [{ id: `assertion-${id}`, method, values: {} }],
      },
    ]
  }
  async function testAssertion() {
    if (!active || editorBlocked.value) return
    if (!testAvailability.value.allowed) {
      Message.warning(testAvailability.value.reason)
      return
    }
    const items = assertionGroups.value.flatMap((group) => group.assertions)
    if (!items.length || items.some((item) => !item.method)) {
      Message.warning('请为每条断言选择断言方法')
      return
    }
    const unavailable = items
      .map((item) => flatMethods.value.find((method) => method.value === item.method))
      .find((method) => method?.testable === false)
    if (unavailable) {
      Message.warning(unavailable.test_disabled_reason || '当前断言只能在用例运行时验证')
      return
    }
    const version = generation,
      inputVersion = draftVersion,
      context = contextKey.value,
      request = testPayload(assertionGroups.value)
    const current = () =>
      active &&
      version === generation &&
      inputVersion === draftVersion &&
      context === contextKey.value
    testing.value = true
    testResult.value = null
    testError.value = ''
    try {
      const result = parseTestResult(await postSystemAssertionTest(request), request)
      if (current()) testResult.value = result
    } catch (requestFailure) {
      if (current()) testError.value = requestFailureMessage(requestFailure, '断言测试请求失败或结果不匹配，输入已保留，请重试')
    } finally {
      testing.value = false
    }
  }
  function invalidateContext() {
    ++generation
    ++catalogSequence
    ++editorEpoch.value
    assertionList.value = []
    assertionGroups.value = []
    activeGroupValue.value = ''
    testResult.value = null
    catalogError.value = ''
    testError.value = ''
    catalogLoading.value = false
    testAvailability.value = { allowed: true, reason: '' }
  }
  watch(
    () => stringifyLosslessJson(assertionGroups.value),
    () => {
      ++draftVersion
      testResult.value = null
      testError.value = ''
    },
    { flush: 'sync' }
  )
  watch(
    contextKey,
    () => {
      invalidateContext()
      if (active && mounted) void loadCatalog()
    },
    { flush: 'sync' }
  )
  onMounted(() => {
    mounted = true
    void loadCatalog()
  })
  onDeactivated(() => {
    active = false
    ++generation
    ++catalogSequence
    catalogLoading.value = false
  })
  onActivated(() => {
    if (!active) {
      active = true
      if (mounted) void loadCatalog()
    }
  })
  onBeforeUnmount(() => {
    active = false
    invalidateContext()
  })
</script>

<style lang="less" scoped>
  .mango-assertion-panel {
    width: 100%;
    min-width: 0;
  }

  .assertion-page {
    width: 100%;
  }

  .assertion-shell {
    height: 100%;
    min-height: 0;
    overflow: auto;
  }

  .try-card {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .assertion-test-result-group__header,
  .assertion-test-result-group__header > div {
    display: flex;
    gap: 8px;
    align-items: center;
    justify-content: space-between;
  }

  .try-actions {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
  }

  .assertion-test-results,
  .assertion-test-result-group__items {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .assertion-test-result-group {
    overflow: hidden;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-sm);
    background: var(--m-surface);
  }

  .assertion-test-result-group__header {
    padding: 9px 10px;
    border-bottom: 1px solid var(--m-border);
    background: var(--m-surface-soft);
  }

  .assertion-test-result-group__items {
    padding: 8px 10px;
  }

  .assertion-test-result-item {
    display: grid;
    grid-template-columns: minmax(180px, 0.8fr) 54px minmax(0, 2fr);
    gap: 10px;
    align-items: start;
    color: var(--m-text-2);
    font-size: 13px;
  }

  .assertion-test-result-item .is-success {
    color: var(--m-success);
  }

  .assertion-test-result-item > span {
    min-width: 0;
    overflow-wrap: anywhere;
  }

  .assertion-test-result-item .is-error {
    color: var(--m-danger);
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
    gap: var(--m-page-gap);
    align-items: flex-start;
  }

  .category-panel {
    position: sticky;
    top: 12px;
    overflow: hidden;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-lg);
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

  .category-item > span:first-child {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
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

  .mango-assertion-catalog {
    --mango-workbench-min-width: 960px;
  }
</style>
