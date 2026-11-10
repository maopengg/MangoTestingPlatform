<template>
  <TableBody :embedded="props.embedded">
    <template #header></template>
    <template #default>
      <section class="mango-section-card mango-variable-shell">
        <div class="mango-section-title">
          <div>
            <h2>公共变量</h2>
            <p>调试随机数据、缓存变量和扩展变量表达式</p>
          </div>
        </div>
        <a-space class="mango-variable-page" direction="vertical" fill :size="scaleDensityPixels(16)">
          <div class="mango-variable-try-card mango-soft-panel">
            <a-space direction="vertical" fill :size="scaleDensityPixels(12)">
              <div class="mango-variable-try-title">测试变量表达式</div>
              <a-input-search
                v-model="input"
                search-button
                button-text="测试一下"
                placeholder="请输入变量表达式"
                :loading="testing"
                :disabled="testing"
                @search="obtain(input)" data-testid="qa-views-help-variable-input-search-请输入变量表达式"
              />
              <a-alert v-if="testError" type="error">
                {{ testError }}
                <template #action><a-button size="small" :loading="testing" @click="retryTest">重试</a-button></template>
              </a-alert>
              <div class="mango-variable-usage-panel">
                <div class="mango-variable-usage-title">用法说明</div>
                <div class="mango-variable-usage-list">
                  <div class="mango-variable-usage-item">
                    <span class="mango-variable-usage-label">变量表达式</span>
                    <span class="mango-variable-usage-action">直接生成</span>
                    <span class="mango-variable-inline-code">{{ wrapExpression('方法名(参数)') }}</span>
                    <span class="mango-variable-usage-action">生成并缓存</span>
                    <span class="mango-variable-inline-code">{{ wrapExpression('方法名()|缓存key') }}</span>
                  </div>
                  <div class="mango-variable-usage-item">
                    <span class="mango-variable-usage-label">自定义函数</span>
                    <span class="mango-variable-inline-code">self.test_data.方法名(参数)</span>
                    <span class="mango-variable-usage-note">
                      当前函数上下文提供 self 时，可通过 self.test_data 调用本页方法
                    </span>
                  </div>
                </div>
              </div>
            </a-space>
          </div>

          <MangoPanelSpin class="mango-variable-catalog" :loading="catalogLoading && !randomList.length">
          <a-space direction="vertical" fill :size="scaleDensityPixels(12)">

            <div class="mango-variable-section-tip">
              <template v-if="currentClassGroup?.typeValue === 'performance'">
                仅此分类的 perf_* 方法可编译到 k6：在API自动化 Case 中填写表达式并发布，性能运行时每次命中都会生成新值，无需预建大量参数组。
              </template>
              <template v-else>
                随机数据方法可直接生成测试数据；平台自定义方法属于扩展能力，部分方法会依赖上传文件或运行环境。
              </template>
            </div>
            <div v-if="classGroups.length" class="mango-variable-method-layout">
              <div class="mango-variable-category-panel">
                <div class="mango-variable-category-title">方法分类</div>
                <div class="mango-variable-category-list">
                  <div
                    v-for="section of menuSections"
                    :key="section.value"
                    class="mango-variable-category-section"
                  >
                    <div class="mango-variable-category-section-title">{{ section.title }}</div>
                    <button
                      v-for="item of section.children"
                      :key="item.menuKey"
                      class="mango-variable-category-item"
                      :class="{ active: currentClassGroup?.menuKey === item.menuKey }"
                      type="button"
                      :disabled="testing"
                      :aria-current="currentClassGroup?.menuKey === item.menuKey ? 'true' : undefined"
                      @click="selectGroup(item.menuKey)"
                    >
                      <span class="mango-variable-category-label">
                        <span :title="item.label">{{ item.label }}</span>
                        <span v-if="getMenuRemark(item)" class="mango-variable-category-remark">
                          {{ getMenuRemark(item) }}
                        </span>
                      </span>
                      <span class="mango-variable-category-count">{{ item.children.length }}</span>
                    </button>
                  </div>
                </div>
              </div>
              <div class="mango-variable-method-content">
                <method-class-card
                  v-if="currentClassGroup"
                  :key="currentClassGroup.menuKey"
                  :group="currentClassGroup"
                  :loading="catalogLoading && !!randomList.length"
                  :disabled="testing || !!catalogError"
                  :testing-expression="testing ? lastExpression : null"
                  @test="obtain"
                />
              </div>
            </div>

          </a-space>
          </MangoPanelSpin>
        </a-space>
      </section>
    </template>
  </TableBody>
</template>

<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { computed, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, watch } from 'vue'
  import { useRoute } from 'vue-router'
  import { Message, Notification } from '@arco-design/web-vue'
  import useUserStore from '@/store/modules/user'
  import { scaleDensityPixels } from '@/hooks/useDisplayDensity'
  import { getSystemRandomData, getSystemRandomList } from '@/api/system/system'
  import MangoPanelSpin from '@/components/feedback/MangoPanelSpin.vue'
  import MethodClassCard from './components/MethodClassCard.vue'
  import { methodMenuSections } from './config'
  import { normalizeExpression, readCatalog, readGeneratedValue, wrapExpression } from './records'
  import type { MethodMenuGroup, MethodTypeGroup } from './types'

  const props = withDefaults(defineProps<{ embedded?: boolean }>(), { embedded: false })
  const randomList = ref<MethodTypeGroup[]>([])
  const input = ref(wrapExpression('这里输入函数名称，注意加上英文括号()'))
  const activeGroupValue = ref('')
  const catalogLoading = ref(false)
  const catalogError = ref('')
  const testing = ref(false)
  const testError = ref('')
  const lastExpression = ref<string | null>(null)
  const user = useUserStore(), route = useRoute()
  const contextKey = computed(() => JSON.stringify([
    route.fullPath, user.userId, user.roleId, user.token, user.selected_environment,
  ]))
  let active = true, mounted = false, catalogSequence = 0, testSequence = 0, draftVersion = 0

  const classGroups = computed<MethodMenuGroup[]>(() => randomList.value.flatMap(typeGroup =>
    typeGroup.children.filter(group => group.children.length).map(group => ({
      ...group, menuKey: `${typeGroup.value}:${group.value}`, typeValue: typeGroup.value, typeLabel: typeGroup.label,
    }))
  ))
  const menuSections = computed(() => methodMenuSections.map(section => ({
    ...section,
    children: classGroups.value.filter(group => section.value === 'tools'
      ? !['data', 'performance'].includes(group.typeValue) : group.typeValue === section.value),
  })).filter(section => section.children.length))
  const currentClassGroup = computed(() => classGroups.value.find(group => group.menuKey === activeGroupValue.value) || classGroups.value[0])

  async function loadCatalog() {
    if (!active) return
    const sequence = ++catalogSequence, context = contextKey.value
    const current = () => active && sequence === catalogSequence && context === contextKey.value
    catalogLoading.value = true
    catalogError.value = ''
    try {
      const response = readCatalog(await getSystemRandomList())
      if (!current()) return
      randomList.value = response
      if (!classGroups.value.some(group => group.menuKey === activeGroupValue.value)) {
        activeGroupValue.value = classGroups.value.find(group => group.value === '人物信息测试数据')?.menuKey || classGroups.value[0]?.menuKey || ''
      }
    } catch (loadFailure0) {
      if (current()) (reportLoadError(loadFailure0, "方法目录加载失败，请重试", false), catalogError.value = '方法目录加载失败，请重试')
    } finally {
      if (current()) catalogLoading.value = false
    }
  }

  async function obtain(value?: string) {
    if (!active || testing.value) return
    const expression = normalizeExpression(value || input.value)
    if (!expression) { Message.warning('请输入需要测试的方法'); return }
    const sequence = ++testSequence, context = contextKey.value, draft = draftVersion
    const current = () => active && sequence === testSequence && context === contextKey.value && draft === draftVersion
    testing.value = true
    testError.value = ''
    lastExpression.value = expression
    try {
      const result = readGeneratedValue(await getSystemRandomData(wrapExpression(expression)))
      if (current()) Notification.success({ title: wrapExpression(expression), content: result, closable: true })
    } catch {
      if (current()) testError.value = '数据生成失败，请重试；部分方法依赖上传文件或运行环境'
    } finally {
      testing.value = false
    }
  }

  function retryTest() { if (lastExpression.value !== null) void obtain(lastExpression.value) }
  function selectGroup(key: string) { if (!testing.value) activeGroupValue.value = key }
  function getMenuRemark(item: MethodMenuGroup) {
    return ['cache', 'json'].includes(item.typeValue) ? '不要使用，只做说明' : ''
  }
  function invalidateReads() { catalogSequence++; testSequence++; catalogLoading.value = false }
  watch(input, () => {
    draftVersion++; testSequence++; testError.value = ''; lastExpression.value = null
  }, { flush: 'sync' })
  watch(contextKey, () => {
    invalidateReads()
    randomList.value = []; activeGroupValue.value = ''; catalogError.value = ''; testError.value = ''; lastExpression.value = null
    input.value = wrapExpression('这里输入函数名称，注意加上英文括号()')
    if (active && mounted) void loadCatalog()
  }, { flush: 'sync' })
  onMounted(() => { mounted = true; void loadCatalog() })
  onDeactivated(() => { active = false; invalidateReads(); randomList.value = []; testError.value = ''; lastExpression.value = null })
  onActivated(() => { if (mounted && !active) { active = true; void loadCatalog() } })
  onBeforeUnmount(() => { active = false; mounted = false; invalidateReads() })
</script>
<style lang="less" scoped>
  .mango-variable-page {
    width: 100%;
  }

  .mango-variable-catalog { width: 100%; min-width: 0; }
  .mango-variable-shell {
    box-sizing: border-box;
    padding: var(--m-page-gap);
    height: 100%;
    min-height: 0;
    overflow: auto;
  }

  .mango-variable-try-card {
    padding: 12px;
  }

  .mango-variable-try-title {
    font-size: 16px;
    font-weight: 600;
    color: var(--m-text);
  }

  .mango-variable-usage-panel {
    display: flex;
    gap: 18px;
    align-items: flex-start;
    padding: 12px 14px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-lg);
    background: var(--m-surface);
  }

  .mango-variable-usage-title {
    flex: 0 0 auto;
    padding-top: 2px;
    font-size: 13px;
    font-weight: 600;
    color: var(--m-text);
  }

  .mango-variable-usage-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
    min-width: 0;
  }

  .mango-variable-usage-item {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
  }

  .mango-variable-usage-label {
    width: 84px;
    color: var(--m-text-2);
    font-weight: 500;
  }

  .mango-variable-usage-action {
    color: var(--m-muted);
  }

  .mango-variable-usage-note {
    color: var(--m-muted);
  }

  .mango-variable-section-tip {
    padding: 10px 12px;
    border-left: 3px solid var(--m-success);
    border-radius: 4px;
    background: color-mix(in srgb, var(--m-success) 12%, transparent);
    color: var(--m-text-2);
  }

  .mango-variable-method-layout {
    display: grid;
    grid-template-columns: 220px minmax(0, 1fr);
    gap: var(--m-page-gap);
    align-items: flex-start;
  }

  .mango-variable-category-panel {
    position: sticky;
    top: 12px;
    overflow: hidden;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-lg);
    background: var(--m-surface);
  }

  .mango-variable-category-title {
    padding: 12px 14px;
    border-bottom: 1px solid var(--m-border);
    font-weight: 600;
    color: var(--m-text);
  }

  .mango-variable-category-list {
    display: flex;
    flex-direction: column;
    padding: 8px;
    gap: 12px;
  }

  .mango-variable-category-section {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .mango-variable-category-section-title {
    padding: 4px 8px;
    color: var(--m-muted);
    font-size: 12px;
    font-weight: 600;
  }

  .mango-variable-category-item {
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

  .mango-variable-category-item:hover {
    background: var(--m-hover);
    color: var(--m-text);
  }

  .mango-variable-category-item.active {
    background: var(--m-hover);
    color: var(--m-text);
    font-weight: 600;
  }

  .mango-variable-category-item.active::before {
    position: absolute;
    top: 8px;
    bottom: 8px;
    left: 0;
    width: 3px;
    border-radius: 2px;
    background: var(--m-primary);
    content: '';
  }

  .mango-variable-category-label > span { overflow: hidden; text-overflow: ellipsis; }
  .mango-variable-category-label {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 2px;
  }

  .mango-variable-category-remark {
    color: var(--m-muted);
    font-size: 12px;
    font-weight: 400;
    line-height: 16px;
  }

  .mango-variable-category-count {
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

  .mango-variable-method-content {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 14px;
  }

  .mango-variable-inline-code {
    font-family: Consolas, 'Courier New', monospace;
    padding: 2px 7px;
    border-radius: 4px;
    border: 1px solid var(--m-border);
    background: var(--m-surface-soft);
    color: var(--m-primary);
    overflow-wrap: anywhere;
  }

</style>
