<template>
  <TableBody ref="tableBody" content-flush>
    <template #header>
      <TableHeader title="配置管理">
        <template #header-extra>
          <span class="mango-system-settings__save-hint">修改后自动保存</span>
        </template>
      </TableHeader>
    </template>
    <template #default>
      <div v-if="settingsLoading" class="mango-system-settings__loading">
        <a-spin :loading="true" tip="正在加载系统配置..." />
      </div>
      <div v-else class="mango-system-settings">
        <div class="mango-system-settings__layout">
          <nav class="mango-system-settings__tabs" aria-label="配置分组目录">
            <p class="mango-system-settings__nav-caption">配置目录</p>
            <button
              v-for="group in navigationGroups"
              :key="group.key"
              type="button"
              class="mango-system-settings__tab"
              :class="{ 'mango-system-settings__tab--active': activeNavigationKey === group.key }"
              :aria-current="activeNavigationKey === group.key ? 'location' : undefined"
              @click="scrollToGroup(group.key)"
            >
              <span class="mango-system-settings__tab-icon" aria-hidden="true">
                <component :is="resolveNavigationIcon(group.key)" />
              </span>
              <span class="mango-system-settings__tab-copy">
                <strong>{{ group.title }}</strong>
                <span>{{ group.description }}</span>
              </span>
            </button>
          </nav>

          <main
            ref="panelRef"
            class="mango-system-settings__panel"
            @scroll.passive="handlePanelScroll"
          >
            <div class="mango-system-settings__level-filter">
              <div
                class="mango-system-settings__level-options"
                role="group"
                aria-label="配置级别筛选"
              >
                <span class="mango-system-settings__level-label">配置级别：</span>
                <button
                  v-for="option in CONFIG_LEVEL_OPTIONS"
                  :key="option.key"
                  type="button"
                  class="mango-system-settings__level-option"
                  :aria-pressed="selectedLevel === option.key"
                  @click="selectedLevel = option.key"
                  >{{ option.title }}</button
                >
              </div>
            </div>
            <section
              v-for="navigationGroup in navigationGroups"
              :key="navigationGroup.key"
              :ref="(element) => setSectionElement(navigationGroup.key, element)"
              class="mango-system-settings__large-section"
            >
              <div class="mango-system-settings__large-header">
                <div class="mango-system-settings__heading-copy">
                  <h2 class="mango-system-settings__large-title">{{ navigationGroup.title }}</h2>
                  <p class="mango-system-settings__large-description">
                    {{ navigationGroup.description }}
                  </p>
                </div>
              </div>

              <div class="mango-system-settings__section-grid">
                <section
                  v-if="navigationGroup.includeBackendService"
                  v-show="matchesBackend()"
                  class="mango-system-settings__small-section"
                >
                  <div class="mango-system-settings__card-header">
                    <div class="mango-system-settings__heading-copy">
                      <h3 class="mango-system-settings__card-title">后端服务</h3>
                      <p class="mango-system-settings__card-description">
                        日志、数据权限与方法缓存
                      </p>
                    </div>
                  </div>
                  <div
                    class="mango-system-settings__card-content mango-system-settings__card-content--compact"
                  >
                    <div class="mango-system-settings__switch-row">
                      <span class="mango-system-settings__label">调试日志</span>
                      <a-switch
                        :model-value="settingsData.isDebug"
                        :loading="debugLogSaving"
                        aria-label="调试日志"
                        size="medium"
                        @change="doPostSystemSetDebugLog"
                      />
                    </div>
                    <div
                      v-if="guestProjectDataScopeConfig"
                      class="mango-system-settings__switch-row"
                    >
                      <span class="mango-system-settings__label">允许游客查看所有项目数据</span>
                      <a-switch
                        :model-value="switchValue(guestProjectDataScopeConfig)"
                        :loading="backendServiceConfigLoading.GUEST_CAN_VIEW_ALL_PROJECT_DATA"
                        size="medium"
                        aria-label="允许游客查看所有项目数据"
                        @change="(value) => handleBackendServiceSwitchChange(guestProjectDataScopeConfig!, value)"
                      />
                    </div>
                    <div class="mango-system-settings__cache-list">
                      <div
                        v-for="item in methodCacheItems"
                        :key="item.type"
                        class="mango-system-settings__cache-item"
                      >
                        <div class="mango-system-settings__cache-meta">
                          <span class="mango-system-settings__label">{{ item.label }}</span>
                        </div>
                        <div class="mango-system-settings__cache-actions">
                          <a-button
                            size="small"
                            :loading="methodCacheRefreshLoading[item.type]"
                            @click="handleMethodCacheRefresh(item)"
                            data-testid="qa-views-system-settings-button-刷新缓存"
                          >
                            刷新缓存
                          </a-button>
                          <a-button
                            size="small"
                            :loading="methodCacheViewLoading[item.cacheKey]"
                            @click="handleMethodCacheView(item)"
                            data-testid="qa-views-system-settings-button-查看缓存"
                          >
                            查看缓存
                          </a-button>
                        </div>
                      </div>
                    </div>
                  </div>
                </section>

                <section
                  v-for="group in navigationGroup.groups"
                  :key="group.key"
                  :ref="(element) => setConfigSectionElement(group.key, element)"
                  class="mango-system-settings__small-section"
                >
                  <div
                    v-if="
                      navigationGroup.includeBackendService || navigationGroup.groups.length > 1
                    "
                    class="mango-system-settings__card-header"
                  >
                    <div>
                      <h3 class="mango-system-settings__card-title">{{ groupTitle(group) }}</h3>
                    </div>
                    <a-button
                      v-if="group.key === 'cache_performance'"
                      size="small"
                      :loading="runtimeCacheClearLoading"
                      @click="handleRuntimeCacheClear"
                    >
                      立即清理统计缓存
                    </a-button>
                  </div>
                  <div class="mango-system-settings__card-content">
                    <div
                      v-if="!displayItems(group).some((item) => matchesItem(group, item))"
                      class="mango-empty-state mango-system-settings__empty"
                    >
                      当前分组暂无符合级别的配置
                    </div>
                    <div
                      v-for="item in displayItems(group)"
                      v-show="matchesItem(group, item)"
                      :key="item.key"
                      class="mango-system-settings__item"
                    >
                      <ReportDeliveryEditor v-if="item.key === 'REPORT_DELIVERY_CONFIG'" v-model="item.value" :loading="itemSaving(item)" @save="saveItem(group, item)" />
                      <div v-else class="mango-system-settings__row">
                        <div class="mango-system-settings__label-wrap">
                          <span class="mango-system-settings__label">{{ itemLabel(item) }}</span>
                        </div>
                        <div class="mango-system-settings__type" aria-label="配置类型">
                          <a-tag
                            v-if="item.management_level === MANAGEMENT_LEVEL_CAUTION"
                            size="small"
                            color="orange"
                          >
                            谨慎修改
                          </a-tag>
                          <a-tag
                            v-else-if="item.management_level === MANAGEMENT_LEVEL_STANDARD"
                            size="small"
                          >
                            普通配置
                          </a-tag>
                        </div>
                        <div class="mango-system-settings__control">
                          <a-switch
                            v-if="isSwitchType(item)"
                            :model-value="switchValue(item)"
                            :loading="itemSaving(item)"
                            size="medium"
                            :aria-label="itemLabel(item)"
                            @change="(value) => handleSwitchChange(group, item, value)"
                          />
                          <EnvironmentNameOverrides
                            v-else-if="isEnvironmentDisplayNames(item)"
                            v-model="item.value"
                            :options="enumStore.environment_type_defaults"
                            :loading="itemSaving(item)"
                            @save="saveItem(group, item)"
                          />
                          <EvaluationAiProfilesEditor v-else-if="item.key === 'EVALUATION_AI_PROFILES'" v-model="item.value" :loading="itemSaving(item)" @save="saveItem(group, item)" />
                          <a-select
                            v-else-if="item.key === API_TRANSIENT_RETRY_CONDITIONS_KEY"
                            v-model="item.value"
                            size="medium"
                            multiple
                            allow-clear
                            :max-tag-count="2"
                            :options="enumStore.api_transient_retry_condition"
                            :field-names="{ value: 'key', label: 'title' }"
                            :disabled="itemSaving(item)"
                            :loading="itemSaving(item)"
                            placeholder="选择触发条件；留空表示不自动重试"
                            :aria-label="itemLabel(item)"
                            @change="saveItem(group, item)"
                          />
                          <a-select
                            v-else-if="isDataFactoryValidationEnvironments(item)"
                            v-model="item.value"
                            :options="environmentOptions"
                            :field-names="fieldNames"
                            :loading="itemSaving(item)"
                            multiple
                            allow-clear
                            :max-tag-count="2"
                            :placeholder="getPlaceholder(item)"
                            size="medium"
                            :aria-label="itemLabel(item)"
                            class="mango-system-settings__input"
                            @change="saveItem(group, item)"
                          />
                          <a-input-number
                            v-else-if="isNumberType(item)"
                            v-model="item.value"
                            :precision="item.value_type === VALUE_TYPE_INT ? 0 : undefined"
                            :min="numberMin(item)"
                            :max="numberMax(item)"
                            :disabled="itemSaving(item)"
                            :placeholder="getPlaceholder(item)"
                            size="medium"
                            :aria-label="itemLabel(item)"
                            class="mango-system-settings__input mango-system-settings__input--number"
                            @blur="saveItem(group, item)"
                          />
                          <a-textarea
                            v-else-if="isLongTextType(item)"
                            v-model="item.value"
                            :disabled="itemSaving(item)"
                            :placeholder="getPlaceholder(item)"
                            allow-clear
                            auto-size
                            size="medium"
                            :aria-label="itemLabel(item)"
                            class="mango-system-settings__input"
                            @blur="saveItem(group, item)"
                          />
                          <a-input-password
                            v-else-if="item.is_secret"
                            v-model="item.value"
                            :disabled="itemSaving(item)"
                            :placeholder="secretPlaceholder(item)"
                            allow-clear
                            size="medium"
                            :aria-label="itemLabel(item)"
                            class="mango-system-settings__input"
                            @blur="saveItem(group, item)"
                          />
                          <a-input
                            v-else
                            v-model="item.value"
                            :disabled="itemSaving(item)"
                            :placeholder="getPlaceholder(item)"
                            allow-clear
                            size="medium"
                            :aria-label="itemLabel(item)"
                            class="mango-system-settings__input"
                            @blur="saveItem(group, item)"
                          />
                          <span
                            v-if="itemSaving(item)"
                            class="mango-system-settings__help"
                            role="status"
                          >
                            正在保存…
                          </span>
                        </div>
                        <div
                          v-if="
                            itemHelp(item) ||
                            item.management_level === MANAGEMENT_LEVEL_CAUTION ||
                            isTestAnchor(group, item)
                          "
                          class="mango-system-settings__aside"
                        >
                          <span
                            v-if="item.management_level === MANAGEMENT_LEVEL_CAUTION"
                            class="mango-system-settings__help mango-system-settings__help--caution"
                          >
                            此配置会影响系统运行或数据生命周期，修改前请确认影响范围。
                          </span>
                          <span v-if="itemHelp(item)" class="mango-system-settings__help">{{
                            itemHelp(item)
                          }}</span>
                          <template v-if="isTestAnchor(group, item)">
                            <div
                              v-if="group.key === 'email'"
                              class="mango-system-settings__email-test-controls"
                            >
                              <a-input
                                v-model="testRecipient"
                                aria-label="测试收件邮箱"
                                placeholder="测试收件邮箱"
                                :disabled="emailTestLoading"
                                size="medium"
                                @press-enter="handleEmailTest(group)"
                              />
                              <a-button
                                size="medium"
                                :loading="emailTestLoading"
                                @click="handleEmailTest(group)"
                              >
                                发送测试邮件
                              </a-button>
                            </div>
                            <a-button
                              v-else-if="group.key === AI_VISION_GROUP_KEY"
                              size="medium"
                              :loading="visionTestLoading"
                              @click="handleVisionTest(group)"
                              data-testid="qa-views-system-settings-button-测试视觉模型"
                              >测试视觉模型</a-button
                            >
                            <a-button
                              v-else
                              size="medium"
                              :loading="aiTestLoading"
                              @click="handleAiTest(group)"
                              data-testid="qa-views-system-settings-button-测试文本模型"
                              >测试文本模型</a-button
                            >
                            <p
                              v-if="testResults[group.key]"
                              class="mango-system-settings__test-result"
                              :class="{
                                'mango-system-settings__test-result--error':
                                  !testResults[group.key].status,
                              }"
                              role="status"
                              >{{ testResults[group.key].message }}</p
                            >
                          </template>
                        </div>
                      </div>
                    </div>
                  </div>
                </section>
              </div>
            </section>
            <div
              v-if="navigationGroups.length === 0"
              class="mango-empty-state mango-system-settings__panel-empty"
            >
              当前级别暂无可用配置
            </div>
          </main>
        </div>
      </div>
      <a-drawer
        v-model:visible="cacheDrawer.visible"
        :title="cacheDrawer.title"
        width="50%"
        unmount-on-close
      >
        <div class="mango-system-settings__cache-json">
          <JsonDisplay
            :data="cacheDrawer.data"
            :default-expanded="false"
            :show-drawer-button="false"
          />
        </div>
        <template #footer>
          <a-button
            size="small"
            @click="cacheDrawer.visible = false"
            data-testid="qa-views-system-settings-button-关闭"
            >关闭</a-button
          >
        </template>
      </a-drawer>
    </template>
  </TableBody>
</template>

<script lang="ts" setup>
  import { computed, nextTick, onMounted, reactive, ref } from 'vue'
  import { useRoute } from 'vue-router'
  import { Message, Modal } from '@arco-design/web-vue'
  import { fieldNames } from '@/setting'
  import { useEnum } from '@/store/modules/get-enum'
  import usePlatformBrandingStore from '@/store/modules/platform-branding'
  import { useMenuIcon } from '@/hooks/useMenuIcon'
  import { postSystemAiTest } from '@/api/system/ai'
  import JsonDisplay from '@/components/display/JsonDisplay.vue'
  import EnvironmentNameOverrides from './components/EnvironmentNameOverrides.vue'
  import EvaluationAiProfilesEditor from './components/EvaluationAiProfilesEditor.vue'
  import ReportDeliveryEditor from './components/ReportDeliveryEditor.vue'
  import {
    getSystemCacheDataGrouped,
    getSystemCacheDataKeyValue,
    postSystemEmailTest,
    postSystemRuntimeCacheClear,
    putSystemCacheData,
  } from '@/api/system/cache_data'
  import { postSystemMethodCacheRefresh, postSystemSetDebugLog } from '@/api/system/system'
  import {
    API_TRANSIENT_RETRY_CONDITIONS_KEY,
    API_TRANSIENT_RETRY_HELP,
    normalizeRetryConditions,
    DATA_FACTORY_VALIDATION_ENVIRONMENTS_HELP,
    CONFIG_FIELD_HELP,
    CONFIG_LEVEL_OPTIONS,
    matchesConfigLevel,
    DATA_FACTORY_VALIDATION_ENVIRONMENTS_KEY,
    normalizeConfigNumber,
  } from './config'

  const VALUE_TYPE_INT = 1
  const VALUE_TYPE_FLOAT = 2
  const VALUE_TYPE_BOOL = 3
  const VALUE_TYPE_LIST = 5
  const VALUE_TYPE_DICT = 6
  const VALUE_TYPE_JSON = 8
  const MANAGEMENT_LEVEL_CAUTION = 2
  const MANAGEMENT_LEVEL_STANDARD = 3
  const AI_TIMEOUT_MIN_SECONDS = 600
  const UI_FIXED_LOCATOR_RETRY_SECONDS_KEY = 'UI_FIXED_LOCATOR_RETRY_SECONDS'
  const UI_SMART_LOCATOR_TIMEOUT_SECONDS_KEY = 'UI_SMART_LOCATOR_TIMEOUT_SECONDS'
  const UI_VISUAL_LOCATOR_ENABLED_KEY = 'UI_VISUAL_LOCATOR_ENABLED'
  const AI_VISION_GROUP_KEY = 'ai_vision'
  const AI_VISION_USE_SEPARATE_CONFIG_KEY = 'AI_VISION_USE_SEPARATE_CONFIG'
  const AI_VISION_TIMEOUT_KEY = 'AI_VISION_TIMEOUT'
  const SQL_SLOW_QUERY_THRESHOLD_SECONDS_KEY = 'SQL_SLOW_QUERY_THRESHOLD_SECONDS'
  const EXECUTOR_API_MAX_RUNTIME_MINUTES_KEY = 'EXECUTOR_API_MAX_RUNTIME_MINUTES'
  const EXECUTOR_PYTEST_MAX_RUNTIME_MINUTES_KEY = 'EXECUTOR_PYTEST_MAX_RUNTIME_MINUTES'
  const EXECUTOR_UI_CASE_MAX_RUNTIME_MINUTES_KEY = 'EXECUTOR_UI_CASE_MAX_RUNTIME_MINUTES'
  const EXECUTOR_UI_PAGE_STEP_MAX_RUNTIME_MINUTES_KEY = 'EXECUTOR_UI_PAGE_STEP_MAX_RUNTIME_MINUTES'
  const TEST_SUITE_STUCK_RESET_MINUTES_KEY = 'TEST_SUITE_STUCK_RESET_MINUTES'
  const TEST_SUITE_TIMEOUT_RETRY_COUNT_KEY = 'TEST_SUITE_TIMEOUT_RETRY_COUNT'
  const SYSTEM_DOMAIN_NAME_KEY = 'SYSTEM_DOMAIN_NAME'
  const EXECUTION_TIMEOUT_KEYS = new Set([
    EXECUTOR_API_MAX_RUNTIME_MINUTES_KEY,
    EXECUTOR_PYTEST_MAX_RUNTIME_MINUTES_KEY,
    EXECUTOR_UI_CASE_MAX_RUNTIME_MINUTES_KEY,
    EXECUTOR_UI_PAGE_STEP_MAX_RUNTIME_MINUTES_KEY,
    TEST_SUITE_STUCK_RESET_MINUTES_KEY,
  ])
  const EXECUTION_CONFIG_KEYS = new Set([
    ...EXECUTION_TIMEOUT_KEYS,
    TEST_SUITE_TIMEOUT_RETRY_COUNT_KEY,
  ])
  const GUEST_CAN_VIEW_ALL_PROJECT_DATA_KEY = 'GUEST_CAN_VIEW_ALL_PROJECT_DATA'
  const SYSTEM_SERVICES_GROUP_KEY = 'system-services'
  const DATA_CAPABILITIES_GROUP_KEY = 'data-capabilities'
  const AI_CAPABILITIES_GROUP_KEY = 'ai-capabilities'
  const route = useRoute()
  const { resolveMenuIcon } = useMenuIcon()
  const navigationIcons: Record<string, { paths: string[]; fallback: string }> = {
    [SYSTEM_SERVICES_GROUP_KEY]: {
      paths: ['/system/settings/index', '/system'],
      fallback: 'icon-settings',
    },
    access: {
      paths: ['/organization-permission', '/system/user/index'],
      fallback: 'icon-user-group',
    },
    retention: { paths: [], fallback: 'icon-history' },
    'report-delivery': { paths: [], fallback: 'icon-file' },
    'cache-performance': { paths: [], fallback: 'icon-dashboard' },
    api: { paths: ['/apitest'], fallback: 'icon-thunderbolt' },
    ui: { paths: ['/uitest'], fallback: 'icon-desktop' },
    pytest: { paths: ['/pytest'], fallback: 'icon-code' },
    execution: { paths: ['/timing'], fallback: 'icon-calendar-clock' },
    'runtime-capacity': {
      paths: ['/platform-management/runtime', '/system/runtime-center/index', '/equipment'],
      fallback: 'icon-computer',
    },
    [DATA_CAPABILITIES_GROUP_KEY]: { paths: ['/data-factory'], fallback: 'icon-storage' },
    [AI_CAPABILITIES_GROUP_KEY]: { paths: ['/ai'], fallback: 'icon-robot' },
  }
  function resolveNavigationIcon(key: string) {
    const mapping = navigationIcons[key]
    return mapping ? resolveMenuIcon(mapping.paths, mapping.fallback) : 'icon-settings'
  }

  interface ConfigItem {
    id: number
    key: string
    describe: string
    value: any
    value_type: number
    is_secret: boolean
    management_level: number
    has_value: boolean
    placeholder?: string
  }

  interface ConfigGroup {
    key: string
    title: string
    items: ConfigItem[]
  }

  interface NavigationGroup {
    key: string
    title: string
    description: string
    groupKeys: string[]
    groups: ConfigGroup[]
    includeBackendService?: boolean
  }

  const navigationDefinitions = [
    { key: 'report-delivery', title: '报告生成与交付', description: '离线 HTML、对象存储与通知交付', groupKeys: ['report_delivery'] },
    {
      key: SYSTEM_SERVICES_GROUP_KEY,
      title: '系统服务',
      description: '基础服务与邮件',
      groupKeys: ['system', 'email'],
      includeBackendService: true,
    },
    {
      key: 'access',
      title: '用户与访问',
      description: '自助注册、访问提示与登录页展示',
      groupKeys: ['access'],
    },
    {
      key: 'retention',
      title: '数据保留',
      description: '历史数据与运行产物自动清理周期',
      groupKeys: ['retention'],
    },
    {
      key: 'cache-performance',
      title: '缓存与性能',
      description: '页面统计缓存和数据访问边界',
      groupKeys: ['cache_performance', 'data_source'],
    },
    {
      key: 'api',
      title: 'API 自动化',
      description: '接口请求、执行与 Mock 参数',
      groupKeys: ['api', 'mock'],
    },
    {
      key: 'ui',
      title: 'UI 自动化',
      description: '元素定位与执行参数',
      groupKeys: ['ui'],
    },
    {
      key: 'pytest',
      title: 'Pytest 自动化',
      description: 'Pytest 执行参数',
      groupKeys: ['pytest'],
    },
    {
      key: 'execution',
      title: '执行任务',
      description: '执行超时、恢复与重试',
      groupKeys: ['execution'],
    },
    {
      key: 'runtime-capacity',
      title: '运行与容量',
      description: 'Worker、执行器与实时工作区容量',
      groupKeys: ['runtime'],
    },
    {
      key: DATA_CAPABILITIES_GROUP_KEY,
      title: '数据工厂',
      description: '数据校验与数据工厂参数',
      groupKeys: ['data_factory'],
    },
    {
      key: AI_CAPABILITIES_GROUP_KEY,
      title: '智能能力',
      description: '模型服务与智能定位参数',
      groupKeys: ['ai', AI_VISION_GROUP_KEY],
    },
    { key: 'evaluation_ai', title: '效果测评 AI', description: '独立维护评分与总结 AI 列表', groupKeys: ['evaluation_ai'] },
  ]

  const settingsGroups = ref<ConfigGroup[]>([])
  const activeNavigationKey = ref(SYSTEM_SERVICES_GROUP_KEY)
  const panelRef = ref<HTMLElement | null>(null)
  const sectionElements = new Map<string, HTMLElement>()
  const configSectionElements = new Map<string, HTMLElement>()
  const enumStore = useEnum()
  const settingsLoading = ref(true)
  const aiTestLoading = ref(false)
  const visionTestLoading = ref(false)
  const emailTestLoading = ref(false)
  const runtimeCacheClearLoading = ref(false)
  const testRecipient = ref('')
  const testResults = reactive<Record<string, { status: boolean; message: string }>>({})
  const pendingSaves = new Map<string, Promise<boolean>>()
  const itemSaveLoading = reactive<Record<string, boolean>>({})
  const lastSavedValues = new Map<string, string>()
  const methodCacheRefreshLoading = reactive<Record<string, boolean>>({})
  const methodCacheViewLoading = reactive<Record<string, boolean>>({})
  const backendServiceConfigLoading = reactive<Record<string, boolean>>({})
  const hiddenConfigKeys = ['AI_PROVIDER_TYPE']
  const hiddenGroupKeys = ['gray']
  const integerSwitchKeys: string[] = ['MOCK_CALLBACK_ENABLED']
  const environmentOptions = computed(() => enumStore.environment_type || [])
  const methodCacheItems = [
    {
      label: '随机测试数据方法缓存',
      type: 'test_data',
      cacheKey: 'test_data_select_value',
    },
    {
      label: 'API断言方法缓存',
      type: 'api_assertion',
      cacheKey: 'ass_select_value',
    },
    {
      label: 'UI自动化操作/断言缓存',
      type: 'ui_operation',
      cacheKey: 'select_value',
    },
  ]

  const settingsData = reactive({
    isDebug: false,
  })
  const cacheDrawer = reactive({
    visible: false,
    title: '缓存数据',
    data: null as any,
  })

  const visibleGroups = computed(() => {
    const groups = settingsGroups.value
      .filter((group) => !hiddenGroupKeys.includes(group.key))
      .map((group) => ({
        ...group,
        items: group.items.filter((item) =>
          group.key === 'system'
            ? isEnvironmentDisplayNames(item)
            : !hiddenConfigKeys.includes(item.key)
        ),
      }))
    const execution = groups.find((group) => group.key === 'execution')
    const pytestTimeout = execution?.items.find(
      (item) => item.key === EXECUTOR_PYTEST_MAX_RUNTIME_MINUTES_KEY
    )
    if (execution && pytestTimeout) {
      execution.items = execution.items.filter((item) => item !== pytestTimeout)
      const pytest = groups.find((group) => group.key === 'pytest')
      if (pytest) pytest.items.push(pytestTimeout)
      else groups.push({ key: 'pytest', title: 'Pytest 自动化配置', items: [pytestTimeout] })
    }
    return groups.filter((group) => group.items.length > 0)
  })
  const navigationGroups = computed<NavigationGroup[]>(() => {
    const groupsByKey = new Map(visibleGroups.value.map((group) => [group.key, group]))
    return navigationDefinitions
      .map((definition) => ({
        ...definition,
        groups: definition.groupKeys
          .map((groupKey) => groupsByKey.get(groupKey))
          .filter((group): group is ConfigGroup => Boolean(group)),
      }))
      .filter((group) => group.includeBackendService || group.groups.length > 0)
  })
  const groupTitle = (group: ConfigGroup) => {
    const titles: Record<string, string> = {
      system: '环境显示名称',
      api: 'API 自动化配置',
      ui: 'UI 自动化配置',
      pytest: 'Pytest 自动化配置',
      ai: '文本与推理模型',
      ai_vision: '视觉模型配置',
    }
    return titles[group.key] || group.title
  }
  const setSectionElement = (groupKey: string, element: unknown) => {
    if (element instanceof HTMLElement) sectionElements.set(groupKey, element)
    else sectionElements.delete(groupKey)
  }
  const setConfigSectionElement = (groupKey: string, element: unknown) => {
    if (element instanceof HTMLElement) configSectionElements.set(groupKey, element)
    else configSectionElements.delete(groupKey)
  }
  const findNavigationGroup = (groupKey: string) =>
    navigationGroups.value.find(
      (group) => group.key === groupKey || group.groupKeys.includes(groupKey)
    )
  const scrollElementIntoPanel = (element: HTMLElement, behavior: ScrollBehavior) => {
    const panel = panelRef.value
    if (!panel) return
    const panelTop = panel.getBoundingClientRect().top
    const elementTop = element.getBoundingClientRect().top
    panel.scrollTo({ top: panel.scrollTop + elementTop - panelTop, behavior })
  }
  const scrollToGroup = (groupKey: string) => {
    activeNavigationKey.value = groupKey
    const element = sectionElements.get(groupKey)
    if (element) {
      const behavior = window.matchMedia('(prefers-reduced-motion: reduce)').matches
        ? 'auto'
        : 'smooth'
      scrollElementIntoPanel(element, behavior)
    }
  }
  const handlePanelScroll = () => {
    const panel = panelRef.value
    if (!panel || navigationGroups.value.length === 0) return
    const panelTop = panel.getBoundingClientRect().top
    let currentKey = navigationGroups.value[0].key
    navigationGroups.value.forEach((group) => {
      const section = sectionElements.get(group.key)
      if (section && section.getBoundingClientRect().top - panelTop <= 1) {
        currentKey = group.key
      }
    })
    activeNavigationKey.value = currentKey
  }
  const systemGroup = computed(() => settingsGroups.value.find((group) => group.key === 'system'))
  const guestProjectDataScopeConfig = computed(() =>
    systemGroup.value?.items.find((item) => item.key === GUEST_CAN_VIEW_ALL_PROJECT_DATA_KEY)
  )
  const itemSaving = (item: ConfigItem) => itemSaveLoading[item.key] === true
  const isAiGroup = (group: ConfigGroup) => group.key === 'ai' || group.key === AI_VISION_GROUP_KEY
  const isTestAnchor = (group: ConfigGroup, item: ConfigItem) => {
    const preferredKey =
      group.key === 'email'
        ? 'SYSTEM_SEND_USER'
        : group.key === AI_VISION_GROUP_KEY
        ? AI_VISION_USE_SEPARATE_CONFIG_KEY
        : 'AI_MODEL'
    if (group.key !== 'email' && !isAiGroup(group)) return false
    return (
      item === (group.items.find((candidate) => candidate.key === preferredKey) || group.items[0])
    )
  }
  const itemHelp = (item: ConfigItem): string => {
    if (item.key === 'API_TRANSIENT_RETRY_ENABLED') return API_TRANSIENT_RETRY_HELP
    if (item.key === API_TRANSIENT_RETRY_CONDITIONS_KEY)
      return '默认选择连接异常、请求超时、HTTP 502/503/504。业务断言失败须主动选择；不会把 JSON 业务码误判为 HTTP 状态码。'
    if (item.key === 'MOCK_CALLBACK_ENABLED')
      return '完成数据库迁移后开启；仅影响配置了回调断言的 Case，不改变普通 Mock 接口。'
    if (isDataFactoryValidationEnvironments(item)) return DATA_FACTORY_VALIDATION_ENVIRONMENTS_HELP
    if (isExecutionConfig(item)) return item.placeholder || ''
    if (item.key === UI_FIXED_LOCATOR_RETRY_SECONDS_KEY)
      return '所有定位组共享此窗口；无固定定位时直接进入智能定位。'
    if (item.key === UI_SMART_LOCATOR_TIMEOUT_SECONDS_KEY)
      return '历史、DOM、Accessibility AI 与视觉兜底共用的定位总时间；开启视觉后会预留部分时间，避免被文本 AI 全部耗尽。'
    if (item.key === UI_VISUAL_LOCATOR_ENABLED_KEY)
      return '固定定位、历史/DOM 与 Accessibility AI 均失败后才调用；页面截图会发送给当前生效的模型供应商，常见密码和 Token 输入框会先遮挡，视觉失败会安全降级。'
    if (item.key === AI_VISION_USE_SEPARATE_CONFIG_KEY)
      return switchValue(item)
        ? '独立视觉配置将覆盖主 AI 的供应商、APIKey、接口地址和模型；文本定位仍使用主 AI。'
        : '当前跟随主 AI，复用主 AI 的供应商、APIKey、接口地址和模型。开启后可配置独立视觉模型。'
    if (item.key === AI_VISION_TIMEOUT_KEY)
      return '视觉 AI 单次请求的超时上限；实际执行时间同时受“智能定位总超时”剩余预算限制。'
    if (item.key === 'AI_VISION_PROVIDER_TYPE')
      return '当前执行器支持 OpenAI 兼容协议：openai_compatible、openai、azure_openai。'
    if (item.key.startsWith('AI_VISION_'))
      return '仅在“使用独立视觉模型配置”开启时生效，不影响文本定位模型。'
    if (isSystemDomain(item)) return '用于邮件、机器人通知中的平台访问链接。'
    if (item.key === 'API_TIMEOUT') return '单位：秒，限制单次接口请求的等待时间。'
    return CONFIG_FIELD_HELP[item.key] || item.placeholder || ''
  }
  const isAiTimeout = (item: ConfigItem) => item.key === 'AI_TIMEOUT'
  const isEnvironmentDisplayNames = (item: ConfigItem) => item.key === 'ENVIRONMENT_DISPLAY_NAMES'
  const isDataFactoryValidationEnvironments = (item: ConfigItem) =>
    item.key === DATA_FACTORY_VALIDATION_ENVIRONMENTS_KEY
  const isSystemDomain = (item: ConfigItem) => item.key === SYSTEM_DOMAIN_NAME_KEY
  const isExecutionConfig = (item: ConfigItem) => EXECUTION_CONFIG_KEYS.has(item.key)
  const isNumberType = (item: ConfigItem) =>
    item.value_type === VALUE_TYPE_INT || item.value_type === VALUE_TYPE_FLOAT
  const numberMin = (item: ConfigItem) => {
    if (isAiTimeout(item)) return AI_TIMEOUT_MIN_SECONDS
    if (item.key === UI_FIXED_LOCATOR_RETRY_SECONDS_KEY) return 0
    if (item.key === UI_SMART_LOCATOR_TIMEOUT_SECONDS_KEY) return 5
    if (item.key === AI_VISION_TIMEOUT_KEY) return 1
    if (item.key === SQL_SLOW_QUERY_THRESHOLD_SECONDS_KEY) return 1
    if (EXECUTION_TIMEOUT_KEYS.has(item.key)) return 1
    if (item.key === TEST_SUITE_TIMEOUT_RETRY_COUNT_KEY) return 0
    if (item.key.endsWith('_RETENTION_DAYS')) return 1
    if (item.key.endsWith('_CACHE_SECONDS')) return 0
    if (item.key.endsWith('_MAX_KB')) return 1
    return undefined
  }
  const numberMax = (item: ConfigItem) => {
    if (item.key === UI_FIXED_LOCATOR_RETRY_SECONDS_KEY) return 60
    if (item.key === UI_SMART_LOCATOR_TIMEOUT_SECONDS_KEY) return 120
    if (item.key === AI_VISION_TIMEOUT_KEY) return 120
    if (item.key === SQL_SLOW_QUERY_THRESHOLD_SECONDS_KEY) return 3600
    if (EXECUTION_TIMEOUT_KEYS.has(item.key)) return 1440
    if (item.key === TEST_SUITE_TIMEOUT_RETRY_COUNT_KEY) return 10
    if (item.key.endsWith('_RETENTION_DAYS')) return 3650
    if (item.key.endsWith('_CACHE_SECONDS')) return 86400
    if (item.key.endsWith('_MAX_KB')) return 10240
    return undefined
  }
  const isBoolType = (item: ConfigItem) => item.value_type === VALUE_TYPE_BOOL
  const isIntegerSwitchType = (item: ConfigItem) => integerSwitchKeys.includes(item.key)
  const isSwitchType = (item: ConfigItem) => isBoolType(item) || isIntegerSwitchType(item)
  const isLongTextType = (item: ConfigItem) =>
    [VALUE_TYPE_LIST, VALUE_TYPE_DICT, VALUE_TYPE_JSON].includes(item.value_type)
  const itemLabel = (item: ConfigItem) => {
    if (item.key === 'MOCK_CALLBACK_ENABLED') return '启用 Case 回调验证'
    if (isSystemDomain(item)) return '访问地址'
    if (item.key === 'SYSTEM_STAMP_KET') return '邮箱授权码'
    if (item.key === 'SYSTEM_EMAIL_HOST') return 'SMTP 服务器'
    return item.describe
  }
  const getPlaceholder = (item: ConfigItem) => {
    if (isSystemDomain(item)) return '请输入发送邮件中使用的系统访问域名'
    return item.placeholder || `请输入${item.describe}`
  }
  const secretPlaceholder = (item: ConfigItem) =>
    item.has_value ? '已配置，留空表示不修改' : getPlaceholder(item)
  const isEnabledValue = (value: any) => [true, 1, '1', 'true', 'True'].includes(value)
  const switchValue = (item: ConfigItem) => isEnabledValue(item.value)
  const setSwitchValue = (item: ConfigItem, value: boolean | string | number) => {
    item.value = isEnabledValue(value)
  }
  const displayItems = (group: ConfigGroup) => {
    if (group.key !== AI_VISION_GROUP_KEY) return group.items
    const sourceConfig = group.items.find((item) => item.key === AI_VISION_USE_SEPARATE_CONFIG_KEY)
    if (sourceConfig && !switchValue(sourceConfig)) {
      return group.items.filter(
        (item) =>
          item.key === AI_VISION_USE_SEPARATE_CONFIG_KEY || item.key === AI_VISION_TIMEOUT_KEY
      )
    }
    return group.items
  }

  const selectedLevel = ref('all')
  const matchesItem = (_group: ConfigGroup, item: ConfigItem) =>
    matchesConfigLevel(selectedLevel.value, item.management_level)
  const matchesBackend = (): boolean => selectedLevel.value === 'all'

  const normalizeEnvironmentList = (value: any): number[] => {
    let environments = value
    if (typeof environments === 'string') {
      try {
        environments = JSON.parse(environments)
      } catch {
        environments = []
      }
    }
    if (!Array.isArray(environments)) return []
    const validValues = new Set(environmentOptions.value.map((option: any) => Number(option.key)))
    return Array.from(
      new Set(
        environments
          .map((environment) => Number(environment))
          .filter((environment) => validValues.has(environment))
      )
    ).sort((left, right) => left - right)
  }

  const normalizeEditValue = (item: ConfigItem) => {
    if (item.key === API_TRANSIENT_RETRY_CONDITIONS_KEY) return normalizeRetryConditions(item.value)
    if (item.key === 'REPORT_DELIVERY_CONFIG') {
      if (typeof item.value !== 'string') return { ...(item.value || {}) }
      try { return JSON.parse(item.value) } catch { return {} }
    }
    if (item.key === 'EVALUATION_AI_PROFILES') return Array.isArray(item.value) ? item.value : []
    if (isEnvironmentDisplayNames(item)) {
      let names = item.value || {}
      if (typeof names === 'string') {
        try {
          names = JSON.parse(names)
        } catch {
          names = {}
        }
      }
      return names && typeof names === 'object' && !Array.isArray(names) ? { ...names } : {}
    }
    if (isDataFactoryValidationEnvironments(item)) {
      const environments = normalizeEnvironmentList(item.value)
      return environments.length ? environments : null
    }
    if (isAiTimeout(item)) {
      const timeout = Number(item.value)
      return Number.isFinite(timeout) && timeout >= AI_TIMEOUT_MIN_SECONDS
        ? timeout
        : AI_TIMEOUT_MIN_SECONDS
    }
    if (isSwitchType(item)) {
      return switchValue(item)
    }
    if (isNumberType(item)) {
      return normalizeConfigNumber(item.value)
    }
    if (isLongTextType(item) && typeof item.value !== 'string') {
      return JSON.stringify(item.value, null, 2)
    }
    return item.value
  }

  const normalizePayloadValue = (item: ConfigItem) => {
    if (item.key === API_TRANSIENT_RETRY_CONDITIONS_KEY) return normalizeRetryConditions(item.value)
    if (isEnvironmentDisplayNames(item)) {
      return Object.fromEntries(
        Object.entries(item.value).map(([key, value]) => [key, String(value).trim()])
      )
    }
    if (isDataFactoryValidationEnvironments(item)) {
      const environments = normalizeEnvironmentList(item.value)
      return environments.length ? environments : null
    }
    if (isAiTimeout(item)) {
      const timeout = Number(item.value)
      return Number.isFinite(timeout) && timeout >= AI_TIMEOUT_MIN_SECONDS
        ? timeout
        : AI_TIMEOUT_MIN_SECONDS
    }
    if (isIntegerSwitchType(item)) {
      return switchValue(item) ? 1 : 0
    }
    return item.value === '' ? null : item.value
  }

  const serializedItemValue = (item: ConfigItem) =>
    JSON.stringify(normalizePayloadValue(item)) ?? 'null'

  const restoreSavedValue = (item: ConfigItem, savedValue?: string) => {
    if (savedValue === undefined) return
    item.value = normalizeEditValue({ ...item, value: JSON.parse(savedValue) })
  }

  const rememberSavedValues = (groups: ConfigGroup[]) => {
    lastSavedValues.clear()
    groups.forEach((group) => {
      group.items.forEach((item) => lastSavedValues.set(item.key, serializedItemValue(item)))
    })
  }

  const validateGroup = (group: ConfigGroup) => {
    const aiTimeout = group.items.find((item) => item.key === 'AI_TIMEOUT')
    const timeout = Number(aiTimeout?.value)
    if (aiTimeout && (!Number.isFinite(timeout) || timeout < AI_TIMEOUT_MIN_SECONDS)) {
      Message.warning(`AI请求超时时间不能低于${AI_TIMEOUT_MIN_SECONDS}秒`)
      return false
    }
    const fixedTimeout = group.items.find((item) => item.key === UI_FIXED_LOCATOR_RETRY_SECONDS_KEY)
    if (fixedTimeout && (Number(fixedTimeout.value) < 0 || Number(fixedTimeout.value) > 60)) {
      Message.warning('固定定位重试窗口必须在 0～60 秒之间')
      return false
    }
    const smartTimeout = group.items.find(
      (item) => item.key === UI_SMART_LOCATOR_TIMEOUT_SECONDS_KEY
    )
    if (smartTimeout && (Number(smartTimeout.value) < 5 || Number(smartTimeout.value) > 120)) {
      Message.warning('智能定位总超时必须在 5～120 秒之间')
      return false
    }
    const invalidExecutionTimeout = group.items.find(
      (item) =>
        EXECUTION_TIMEOUT_KEYS.has(item.key) &&
        (!Number.isInteger(Number(item.value)) ||
          Number(item.value) < 1 ||
          Number(item.value) > 1440)
    )
    if (invalidExecutionTimeout) {
      Message.warning(`${invalidExecutionTimeout.describe}必须是 1～1440 分钟的整数`)
      return false
    }
    const retryCount = group.items.find((item) => item.key === TEST_SUITE_TIMEOUT_RETRY_COUNT_KEY)
    if (
      retryCount &&
      (!Number.isInteger(Number(retryCount.value)) ||
        Number(retryCount.value) < 0 ||
        Number(retryCount.value) > 10)
    ) {
      Message.warning('测试报告超时重试次数必须是 0～10 次的整数')
      return false
    }
    const resetTime = group.items.find((item) => item.key === TEST_SUITE_STUCK_RESET_MINUTES_KEY)
    const reportTimeouts = group.items.filter((item) =>
      [
        EXECUTOR_API_MAX_RUNTIME_MINUTES_KEY,
        EXECUTOR_PYTEST_MAX_RUNTIME_MINUTES_KEY,
        EXECUTOR_UI_CASE_MAX_RUNTIME_MINUTES_KEY,
      ].includes(item.key)
    )
    if (
      resetTime &&
      reportTimeouts.length > 0 &&
      Number(resetTime.value) <= Math.max(...reportTimeouts.map((item) => Number(item.value)))
    ) {
      Message.warning('测试报告卡住重置时间必须大于 API、Pytest 和 UI 用例最大执行时间')
      return false
    }
    return true
  }

  const persistItem = async (group: ConfigGroup, item: ConfigItem): Promise<boolean> => {
    if (item.is_secret && item.has_value && [null, undefined, ''].includes(item.value)) return true
    const nextValue = serializedItemValue(item)
    if (lastSavedValues.get(item.key) === nextValue) return true
    const previousValue = lastSavedValues.get(item.key)
    if (!validateGroup(group)) {
      restoreSavedValue(item, previousValue)
      return false
    }
    if (
      item.management_level === MANAGEMENT_LEVEL_CAUTION &&
      !(await confirmCautionLevelChange(item))
    ) {
      restoreSavedValue(item, previousValue)
      return false
    }
    itemSaveLoading[item.key] = true
    try {
      const res = await putSystemCacheData([
        {
          id: item.id,
          key: item.key,
          value: normalizePayloadValue(item),
        },
      ])
      lastSavedValues.set(item.key, nextValue)
      if (item.key === 'PLATFORM_NAME' || item.key === 'PLATFORM_NAME_EN') {
        usePlatformBrandingStore().apply({
          [item.key === 'PLATFORM_NAME' ? 'platform_name' : 'platform_name_en']: String(item.value),
        })
      }
      item.has_value = true
      if (item.key === 'EVALUATION_AI_PROFILES') {
        item.value = item.value.map((profile: any) => ({ ...profile, api_key: profile.api_key ? '__KEEP_SECRET__' : '' }))
        lastSavedValues.set(item.key, serializedItemValue(item))
      }
      if (isEnvironmentDisplayNames(item)) {
        try {
          await enumStore.getEnum(true)
        } catch {
          Message.warning('名称已保存，枚举刷新失败，请刷新页面后查看')
        }
      }
      Message.success(res.msg || `${itemLabel(item)}已保存`)
      return true
    } catch (error) {
      restoreSavedValue(item, previousValue)
      console.error(error)
      return false
    } finally {
      itemSaveLoading[item.key] = false
    }
  }

  const confirmCautionLevelChange = (item: ConfigItem): Promise<boolean> =>
    new Promise((resolve) => {
      Modal.warning({
        title: '确认修改谨慎配置',
        content: `“${itemLabel(item)}”会影响系统运行或数据生命周期，请确认已了解影响后再保存。`,
        okText: '确认修改',
        cancelText: '取消',
        hideCancel: false,
        onOk: () => resolve(true),
        onCancel: () => resolve(false),
      })
    })

  const saveItem = (group: ConfigGroup, item: ConfigItem): Promise<boolean> => {
    const pending = pendingSaves.get(item.key)
    if (pending) return pending
    const promise = persistItem(group, item).finally(() => pendingSaves.delete(item.key))
    pendingSaves.set(item.key, promise)
    return promise
  }

  const saveBeforeTest = async (group: ConfigGroup) => {
    for (const item of group.items) {
      const pending = pendingSaves.get(item.key)
      if (pending && !(await pending)) return false
      if (!(await saveItem(group, item))) return false
    }
    return true
  }

  const handleSwitchChange = async (
    group: ConfigGroup,
    item: ConfigItem,
    value: boolean | string | number
  ) => {
    setSwitchValue(item, value)
    await saveItem(group, item)
  }

  const handleAiTest = async (group: ConfigGroup) => {
    if (aiTestLoading.value) return
    aiTestLoading.value = true
    delete testResults.ai
    try {
      if (!(await saveBeforeTest(group))) {
        testResults.ai = { status: false, message: '配置未保存成功，请检查后重试测试。' }
        return
      }
      const res = await postSystemAiTest('text')
      testResults.ai = {
        status: Boolean(res.data?.status),
        message: res.data?.message || res.msg,
      }
      if (res.data?.status) {
        Message.success(res.data.message || res.msg)
      } else {
        Message.error(res.data?.message || '文本模型测试失败')
      }
    } catch (error) {
      testResults.ai = { status: false, message: '文本模型测试失败，请检查模型配置或网络连接。' }
      console.error(error)
    } finally {
      aiTestLoading.value = false
    }
  }

  const handleVisionTest = async (group: ConfigGroup) => {
    if (visionTestLoading.value) return
    visionTestLoading.value = true
    delete testResults[AI_VISION_GROUP_KEY]
    try {
      if (!(await saveBeforeTest(group))) {
        testResults[AI_VISION_GROUP_KEY] = {
          status: false,
          message: '配置未保存成功，请检查后重试测试。',
        }
        return
      }
      const res = await postSystemAiTest('vision')
      testResults[AI_VISION_GROUP_KEY] = {
        status: Boolean(res.data?.status),
        message: res.data?.message || res.msg,
      }
      if (res.data?.status) Message.success(res.data.message || res.msg)
      else Message.error(res.data?.message || '视觉模型测试失败')
    } catch (error) {
      testResults[AI_VISION_GROUP_KEY] = {
        status: false,
        message: '视觉模型测试失败，请检查当前生效的模型是否支持图片输入。',
      }
      console.error(error)
    } finally {
      visionTestLoading.value = false
    }
  }

  const handleEmailTest = async (group: ConfigGroup) => {
    if (emailTestLoading.value) return
    const recipient = testRecipient.value.trim()
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(recipient)) {
      Message.warning('请输入有效的测试收件邮箱')
      return
    }
    emailTestLoading.value = true
    delete testResults.email
    try {
      if (!(await saveBeforeTest(group))) {
        testResults.email = { status: false, message: '配置未保存成功，请检查后重试测试。' }
        return
      }
      const res = await postSystemEmailTest(recipient)
      testResults.email = {
        status: Boolean(res.data?.status),
        message: res.data?.message || res.msg,
      }
    } catch (error) {
      testResults.email = { status: false, message: '测试邮件发送失败，请检查邮箱配置或网络连接。' }
    } finally {
      emailTestLoading.value = false
    }
  }

  const handleRuntimeCacheClear = async () => {
    if (runtimeCacheClearLoading.value) return
    runtimeCacheClearLoading.value = true
    try {
      const res = await postSystemRuntimeCacheClear()
      Message.success(res.msg || '页面统计缓存已清理')
    } finally {
      runtimeCacheClearLoading.value = false
    }
  }

  const handleMethodCacheRefresh = async (item: (typeof methodCacheItems)[number]) => {
    methodCacheRefreshLoading[item.type] = true
    try {
      const res = await postSystemMethodCacheRefresh(item.type)
      const refreshResult = res.data?.[item.type]
      if (refreshResult?.status === false) {
        Message.warning(refreshResult.message || res.msg)
      } else {
        Message.success(refreshResult?.message || res.msg)
      }
    } catch (error) {
      console.error(error)
    } finally {
      methodCacheRefreshLoading[item.type] = false
    }
  }

  const handleMethodCacheView = async (item: (typeof methodCacheItems)[number]) => {
    methodCacheViewLoading[item.cacheKey] = true
    try {
      const res = await getSystemCacheDataKeyValue(item.cacheKey)
      cacheDrawer.title = `${item.label}：${item.cacheKey}`
      cacheDrawer.data = res.data ?? null
      cacheDrawer.visible = true
    } catch (error) {
      console.error(error)
    } finally {
      methodCacheViewLoading[item.cacheKey] = false
    }
  }

  const handleBackendServiceSwitchChange = async (
    item: ConfigItem,
    value: boolean | string | number
  ) => {
    const enabled = isEnabledValue(value)
    backendServiceConfigLoading[item.key] = true
    try {
      const res = await putSystemCacheData([
        {
          id: item.id,
          key: item.key,
          value: enabled,
        },
      ])
      item.value = enabled
      item.has_value = true
      Message.success(res.msg)
    } catch (error) {
      console.error(error)
    } finally {
      backendServiceConfigLoading[item.key] = false
    }
  }

  async function doRefresh() {
    settingsLoading.value = true
    const requestedGroup = typeof route.query.group === 'string' ? route.query.group : ''
    try {
      const res = await getSystemCacheDataGrouped()
      await enumStore.getEnum(true)
      settingsGroups.value = res.data || []
      settingsGroups.value.forEach((group) => {
        group.items.forEach((item) => {
          item.value = normalizeEditValue(item)
        })
      })
      rememberSavedValues(settingsGroups.value)
      const requestedNavigationGroup = findNavigationGroup(requestedGroup)
      activeNavigationKey.value =
        requestedNavigationGroup?.key || navigationGroups.value[0]?.key || SYSTEM_SERVICES_GROUP_KEY
    } catch (error) {
      console.error(error)
    } finally {
      settingsLoading.value = false
      await nextTick()
      const configElement = configSectionElements.get(requestedGroup)
      const navigationElement = sectionElements.get(requestedGroup)
      const targetElement = configElement || navigationElement
      if (requestedGroup && targetElement) {
        scrollElementIntoPanel(targetElement, 'auto')
      } else {
        panelRef.value?.scrollTo({ top: 0, behavior: 'auto' })
      }
    }
  }

  const debugLogSaving = ref(false)
  async function doPostSystemSetDebugLog(isDebug: boolean) {
    if (debugLogSaving.value) return
    debugLogSaving.value = true
    try {
      const res = await postSystemSetDebugLog(isDebug)
      settingsData.isDebug = res.data.is_debug
      Message.success(res.msg)
    } catch (error) {
      console.error(error)
    } finally {
      debugLogSaving.value = false
    }
  }

  onMounted(async () => {
    await doRefresh()
  })
</script>

<style scoped>
  .mango-system-settings__email-test-controls {
    display: flex;
    flex-wrap: wrap;
    gap: var(--m-space-sm);
    min-width: 0;
    max-width: 420px;
    align-items: center;
  }

  .mango-system-settings__email-test-controls :deep(.arco-input-wrapper) {
    flex: 1 1 180px;
    min-width: 0;
  }

  .mango-system-settings__test-result {
    margin: var(--m-space-sm) 0;
    color: var(--m-success);
    overflow-wrap: anywhere;
  }

  .mango-system-settings__test-result--error {
    color: var(--m-danger);
  }
  .mango-system-settings__loading {
    display: flex;
    width: 100%;
    min-height: 180px;
    align-items: center;
    justify-content: center;
  }

  .mango-system-settings {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
    background-color: var(--m-bg);
  }

  .mango-system-settings__layout {
    flex: 1;
    display: grid;
    grid-template-columns: 220px minmax(0, 1fr);
    min-height: 0;
    background-color: var(--m-bg);
    border-top: 1px solid var(--m-border);
  }

  .mango-system-settings__tabs {
    display: flex;
    flex-direction: column;
    gap: var(--m-space-xs);
    min-width: 0;
    min-height: 0;
    padding: var(--m-page-gap);
    overflow-y: auto;
    background-color: var(--m-surface-soft);
    border-right: 1px solid var(--m-border);
  }

  .mango-system-settings__tab {
    display: grid;
    grid-template-columns: 24px minmax(0, 1fr);
    align-items: center;
    gap: var(--m-space-sm);
    width: 100%;
    min-height: 52px;
    padding: var(--m-space-sm) var(--m-space-md);
    color: var(--m-text-2);
    font: inherit;
    text-align: left;
    background: transparent;
    border: 1px solid transparent;
    border-radius: var(--m-radius-md);
    cursor: pointer;
    transition: background-color 160ms ease-out, border-color 160ms ease-out, color 160ms ease-out;
  }

  .mango-system-settings__tab:hover {
    color: var(--m-text);
    background-color: var(--m-surface);
  }

  .mango-system-settings__tab:focus-visible {
    outline: 2px solid var(--m-primary);
    outline-offset: 2px;
  }

  .mango-system-settings__tab--active {
    color: var(--m-primary);
    background-color: var(--m-primary-soft);
    border-color: var(--m-primary-border);
  }

  .mango-system-settings__tab-icon {
    display: inline-flex;
    width: 24px;
    height: 24px;
    align-items: center;
    justify-content: center;
    font-size: 18px;
  }

  .mango-system-settings__tab-copy {
    min-width: 0;
  }

  .mango-system-settings__tab-copy strong,
  .mango-system-settings__tab-copy span {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-system-settings__tab-copy strong {
    color: inherit;
    font-size: 14px;
    font-weight: 600;
    line-height: 20px;
  }

  .mango-system-settings__tab-copy span {
    margin-top: 2px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .mango-system-settings__panel {
    container-type: inline-size;
    position: relative;
    min-width: 0;
    min-height: 0;
    overflow-y: auto;
    padding: 0 var(--m-card-small-body-padding-inline);
    background-color: var(--m-surface);
  }

  .mango-system-settings__large-section {
    padding: var(--m-space-md) 0;
    background-color: var(--m-surface);
  }

  .mango-system-settings__large-section:last-of-type {
    min-height: 100%;
  }

  .mango-system-settings__large-section + .mango-system-settings__large-section {
    margin-top: var(--m-page-gap);
  }

  .mango-system-settings__large-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: var(--m-space-sm);
    width: 100%;
    margin: 0 0 var(--m-space-md);
    padding: var(--m-space-md) var(--m-space-lg);
    background-color: var(--m-surface-soft);
    border-inline-start: 3px solid var(--m-primary);
  }

  .mango-system-settings__heading-copy {
    display: flex;
    align-items: baseline;
    flex-wrap: wrap;
    gap: var(--m-space-xs) var(--m-space-lg);
  }

  .mango-system-settings__large-title {
    margin: 0;
    color: var(--m-text);
    font-size: 18px;
    font-weight: 700;
    line-height: 24px;
  }

  .mango-system-settings__large-description {
    margin: 0;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .mango-system-settings__section-grid {
    display: flex;
    flex-direction: column;
    width: 100%;
    padding-inline-start: var(--m-space-lg);
    box-sizing: border-box;
  }

  .mango-system-settings__small-section {
    min-width: 0;
    padding: var(--m-space-sm) 0 var(--m-space-md);
  }

  .mango-system-settings__small-section + .mango-system-settings__small-section {
    border-top: 1px solid var(--m-border);
    padding-top: var(--m-space-lg);
  }

  .mango-system-settings__card-header {
    display: flex;
    justify-content: flex-start;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--m-section-gap);
    padding: 0 0 var(--m-space-md);
  }

  .mango-system-settings__card-title {
    margin: 0;
    font-size: 14px;
    font-weight: 600;
    color: var(--m-text-2);
  }

  .mango-system-settings__card-description {
    margin: 0;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .mango-system-settings__card-content {
    min-width: 0;
    padding: var(--m-space-xs) 0 var(--m-space-sm);
  }

  .mango-system-settings__card-content--compact {
    min-height: auto;
  }

  .mango-system-settings__switch-row {
    display: grid;
    grid-template-columns: 200px 90px minmax(240px, 420px) minmax(0, 1fr);
    justify-items: start;
    align-items: center;
    gap: var(--m-space-md);
    min-height: calc(var(--m-control-height-medium) + var(--m-space-md));
  }

  .mango-system-settings__cache-list {
    display: flex;
    flex-direction: column;
    gap: var(--m-space-sm);
    margin-top: var(--m-space-sm);
    padding-top: var(--m-space-sm);
    border-top: 1px solid var(--m-border);
  }

  .mango-system-settings__cache-item {
    display: grid;
    grid-template-columns: 200px 90px minmax(240px, 420px) minmax(0, 1fr);
    align-items: center;
    gap: var(--m-space-md);
    min-height: calc(var(--m-control-height-medium) + var(--m-space-xs));
  }

  .mango-system-settings__cache-meta {
    min-width: 0;
  }

  .mango-system-settings__cache-actions {
    grid-column: 3;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--m-space-sm);
    flex: 0 0 auto;
  }

  .mango-system-settings__cache-json {
    min-height: 100%;
    margin: 0;
    padding: var(--m-card-padding);
    overflow: auto;
    color: var(--m-text);
    font-size: 12px;
    line-height: 18px;
    background-color: var(--m-surface-soft);
    border: 1px solid var(--m-border);
    border-radius: 6px;
  }

  .mango-system-settings__item + .mango-system-settings__item,
  :deep(.mango-report-delivery .mango-system-settings__row + .mango-system-settings__row) {
    margin-top: var(--m-space-md);
  }

  .mango-system-settings__row,
  :deep(.mango-report-delivery .mango-system-settings__row) {
    display: grid;
    grid-template-columns: 200px 90px minmax(240px, 420px) minmax(0, 1fr);
    align-items: center;
    gap: var(--m-space-md);
  }

  .mango-system-settings__label,
  :deep(.mango-report-delivery .mango-system-settings__label) {
    min-width: 0;
    font-size: 14px;
    line-height: 20px;
    color: var(--m-text);
  }

  .mango-system-settings__label-wrap,
  :deep(.mango-report-delivery .mango-system-settings__label-wrap) {
    display: flex;
    min-width: 0;
    align-items: center;
    flex-wrap: wrap;
    gap: var(--m-space-xs);
  }

  .mango-system-settings__control,
  :deep(.mango-report-delivery .mango-system-settings__control) {
    grid-column: 3;
    min-width: 0;
  }

  .mango-system-settings__type,
  :deep(.mango-report-delivery .mango-system-settings__type) {
    min-width: 0;
    white-space: nowrap;
  }

  .mango-system-settings__switch-row > .arco-switch {
    grid-column: 3;
  }

  .mango-system-settings__aside {
    min-width: 0;
    max-width: 520px;
    overflow-wrap: anywhere;
  }

  .mango-system-settings__aside > .mango-system-settings__help {
    margin-top: 0;
  }

  @container (max-width: 1000px) {
    .mango-system-settings__row,
    :deep(.mango-report-delivery .mango-system-settings__row),
    .mango-system-settings__switch-row,
    .mango-system-settings__cache-item {
      grid-template-columns: 200px 90px minmax(0, 1fr);
    }

    .mango-system-settings__aside {
      grid-column: 3;
    }
  }

  @container (max-width: 540px) {
    .mango-system-settings__row,
    :deep(.mango-report-delivery .mango-system-settings__row),
    .mango-system-settings__cache-item {
      grid-template-columns: minmax(0, 1fr) auto;
    }

    .mango-system-settings__switch-row {
      grid-template-columns: minmax(0, 1fr) auto;
    }

    .mango-system-settings__aside {
      grid-column: 1 / -1;
    }

    .mango-system-settings__control,
    :deep(.mango-report-delivery .mango-system-settings__control),
    .mango-system-settings__cache-actions {
      grid-column: 1 / -1;
    }

    .mango-system-settings__switch-row > .arco-switch {
      grid-column: 2;
    }
  }

  .mango-system-settings__help {
    display: block;
    margin-top: 4px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .mango-system-settings__help--caution {
    color: var(--m-warning);
  }

  .mango-system-settings__input,
  :deep(.mango-report-delivery .mango-system-settings__input) {
    width: 100%;
  }

  .mango-system-settings__input--number,
  :deep(.mango-report-delivery .mango-system-settings__input--number) {
    max-width: 200px;
  }

  .mango-system-settings__level-filter {
    padding: var(--m-page-gap) 0;
    background: var(--m-surface);
  }

  .mango-system-settings__level-options {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--m-space-xs);
  }

  .mango-system-settings__level-label {
    color: var(--m-text-2);
    white-space: nowrap;
  }

  .mango-system-settings__level-option {
    padding: var(--m-space-xs) var(--m-space-sm);
    min-height: var(--m-control-height-medium);
    border: 0;
    background: transparent;
    color: var(--m-text-2);
    font: inherit;
    cursor: pointer;
  }

  .mango-system-settings__level-option:hover {
    background: var(--m-surface-soft);
  }

  .mango-system-settings__level-option[aria-pressed='true'] {
    color: var(--m-primary);
    background: var(--m-surface-soft);
    font-weight: 600;
  }

  .mango-system-settings__level-option:focus-visible {
    outline: 2px solid var(--m-primary);
    outline-offset: 2px;
  }

  .mango-system-settings__nav-caption,
  .mango-system-settings__save-hint {
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .mango-system-settings__nav-caption {
    margin: var(--m-space-xs) var(--m-space-md) var(--m-space-sm);
    font-weight: 600;
  }

  @media (prefers-reduced-motion: reduce) {
    .mango-system-settings__tab {
      transition: none;
    }
  }

  .mango-system-settings__empty {
    height: 88px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--m-muted);
  }

  .mango-system-settings__panel-empty {
    min-height: 100%;
    background-color: var(--m-bg);
  }

  :deep(.mango-table-body__content--flush) {
    padding-bottom: 0;
  }

  @media (max-width: 960px) {
    .mango-system-settings__layout {
      grid-template-columns: 1fr;
      grid-template-rows: auto minmax(0, 1fr);
    }

    .mango-system-settings__tabs {
      flex-direction: row;
      overflow-x: auto;
      overflow-y: hidden;
      border-right: 0;
      border-bottom: 1px solid var(--m-border);
    }

    .mango-system-settings__nav-caption {
      display: none;
    }

    .mango-system-settings__tab {
      flex: 0 0 220px;
    }
  }

  @media (max-width: 640px) {
    .mango-system-settings__tab {
      flex-basis: 190px;
    }
  }
</style>
