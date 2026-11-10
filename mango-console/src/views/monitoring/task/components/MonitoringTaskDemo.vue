<template>
  <BaseSidePanel
    v-model:visible="visible"
    title="监控脚本使用说明"
    width="50vw"
    :show-footer="false"
  >
    <template #header-actions>
      <a-button size="small" type="primary" :loading="copying" @click="copyMonitoringDemo">复制 Demo</a-button>
    </template>
    <div class="mango-monitoring-demo-panel">
      <a-tabs v-model:active-key="activeDemoType" class="mango-monitoring-demo-panel__tabs">
        <a-tab-pane key="basic" title="不带测试环境">
          <div class="mango-monitoring-demo-panel__tab-content">
            <a-alert type="info" :show-icon="true">
              适用于不依赖平台测试配置的 Python 监控任务，例如业务指标预警、独立接口巡检和 Mock
              服务。脚本自行管理所需配置，不会读取平台中的域名或数据库。
            </a-alert>

            <section class="mango-monitoring-demo-panel__section">
              <div class="mango-monitoring-demo-panel__title">使用条件</div>
              <div class="mango-monitoring-demo-panel__conditions">
                <span>监控执行服务必须在线，否则任务无法启动。</span>
                <span>任务无需选择测试环境，平台不会注入域名和数据库配置。</span>
                <span>任务启用通知并配置通知组后，self.send 才会真正发送消息。</span>
                <span>脚本只能使用平台后端环境中已安装的 Python 依赖。</span>
              </div>
            </section>

            <section class="mango-monitoring-demo-panel__section">
              <div class="mango-monitoring-demo-panel__title">编写要求</div>
              <div class="mango-monitoring-demo-panel__requirements">
                <span>继承 MonitorBase，并实现 run() 作为任务入口。</span>
                <span>保留 __main__ 入口，并调用 start_monitoring()。</span>
                <span>常驻循环必须设置 sleep 间隔，避免空循环占满 CPU。</span>
                <span>使用 self.log、self.log_warning、self.log_error 输出实时日志。</span>
                <span>检测到不满足监控条件的数据时调用 self.send，消息会发送给通知组人员。</span>
                <span>密码、Token 等敏感信息应从环境变量或平台配置读取，禁止硬编码。</span>
                <span>单次检查异常应自行捕获，避免常驻任务因一次失败直接退出。</span>
              </div>
            </section>

            <section
              class="mango-monitoring-demo-panel__section mango-monitoring-demo-panel__code-section"
            >
              <div class="mango-monitoring-demo-panel__title">完整 Demo</div>
              <div class="mango-monitoring-demo-panel__code">
                <CodeEditor
                  :model-value="basicMonitoringDemoCode"
                  language="python"
                  :codeStyle="{ height: '100%' }"
                  :dark="true"
                  readonly
                />
              </div>
            </section>
          </div>
        </a-tab-pane>

        <a-tab-pane key="environment" title="带测试环境">
          <div class="mango-monitoring-demo-panel__tab-content">
            <a-alert type="info" :show-icon="true">
              适用于需要复用平台测试配置的 Python 监控任务。选择测试环境后，可直接从 self
              获取当前项目/产品在该环境下的域名和逻辑数据库连接。
            </a-alert>

            <section class="mango-monitoring-demo-panel__section">
              <div class="mango-monitoring-demo-panel__title">使用条件</div>
              <div class="mango-monitoring-demo-panel__conditions">
                <span>监控执行服务必须在线，否则任务无法启动。</span>
                <span>任务必须选择测试环境，并归属到已配置测试对象的项目/产品。</span>
                <span>域名来自测试对象配置，数据库来自该产品与环境的逻辑数据库绑定。</span>
                <span>任务启用通知并配置通知组后，self.send 才会真正发送消息。</span>
                <span>脚本只能使用平台后端环境中已安装的 Python 依赖。</span>
              </div>
            </section>

            <section class="mango-monitoring-demo-panel__section">
              <div class="mango-monitoring-demo-panel__title">编写要求</div>
              <div class="mango-monitoring-demo-panel__requirements">
                <span>继承 MonitorBase，并实现 run() 作为任务入口。</span>
                <span>保留 __main__ 入口，并调用 start_monitoring()。</span>
                <span>常驻循环必须设置 sleep 间隔，避免空循环占满 CPU。</span>
                <span>使用 self.log、self.log_warning、self.log_error 输出实时日志。</span>
                <span>检测到不满足监控条件的数据时调用 self.send，消息会发送给通知组人员。</span>
                <span>密码、Token 等敏感信息应从环境变量或平台配置读取，禁止硬编码。</span>
                <span>单次检查异常应自行捕获，避免常驻任务因一次失败直接退出。</span>
              </div>
            </section>

            <section class="mango-monitoring-demo-panel__section">
              <div class="mango-monitoring-demo-panel__title">测试环境注入的 self 字段</div>
              <div class="mango-monitoring-demo-panel__injections">
                <div>
                  <code>self.test_config</code><span>当前环境、域名和数据库配置的汇总字典</span>
                </div>
                <div>
                  <code>self.test_env / self.test_env_name</code><span>环境值和中文名称</span>
                </div>
                <div>
                  <code>self.domain / self.domains</code><span>默认域名和不同自动化类型的域名</span>
                </div>
                <div>
                  <code>self.database_configs / self.databases</code
                  ><span>按逻辑数据库名称索引的配置</span>
                </div>
                <div>
                  <code>self.get_database_config(alias)</code
                  ><span>获取指定逻辑数据库；只有一个时可不传名称</span>
                </div>
                <div>
                  <code>self.get_database_connection(alias)</code
                  ><span>获取受平台查询和写入权限控制的数据库连接</span>
                </div>
              </div>
              <div class="mango-monitoring-demo-panel__security-tip">
                平台不会把数据库密码放入 test_config。请通过 get_database_connection()
                建立连接，并在使用后关闭。
              </div>
            </section>

            <section
              class="mango-monitoring-demo-panel__section mango-monitoring-demo-panel__code-section"
            >
              <div class="mango-monitoring-demo-panel__title">完整 Demo</div>
              <div class="mango-monitoring-demo-panel__code">
                <CodeEditor
                  :model-value="environmentMonitoringDemoCode"
                  language="python"
                  :codeStyle="{ height: '100%' }"
                  :dark="true"
                  readonly
                />
              </div>
            </section>
          </div>
        </a-tab-pane>
      </a-tabs>
    </div>
  </BaseSidePanel>
</template>

<script setup lang="ts">
  import { computed, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import CodeEditor from '@/components/editors/CodeEditor.vue'
  import { basicMonitoringDemoCode, environmentMonitoringDemoCode } from '../config'
  import { useMonitoringTaskScope } from '../composables/useMonitoringTaskScope'
  import type { TaskDemoHandle } from '../types'
  const visible = ref(false), copying = ref(false)
  const activeDemoType = ref<'basic' | 'environment'>('basic')
  const activeMonitoringDemoCode = computed(() => activeDemoType.value === 'environment' ? environmentMonitoringDemoCode : basicMonitoringDemoCode)
  let windowVersion = 0
  const scope = useMonitoringTaskScope(close)
  watch(() => [visible.value, activeDemoType.value], () => { ++windowVersion }, { flush: 'sync' })
  function open() { if (scope.available()) visible.value = true }
  function close() { visible.value = false; ++windowVersion }
  async function copyMonitoringDemo() {
    if (!scope.available() || !visible.value || copying.value) return
    const version = scope.snapshot(), window = windowVersion, code = activeMonitoringDemoCode.value
    const current = () => scope.current(version) && visible.value && window === windowVersion
    copying.value = true
    try {
      await navigator.clipboard.writeText(code)
      if (current()) Message.success('Demo 代码已复制')
    } catch { if (current()) Message.error('复制失败，请在代码区域中手动选择复制') }
    finally { copying.value = false }
  }
  defineExpose<TaskDemoHandle>({ open, close })
</script>

<style scoped lang="less">
  .mango-monitoring-demo-panel {
    box-sizing: border-box;
    min-height: 100%;
    padding: 0;
    background: var(--m-bg);
  }

  .mango-monitoring-demo-panel__tabs {
    width: 100%;
  }

  .mango-monitoring-demo-panel__tab-content {
    display: flex;
    padding-top: var(--m-page-gap);
    flex-direction: column;
    gap: var(--m-page-gap);
  }

  .mango-monitoring-demo-panel__section {
    padding: 12px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius);
    background: var(--m-surface);
  }

  .mango-monitoring-demo-panel__title {
    margin-bottom: 8px;
    color: var(--m-text);
    font-size: 14px;
    font-weight: 600;
    line-height: 22px;
  }

  .mango-monitoring-demo-panel__conditions,
  .mango-monitoring-demo-panel__requirements {
    display: grid;
    gap: 6px 18px;
    color: var(--m-text-2);
    font-size: 12px;
    line-height: 20px;
  }

  .mango-monitoring-demo-panel__injections {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px 18px;

    div {
      display: flex;
      min-width: 0;
      flex-direction: column;
      gap: 2px;
    }

    code {
      color: var(--m-primary);
      font-size: 12px;
    }

    span {
      color: var(--m-muted);
      font-size: 12px;
      line-height: 18px;
    }
  }

  .mango-monitoring-demo-panel__security-tip {
    margin-top: 10px;
    color: var(--m-warning);
    font-size: 12px;
    line-height: 18px;
  }

  .mango-monitoring-demo-panel__requirements {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .mango-monitoring-demo-panel__conditions span::before,
  .mango-monitoring-demo-panel__requirements span::before {
    margin-right: 6px;
    color: var(--m-primary);
    content: '•';
  }

  .mango-monitoring-demo-panel__code-section {
    display: flex;
    min-height: 520px;
    flex-direction: column;
  }

  .mango-monitoring-demo-panel__code {
    min-height: 0;
    flex: 1;
    overflow: hidden;
    border: 1px solid var(--m-code-border);
    border-radius: var(--m-radius);

    :deep(.code-editor),
    :deep(.cm-editor) {
      height: 100%;
      min-height: 0;
    }

    :deep(.cm-scroller) {
      overflow: auto;
    }
  }

  @media (max-width: 1100px) {
    .mango-monitoring-demo-panel__requirements, .mango-monitoring-demo-panel__injections { grid-template-columns: minmax(0, 1fr); }
  }
</style>
