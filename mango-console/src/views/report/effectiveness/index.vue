<template>
  <TableBody
    id="mango-effectiveness-report"
    plain
    :sticky-horizontal-scroll="false"
    :class="[
      'mango-effectiveness-page',
      'mango-detail-workbench-page',
      { 'is-report-mode': reportMode, 'is-printing': printing },
    ]"
  >
    <template #header>
      <TableHeader title="质量效能">
        <template #header-extra>
          <a-tag v-if="reportMode" size="small" color="arcoblue">A4 横向 · 连续排版</a-tag>
          <a-popover
            :popup-visible="filterVisible && !reportMode && !printing"
            trigger="click"
            position="br"
            @popup-visible-change="onFilterPopoverVisibleChange"
          >
            <a-button
              size="small"
              :type="filterVisible && !reportMode ? 'primary' : 'secondary'"
              :disabled="reportMode || printing"
            >
              <template #icon><icon-filter /></template>
              {{ filterButtonText }}
            </a-button>
            <template #content>
              <section class="mango-effectiveness-filter-popover">
                <div class="mango-effectiveness-filter__heading">
                  <div><icon-filter /><strong>筛选范围</strong></div>
                  <span>调整条件后点击查询，下方指标使用同一统计口径</span>
                </div>
                <div class="mango-effectiveness-filter__fields">
                  <div class="mango-effectiveness-filter__field">
                    <span>项目 / 产品</span>
                    <ProjectProductSelect
                      v-model="draftFilters.project_product"
                      placeholder="全部项目/产品"
                      allow-clear
                    />
                  </div>
                  <div class="mango-effectiveness-filter__field">
                    <span>统计周期</span>
                    <a-select
                      v-model="draftFilters.periodPreset"
                      :options="periodPresetOptions"
                      :allow-clear="false"
                      @change="onPeriodPresetChange"
                    />
                  </div>
                  <div class="mango-effectiveness-filter__field">
                    <span>测试环境</span>
                    <a-select
                      v-model="draftFilters.test_env"
                      :field-names="fieldNames"
                      :options="enumStore.environment_type || []"
                      placeholder="全部测试环境"
                      multiple
                      :max-tag-count="1"
                      allow-clear
                    />
                  </div>
                  <div class="mango-effectiveness-filter__field">
                    <span>执行场景</span>
                    <a-select
                      v-model="draftFilters.execution_scene"
                      :field-names="fieldNames"
                      :options="sceneOptions"
                      placeholder="全部执行场景"
                      multiple
                      :max-tag-count="1"
                      allow-clear
                    />
                  </div>
                  <div class="mango-effectiveness-filter__field">
                    <span>执行范围</span>
                    <a-select
                      v-model="draftFilters.execution_scope"
                      :field-names="fieldNames"
                      :options="scopeOptions"
                      placeholder="全部执行范围"
                      multiple
                      :max-tag-count="1"
                      allow-clear
                    />
                  </div>
                </div>
                <div class="mango-effectiveness-filter__actions">
                  <a-button type="primary" size="small" :loading="loading" @click="applyFilters"
                    >查询</a-button
                  >
                  <a-button size="small" :disabled="loading" @click="resetFilters">重置</a-button>
                </div>
              </section>
            </template>
          </a-popover>
          <a-tooltip
            content="仅清除当前页面统计数据缓存，不会清除 AI 总结缓存"
            position="bottom"
            mini
          >
            <a-button
              size="small"
              :loading="cacheClearing"
              :disabled="reportMode || printing"
              @click="clearEffectivenessCache"
            >
              <template #icon><icon-refresh /></template>
              清除缓存
            </a-button>
          </a-tooltip>
          <a-button size="small" :disabled="printing || imageExporting" @click="toggleReportMode">
            {{ reportMode ? '退出汇报模式' : '汇报模式' }}
          </a-button>
          <a-tooltip v-if="reportMode" :content="imageExportTooltip" position="bottom" mini>
            <span class="mango-effectiveness-export-button-wrap">
              <a-button
                size="small"
                type="primary"
                :loading="imageExporting"
                :disabled="imageExportDisabled"
                @click="downloadReportImage"
              >
                <template #icon><icon-image /></template>
                下载高清图片
              </a-button>
            </span>
          </a-tooltip>
        </template>
      </TableHeader>
    </template>
    <template #default>
      
      <div id="mango-effectiveness-report-image" class="mango-effectiveness-report-document">
        <div class="mango-effectiveness-paper-page mango-effectiveness-paper-page--summary">
          <span class="mango-effectiveness-paper-page__number">01 / 07 · 质量摘要</span>
          <section class="mango-effectiveness-report-header">
            <div class="mango-effectiveness-report-header__main">
              <div class="mango-effectiveness-eyebrow">
                <icon-dashboard />
                <span>自动化质量效能报告 · QUALITY EFFECTIVENESS</span>
              </div>
              <h1>{{ reportDocumentTitle }}</h1>
              <p>聚合正式定时任务的质量、稳定性与结果反馈时效，帮助团队快速定位风险。</p>
              <div class="mango-effectiveness-scope" aria-label="当前统计范围">
                <span v-for="scope in reportScopeItems" :key="scope">{{ scope }}</span>
              </div>
            </div>
            <div :class="['mango-effectiveness-verdict', `is-${verdictColor}`]" aria-live="polite">
              <span>综合质量结论</span>
              <strong>{{ verdictText }}</strong>
              <p :class="`is-${verdictReasonTone}`">{{ verdictReasonText }}</p>
              <div>
                <span>{{ overview.cards.suite_count || 0 }} 份报告</span>
                <span>失败 {{ overview.cards.failed_count || 0 }}</span>
                <span>警告 {{ overview.cards.warning_count || 0 }}</span>
                <span v-if="overview.cards.flaky_count"
                  >重试恢复 {{ overview.cards.flaky_count }}</span
                >
              </div>
            </div>
            <div class="mango-effectiveness-report-header__meta">
              <span><icon-calendar />统计周期：{{ reportPeriodText }}</span>
              <span>环比周期：{{ comparisonPeriodText }}</span>
              <span>生成时间：{{ generatedAt }}</span>
              <span>统计口径：仅正式定时任务</span>
              <a-tooltip :content="dataConfidence.description" position="bottom">
                <a-tag size="small" :color="dataConfidence.color"
                  >数据可信度：{{ dataConfidence.label }}</a-tag
                >
              </a-tooltip>
            </div>
          </section>
          <div class="mango-effectiveness-chapter-heading">
            <span>01</span>
            <div>
              <strong>质量总览</strong>
              <small>集中呈现当前质量结论、关键风险信号与核心执行指标</small>
            </div>
            <em>EXECUTIVE OVERVIEW</em>
          </div>
          <section
            v-if="overview.insights.length"
            class="mango-section-card mango-effectiveness-insight-panel"
          >
            <div class="mango-effectiveness-insight-summary">
              <div class="mango-effectiveness-insight-summary__content">
                <span class="mango-effectiveness-insight-summary__eyebrow"
                  ><icon-bulb />质量信号</span
                >
                <strong>关键洞察</strong>
                <small>基于当前统计范围，优先呈现值得关注的变化与风险</small>
              </div>
              <span class="mango-effectiveness-insight-summary__count"
                >{{ overview.insights.length }} 条</span
              >
            </div>
            <div class="mango-effectiveness-insights">
              <article
                v-for="insight in overview.insights"
                :key="`${insight.level}-${insight.title}`"
                :class="[
                  'mango-section-card',
                  'mango-effectiveness-overview-card',
                  'mango-effectiveness-insight',
                  `is-${insight.level}`,
                ]"
              >
                <span class="mango-effectiveness-insight__marker"></span>
                <div
                  ><strong>{{ insight.title }}</strong
                  ><p>{{ insight.description }}</p></div
                >
              </article>
            </div>
          </section>

          <section
            class="mango-section-card mango-effectiveness-insight-panel mango-effectiveness-conclusion-panel"
          >
            <div class="mango-effectiveness-insight-summary">
              <div class="mango-effectiveness-insight-summary__content">
                <span class="mango-effectiveness-insight-summary__eyebrow"
                  ><icon-dashboard />质量摘要</span
                >
                <strong>汇报结论</strong>
                <small>直接回答质量、收敛、执行规模与问题发现</small>
              </div>
              <span class="mango-effectiveness-insight-summary__count"
                >{{ executiveCards.length }} 项</span
              >
            </div>
            <section class="mango-effectiveness-cards" :class="{ 'is-loading': loading }">
              <article
                v-for="card in executiveCards"
                :key="card.key"
                :class="[
                  'mango-section-card',
                  'mango-effectiveness-overview-card',
                  'mango-effectiveness-card',
                  `is-${card.tone}`,
                ]"
              >
                <div class="mango-effectiveness-card__title"
                  ><span>{{ card.title }}</span
                  ><small>{{ card.badge }}</small></div
                >
                <strong :class="card.valueClass">{{ card.value }}</strong>
                <div
                  :class="['mango-effectiveness-card__comparison', card.comparisonClass]"
                  :title="card.comparisonTitle || card.comparison"
                  >{{ card.comparison }}</div
                >
                <div class="mango-effectiveness-card__footer"
                  ><span></span><small :title="card.description">{{ card.description }}</small></div
                >
                <a-popover
                  v-if="card.key === 'source' && !reportMode && !printing"
                  trigger="click"
                  position="bottom"
                  :content-style="{ padding: '0' }"
                >
                  <button
                    type="button"
                    class="mango-effectiveness-source-card__trigger"
                    aria-label="查看数据来源任务明细"
                    title="点击查看数据来源任务明细"
                  ></button>
                  <template #content>
                    <section class="mango-effectiveness-source-popover">
                      <header>
                        <div>
                          <strong>数据来源任务明细</strong>
                          <small
                            >{{ sourceTaskRows.length }} 个定时任务 ·
                            {{ formatCount(overview.task_source_summary.report_count) }}
                            份报告</small
                          >
                        </div>
                        <span>报告成功率由低到高</span>
                      </header>
                      <div
                        class="mango-effectiveness-source-popover__table-wrap mango-native-scrollbar"
                      >
                        <table>
                          <thead>
                            <tr>
                              <th>定时任务</th>
                              <th>报告数</th>
                              <th>报告成功率</th>
                              <th>用例通过率</th>
                            </tr>
                          </thead>
                          <tbody>
                            <tr v-for="item in sourceTaskRows" :key="item.task_id">
                              <td>
                                <strong :title="item.task_name">{{ item.task_name }}</strong>
                                <small :title="`${item.project_product_name} · ${item.module_name}`"
                                  >{{ item.project_product_name }} · {{ item.module_name }}</small
                                >
                              </td>
                              <td>{{ item.suite_count || 0 }}</td>
                              <td :class="rateClass(item.report_success_rate)">{{
                                formatRate(item.report_success_rate)
                              }}</td>
                              <td :class="rateClass(item.final_pass_rate)">{{
                                formatRate(item.final_pass_rate)
                              }}</td>
                            </tr>
                          </tbody>
                        </table>
                      </div>
                    </section>
                  </template>
                </a-popover>
              </article>
              <EffectivenessAiNote
                class="mango-effectiveness-cards__ai"
                :text="componentInsight('overview')"
              />
            </section>
          </section>
        </div>

        <div class="mango-effectiveness-paper-page mango-effectiveness-paper-page--ai">
          <span class="mango-effectiveness-paper-page__number">07 / 07 · 汇报总结</span>
          <div class="mango-effectiveness-chapter-heading">
            <span>07</span>
            <div>
              <strong>汇报总结与行动建议</strong>
              <small>综合前述质量证据，归纳收益、风险、趋势与后续优先行动</small>
            </div>
            <em>EXECUTIVE CONCLUSION</em>
          </div>
          <section class="mango-section-card mango-effectiveness-ai-card" aria-live="polite">
            <header
              v-if="aiState.available || (!reportMode && !printing)"
              class="mango-effectiveness-ai-card__header"
            >
              <div class="mango-effectiveness-ai-card__identity">
                <span class="mango-effectiveness-ai-card__icon"><icon-robot /></span>
                <div>
                  <strong>Mango AI 质量总结</strong>
                  <span>基于当前筛选范围的完整效能数据生成</span>
                </div>
              </div>
              <div v-if="aiState.available" class="mango-effectiveness-ai-card__meta">
                <span>{{ aiState.model || 'AI 模型' }}</span>
                <small>{{ aiState.generated_at || '-' }}</small>
              </div>
              <a-tooltip
                v-if="!reportMode && !printing"
                content="重新生成全局汇报总结及所有图表、卡片解读；生成结果分别缓存 1 小时"
                position="bottom"
              >
                <a-button
                  class="mango-effectiveness-ai-card__action"
                  size="small"
                  :loading="aiLoading"
                  :disabled="loading || !overviewReady"
                  @click="loadAiSummary(true)"
                >
                  <template #icon><icon-refresh /></template>
                  重新总结
                </a-button>
              </a-tooltip>
            </header>

            <div v-if="aiInsightError && !loading && !aiLoading" class="mango-soft-panel" role="alert">{{ aiInsightError }}</div>
            <div v-if="loading || aiLoading" class="mango-effectiveness-ai-loading">
              <div class="mango-effectiveness-ai-loading__intro">
                <a-skeleton :animation="true">
                  <a-skeleton-line :rows="3" :widths="['42%', '100%', '82%']" />
                </a-skeleton>
              </div>
              <div class="mango-effectiveness-ai-loading__columns">
                <a-skeleton v-for="item in 3" :key="item" :animation="true">
                  <a-skeleton-line :rows="5" />
                </a-skeleton>
              </div>
              <span>AI 正在分析质量趋势、自动化收益与风险优先级…</span>
            </div>

            <div
              v-else-if="aiState.available && aiState.summary"
              class="mango-effectiveness-ai-result"
            >
              <div class="mango-effectiveness-ai-result__hero">
                <div>
                  <span>AI 核心判断</span>
                  <h2>{{ aiState.summary.headline }}</h2>
                  <p>{{ aiState.summary.executive_summary }}</p>
                </div>
                <div
                  :class="[
                    'mango-effectiveness-ai-trend',
                    `is-${aiState.summary.quality_trend?.status || 'unknown'}`,
                  ]"
                >
                  <span>质量趋势</span>
                  <strong>{{ aiState.summary.quality_trend?.label || '暂无明确趋势' }}</strong>
                  <p>{{
                    aiState.summary.quality_trend?.analysis || '当前数据不足以形成趋势判断。'
                  }}</p>
                </div>
              </div>

              <div class="mango-effectiveness-ai-result__columns">
                <section class="is-benefit">
                  <div
                    ><strong>可验证收益</strong
                    ><span>{{ aiState.summary.benefits?.length || 0 }} 项</span></div
                  >
                  <ul v-if="aiState.summary.benefits?.length">
                    <li v-for="item in aiState.summary.benefits" :key="item.title">
                      <strong>{{ item.title }}</strong>
                      <p>{{ item.detail }}</p>
                      <small>{{ item.evidence }}</small>
                    </li>
                  </ul>
                  <div v-else class="mango-effectiveness-ai-result__empty">暂未识别到明确收益</div>
                </section>
                <section class="is-risk">
                  <div
                    ><strong>重点问题</strong
                    ><span>{{ aiState.summary.risks?.length || 0 }} 项</span></div
                  >
                  <ul v-if="aiState.summary.risks?.length">
                    <li v-for="item in aiState.summary.risks" :key="item.title">
                      <strong>{{ item.title }}</strong>
                      <p>{{ item.detail }}</p>
                      <small>{{ priorityLabel(item.severity) }}</small>
                    </li>
                  </ul>
                  <div v-else class="mango-effectiveness-ai-result__empty">暂未识别到突出风险</div>
                </section>
                <section class="is-action">
                  <div
                    ><strong>建议动作</strong
                    ><span>{{ aiState.summary.recommendations?.length || 0 }} 项</span></div
                  >
                  <ul v-if="aiState.summary.recommendations?.length">
                    <li v-for="item in aiState.summary.recommendations" :key="item.title">
                      <strong>{{ item.title }}</strong>
                      <p>{{ item.detail }}</p>
                      <small>{{ priorityLabel(item.priority) }}</small>
                    </li>
                  </ul>
                  <div v-else class="mango-effectiveness-ai-result__empty">暂无额外建议动作</div>
                </section>
              </div>
            </div>

            <div v-else-if="aiError" class="mango-empty-state" role="alert">
              <strong>{{ aiError }}</strong>
              <a-button size="small" :loading="aiLoading" :disabled="!overviewReady" @click="loadAiSummary(true)">重试</a-button>
            </div>
            <div v-else-if="aiState.available === false" class="mango-effectiveness-ai-unavailable" role="alert">
              <div class="mango-effectiveness-ai-unavailable__visual">
                <span><icon-robot /></span>
              </div>
              <div class="mango-effectiveness-ai-unavailable__content">
                <span>AI 能力尚未接入</span>
                <h2>完成 AI 配置后，可自动生成质量汇报结论</h2>
                <p
                  >配置 AI 接口地址、API Key 和模型后，本页将自动总结收益、问题、趋势与建议动作。</p
                >
                <small v-if="aiState.reason">当前状态：{{ aiState.reason }}</small>
                <div>
                  <a-button type="primary" size="small" @click="openAiSettings">
                    <template #icon><icon-settings /></template>
                    前往接入 AI
                  </a-button>
                  <span>如果没有配置权限，请联系系统管理员。</span>
                </div>
              </div>
            </div>
          </section>

          <footer class="mango-effectiveness-report-footer">
            <strong>数据说明</strong>
            <dl>
              <div>
                <dt>数据来源</dt>
                <dd>平台正式定时任务生成的测试报告、用例最终结果及执行重试记录。</dd>
              </div>
              <div>
                <dt>统计范围</dt>
                <dd
                  >仅统计当前账号有权查看且符合日期、项目产品、模块、测试环境、执行场景和执行范围筛选的数据；环比采用紧邻且等长的上一周期。</dd
                >
              </div>
              <div>
                <dt>排除范围</dt>
                <dd
                  >不包含手动批量执行、单 Case
                  调试、未绑定定时任务的报告，以及筛选范围外或无权访问的数据。</dd
                >
              </div>
              <div>
                <dt>更新规则</dt>
                <dd
                  >页面统计默认缓存 10 分钟，AI 总结单独缓存 1
                  小时；清除缓存只刷新页面统计数据，不会清除 AI 总结。</dd
                >
              </div>
            </dl>
          </footer>
        </div>

        <div class="mango-effectiveness-paper-page mango-effectiveness-paper-page--period">
          <span class="mango-effectiveness-paper-page__number">02 / 07 · 周期趋势</span>
          <div class="mango-effectiveness-chapter-heading">
            <span>02</span>
            <div>
              <strong>周期质量趋势</strong>
              <small>按当前筛选时长，对比本周期及前三个等长周期的质量变化</small>
            </div>
            <em>PERIOD QUALITY TREND</em>
          </div>
          <section class="mango-effectiveness-period-workbench">
            <PeriodQualityTrend
              :items="overview.period_quality"
              :loading="loading"
              :insight="componentInsight('status')"
              :report-mode="reportMode"
              @period-click="onPeriodQualityClick"
            />
          </section>
        </div>

        <div class="mango-effectiveness-paper-page mango-effectiveness-paper-page--convergence">
          <span class="mango-effectiveness-paper-page__number">04 / 07 · 收敛与收益</span>
          <div class="mango-effectiveness-chapter-heading">
            <span>04</span>
            <div>
              <strong>{{ reportMode ? '问题收敛与自动化执行产出' : '问题收敛与自动化收益' }}</strong>
              <small>对比问题变化与真实执行产出，判断质量改善与自动化执行效果</small>
            </div>
            <em>CONVERGENCE & VALUE</em>
          </div>
          <section class="mango-effectiveness-grid mango-effectiveness-grid--convergence">
            <mango-panel-spin v-if="reportMode" :loading="loading" class="mango-effectiveness-output-loading">
              <div v-if="hasEffectivenessData" class="mango-effectiveness-output-metrics">
                <article v-for="item in reportOutputItems" :key="item.label">
                  <span>{{ item.label }}</span>
                  <strong>{{ item.value }}</strong>
                  <small>{{ item.description }}</small>
                </article>
              </div>
              <EffectivenessEmptyState v-else-if="!loading" title="暂无自动化执行产出" />
            </mango-panel-spin>
            <article class="mango-section-card mango-effectiveness-panel">
              <div class="mango-effectiveness-panel-title">
                <div><strong>问题收敛趋势</strong><span>失败、警告与最终通过率的变化</span></div>
                <small :class="comparisonClass(overview.convergence.issue_rate_delta, false)">{{
                  convergenceLabel
                }}</small>
              </div>
              <EffectivenessChart
                :option="trendOption"
                :loading="loading"
                :empty="!hasTrendData"
                empty-text="当前项目暂无问题趋势"
                empty-description="当前统计周期内没有正式定时任务执行结果，暂时无法分析问题收敛变化"
                :insight="chartInsight('trend')"
                height="330px"
                @chart-click="onTrendChartClick"
              />
            </article>
            <article
              class="mango-section-card mango-effectiveness-panel mango-effectiveness-benefit"
            >
              <div class="mango-effectiveness-panel-title">
                <div
                  ><strong>{{ reportMode ? '任务执行构成' : '自动化收益' }}</strong
                  ><span>{{ reportMode ? '按任务类型展示执行轮次与校验次数' : '呈现替代人工回归、持续巡检、覆盖规模与结果反馈时效' }}</span></div
                >
                <small>{{
                  hasEffectivenessData
                    ? `持续运行 ${overview.benefits.active_day_count || 0} 天`
                    : '暂无正式执行'
                }}</small>
              </div>
              <template v-if="hasEffectivenessData">
                <div v-if="!reportMode" class="mango-effectiveness-benefit__lead">
                  <article
                    v-for="item in primaryBenefitItems"
                    :key="item.key"
                    :class="`is-${item.key}`"
                  >
                    <div
                      ><span>{{ item.label }}</span
                      ><small>{{ item.badge }}</small></div
                    >
                    <strong>{{ item.value }}</strong>
                    <p>{{ item.description }}</p>
                    <small>{{ item.meaning }}</small>
                  </article>
                </div>
                <div v-if="!reportMode" class="mango-effectiveness-benefit__grid">
                  <div v-for="item in benefitItems" :key="item.label">
                    <span>{{ item.label }}</span
                    ><strong>{{ item.value }}</strong
                    ><small>{{ item.description }}</small>
                  </div>
                </div>
                <table v-if="reportMode && benefitSceneItems.length" class="mango-effectiveness-output-table">
                  <thead><tr><th scope="col">任务类型</th><th scope="col">执行轮次</th><th scope="col">校验次数</th></tr></thead>
                  <tbody><tr v-for="item in benefitSceneItems" :key="item.scene">
                    <td>{{ item.name }}</td><td>{{ formatCount(item.suite_count) }}</td><td>{{ formatCount(item.execution_count) }}</td>
                  </tr></tbody>
                </table>
                <div v-else-if="benefitSceneItems.length" class="mango-effectiveness-benefit__types">
                  <strong>任务价值构成</strong>
                  <span v-for="item in benefitSceneItems" :key="item.scene"
                    >{{ item.name }} {{ item.suite_count }} 轮 ·
                    {{ item.execution_count }} 次校验</span
                  >
                </div>
                <div
                  v-if="overview.benefits.automation_types?.length"
                  class="mango-effectiveness-benefit__types is-automation"
                >
                  <strong>自动化类型覆盖</strong>
                  <span v-for="item in overview.benefits.automation_types" :key="item.type"
                    >{{ item.name }} {{ item.count }} 次校验</span
                  >
                </div>
                <EffectivenessAiNote :text="componentInsight('benefits')" />
              </template>
              <EffectivenessEmptyState
                v-else-if="!loading"
                class="mango-effectiveness-benefit__empty"
                title="当前项目暂无自动化收益数据"
                description="当前统计周期内没有正式定时任务执行报告，暂时无法计算回归替代、覆盖规模和结果反馈时效"
              />
            </article>
          </section>
        </div>

        <div class="mango-effectiveness-paper-page mango-effectiveness-paper-page--modules">
          <span class="mango-effectiveness-paper-page__number">03 / 07 · 模块质量</span>
          <div class="mango-effectiveness-chapter-heading">
            <span>03</span>
            <div>
              <strong>模块质量分析</strong>
              <small>下钻业务模块，识别稳定区域、质量短板与问题集中点</small>
            </div>
            <em>MODULE QUALITY</em>
          </div>
          <section class="mango-effectiveness-module-workbench">
            <section class="mango-effectiveness-grid mango-effectiveness-grid--module-analysis">
              <article class="mango-section-card mango-effectiveness-panel">
                <div class="mango-effectiveness-panel-title">
                  <div
                    ><strong>模块风险四象限</strong
                    ><span>按执行规模、最终通过率和问题数量识别高优先级模块</span></div
                  >
                  <small>{{ moduleRiskSummary }}</small>
                </div>
                <EffectivenessChart
                  :option="moduleRiskOption"
                  :loading="loading"
                  :empty="!moduleRiskData.length"
                  empty-text="当前范围暂无模块风险数据"
                  empty-description="尚无足够的模块执行结果用于计算风险分布"
                  :insight="chartInsight('module_risk')"
                  height="270px"
                  @chart-click="onModuleRiskClick"
                />
              </article>
              <article class="mango-section-card mango-effectiveness-panel">
                <div class="mango-effectiveness-panel-title">
                  <div
                    ><strong>问题贡献排行</strong
                    ><span>按模块汇总失败与警告，定位问题最集中的业务区域</span></div
                  >
                  <small>{{ issueParetoSummary }}</small>
                </div>
                <EffectivenessChart
                  :option="issueParetoOption"
                  :loading="loading"
                  :empty="!issueParetoData.length"
                  empty-text="本周期未发现失败或警告"
                  empty-description="当前模块没有问题结果，整体执行表现稳定"
                  :empty-positive="true"
                  :insight="chartInsight('issue_pareto')"
                  height="270px"
                  @chart-click="onIssueParetoClick"
                />
              </article>
              <article class="mango-section-card mango-effectiveness-panel">
                <div class="mango-effectiveness-panel-title">
                  <div
                    ><strong>模块环比升降榜</strong><span>同时关注改善模块与质量下降模块</span></div
                  >
                  <small>{{ moduleChangeSummary }}</small>
                </div>
                <EffectivenessChart
                  :option="moduleChangeOption"
                  :loading="loading"
                  :empty="!moduleChangeData.length"
                  empty-text="暂无模块环比数据"
                  empty-description="需要当前周期与上一等长周期均存在模块执行数据"
                  :insight="chartInsight('module_change')"
                  height="270px"
                  @chart-click="onModuleChangeClick"
                />
              </article>
            </section>
            <section
              class="mango-section-card mango-effectiveness-panel mango-effectiveness-module-quality"
            >
              <div class="mango-effectiveness-panel-title">
                <div
                  ><strong>模块质量分层</strong
                  ><span>风险优先展示，支持按质量等级筛选模块</span></div
                >
                <div class="mango-effectiveness-module-quality__summary">
                  <a-tag size="small" color="green">稳定 {{ moduleQualitySummary.success }}</a-tag>
                  <a-tag size="small" color="orange">关注 {{ moduleQualitySummary.warning }}</a-tag>
                  <a-tag size="small" color="red">高风险 {{ moduleQualitySummary.danger }}</a-tag>
                </div>
              </div>
              <div v-if="!reportMode" class="mango-effectiveness-module-quality__toolbar">
                <a-tabs
                  v-model:active-key="moduleQualityFilter"
                  class="mango-effectiveness-module-quality__tabs"
                  size="small"
                  hide-content
                >
                  <a-tab-pane key="attention" :title="`需关注 ${moduleQualityAttentionCount}`" />
                  <a-tab-pane key="all" :title="`全部 ${moduleQualitySummary.total}`" />
                  <a-tab-pane key="danger" :title="`高风险 ${moduleQualitySummary.danger}`" />
                  <a-tab-pane key="warning" :title="`关注 ${moduleQualitySummary.warning}`" />
                  <a-tab-pane key="success" :title="`稳定 ${moduleQualitySummary.success}`" />
                </a-tabs>
              </div>
              <mango-panel-spin :loading="loading" class="mango-effectiveness-module-quality__loading">
                <div
                  v-if="moduleQualityData.length"
                  class="mango-effectiveness-module-quality__list"
                >
                  <div class="mango-effectiveness-module-row mango-effectiveness-module-row--head">
                    <span>模块 / 项目产品</span>
                    <span>质量等级</span>
                    <span>最终通过率</span>
                    <span>执行次数</span>
                    <span>问题结果</span>
                    <span>较上周期</span>
                  </div>
                  <article
                    v-for="(record, index) in moduleQualityData"
                    :key="record.module_key"
                    :class="['mango-effectiveness-module-row', `is-${record.quality_level}`]"
                  >
                    <div class="mango-effectiveness-module-row__identity">
                      <span class="mango-effectiveness-module-row__rank">{{
                        String(index + 1).padStart(2, '0')
                      }}</span>
                      <div class="mango-effectiveness-module-row__main">
                        <strong :title="record.module_path">{{ record.module_path }}</strong>
                        <small>{{ record.project_name }} / {{ record.project_product_name }}</small>
                      </div>
                    </div>
                    <a-tag
                      size="small"
                      :color="record.quality_level === 'danger' ? 'red' : record.quality_level === 'warning' ? 'orange' : record.quality_level === 'success' ? 'green' : 'gray'"
                    >{{ record.quality_label }}</a-tag>
                    <div class="mango-effectiveness-module-row__rate">
                      <strong :class="rateClass(record.final_pass_rate)">{{
                        formatRate(record.final_pass_rate)
                      }}</strong>
                      <a-progress
                        :percent="Number(record.final_pass_rate || 0) / 100"
                        :show-text="false"
                        size="small"
                      />
                    </div>
                    <strong class="mango-effectiveness-module-row__count">{{
                      formatCount(record.detail_count)
                    }}</strong>
                    <div class="mango-effectiveness-module-row__issues">
                      <span :class="{ 'is-danger': Number(record.failed_count || 0) > 0 }"
                        >{{ record.failed_count || 0 }} 失败</span
                      >
                      <span :class="{ 'is-warning': Number(record.warning_count || 0) > 0 }"
                        >{{ record.warning_count || 0 }} 警告</span
                      >
                    </div>
                    <strong
                      class="mango-effectiveness-module-row__comparison"
                      :class="deltaClass(record.pass_rate_delta)"
                      >{{ comparisonText(record.pass_rate_delta, '个百分点', true) }}</strong
                    >
                  </article>
                </div>
                <EffectivenessEmptyState
                  v-else-if="!loading"
                  :title="moduleQualityEmptyTitle"
                  :description="moduleQualityEmptyDescription"
                />
              </mango-panel-spin>
              <EffectivenessAiNote :text="componentInsight('modules')" />
            </section>
          </section>
        </div>

        <div class="mango-effectiveness-paper-page mango-effectiveness-paper-page--operations">
          <span class="mango-effectiveness-paper-page__number">06 / 07 · 执行治理</span>
          <div class="mango-effectiveness-chapter-heading">
            <span>06</span>
            <div>
              <strong>执行治理与交叉分析</strong>
              <small>结合环境任务交叉表现、自动化类型与任务健康度，识别执行治理重点</small>
            </div>
            <em>EXECUTION GOVERNANCE</em>
          </div>
          <section class="mango-effectiveness-grid mango-effectiveness-grid--operations">
            <article class="mango-section-card mango-effectiveness-panel">
              <div class="mango-effectiveness-panel-title">
                <div
                  ><strong>自动化类型效能</strong
                  ><span>对比 API、UI、Pytest 等类型的执行规模、质量与恢复能力</span></div
                >
                <small>{{ automationTypeSummary }}</small>
              </div>
              <EffectivenessChart
                :option="automationTypeOption"
                :loading="loading"
                :empty="!overview.automation_type_quality.length"
                empty-text="当前范围暂无自动化类型数据"
                empty-description="尚未形成 API、UI 或 Pytest 等类型的执行结果"
                :insight="chartInsight('automation_type')"
                height="300px"
              />
            </article>
            <article class="mango-section-card mango-effectiveness-panel">
              <div class="mango-effectiveness-panel-title">
                <div
                  ><strong>环境 × 执行场景</strong
                  ><span>交叉查看不同环境下巡检、回归、冒烟等任务的最终通过率</span></div
                >
                <small>{{ sceneMatrixSummary }}</small>
              </div>
              <EffectivenessChart
                :option="sceneMatrixOption"
                :loading="loading"
                :empty="!sceneMatrixData.length"
                empty-text="暂无环境与执行场景交叉数据"
                empty-description="至少需要一个测试环境与一种执行场景的执行结果"
                :insight="chartInsight('environment_task_matrix')"
                height="300px"
                @chart-click="onSceneMatrixClick"
              />
            </article>
          </section>
          <section class="mango-effectiveness-grid mango-effectiveness-grid--health">
            <article
              class="mango-section-card mango-effectiveness-panel mango-effectiveness-task-health"
            >
              <div class="mango-effectiveness-panel-title">
                <div
                  ><strong>定时任务健康矩阵</strong
                  ><span>优先展示连续异常、通过率偏低或问题结果集中的任务</span></div
                >
                <small>{{ taskHealthSummary }}</small>
              </div>
              <div
                v-if="taskHealthRows.length"
                class="mango-effectiveness-task-health__list mango-native-scrollbar"
                tabindex="0"
                aria-label="定时任务健康矩阵列表"
              >
                <article
                  v-for="item in taskHealthRows"
                  :key="item.task_id"
                  :class="taskHealthClass(item)"
                >
                  <div class="mango-effectiveness-health-row__main">
                    <strong>{{ item.task_name }}</strong>
                    <small>{{ item.project_product_name }} · {{ item.module_name }}</small>
                  </div>
                  <div v-if="!reportMode" class="mango-effectiveness-health-row__actions">
                    <a-button
                      type="text"
                      size="mini"
                      @click="openReportList({ tasks_id: item.task_id })"
                      >查看报告</a-button
                    >
                    <a-button type="text" size="mini" @click="openTaskDiagnostic(item)"
                      >排查结果</a-button
                    >
                  </div>
                  <div class="mango-effectiveness-health-row__metrics">
                    <span
                      >{{ item.environment_name }} ·
                      {{ (item.execution_scene_names || []).join('、') || '未分类' }}</span
                    >
                    <span>报告 {{ item.suite_count }} 份</span>
                    <span
                      >通过率
                      <strong :class="rateClass(item.final_pass_rate)">{{
                        formatRate(item.final_pass_rate)
                      }}</strong></span
                    >
                    <span
                      >连续异常 <strong>{{ item.consecutive_abnormal || 0 }}</strong> 次</span
                    >
                  </div>
                </article>
              </div>
              <EffectivenessEmptyState
                v-else-if="!loading"
                title="当前范围暂无定时任务健康数据"
                description="当前筛选范围内尚未产生可评估的定时任务报告"
              />
              <EffectivenessAiNote :text="chartInsight('task_health')" />
            </article>

            <article
              class="mango-section-card mango-effectiveness-panel mango-effectiveness-case-health"
            >
              <div class="mango-effectiveness-panel-title">
                <div
                  ><strong>失败用例排行</strong
                  ><span>按本周期失败次数排序，最多展示 30 个去重 Case</span></div
                >
                <small>{{ failedCaseRankingSummary }}</small>
              </div>
              <div
                v-if="failedCaseRankingRows.length"
                class="mango-effectiveness-case-health__list mango-native-scrollbar"
                tabindex="0"
                aria-label="失败用例排行列表"
              >
                <article
                  v-for="item in failedCaseRankingRows"
                  :key="`${item.task_id}-${item.case_type}-${item.case_id}`"
                >
                  <div class="mango-effectiveness-health-row__main">
                    <strong :title="item.case_name">{{ item.case_name }}</strong>
                    <small
                      >{{ item.case_type_name }} · Case #{{ item.case_id }} ·
                      {{ item.task_name }}</small
                    >
                  </div>
                  <a-button
                    v-if="!reportMode"
                    type="text"
                    size="mini"
                    @click="openFailedCaseReport(item)"
                    >查看最近失败</a-button
                  >
                  <div class="mango-effectiveness-health-row__metrics">
                    <span>{{ item.project_product_name }} · {{ item.environment_name }}</span>
                    <span>本周期执行 {{ item.attempt_count }} 次</span>
                    <span
                      >失败出现
                      <strong class="mango-tone-danger">{{ item.failed_count }}</strong> 次</span
                    >
                    <span>失败占比 {{ formatRate(item.failure_rate) }}</span>
                    <span>最近失败 {{ item.latest_time || '-' }}</span>
                  </div>
                  <a-tooltip
                    :content="item.latest_error || '本次失败未返回具体原因'"
                    position="top"
                  >
                    <span
                      class="mango-effectiveness-case-health__error"
                      :class="{ 'is-empty': !item.latest_error }"
                    >
                      <strong>失败原因</strong>
                      {{ item.latest_error || '本次失败未返回具体原因' }}
                    </span>
                  </a-tooltip>
                </article>
              </div>
              <EffectivenessEmptyState
                v-else-if="!loading"
                title="本周期未发现失败用例"
                description="当前筛选范围内没有失败记录，整体执行表现稳定"
                :positive="true"
              />
              <EffectivenessAiNote :text="chartInsight('failed_case_ranking')" />
            </article>
          </section>
        </div>

        <div class="mango-effectiveness-paper-page mango-effectiveness-paper-page--diagnostics">
          <span class="mango-effectiveness-paper-page__number">05 / 07 · 多维诊断</span>
          <div class="mango-effectiveness-chapter-heading">
            <span>05</span>
            <div>
              <strong>多维质量诊断</strong>
              <small>按测试环境、执行场景和执行范围交叉识别质量差异</small>
            </div>
            <em>QUALITY DIAGNOSTICS</em>
          </div>
          <section class="mango-effectiveness-grid mango-effectiveness-grid--diagnostics">
            <article
              class="mango-section-card mango-effectiveness-panel mango-effectiveness-panel--environment"
            >
              <div class="mango-effectiveness-panel-title"
                ><div
                  ><strong>测试环境质量</strong
                  ><span>对比各环境通过与未通过占比，快速识别质量差异</span></div
                ><small>{{ environmentQualitySummary }}</small></div
              >
              <EffectivenessChart
                :option="environmentOption"
                :loading="loading"
                :empty="!overview.environment_quality.length"
                empty-text="当前范围暂无测试环境数据"
                empty-description="尚未形成可用于比较环境质量的正式执行结果"
                :insight="chartInsight('environment')"
                height="250px"
                @chart-click="onEnvironmentChartClick"
              />
            </article>
            <article class="mango-section-card mango-effectiveness-panel">
              <div class="mango-effectiveness-panel-title"
                ><div
                  ><strong>执行场景质量</strong
                  ><span>回归、冒烟、巡检、效果评测等任务的执行量与通过率</span></div
                ></div
              >
              <EffectivenessChart
                :option="sceneOption"
                :loading="loading"
                :empty="!overview.scene_distribution.length"
                empty-text="当前范围暂无执行场景数据"
                empty-description="巡检、回归、冒烟等任务尚未产生可分析结果"
                :insight="chartInsight('task_type')"
                height="250px"
                @chart-click="onSceneChartClick"
              />
            </article>
            <article class="mango-section-card mango-effectiveness-panel">
              <div class="mango-effectiveness-panel-title"
                ><div
                  ><strong>执行范围质量</strong
                  ><span>产品全量、模块全量和手动指定的质量差异</span></div
                ></div
              >
              <EffectivenessChart
                :option="scopeOption"
                :loading="loading"
                :empty="!overview.scope_distribution.length"
                empty-text="当前范围暂无执行范围数据"
                empty-description="尚未形成产品全量、模块全量或手动指定等执行结果"
                :insight="chartInsight('coverage_scope')"
                height="250px"
                @chart-click="onScopeChartClick"
              />
            </article>
          </section>
        </div>
      </div>
    </template>
  </TableBody>
  <TestReportResultDrawer
    v-model:visible="failureReportDrawer.visible"
    :test-suite-detail-id="failureReportDrawer.testSuiteDetailId"
    :case-type="failureReportDrawer.caseType"
    :case-id="failureReportDrawer.caseId"
    :case-name="failureReportDrawer.caseName"
    :fallback-error="failureReportDrawer.fallbackError"
  />
  <DiagnosticMarkdownDrawer
    v-model:visible="diagnosticDrawer.visible"
    target-type="scheduled_task"
    :target-id="diagnosticDrawer.targetId"
    :document-available="diagnosticDrawer.documentAvailable"
    :title="diagnosticDrawer.title"
  />
</template>

<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { computed, nextTick, onMounted, onBeforeUnmount, onActivated, onDeactivated, reactive, ref, watch } from 'vue'
  import { useRoute, useRouter, type LocationQueryRaw } from 'vue-router'
  import { useUserStoreContext } from '@/store/modules/user'

  import { Message } from '@arco-design/web-vue'
  import {
    IconBulb,
    IconCalendar,
    IconDashboard,
    IconFilter,
    IconImage,
    IconRefresh,
    IconRobot,
    IconSettings,
  } from '@arco-design/web-vue/es/icon'
  import { useEnum } from '@/store/modules/get-enum'
  import { useProject } from '@/store/modules/get-project'
  import { fieldNames } from '@/setting'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import TestReportResultDrawer from '@/components/reports/TestReportResultDrawer.vue'
  import DiagnosticMarkdownDrawer from '@/components/reports/DiagnosticMarkdownDrawer.vue'
  import {
    getAutomationEffectivenessOverview,
    postAutomationEffectivenessCacheClear,
  } from '@/api/system/automation-effectiveness'
  import EffectivenessChart from './components/EffectivenessChart.vue'
  import EffectivenessAiNote from './components/EffectivenessAiNote.vue'
  import EffectivenessEmptyState from './components/EffectivenessEmptyState.vue'
  import PeriodQualityTrend from './components/PeriodQualityTrend.vue'
  import { effectivenessQualityThresholds, periodPresetOptions, defaultPeriodPreset, type PeriodPreset } from './config'
  import { effectivenessPayload, effectivenessObject, type InsightKey } from './ai-summary'
  import { useEffectivenessAiSummary } from './composables/useEffectivenessAiSummary'
  import { useEffectivenessExport } from './composables/useEffectivenessExport'
  import { createEmptyOverview, normalizeEffectivenessOverview, effectivenessNumber, effectivenessMatrixRows, effectivenessChartIndex, effectivenessDate, type EffectivenessOverview, type EffectivenessDimension, type EffectivenessTask, type EffectivenessFailedCase } from './overview'
  import { createDefaultFilters, copyEffectivenessFilters, selectedEffectivenessProduct, effectivenessQuery, resolvePeriodDateRange, type EffectivenessFilters } from './filters'
  import { chartPoint, chartPoints, chartHtml } from './chart-boundary'

  type ModuleQualityFilter = 'attention' | 'all' | 'danger' | 'warning' | 'success'

  const enumStore = useEnum()
  const projectStore = useProject()
  const router = useRouter()
  const route = useRoute(), userStore = useUserStoreContext(), pagePath = route.path
  let mounted = false, active = true, disposed = false, needsLoad = true
  const pageAvailable = () => mounted && active && !disposed && route.path === pagePath && document.visibilityState === 'visible'
  let initialized = false
  const loading = ref(false)
  const reportMode = ref(false)
  const filterVisible = ref(false)
  const printing = ref(false)
  const imageExporting = ref(false)
  const cacheClearing = ref(false)
  const moduleQualityFilter = ref<ModuleQualityFilter>('attention')
  const failureReportDrawer = reactive({
    visible: false,
    testSuiteDetailId: '' as number | string,
    caseType: -1 as number | string,
    caseId: '' as number | string,
    caseName: '',
    fallbackError: '',
  })
  const diagnosticDrawer = reactive({
    visible: false,
    targetId: '' as number | string,
    documentAvailable: false,
    title: '定时任务排查结果',
  })
  const reportContentLoading = computed(
    () => loading.value || aiLoading.value || cacheClearing.value
  )
  const pdfExportDisabled = computed(
    () => !overviewReady.value || reportContentLoading.value || imageExporting.value || printing.value
  )
  const imageExportDisabled = computed(
    () => !overviewReady.value || reportContentLoading.value || printing.value || imageExporting.value
  )
  const pdfExportTooltip = computed(() =>
    pdfExportDisabled.value ? '请等待全部加载完成' : '打印或保存为 PDF'
  )
  const imageExportTooltip = computed(() =>
    imageExportDisabled.value ? '请等待全部加载完成' : '下载完整高清 PNG 图片'
  )
  const pageContextVersion = ref(0), overviewReady = ref(false), loadError = ref('')
  const ai = useEffectivenessAiSummary({
    scopeKey: () => pageContextVersion.value,
    available: () => pageAvailable() && overviewReady.value && !loading.value,
    snapshot: () => overviewReady.value && overviewEvidence.value ? {
      overview: overviewEvidence.value,
      context: {
        project_product: selectedProjectProductTitle.value,
        period: reportPeriodText.value,
        comparison_period: comparisonPeriodText.value,
        environment: optionTitles(enumStore.environment_type, filters.test_env, '全部环境'),
        task_type: optionTitles(sceneOptions.value, filters.execution_scene, '全部执行场景'),
        coverage_scope: optionTitles(scopeOptions.value, filters.execution_scope, '全部执行范围'),
      },
    } : null,
  })
  const aiState = ai.state, aiInsightState = ai.insightState
  const aiLoading = ai.loading
  const aiError = ai.error, aiInsightError = ai.insightError
  const chartInsight = (key: InsightKey) => aiInsightState.insights[key] || aiState.summary?.chart_insights[key] || ''
  const componentInsight = (key: InsightKey) => aiInsightState.insights[key] || aiState.summary?.component_insights[key] || ''
  const loadAiSummary = (force = false) => ai.load(force)
  let overviewRequestSequence = 0
  const filters: EffectivenessFilters = reactive(createDefaultFilters())
  const draftFilters: EffectivenessFilters = reactive(createDefaultFilters())
  const overview: EffectivenessOverview = reactive(createEmptyOverview())
  const overviewEvidence = ref<Record<string, unknown> | null>(null)
  const hasEffectivenessData = computed(
    () =>
      Number(overview.cards?.suite_count || 0) > 0 || Number(overview.cards?.detail_count || 0) > 0
  )
  const hasTrendData = computed(
    () =>
      hasEffectivenessData.value &&
      (overview.trend || []).some((item) => Number(item.detail_count || 0) > 0)
  )
  const dataConfidence = computed(() => {
    const suites = Number(overview.cards.suite_count || 0)
    const executions = Number(overview.cards.detail_count || 0)
    const completeness = Number(overview.cards.data_completeness || 0)
    if (!suites || !executions) {
      return { label: '暂无评估', color: 'gray', description: '当前范围暂无足够的正式执行数据。' }
    }
    const reasons: string[] = []
    if (suites < 3) reasons.push('报告样本少于 3 份')
    if (completeness < 60) reasons.push('部分执行记录缺少统一明细')
    if (!overview.comparison?.has_previous) reasons.push('缺少完整的上一周期对比数据')
    if (reasons.length >= 2) return { label: '偏低', color: 'red', description: reasons.join('；') }
    if (reasons.length || completeness < 80 || suites < 5)
      return {
        label: '一般',
        color: 'orange',
        description: reasons.join('；') || '当前数据可用于观察，但样本规模或记录完整度仍可提升。',
      }
    return { label: '较高', color: 'green', description: '样本规模、执行记录和环比数据较完整。' }
  })
  const sceneOptions = computed(() =>
    (enumStore.automation_execution_scene || []).filter((item) => item.key !== 'unclassified')
  )
  const scopeOptions = computed(() =>
    (enumStore.automation_execution_scope || []).filter((item) => item.key !== 'unclassified')
  )
  const selectedProjectProductId = computed(() => selectedEffectivenessProduct(filters.project_product))
  const selectedProjectProductTitle = computed(() => {
    const productId = selectedProjectProductId.value
    if (productId === null || productId === undefined) return '全部项目/产品'
    for (const project of projectStore.projectProduct || []) {
      const product = (project.children || []).find(
        (item) => String(item.value) === String(productId)
      )
      if (product) return `${project.label} / ${product.label}`
    }
    return '已选项目/产品'
  })
  const generatedAt = ref('')
  const reportPeriodText = computed(() =>
    filters.dateRange?.length === 2
      ? `${filters.dateRange[0]} 至 ${filters.dateRange[1]}`
      : '最近 7 天'
  )
  const comparisonPeriodText = computed(() => {
    const period = overview.previous_period || {}
    const startDate = String(period.start || '').slice(0, 10)
    const endDate = String(period.end || '').slice(0, 10)
    return startDate && endDate ? `${startDate} 至 ${endDate}` : '紧邻的上一周期'
  })
  const reportDocumentTitle = computed(
    () => `${selectedProjectProductTitle.value} · ${reportPeriodText.value} 质量报告`
  )
  const activeFilterCount = computed(() => {
    let count = 0
    if (filters.periodPreset !== defaultPeriodPreset) count += 1
    if (selectedProjectProductId.value !== null && selectedProjectProductId.value !== undefined)
      count += 1
    if (filters.test_env.length) count += 1
    if (filters.execution_scene.length) count += 1
    if (filters.execution_scope.length) count += 1
    return count
  })
  const filterButtonText = computed(
    () => `筛选条件${activeFilterCount.value ? `（${activeFilterCount.value}）` : ''}`
  )
  const optionTitles = (
    options: Array<{ key: string | number; title: string }> | null | undefined,
    values: Array<string | number>,
    fallback: string
  ) => {
    if (!values.length) return fallback
    const titles = values
      .map((value) => options?.find((item) => String(item.key) === String(value))?.title)
      .filter(Boolean)
    return titles.length ? titles.join('、') : fallback
  }
  const reportScopeItems = computed(() => [
    selectedProjectProductTitle.value,
    optionTitles(enumStore.environment_type, filters.test_env, '全部环境'),
    optionTitles(sceneOptions.value, filters.execution_scene, '全部执行场景'),
    optionTitles(scopeOptions.value, filters.execution_scope, '全部执行范围'),
  ])
  const verdictText = computed(() => {
    if (!overview.cards.suite_count) return '暂无正式数据'
    if (overview.cards.final_pass_rate === null) return overview.cards.unfinished_count > 0 ? '执行尚未完成' : '暂无完成结果'
    if (overview.cards.final_pass_rate < effectivenessQualityThresholds.highRiskPassRate)
      return '质量风险较高'
    if (
      overview.cards.failed_count > 0 ||
      overview.cards.final_pass_rate < effectivenessQualityThresholds.healthyPassRate
    )
      return '质量需要改进'
    if (overview.cards.unfinished_count > 0) return '执行尚未完成'
    if (
      overview.cards.warning_count > 0 ||
      (overview.cards.flaky_rate !== null && overview.cards.flaky_rate > effectivenessQualityThresholds.healthyFlakyRate)
    )
      return '质量需要关注'
    return '质量良好'
  })
  const flakyRateNeedsAttention = computed(
    () => Number(overview.cards.flaky_rate || 0) > effectivenessQualityThresholds.healthyFlakyRate
  )
  const verdictReasonText = computed(() => {
    if (!overview.cards.suite_count) return '当前筛选范围暂无正式定时任务报告'
    if (overview.cards.final_pass_rate === null) return overview.cards.unfinished_count > 0 ? `仍有 ${overview.cards.unfinished_count} 个执行明细尚未结束` : '当前周期尚无可计算通过率的完成结果'
    if (overview.cards.final_pass_rate < effectivenessQualityThresholds.highRiskPassRate)
      return `最终通过率 ${formatRate(overview.cards.final_pass_rate)}，低于质量基线`
    if (overview.cards.failed_count > 0)
      return `本周期仍有 ${overview.cards.failed_count} 个最终失败结果`
    if (overview.cards.final_pass_rate < effectivenessQualityThresholds.healthyPassRate)
      return `最终通过率 ${formatRate(overview.cards.final_pass_rate)}，尚未达到健康标准`
    if (overview.cards.unfinished_count > 0)
      return `仍有 ${overview.cards.unfinished_count} 个执行明细尚未结束`
    const attentionReasons: string[] = []
    if (overview.cards.warning_count > 0)
      attentionReasons.push(`${overview.cards.warning_count} 个警告结果`)
    if (flakyRateNeedsAttention.value)
      attentionReasons.push(
        `不稳定率 ${formatRate(overview.cards.flaky_rate)}，超过健康阈值 ${formatRate(
          effectivenessQualityThresholds.healthyFlakyRate
        )}`
      )
    if (attentionReasons.length) return attentionReasons.join('；')
    return `最终通过率 ${formatRate(overview.cards.final_pass_rate)}，执行结果稳定`
  })
  const verdictColor = computed(() =>
    verdictText.value === '质量风险较高'
      ? 'red'
      : ['质量需要改进', '执行尚未完成', '质量需要关注'].includes(verdictText.value)
      ? 'orange'
      : verdictText.value === '质量良好'
      ? 'green'
      : 'gray'
  )
  const verdictReasonTone = computed(() =>
    verdictColor.value === 'red'
      ? 'danger'
      : verdictColor.value === 'green'
      ? 'success'
      : verdictColor.value === 'orange'
      ? 'warning'
      : 'neutral'
  )
  const qualityCardDescription = computed(() =>
    flakyRateNeedsAttention.value
      ? `不稳定率 ${formatRate(overview.cards.flaky_rate)} · 重试恢复 ${
          overview.cards.flaky_count || 0
        } 个`
      : `完成率 ${formatRate(overview.cards.completion_rate)}`
  )
  const convergenceTone = computed(() => {
    if (overview.convergence.direction === 'converging') return 'success'
    if (overview.convergence.direction === 'diverging') return 'danger'
    return 'neutral'
  })
  const convergenceValue = computed(
    () =>
      ({
        converging: '正在收敛',
        diverging: '风险扩大',
        stable: '基本持平',
        unknown: '暂无对比',
      }[overview.convergence.direction] || '暂无对比')
  )
  const convergenceClass = computed(() =>
    convergenceTone.value === 'success'
      ? 'mango-effectiveness-state-success'
      : convergenceTone.value === 'danger'
      ? 'mango-effectiveness-state-danger'
      : ''
  )
  const convergenceLabel = computed(() => {
    if (!hasEffectivenessData.value) return '暂无正式执行'
    return rateComparisonText(overview.convergence.issue_rate_delta, '问题率', false)
  })
  const sourceTaskRows = computed(() =>
    [...(overview.task_health || [])].sort((left, right) => {
      const leftRate = left.report_success_rate
      const rightRate = right.report_success_rate
      if (
        (leftRate === null || leftRate === undefined) &&
        (rightRate === null || rightRate === undefined)
      )
        return String(left.task_name || '').localeCompare(String(right.task_name || ''), 'zh-CN')
      if (leftRate === null || leftRate === undefined) return 1
      if (rightRate === null || rightRate === undefined) return -1
      return Number(leftRate) - Number(rightRate)
    })
  )
  const sourceTaskDetails = computed(() =>
    sourceTaskRows.value.map(
      (item) =>
        `${item.task_name}：报告 ${formatRate(item.report_success_rate)} / 用例 ${formatRate(
          item.final_pass_rate
        )}`
    )
  )
  const sourceTaskSummary = computed(() => {
    if (!sourceTaskDetails.value.length) return '当前周期无正式定时任务来源'
    const visible = sourceTaskDetails.value.slice(0, 2).join('；')
    const remaining = sourceTaskDetails.value.length - 2
    return remaining > 0 ? `${visible}；另 ${remaining} 个任务` : visible
  })
  const sourceTaskSummaryTitle = computed(() => sourceTaskDetails.value.join('；'))
  const executiveCards = computed(() => [
    {
      key: 'source',
      title: '数据来源',
      value: `${overview.task_source_summary.task_count || 0} 个任务`,
      badge: `${overview.task_source_summary.report_count || 0} 份报告`,
      description: `${formatCount(overview.task_source_summary.execution_count)} 次用例执行`,
      comparison: sourceTaskSummary.value,
      comparisonTitle: sourceTaskSummaryTitle.value,
      comparisonClass: '',
      valueClass: '',
      tone: 'neutral',
    },
    {
      key: 'execution',
      title: '自动化执行',
      value: overview.cards.detail_count || 0,
      badge: `${overview.cards.suite_count || 0} 份报告`,
      description: `覆盖 ${overview.benefits.unique_case_count || 0} 个用例`,
      comparison: comparisonText(overview.comparison.detail_count_delta, ' 次', true),
      comparisonClass: '',
      valueClass: '',
      tone: 'neutral',
    },
    {
      key: 'feedback',
      title: '首轮结果反馈时效',
      value: formatDuration(
        overview.cards.p95_first_feedback_seconds ?? overview.cards.p95_feedback_seconds
      ),
      badge: 'P95 首轮',
      description: `时效样本 ${overview.cards.feedback_sample_count || 0}/${
        overview.cards.feedback_report_count || 0
      } 份 · 重试恢复 ${overview.benefits.retry_recovered_count || 0} 个`,
      comparison: overview.cards.feedback_sample_count
        ? '95% 的完整报告在此时间内产出首轮结果'
        : '暂无完整首轮结果样本',
      comparisonClass: '',
      valueClass: '',
      tone: 'neutral',
    },
    {
      key: 'discovery',
      title: '异常执行结果',
      value: `${formatCount(overview.benefits.detected_issue_count)} 次`,
      badge: `涉及 ${overview.benefits.affected_case_count || 0} 个用例`,
      description: `其中新增异常用例 ${overview.convergence.new_issue_case_count || 0} 个`,
      comparison: issueComparisonText(
        overview.benefits.detected_issue_count,
        overview.comparison.issue_count_delta
      ),
      comparisonClass: comparisonClass(overview.comparison.issue_count_delta, false),
      valueClass: '',
      tone: overview.benefits.detected_issue_count ? 'danger' : 'success',
    },
    {
      key: 'quality',
      title: '当前质量',
      value: formatRate(overview.cards.final_pass_rate),
      badge: verdictText.value,
      description: qualityCardDescription.value,
      comparison: rateComparisonText(overview.comparison.final_pass_rate_delta, '最终通过率', true),
      comparisonClass: comparisonClass(overview.comparison.final_pass_rate_delta, true),
      valueClass: rateClass(overview.cards.final_pass_rate),
      tone:
        verdictColor.value === 'red'
          ? 'danger'
          : verdictColor.value === 'orange'
          ? 'warning'
          : verdictColor.value === 'green'
          ? 'success'
          : 'neutral',
    },
    {
      key: 'convergence',
      title: '问题收敛',
      value: convergenceValue.value,
      badge: formatRate(overview.convergence.current_issue_rate),
      description: `本周期问题 ${overview.convergence.current_issue_count || 0} 次`,
      comparison: rateComparisonText(overview.convergence.issue_rate_delta, '问题率', false),
      comparisonClass: comparisonClass(overview.convergence.issue_rate_delta, false),
      valueClass: convergenceClass.value,
      tone: convergenceTone.value,
    },
  ])

  const chartBase = {
    textStyle: { color: 'var(--m-text-2)' },
    tooltip: { trigger: 'axis', confine: true },
    legend: { top: 0, textStyle: { color: 'var(--m-text-2)' } },
    grid: { left: 42, right: 42, top: 42, bottom: 30, containLabel: true },
  }
  function normalizeChartRate(value: unknown) {
    const normalized = effectivenessNumber(value)
    return normalized === null ? null : Number(normalized.toFixed(2))
  }
  function formatChartRate(value: unknown) {
    const normalized = normalizeChartRate(value)
    return normalized === null ? '-' : `${normalized.toFixed(2)}%`
  }
  function formatPercentagePoint(value: unknown, signed = false) {
    const normalized = normalizeChartRate(value)
    if (normalized === null) return '-'
    return `${signed && normalized > 0 ? '+' : ''}${normalized.toFixed(2)}`
  }
  function formatAxisTooltip(params: unknown, rateSeriesNames: string[]) {
    const items = chartPoints(params)
    if (!items.length) return ''
    const rateSeries = new Set(rateSeriesNames)
    const title = chartHtml(items[0].axisValueLabel || items[0].name)
    const rows = items.map((item) => {
      const displayValue = rateSeries.has(item.seriesName)
        ? formatChartRate(item.value)
        : formatCount(item.value)
      return `● ${chartHtml(item.seriesName)}：${displayValue}`
    })
    return [title, ...rows].filter(Boolean).join('<br/>')
  }
  const trendAxisLabelInterval = computed(() => {
    const dayCount = overview.trend.length
    if (dayCount <= 7) return 0
    const step = Math.ceil((dayCount - 1) / 6)
    return (index: number) => index === 0 || index === dayCount - 1 || index % step === 0
  })
  const trendOption = computed(() => ({
    ...chartBase,
    tooltip: {
      trigger: 'axis',
      confine: true,
      formatter: (params: unknown) => formatAxisTooltip(params, ['最终通过率']),
    },
    color: ['var(--m-danger)', 'var(--m-warning)', 'var(--m-chart-2)'],
    xAxis: {
      type: 'category',
      data: overview.trend.map((item) => item.date),
      axisLabel: {
        color: 'var(--m-muted)',
        interval: trendAxisLabelInterval.value,
        showMinLabel: true,
        showMaxLabel: true,
      },
    },
    yAxis: [
      {
        type: 'value',
        name: '问题次数',
        minInterval: 1,
        axisLabel: { color: 'var(--m-muted)' },
        splitLine: { lineStyle: { color: 'var(--m-border)' } },
      },
      {
        type: 'value',
        name: '通过率',
        min: 0,
        max: 100,
        axisLabel: { formatter: '{value}%', color: 'var(--m-muted)' },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: '失败',
        type: 'bar',
        stack: 'issue',
        barMaxWidth: 22,
        data: overview.trend.map((item) => item.failed_count),
        itemStyle: { borderRadius: [0, 0, 2, 2] },
      },
      {
        name: '警告',
        type: 'bar',
        stack: 'issue',
        barMaxWidth: 22,
        data: overview.trend.map((item) => item.warning_count),
        itemStyle: { borderRadius: [3, 3, 0, 0] },
      },
      {
        name: '最终通过率',
        type: 'line',
        yAxisIndex: 1,
        smooth: true,
        symbolSize: 6,
        z: 3,
        data: overview.trend.map((item) => normalizeChartRate(item.final_pass_rate)),
        lineStyle: { color: 'var(--m-success)', width: 2 },
        itemStyle: { color: 'var(--m-success)' },
        emphasis: {
          focus: 'none',
          lineStyle: { color: 'var(--m-success)', width: 3, opacity: 1 },
          itemStyle: { color: 'var(--m-success)', opacity: 1 },
        },
        blur: {
          lineStyle: { opacity: 1 },
          itemStyle: { opacity: 1 },
        },
      },
    ],
  }))
  const environmentOption = computed(() => ({
    ...chartBase,
    tooltip: {
      trigger: 'axis',
      confine: true,
      formatter: (params: unknown) => formatAxisTooltip(params, ['通过', '未通过']),
    },
    color: ['var(--m-success)', 'var(--m-danger)'],
    legend: {
      show: true,
      top: 0,
      itemWidth: 14,
      itemHeight: 8,
      textStyle: { color: 'var(--m-text-2)' },
    },
    grid: { left: 70, right: 72, top: 38, bottom: 18, containLabel: true },
    xAxis: {
      type: 'value',
      min: 0,
      max: 100,
      splitNumber: reportMode.value ? 2 : 5,
      axisLabel: { formatter: '{value}%', color: 'var(--m-muted)' },
      splitLine: { lineStyle: { color: 'var(--m-border)' } },
    },
    yAxis: {
      type: 'category',
      inverse: true,
      data: overview.environment_quality.map((item) => item.environment_name),
      axisLabel: { color: 'var(--m-text-2)' },
    },
    series: [
      {
        name: '通过',
        type: 'bar',
        stack: 'quality',
        barMaxWidth: 22,
        data: overview.environment_quality.map((item) => ({
          value: normalizeChartRate(item.final_pass_rate) ?? 0,
          itemStyle: {
            color: 'var(--m-success)',
            borderRadius: [3, 0, 0, 3],
          },
        })),
      },
      {
        name: '未通过',
        type: 'bar',
        stack: 'quality',
        barMaxWidth: 22,
        data: overview.environment_quality.map((item) => {
          const rate = item.final_pass_rate
          const hasResult = rate !== null && rate !== undefined
          return {
            value: hasResult ? normalizeChartRate(Math.max(100 - Number(rate), 0)) ?? 0 : 100,
            itemStyle: {
              color: hasResult ? 'var(--m-danger)' : 'var(--m-muted)',
              borderRadius: [0, 3, 3, 0],
            },
          }
        }),
        label: {
          show: true,
          position: 'right',
          formatter: (params: unknown) => {
            const index = effectivenessChartIndex(params)
            const rate = index === null ? null : overview.environment_quality[index]?.final_pass_rate
            return rate === null || rate === undefined ? '暂无结果' : formatChartRate(rate)
          },
        },
      },
    ],
  }))
  const dimensionOption = (items: EffectivenessDimension[], nameKey: 'scene_name' | 'scope_name' | 'type_name') => {
    const otherStatus = items.map((item) =>
      Math.max(
        Number(item.detail_count || 0) -
          Number(item.success_count || 0) -
          Number(item.failed_count || 0) -
          Number(item.warning_count || 0),
        0
      )
    )
    const barSeries = [
      {
        name: '通过',
        color: 'var(--m-success)',
        data: items.map((item) => item.success_count || 0),
      },
      {
        name: '失败',
        color: 'var(--m-danger)',
        data: items.map((item) => item.failed_count || 0),
      },
      {
        name: '警告',
        color: 'var(--m-warning)',
        data: items.map((item) => item.warning_count || 0),
      },
      { name: '其他状态', color: 'var(--m-muted)', data: otherStatus },
    ]
      .filter((series) => series.data.some((value) => Number(value) > 0))
      .map((series) => ({
        name: series.name,
        type: 'bar',
        stack: 'result',
        barMaxWidth: 26,
        data: series.data,
        itemStyle: { color: series.color },
      }))

    return {
      ...chartBase,
      tooltip: {
        trigger: 'axis',
        confine: true,
        formatter: (params: unknown) => formatAxisTooltip(params, ['最终通过率']),
      },
      legend: {
        top: 0,
        left: 'center',
        itemWidth: reportMode.value ? 10 : 12,
        itemHeight: 7,
        itemGap: reportMode.value ? 6 : 10,
        textStyle: {
          color: 'var(--m-text-2)',
          fontSize: reportMode.value ? 10 : 11,
        },
      },
      grid: {
        left: 24,
        right: 32,
        top: reportMode.value ? 46 : 44,
        bottom: 34,
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: items.map((item) => item[nameKey]),
        axisLabel: {
          color: 'var(--m-text-2)',
          interval: 0,
          overflow: 'truncate',
          width: reportMode.value ? 62 : 82,
          hideOverlap: true,
          formatter: (value: string) => {
            if (!reportMode.value) return value
            const characters = Array.from(String(value))
            if (characters.length <= 4) return value
            return `${characters.slice(0, 4).join('')}\n${characters.slice(4, 8).join('')}${characters.length > 8 ? '…' : ''}`
          },
          fontSize: reportMode.value ? 10 : 11,
        },
      },
      yAxis: [
        {
          type: 'value',
          minInterval: 1,
          axisLabel: { color: 'var(--m-muted)', fontSize: reportMode.value ? 10 : 11 },
          splitLine: { lineStyle: { color: 'var(--m-border)' } },
        },
        {
          type: 'value',
          min: 0,
          max: 100,
          axisLabel: {
            formatter: '{value}%',
            color: 'var(--m-muted)',
            fontSize: reportMode.value ? 10 : 11,
          },
          splitLine: { show: false },
        },
      ],
      series: [
        ...barSeries,
        {
          name: '最终通过率',
          type: 'line',
          yAxisIndex: 1,
          symbolSize: 7,
          z: 3,
          data: items.map((item) => normalizeChartRate(item.final_pass_rate)),
          lineStyle: { color: 'var(--m-success)', width: 2 },
          itemStyle: { color: 'var(--m-success)' },
          emphasis: {
            focus: 'none',
            lineStyle: { color: 'var(--m-success)', width: 3, opacity: 1 },
            itemStyle: { color: 'var(--m-success)', opacity: 1 },
          },
          blur: {
            lineStyle: { opacity: 1 },
            itemStyle: { opacity: 1 },
          },
        },
      ],
    }
  }
  const sceneOption = computed(() => dimensionOption(overview.scene_distribution, 'scene_name'))
  const scopeOption = computed(() => dimensionOption(overview.scope_distribution, 'scope_name'))

  const moduleRiskData = computed(() => {
    const items = [...(overview.module_quality || [])]
      .filter((item) => item.final_pass_rate !== null && item.final_pass_rate !== undefined)
      .sort((left, right) => {
        const leftIssues = Number(left.failed_count || 0) + Number(left.warning_count || 0)
        const rightIssues = Number(right.failed_count || 0) + Number(right.warning_count || 0)
        return (
          rightIssues - leftIssues ||
          Number(right.detail_count || 0) - Number(left.detail_count || 0)
        )
      })
    return items.slice(0, reportMode.value ? 12 : 18)
  })
  const moduleRiskSummary = computed(() => {
    if (!moduleRiskData.value.length) return '暂无模块数据'
    const riskCount = moduleRiskData.value.filter(
      (item) => item.quality_level === 'danger'
    ).length
    return riskCount ? `${riskCount} 个高风险模块` : '当前模块整体稳定'
  })
  function compactModuleRiskLabel(value: unknown) {
    const parts = String(value || '')
      .split('/')
      .map((item) => item.trim())
      .filter(Boolean)
    const label = parts.length ? parts[parts.length - 1] : '未命名模块'
    return label.length > 10 ? `${label.slice(0, 9)}…` : label
  }
  const moduleRiskOption = computed(() => {
    const detailValues = moduleRiskData.value
      .map((item) => Number(item.detail_count || 0))
      .sort((left: number, right: number) => left - right)
    const positiveDetailValues = detailValues.filter((value: number) => value > 0)
    const minPositiveDetail = positiveDetailValues[0] || 1
    const maxDetail = positiveDetailValues[positiveDetailValues.length - 1] || 1
    const useLogScale = maxDetail / minPositiveDetail >= 8
    const medianDetail = detailValues.length
      ? detailValues[Math.floor((detailValues.length - 1) / 2)]
      : 0
    const maxIssues = Math.max(
      ...moduleRiskData.value.map(
        (item) => Number(item.failed_count || 0) + Number(item.warning_count || 0)
      ),
      1
    )
    return {
      ...chartBase,
      grid: { left: 34, right: 30, top: 50, bottom: 34, containLabel: true },
      tooltip: {
        trigger: 'item',
        confine: true,
        formatter: (params: unknown) => {
          const point = chartPoint(params)
          const rawValue = point?.value
          const value = Array.isArray(rawValue) ? rawValue : []
          return `${chartHtml(value[3])}<br/>执行次数：${formatCount(
            value[4] ?? value[0]
          )}<br/>最终通过率：${formatChartRate(value[1])}<br/>问题结果：${formatCount(value[2])}`
        },
      },
      xAxis: {
        type: useLogScale ? 'log' : 'value',
        name: '执行次数',
        ...(useLogScale
          ? {
              min: Math.max(1, Math.floor(minPositiveDetail * 0.72)),
              max: Math.ceil(maxDetail * 1.18),
              logBase: 10,
            }
          : { min: 0, minInterval: 1 }),
        axisLabel: {
          color: 'var(--m-muted)',
          formatter: (value: number) => Number(value).toLocaleString('zh-CN'),
        },
        splitLine: { lineStyle: { color: 'var(--m-border)' } },
      },
      yAxis: {
        type: 'value',
        name: '通过率',
        min: 0,
        max: 110,
        interval: 20,
        axisLabel: { formatter: '{value}%', color: 'var(--m-muted)' },
        splitLine: { lineStyle: { color: 'var(--m-border)' } },
      },
      series: [
        {
          name: '模块风险',
          type: 'scatter',
          data: moduleRiskData.value.map((item, index: number) => {
            const issues = Number(item.failed_count || 0) + Number(item.warning_count || 0)
            const color =
              item.quality_level === 'danger'
                ? 'var(--m-danger)'
                : item.quality_level === 'warning'
                ? 'var(--m-warning)'
                : 'var(--m-success)'
            return {
              value: [
                Math.max(1, Number(item.detail_count || 0)),
                normalizeChartRate(item.final_pass_rate) ?? 0,
                issues,
                item.module_path,
                Number(item.detail_count || 0),
              ],
              symbolSize: 10 + Math.round((issues / maxIssues) * 18),
              itemStyle: { color, opacity: 0.76 },
              label: {
                show: index < (reportMode.value ? 3 : 5),
                formatter: reportMode.value
                  ? `${compactModuleRiskLabel(item.module_path).slice(0, 7)}${
                      compactModuleRiskLabel(item.module_path).length > 7 ? '…' : ''
                    }`
                  : compactModuleRiskLabel(item.module_path),
                position: ['top', 'bottom', 'right', 'left'][index % 4],
                distance: 6,
                color: 'var(--m-text-2)',
                fontSize: 10,
              },
            }
          }),
          labelLayout: { hideOverlap: true },
          emphasis: {
            focus: 'series',
            scale: 1.08,
          },
          markLine: {
            silent: true,
            symbol: 'none',
            label: { color: 'var(--m-muted)', fontSize: 9 },
            lineStyle: { color: 'var(--m-border)', type: 'dashed' },
            data: [
              { yAxis: effectivenessQualityThresholds.highRiskPassRate, name: '质量基线' },
              ...(medianDetail ? [{ xAxis: medianDetail, name: '执行中位数' }] : []),
            ],
          },
        },
      ],
    }
  })

  const issueParetoData = computed(() =>
    [...(overview.module_quality || [])]
      .map((item) => ({
        ...item,
        issue_count: Number(item.failed_count || 0) + Number(item.warning_count || 0),
      }))
      .filter((item) => item.issue_count > 0)
      .sort((left, right) => right.issue_count - left.issue_count)
      .slice(0, 8)
  )
  const issueParetoSummary = computed(() => {
    const allIssues = (overview.module_quality || []).reduce(
      (total: number, item) =>
        total + Number(item.failed_count || 0) + Number(item.warning_count || 0),
      0
    )
    if (!allIssues) return '当前模块暂无问题'
    const topIssues = issueParetoData.value.reduce(
      (total: number, item) => total + item.issue_count,
      0
    )
    return `前 ${issueParetoData.value.length} 个模块贡献 ${Math.round(
      (topIssues / allIssues) * 100
    )}% 问题`
  })
  const issueParetoOption = computed(() => {
    const total = issueParetoData.value.reduce(
      (sum: number, item) => sum + item.issue_count,
      0
    )
    let accumulated = 0
    const cumulative = issueParetoData.value.map((item) => {
      accumulated += item.issue_count
      return total ? Number(((accumulated / total) * 100).toFixed(2)) : 0
    })
    return {
      ...chartBase,
      legend: {
        top: 0,
        itemWidth: 12,
        itemHeight: 7,
        textStyle: { color: 'var(--m-text-2)' },
      },
      grid: { left: 34, right: 46, top: 42, bottom: 56, containLabel: true },
      tooltip: {
        trigger: 'axis',
        confine: true,
        formatter: (params: unknown) => formatAxisTooltip(params, ['累计占比']),
      },
      xAxis: {
        type: 'category',
        data: issueParetoData.value.map((item) => item.module_path),
        axisLabel: {
          color: 'var(--m-muted)',
          interval: 0,
          rotate: issueParetoData.value.length > 5 ? 24 : 0,
          formatter: (value: string) => (value.length > 9 ? `${value.slice(0, 8)}…` : value),
        },
      },
      yAxis: [
        {
          type: 'value',
          name: '问题结果',
          minInterval: 1,
          axisLabel: { color: 'var(--m-muted)' },
          splitLine: { lineStyle: { color: 'var(--m-border)' } },
        },
        {
          type: 'value',
          name: '累计占比',
          min: 0,
          max: 100,
          axisLabel: { formatter: '{value}%', color: 'var(--m-muted)' },
          splitLine: { show: false },
        },
      ],
      series: [
        {
          name: '失败',
          type: 'bar',
          stack: 'issue',
          barMaxWidth: 28,
          data: issueParetoData.value.map((item) => item.failed_count || 0),
          itemStyle: { color: 'var(--m-danger)' },
        },
        {
          name: '警告',
          type: 'bar',
          stack: 'issue',
          barMaxWidth: 28,
          data: issueParetoData.value.map((item) => item.warning_count || 0),
          itemStyle: { color: 'var(--m-warning)', borderRadius: [3, 3, 0, 0] },
        },
        {
          name: '累计占比',
          type: 'line',
          yAxisIndex: 1,
          data: cumulative,
          symbolSize: 6,
          lineStyle: { color: 'var(--m-primary)', width: 2 },
          itemStyle: { color: 'var(--m-primary)' },
        },
      ],
    }
  })

  const sceneMatrixData = computed(() => effectivenessMatrixRows(overview.scene_matrix))
  const sceneMatrixSummary = computed(() => {
    if (!sceneMatrixData.value.length) return '暂无交叉质量数据'
    const lowest = sceneMatrixData.value[0]
    const tone =
      lowest.finalPassRate < effectivenessQualityThresholds.highRiskPassRate
        ? '风险'
        : lowest.finalPassRate < effectivenessQualityThresholds.healthyPassRate
        ? '关注'
        : '稳定'
    return `${tone} ${lowest.environment} × ${lowest.scene} ${formatRate(lowest.finalPassRate)}`
  })
  const sceneMatrixOption = computed(() => {
    const rows = sceneMatrixData.value
    return {
      ...chartBase,
      legend: { show: false },
      tooltip: {
        trigger: 'item',
        confine: true,
        formatter: (params: unknown) => {
          const item = chartPoint(params)?.data
          return `${chartHtml(item?.environment)} × ${chartHtml(item?.scene)}<br/>最终通过率：${formatChartRate(
            item?.value
          )}<br/>执行次数：${formatCount(item?.detailCount)}<br/>失败：${formatCount(
            item?.failedCount
          )}`
        },
      },
      grid: { left: 24, right: 92, top: 10, bottom: 24, containLabel: true },
      xAxis: {
        type: 'value',
        min: 0,
        max: 100,
        interval: 20,
        axisLabel: { color: 'var(--m-muted)', formatter: '{value}%' },
        splitLine: { lineStyle: { color: 'var(--m-border)', type: 'dashed' } },
      },
      yAxis: {
        type: 'category',
        inverse: true,
        data: rows.map((item) => item.label),
        axisLabel: {
          color: 'var(--m-text-2)',
          width: 128,
          overflow: 'truncate',
          fontSize: 10,
        },
      },
      series: [
        {
          name: '交叉质量',
          type: 'bar',
          barMaxWidth: 26,
          showBackground: true,
          backgroundStyle: {
            color: 'var(--m-surface-soft)',
            borderRadius: 4,
          },
          data: rows.map((item) => ({
            ...item,
            value: item.finalPassRate,
            itemStyle: {
              color:
                item.finalPassRate < effectivenessQualityThresholds.highRiskPassRate
                  ? 'var(--m-danger)'
                  : item.finalPassRate < effectivenessQualityThresholds.healthyPassRate
                  ? 'var(--m-warning)'
                  : 'var(--m-success)',
              borderRadius: [0, 4, 4, 0],
            },
          })),
          label: {
            show: true,
            position: 'right',
            formatter: (params: unknown) =>
              `${formatChartRate(chartPoint(params)?.value)} · ${formatCount(chartPoint(params)?.data?.detailCount)} 次`,
            color: 'var(--m-text-2)',
            fontSize: 10,
          },
          emphasis: { focus: 'series' },
        },
      ],
    }
  })

  const moduleChangeData = computed(() => {
    const items = (overview.module_quality || []).filter(
      (item) => item.pass_rate_delta !== null && item.pass_rate_delta !== undefined
    )
    const improved = [...items]
      .filter((item) => Number(item.pass_rate_delta) > 0)
      .sort((left, right) => Number(right.pass_rate_delta) - Number(left.pass_rate_delta))
      .slice(0, 4)
    const declined = [...items]
      .filter((item) => Number(item.pass_rate_delta) < 0)
      .sort((left, right) => Number(left.pass_rate_delta) - Number(right.pass_rate_delta))
      .slice(0, 4)
    return [...declined, ...improved].sort(
      (left, right) => Number(left.pass_rate_delta) - Number(right.pass_rate_delta)
    )
  })
  const moduleChangeSummary = computed(() => {
    const declined = moduleChangeData.value.filter((item) => Number(item.pass_rate_delta) < 0)
    const improved = moduleChangeData.value.filter((item) => Number(item.pass_rate_delta) > 0)
    return `改善 ${improved.length} 个 · 下降 ${declined.length} 个`
  })
  const moduleChangeOption = computed(() => ({
    ...chartBase,
    grid: { left: 110, right: 42, top: 16, bottom: 22, containLabel: true },
    tooltip: {
      trigger: 'item',
      confine: true,
      formatter: (params: unknown) =>
        `${chartHtml(chartPoint(params)?.name)}<br/>较上周期：${formatPercentagePoint(chartPoint(params)?.value, true)} 个百分点`,
    },
    xAxis: {
      type: 'value',
      axisLabel: {
        formatter: (value: number) => formatPercentagePoint(value),
        color: 'var(--m-muted)',
      },
      splitLine: { lineStyle: { color: 'var(--m-border)' } },
    },
    yAxis: {
      type: 'category',
      data: moduleChangeData.value.map((item) => item.module_path),
      axisLabel: {
        color: 'var(--m-text-2)',
        width: 100,
        overflow: 'truncate',
      },
    },
    series: [
      {
        name: '通过率变化',
        type: 'bar',
        barMaxWidth: 20,
        data: moduleChangeData.value.map((item) => ({
          value: normalizeChartRate(item.pass_rate_delta) ?? 0,
          itemStyle: {
            color: Number(item.pass_rate_delta || 0) >= 0 ? 'var(--m-success)' : 'var(--m-danger)',
            borderRadius: Number(item.pass_rate_delta || 0) >= 0 ? [0, 3, 3, 0] : [3, 0, 0, 3],
          },
        })),
        label: {
          show: true,
          position: 'right',
          color: 'var(--m-text-2)',
          formatter: (params: unknown) => `${formatPercentagePoint(chartPoint(params)?.value, true)} 个百分点`,
        },
      },
    ],
  }))

  const automationTypeSummary = computed(() => {
    const items = overview.automation_type_quality || []
    if (!items.length) return '暂无类型数据'
    const best = [...items].sort(
      (left, right) =>
        Number(right.final_pass_rate || 0) - Number(left.final_pass_rate || 0)
    )[0]
    return `最佳 ${best.type_name} ${formatRate(best.final_pass_rate)}`
  })
  const automationTypeOption = computed(() =>
    dimensionOption(overview.automation_type_quality || [], 'type_name')
  )
  const taskHealthRows = computed(() =>
    reportMode.value
      ? (overview.task_health || []).slice(0, 8)
      : (overview.task_health || []).slice(0, 20)
  )
  const taskHealthSummary = computed(() => {
    const abnormal = (overview.task_health || []).filter(
      (item) => Number(item.consecutive_abnormal || 0) > 0
    ).length
    return abnormal ? `${abnormal} 个任务存在连续异常` : '当前任务运行稳定'
  })
  const failedCaseRankingRows = computed(() => (overview.failed_case_ranking || []).slice(0, 30))
  const failedCaseRankingSummary = computed(() => {
    const rows = overview.failed_case_ranking || []
    if (!rows.length) return '本周期无失败用例'
    const maxFailedCount = Math.max(...rows.map((item) => Number(item.failed_count || 0)))
    return `当前展示 ${rows.length} 个去重失败 Case · 最高出现 ${maxFailedCount} 次`
  })

  const environmentQualitySummary = computed(() => {
    const rows = (overview.environment_quality || []).filter(
      (item) => item.final_pass_rate !== null && item.final_pass_rate !== undefined
    )
    if (!rows.length) return '暂无环境数据'
    const best = rows.reduce((current, item) =>
      Number(item.final_pass_rate || 0) > Number(current.final_pass_rate || 0) ? item : current
    )
    const worst = rows.reduce((current, item) =>
      Number(item.final_pass_rate || 0) < Number(current.final_pass_rate || 0) ? item : current
    )
    if (best.environment === worst.environment)
      return `${best.environment_name} ${formatRate(best.final_pass_rate)}`
    return `最佳 ${best.environment_name} ${formatRate(best.final_pass_rate)} · 风险 ${
      worst.environment_name
    } ${formatRate(worst.final_pass_rate)}`
  })
  const moduleQualitySummary = computed(() =>
    (overview.module_quality || []).reduce(
      (summary, item) => {
        summary[item.quality_level] = (summary[item.quality_level] || 0) + 1
        summary.total += 1
        return summary
      },
      { success: 0, warning: 0, danger: 0, unknown: 0, total: 0 }
    )
  )
  const moduleQualityAttentionCount = computed(
    () => moduleQualitySummary.value.danger + moduleQualitySummary.value.warning
  )
  const sortedModuleQualityData = computed(() => {
    const levelOrder: Record<string, number> = { danger: 0, warning: 1, success: 2 }
    return [...(overview.module_quality || [])].sort((left, right) => {
      const leftIssues = Number(left.failed_count || 0) + Number(left.warning_count || 0)
      const rightIssues = Number(right.failed_count || 0) + Number(right.warning_count || 0)
      return (
        (levelOrder[left.quality_level] ?? 3) - (levelOrder[right.quality_level] ?? 3) ||
        rightIssues - leftIssues ||
        Number(left.final_pass_rate ?? 100) - Number(right.final_pass_rate ?? 100) ||
        Number(right.detail_count || 0) - Number(left.detail_count || 0) ||
        String(left.module_path || '').localeCompare(String(right.module_path || ''), 'zh-CN')
      )
    })
  })
  const moduleQualityData = computed(() => {
    if (reportMode.value) return sortedModuleQualityData.value.slice(0, 8)
    return sortedModuleQualityData.value.filter((item) => {
      return (
        moduleQualityFilter.value === 'all' ||
        (moduleQualityFilter.value === 'attention'
          ? ['danger', 'warning'].includes(item.quality_level)
          : item.quality_level === moduleQualityFilter.value)
      )
    })
  })
  const moduleQualityEmptyTitle = computed(() => {
    if (!overview.module_quality?.length) return '当前范围暂无模块质量数据'
    if (moduleQualityFilter.value === 'attention') return '当前没有需关注模块'
    return `当前没有${
      moduleQualityFilter.value === 'danger'
        ? '高风险'
        : moduleQualityFilter.value === 'warning'
        ? '关注'
        : moduleQualityFilter.value === 'success'
        ? '稳定'
        : ''
    }模块`
  })
  const moduleQualityEmptyDescription = computed(() =>
    overview.module_quality?.length
      ? '可以切换质量等级查看其他模块'
      : '尚无足够的正式定时任务结果用于评估模块质量'
  )
  const benefitSceneMap = computed(() =>
    new Map(overview.benefits.scene_benefits.map(item => [item.scene, item] as const))
  )
  const benefitSceneItems = computed(() => overview.benefits.scene_benefits || [])
  const aggregateBenefitScenes = (sceneKeys: string[]) =>
    sceneKeys.reduce(
      (result, sceneKey) => {
        const scene = benefitSceneMap.value.get(sceneKey)
        result.suite_count += Number(scene?.suite_count || 0)
        result.execution_count += Number(scene?.execution_count || 0)
        result.unique_case_count += Number(scene?.unique_case_count || 0)
        result.abnormal_count += Number(scene?.abnormal_count || 0)
        result.active_day_count = Math.max(
          result.active_day_count,
          Number(scene?.active_day_count || 0)
        )
        return result
      },
      {
        suite_count: 0,
        execution_count: 0,
        unique_case_count: 0,
        abnormal_count: 0,
        active_day_count: 0,
      }
    )
  const primaryBenefitItems = computed(() => {
    const regression = aggregateBenefitScenes(['routine_regression', 'production_regression'])
    const inspection = aggregateBenefitScenes(['production_inspection'])
    return [
      {
        key: 'regression',
        label: '回归替代价值',
        badge: `${regression.unique_case_count || 0} 个用例`,
        value: `${regression.suite_count || 0} 轮回归`,
        description: `累计完成 ${regression.execution_count || 0} 次自动校验`,
        meaning: '替代重复人工验证，缩短版本回归反馈周期',
      },
      {
        key: 'inspection',
        label: '持续巡检价值',
        badge: `${inspection.active_day_count || 0} 个活跃日`,
        value: `${inspection.suite_count || 0} 次巡检`,
        description: `完成 ${inspection.execution_count || 0} 次校验，识别 ${
          inspection.abnormal_count || 0
        } 次异常信号`,
        meaning: '持续守护测试对象，帮助团队更早发现异常',
      },
    ]
  })
  const benefitItems = computed(() => [
    {
      label: '覆盖规模',
      value: `${overview.benefits.unique_case_count || 0} 个用例`,
      description: `${overview.benefits.module_count || 0} 个模块 · ${
        overview.benefits.environment_count || 0
      } 个环境`,
    },
    {
      label: '异常发现',
      value: `${overview.benefits.abnormal_result_count || 0} 次信号`,
      description: `涉及 ${overview.benefits.affected_case_count || 0} 个用例`,
    },
    {
      label: '首轮结果反馈时效',
      value: formatDuration(
        overview.benefits.p95_first_feedback_seconds ?? overview.benefits.p95_feedback_seconds
      ),
      description: `P95 首轮产出耗时 · ${overview.benefits.feedback_sample_count || 0}/${
        overview.benefits.feedback_report_count || 0
      } 份完整报告`,
    },
    {
      label: '质量恢复',
      value: `${overview.benefits.retry_recovered_count || 0} 个用例`,
      description: `另有 ${overview.benefits.period_recovered_case_count || 0} 个周期恢复`,
    },
  ])
  const reportOutputItems = computed(() => [
    ...primaryBenefitItems.value.map(item => ({
      label: item.key === 'regression' ? '回归轮次' : '巡检次数',
      value: item.value,
      description: item.description,
    })),
    ...benefitItems.value,
  ])
  let pendingOverview: { key: string; sequence: number; promise: Promise<void> } | null = null
  function clearOverview() {
    Object.assign(overview, createEmptyOverview())
    overviewEvidence.value = null
    generatedAt.value = ''
    overviewReady.value = false
  }
  function invalidateReads(clear = false) {
    overviewRequestSequence++
    pageContextVersion.value++
    needsLoad = true
    loading.value = false
    overviewReady.value = false
    loadError.value = ''
    failureReportDrawer.visible = false
    diagnosticDrawer.visible = false
    filterVisible.value = false
    if (clear) clearOverview()
  }
  function loadData(): Promise<void> {
    if (!pageAvailable()) { needsLoad = true; return Promise.resolve() }
    if (!initialized) return initializePage()
    const params = effectivenessQuery(filters)
    const key = JSON.stringify(params)
    if (pendingOverview?.key === key && pendingOverview.sequence === overviewRequestSequence) return pendingOverview.promise
    const requestSequence = ++overviewRequestSequence
    pageContextVersion.value++
    const current = () => pageAvailable() && requestSequence === overviewRequestSequence
    clearOverview()
    loadError.value = ''
    loading.value = true
    needsLoad = false
    const promise = Promise.resolve().then(async () => {
      try {
        if (!current()) return
        const response: unknown = await getAutomationEffectivenessOverview(params, true)
        if (!current()) return
        const evidence = effectivenessPayload(response)
        Object.assign(overview, normalizeEffectivenessOverview(evidence))
        overviewEvidence.value = evidence
        generatedAt.value = new Date().toLocaleString('zh-CN', { hour12: false })
        overviewReady.value = true
      } catch (loadFailure0) {
        if (current()) { clearOverview(); (reportLoadError(loadFailure0, "加载失败，请重试", false), loadError.value = '获取自动化效能数据失败，请重试'); needsLoad = true }
      } finally {
        if (current()) {
          loading.value = false
          if (overviewReady.value) void loadAiSummary()
        }
        if (pendingOverview?.promise === promise) pendingOverview = null
      }
    })
    pendingOverview = { key, sequence: requestSequence, promise }
    return promise
  }
  function resetFilters() {
    Object.assign(draftFilters, createDefaultFilters())
  }

  function onPeriodPresetChange(value?: PeriodPreset) {
    draftFilters.dateRange = resolvePeriodDateRange(value || defaultPeriodPreset)
  }

  function syncDraftFilters() {
    Object.assign(draftFilters, copyEffectivenessFilters(filters))
  }

  async function applyFilters() {
    Object.assign(filters, copyEffectivenessFilters(draftFilters))
    projectStore.setProjectProductNavigationSelection(selectedProjectProductId.value)
    filterVisible.value = false
    await loadData()
  }

  function visibleProjectProductIds() {
    return (projectStore.projectProduct || []).flatMap((project) =>
      (project.children || [])
        .map((product) => product.value)
        .filter(value => value !== null && value !== undefined && value !== '')
    )
  }

  function normalizeVisibleProjectProductId(value: unknown) {
    const productIds = visibleProjectProductIds()
    return productIds.find((productId) => String(productId) === String(value))
  }

  function initializeProjectProductFilter() {
    const cachedProduct = projectStore.projectProductNavigationSelection.projectProduct
    filters.project_product = normalizeVisibleProjectProductId(cachedProduct)
    draftFilters.project_product = filters.project_product
  }

  watch(
    () => projectStore.projectProductNavigationSelection.projectProduct,
    (projectProduct) => {
      const normalizedProduct = normalizeVisibleProjectProductId(projectProduct)
      const currentProduct = selectedProjectProductId.value
      const hasNormalizedProduct = normalizedProduct !== null && normalizedProduct !== undefined
      const hasCurrentProduct = currentProduct !== null && currentProduct !== undefined
      if (
        (!hasNormalizedProduct && !hasCurrentProduct) ||
        (hasNormalizedProduct &&
          hasCurrentProduct &&
          String(normalizedProduct) === String(currentProduct))
      )
        return
      filters.project_product = normalizedProduct
      draftFilters.project_product = normalizedProduct
      if (initialized) void loadData()
    }
  )
  function formatRate(value: number | null | undefined) {
    return formatChartRate(value)
  }
  function formatCount(value: unknown) {
    return (effectivenessNumber(value) ?? 0).toLocaleString('zh-CN')
  }
  function formatDuration(value: number | null | undefined) {
    if (value === null || value === undefined) return '-'
    const seconds = Number(value)
    if (seconds < 60) return `${seconds.toFixed(1)} 秒`
    if (seconds < 3600) return `${(seconds / 60).toFixed(1)} 分钟`
    return `${(seconds / 3600).toFixed(1)} 小时`
  }
  function comparisonText(value: number | null | undefined, unit: string, positiveGood: boolean) {
    if (value === null || value === undefined) return '暂无上周期数据'
    if (Math.abs(Number(value)) < 0.01) return '与上周期持平'
    const positive = Number(value) > 0
    const verb = positive ? (positiveGood ? '提升' : '增加') : positiveGood ? '下降' : '减少'
    const normalizedUnit = unit.trim()
    return `较上周期${verb} ${Math.abs(Number(value)).toFixed(1)}${
      normalizedUnit ? ` ${normalizedUnit}` : ''
    }`
  }
  function issueComparisonText(
    currentValue: number | null | undefined,
    deltaValue: number | null | undefined
  ) {
    if (deltaValue === null || deltaValue === undefined) return '暂无上周期异常结果数据'
    const current = Number(currentValue || 0)
    const delta = Number(deltaValue)
    const previous = Math.max(current - delta, 0)
    if (Math.abs(delta) < 0.01) return `上周期 ${formatCount(previous)} 次，与上周期持平`
    return `上周期 ${formatCount(previous)} 次，净${delta > 0 ? '增加' : '减少'} ${formatCount(
      Math.abs(delta)
    )} 次`
  }
  function rateComparisonText(
    value: number | null | undefined,
    metricLabel: string,
    positiveGood: boolean
  ) {
    if (value === null || value === undefined) return `${metricLabel}暂无上周期数据`
    if (Number(Math.abs(Number(value)).toFixed(1)) === 0) return `${metricLabel}与上周期基本持平`
    const positive = Number(value) > 0
    const verb = positive ? (positiveGood ? '提升' : '上升') : '下降'
    return `${metricLabel}较上周期${verb} ${Math.abs(Number(value)).toFixed(1)} 个百分点`
  }
  function deltaClass(value: number | null | undefined) {
    if (value === null || value === undefined || Math.abs(Number(value)) < 0.01)
      return 'mango-effectiveness-muted'
    return Number(value) > 0
      ? 'mango-effectiveness-comparison-positive'
      : 'mango-effectiveness-comparison-negative'
  }
  function comparisonClass(value: number | null | undefined, positiveGood: boolean) {
    if (value === null || value === undefined || Number(Math.abs(Number(value)).toFixed(1)) === 0)
      return 'mango-effectiveness-muted'
    const improved = positiveGood ? Number(value) > 0 : Number(value) < 0
    return improved
      ? 'mango-effectiveness-comparison-positive'
      : 'mango-effectiveness-comparison-negative'
  }
  function rateClass(value: number | null | undefined) {
    if (value === null || value === undefined) return 'mango-effectiveness-muted'
    if (Number(value) >= effectivenessQualityThresholds.healthyPassRate)
      return 'mango-effectiveness-state-success'
    if (Number(value) < effectivenessQualityThresholds.highRiskPassRate)
      return 'mango-effectiveness-state-danger'
    return 'mango-effectiveness-warning'
  }
  function priorityLabel(value: string) {
    const labels: Record<string, string> = {
      high: '高优先级',
      medium: '中优先级',
      low: '低优先级',
    }
    return labels[value] || '待评估'
  }
  function currentReportQuery(): LocationQueryRaw {
    const params = effectivenessQuery(filters)
    const query: LocationQueryRaw = {}
    if (params.start_date) query.start_date = params.start_date
    if (params.end_date) query.end_date = params.end_date
    if (params.project_product_id !== undefined) query.project_product = params.project_product_id
    if (params.test_env) query.test_env = params.test_env
    if (params.execution_scene) query.execution_scene = params.execution_scene
    if (params.execution_scope) query.execution_scope = params.execution_scope
    return query
  }
  function openReportList(extra: LocationQueryRaw = {}) {
    if (!pageAvailable()) return
    return router.push({ path: '/report/index', query: { ...currentReportQuery(), ...extra } })
  }
  function openTaskDiagnostic(item: EffectivenessTask) {
    if (!pageAvailable() || item.task_id === null) return
    diagnosticDrawer.targetId = item.task_id
    diagnosticDrawer.documentAvailable = Boolean(item.diagnostic_file_path)
    diagnosticDrawer.title = `${item.task_name || '定时任务'} · 排查结果`
    diagnosticDrawer.visible = true
  }
  function openFailedCaseReport(item: EffectivenessFailedCase) {
    if (!pageAvailable()) return
    if (item.latest_failed_detail_id === null || item.case_id === null || ![0, 1, 2].includes(item.case_type ?? -1)) {
      Message.error('当前失败用例缺少报告明细 ID，无法查看最近结果')
      return
    }
    failureReportDrawer.testSuiteDetailId = item.latest_failed_detail_id
    failureReportDrawer.caseType = item.case_type ?? -1
    failureReportDrawer.caseId = item.case_id
    failureReportDrawer.caseName = item.case_name || `Case #${item.case_id}`
    failureReportDrawer.fallbackError = item.latest_error
    failureReportDrawer.visible = true
  }
  function onPeriodQualityClick(item: { start?: string; end?: string }) {
    const start = effectivenessDate(item.start), end = effectivenessDate(item.end)
    if (start && end) return openReportList({ start_date: start, end_date: end })
  }
  function onTrendChartClick(params: unknown) {
    const index = effectivenessChartIndex(params)
    if (index === null) return
    const date = effectivenessDate(overview.trend[index]?.date_value)
    if (date) return openReportList({ start_date: date, end_date: date })
  }
  function onEnvironmentChartClick(params: unknown) {
    const index = effectivenessChartIndex(params), item = index === null ? null : overview.environment_quality[index]
    if (item && item.environment !== null) return openReportList({ test_env: item.environment })
  }
  function onSceneChartClick(params: unknown) {
    const index = effectivenessChartIndex(params), item = index === null ? null : overview.scene_distribution[index]
    if (item?.scene) return openReportList({ execution_scene: item.scene })
  }
  function onScopeChartClick(params: unknown) {
    const index = effectivenessChartIndex(params), item = index === null ? null : overview.scope_distribution[index]
    if (item?.scope) return openReportList({ execution_scope: item.scope })
  }
  function onModuleRiskClick(params: unknown) {
    const index = effectivenessChartIndex(params), item = index === null ? null : moduleRiskData.value[index]
    if (item && item.module_id !== null) return openReportList({ module: item.module_id })
  }
  function onIssueParetoClick(params: unknown) {
    const index = effectivenessChartIndex(params), item = index === null ? null : issueParetoData.value[index]
    if (item && item.module_id !== null) return openReportList({ module: item.module_id })
  }
  function onModuleChangeClick(params: unknown) {
    const index = effectivenessChartIndex(params), item = index === null ? null : moduleChangeData.value[index]
    if (item && item.module_id !== null) return openReportList({ module: item.module_id })
  }
  function onSceneMatrixClick(params: unknown) {
    const data = effectivenessObject(effectivenessObject(params)?.data)
    const sceneIndex = effectivenessChartIndex({ dataIndex: data?.sceneIndex })
    const environmentIndex = effectivenessChartIndex({ dataIndex: data?.environmentIndex })
    if (sceneIndex === null || environmentIndex === null) return
    const scene = overview.scene_matrix.scenes[sceneIndex], environment = overview.scene_matrix.environments[environmentIndex]
    if (scene && environment) return openReportList({ execution_scene: scene.key, test_env: environment.key })
  }
  function taskHealthClass(item: EffectivenessTask) {
    if (item.consecutive_abnormal >= 2 || (item.final_pass_rate !== null && item.final_pass_rate < 70))
      return 'is-danger'
    if (item.consecutive_abnormal > 0 || (item.final_pass_rate !== null && item.final_pass_rate < 90))
      return 'is-warning'
    return item.final_pass_rate === null ? 'is-neutral' : 'is-success'
  }
  function openAiSettings() {
    router.push('/system/settings/index')
  }
  function onFilterPopoverVisibleChange(visible: boolean) {
    const nextVisible = visible && !reportMode.value && !printing.value
    if (nextVisible && !filterVisible.value) syncDraftFilters()
    filterVisible.value = nextVisible
  }
  async function toggleReportMode() {
    if (!pageAvailable() || printing.value || imageExporting.value) return
    const context = pageContextVersion.value
    reportMode.value = !reportMode.value
    if (reportMode.value) filterVisible.value = false
    await nextTick()
    if (pageAvailable() && context === pageContextVersion.value) window.dispatchEvent(new Event('resize'))
  }
  async function clearEffectivenessCache() {
    if (cacheClearing.value || !pageAvailable()) return
    const context = pageContextVersion.value
    cacheClearing.value = true
    try {
      const res = await postAutomationEffectivenessCacheClear()
      if (!pageAvailable() || context !== pageContextVersion.value) return
      if (res.code !== 200) throw new Error('清除缓存失败')
      Message.success(res.msg)
      await loadData()
    } catch {
      if (pageAvailable() && context === pageContextVersion.value) Message.error('清除统计缓存失败，请重试')
    } finally {
      cacheClearing.value = false
    }
  }
  const { printReport, downloadReportImage } = useEffectivenessExport({
    contextKey: () => JSON.stringify([pageContextVersion.value, reportMode.value, moduleQualityFilter.value]),
    available: () => pageAvailable() && overviewReady.value,
    loading: () => reportContentLoading.value,
    title: () => reportDocumentTitle.value,
    printing, imageExporting, reportMode, filterVisible,
  })
  let initialization: { version: number; promise: Promise<void> } | null = null
  function initializePage(): Promise<void> {
    if (!pageAvailable()) return Promise.resolve()
    if (initialization?.version === pageContextVersion.value) return initialization.promise
    const version = pageContextVersion.value
    const current = () => pageAvailable() && version === pageContextVersion.value
    loading.value = true
    loadError.value = ''
    const promise = Promise.resolve().then(async () => {
      try {
        if (!current()) return
        await Promise.all([enumStore.getEnum(), projectStore.projectProductName()])
        if (!current()) return
        if (projectStore.optionErrors.products) throw new Error('项目产品加载失败')
        initializeProjectProductFilter()
        initialized = true
        await loadData()
      } catch (loadFailure1) {
        if (current()) { loading.value = false; needsLoad = true; (reportLoadError(loadFailure1, "质量效能选项加载失败，请重试", false), loadError.value = '质量效能选项加载失败，请重试') }
      } finally {
        if (initialization?.promise === promise) initialization = null
      }
    })
    initialization = { version, promise }
    return promise
  }
  function visibilityChanged() {
    if (!pageAvailable()) invalidateReads()
    else if (needsLoad) void loadData()
  }
  watch([
    () => route.fullPath, () => userStore.userId, () => userStore.roleId,
    () => userStore.token, () => userStore.selected_environment,
  ], () => {
    initialized = false
    invalidateReads(true)
    filters.project_product = undefined
    syncDraftFilters()
    if (pageAvailable()) void initializePage()
  }, { flush: 'sync' })
  onMounted(() => {
    mounted = true
    document.addEventListener('visibilitychange', visibilityChanged)
    void initializePage()
  })
  onDeactivated(() => { active = false; invalidateReads() })
  onActivated(() => {
    const wasInactive = !active
    active = true
    if (wasInactive && needsLoad) void loadData()
  })
  onBeforeUnmount(() => {
    disposed = true
    invalidateReads(true)
    document.removeEventListener('visibilitychange', visibilityChanged)
  })
</script>

<style scoped>
  .mango-effectiveness-page {
    background: var(--m-bg);
  }

  .mango-effectiveness-page :deep(.mango-table-body__content) {
    display: flex;
    flex-direction: column;
    gap: var(--m-page-gap);
    padding-top: var(--m-page-gap);
    background: var(--m-bg);
  }

  .mango-effectiveness-page :deep(.mango-table-header) {
    z-index: 1;
  }

  .mango-effectiveness-page :deep(.mango-table-header .arco-card-header) {
    height: auto;
    min-height: 42px;
    align-items: center;
  }

  .mango-effectiveness-page :deep(.mango-table-header .arco-card-header-extra) {
    min-width: 0;
    margin-left: 16px;
  }

  .mango-effectiveness-page :deep(.mango-table-header__extra) {
    flex-wrap: wrap;
    row-gap: 6px;
  }

  .mango-effectiveness-export-button-wrap {
    display: inline-flex;
  }

  .mango-effectiveness-page .mango-section-card + .mango-section-card {
    margin-top: 0;
  }

  .mango-effectiveness-report-document,
  .mango-effectiveness-paper-page {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: var(--m-page-gap);
  }

  .mango-effectiveness-paper-page--summary {
    order: 1;
  }

  .mango-effectiveness-paper-page--period {
    order: 2;
  }

  .mango-effectiveness-paper-page--modules {
    order: 3;
  }

  .mango-effectiveness-paper-page--convergence {
    order: 4;
  }

  .mango-effectiveness-paper-page--diagnostics {
    order: 5;
  }

  .mango-effectiveness-paper-page--operations {
    order: 6;
  }

  .mango-effectiveness-paper-page--ai {
    order: 7;
  }

  .mango-effectiveness-paper-page > * {
    min-width: 0;
  }

  .mango-effectiveness-paper-page__number {
    display: none;
  }

  .mango-effectiveness-chapter-heading {
    display: grid;
    min-height: 44px;
    grid-template-columns: 32px minmax(0, 1fr) auto;
    margin: 0;
    padding: 0 2px 7px;
    align-items: center;
    gap: 10px;
    border-bottom: 1px solid var(--m-border);
  }

  .mango-effectiveness-chapter-heading > span {
    display: inline-flex;
    width: 30px;
    height: 30px;
    align-items: center;
    justify-content: center;
    border-radius: var(--m-radius-md);
    background: color-mix(in srgb, var(--m-primary) 10%, var(--m-surface));
    color: var(--m-primary);
    font-size: 12px;
    font-variant-numeric: tabular-nums;
    font-weight: 650;
  }

  .mango-effectiveness-chapter-heading > div {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 1px;
  }

  .mango-effectiveness-chapter-heading strong {
    color: var(--m-text);
    font-size: 15px;
    line-height: 21px;
  }

  .mango-effectiveness-chapter-heading small {
    overflow: hidden;
    color: var(--m-muted);
    font-size: 11px;
    line-height: 17px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-effectiveness-chapter-heading em {
    color: var(--m-muted);
    font-size: 9px;
    font-style: normal;
    font-weight: 600;
    letter-spacing: 0.8px;
    white-space: nowrap;
  }

  .mango-effectiveness-grid--health {
    margin-top: 0;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    align-items: stretch;
  }

  .mango-effectiveness-task-health,
  .mango-effectiveness-case-health {
    min-width: 0;
  }

  .mango-effectiveness-task-health__list,
  .mango-effectiveness-case-health__list {
    display: grid;
    max-height: clamp(320px, 46vh, 520px);
    padding: 0 12px 12px;
    align-content: start;
    gap: 8px;
    grid-auto-rows: max-content;
    overflow-x: hidden;
    overflow-y: auto;
    overscroll-behavior: contain;
    scrollbar-gutter: stable;
  }

  .mango-effectiveness-task-health__list:focus-visible,
  .mango-effectiveness-case-health__list:focus-visible {
    outline: 2px solid var(--m-primary);
    outline-offset: -2px;
  }

  .mango-effectiveness-task-health__list article,
  .mango-effectiveness-case-health__list article {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    grid-template-rows: repeat(3, max-content);
    align-items: start;
    align-content: start;
    gap: 6px 10px;
    height: auto;
    min-height: 82px;
    padding: 9px 10px;
    border: 1px solid var(--m-border);
    border-left: 3px solid var(--m-success);
    border-radius: var(--m-radius-sm);
    background: var(--m-surface);
  }

  .mango-effectiveness-case-health__list article {
    border-left-color: var(--m-danger);
  }

  .mango-effectiveness-task-health__list article.is-warning {
    border-left-color: var(--m-warning);
  }

  .mango-effectiveness-task-health__list article.is-danger {
    border-left-color: var(--m-danger);
  }

  .mango-effectiveness-health-row__main {
    display: flex;
    min-width: 0;
    flex-direction: column;
  }

  .mango-effectiveness-health-row__actions {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 2px;
  }

  .mango-effectiveness-health-row__main strong,
  .mango-effectiveness-health-row__main small {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-effectiveness-health-row__main small,
  .mango-effectiveness-health-row__metrics,
  .mango-effectiveness-case-health__error {
    color: var(--m-muted);
  }

  .mango-effectiveness-health-row__metrics {
    display: flex;
    min-width: 0;
    grid-column: 1 / -1;
    flex-wrap: wrap;
    gap: 4px 12px;
    font-size: 11px;
  }

  .mango-effectiveness-case-health__error {
    display: -webkit-box;
    overflow: hidden;
    min-width: 0;
    grid-column: 1 / -1;
    padding: 6px 8px;
    border-radius: var(--m-radius-sm);
    background: color-mix(in srgb, var(--m-danger) 6%, var(--m-surface));
    font-size: 11px;
    line-height: 17px;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
  }

  .mango-effectiveness-case-health__error strong {
    margin-right: 6px;
    color: var(--m-danger);
    font-weight: 600;
  }

  .mango-effectiveness-case-health__error.is-empty {
    background: var(--m-surface-soft);
  }

  .mango-effectiveness-case-health__error.is-empty strong {
    color: var(--m-muted);
  }

  .mango-tone-danger {
    color: var(--m-danger);
  }

  .is-report-mode .mango-effectiveness-task-health__list article,
  .is-report-mode .mango-effectiveness-case-health__list article {
    min-height: 0;
    padding: 5px 7px;
    font-size: 10px;
  }

  .is-report-mode .mango-effectiveness-task-health__list,
  .is-report-mode .mango-effectiveness-case-health__list {
    min-height: 0;
    flex: 1 1 auto;
    max-height: none;
    overflow: visible;
    scrollbar-gutter: auto;
  }

  .is-report-mode .mango-effectiveness-grid--health {
    align-items: start;
  }

  .is-report-mode .mango-effectiveness-grid--health > .mango-effectiveness-panel {
    height: auto;
    max-height: none;
    box-sizing: border-box;
    overflow: visible;
  }

  .is-report-mode .mango-effectiveness-task-health__list article .arco-btn,
  .is-report-mode .mango-effectiveness-case-health__list article .arco-btn {
    display: none;
  }

  .mango-effectiveness-report-header {
    position: relative;
    display: grid;
    overflow: hidden;
    grid-template-columns: minmax(0, 1fr) minmax(250px, 300px);
    grid-template-areas: 'main verdict' 'meta verdict';
    column-gap: 32px;
    padding: 20px 22px 0;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-lg);
    background: linear-gradient(
        135deg,
        color-mix(in srgb, var(--m-primary) 8%, var(--m-surface)) 0%,
        var(--m-surface) 52%
      ),
      var(--m-surface);
    box-shadow: var(--m-shadow);
  }

  .mango-effectiveness-report-header::before {
    position: absolute;
    top: 0;
    left: 0;
    width: 4px;
    height: 100%;
    content: '';
    background: var(--m-primary);
  }

  .mango-effectiveness-report-header__main {
    grid-area: main;
    min-width: 0;
    padding-bottom: 18px;
  }

  .mango-effectiveness-eyebrow {
    display: flex;
    align-items: center;
    gap: 7px;
    color: var(--m-primary);
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1.4px;
  }

  .mango-effectiveness-eyebrow svg {
    font-size: 16px;
  }

  .mango-effectiveness-report-header h1 {
    margin: 7px 0 4px;
    color: var(--m-text);
    font-size: 25px;
    font-weight: 650;
    line-height: 34px;
  }

  .mango-effectiveness-report-header p {
    margin: 0;
    color: var(--m-text-2);
    font-size: 13px;
    line-height: 20px;
  }

  .mango-effectiveness-scope {
    display: flex;
    margin-top: 12px;
    flex-wrap: wrap;
    gap: 6px;
  }

  .mango-effectiveness-scope span {
    max-width: 260px;
    overflow: hidden;
    padding: 3px 9px;
    border: 1px solid color-mix(in srgb, var(--m-primary) 16%, var(--m-border));
    border-radius: var(--m-radius-pill);
    background: color-mix(in srgb, var(--m-primary) 5%, var(--m-surface));
    color: var(--m-text-2);
    font-size: 12px;
    line-height: 18px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-effectiveness-verdict {
    display: flex;
    align-self: stretch;
    grid-area: verdict;
    min-width: 0;
    margin-bottom: 20px;
    padding: 14px;
    flex-direction: column;
    justify-content: center;
    gap: 5px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-lg);
    background: color-mix(in srgb, var(--m-primary) 5%, var(--m-surface));
  }

  .mango-effectiveness-verdict > span {
    color: var(--m-muted);
    font-size: 12px;
  }

  .mango-effectiveness-verdict > strong {
    color: var(--m-text);
    font-size: 22px;
    font-weight: 650;
    line-height: 30px;
  }

  .mango-effectiveness-verdict > p {
    width: fit-content;
    padding: 2px 7px;
    border-radius: var(--m-radius-pill);
    background: var(--m-surface-soft);
    color: var(--m-muted);
    font-size: 11px;
    line-height: 18px;
  }

  .mango-effectiveness-verdict > p.is-danger {
    background: color-mix(in srgb, var(--m-danger) 10%, var(--m-surface));
    color: var(--m-danger);
  }

  .mango-effectiveness-verdict > p.is-warning {
    background: color-mix(in srgb, var(--m-warning) 10%, var(--m-surface));
    color: var(--m-warning);
  }

  .mango-effectiveness-verdict > p.is-success {
    background: color-mix(in srgb, var(--m-success) 10%, var(--m-surface));
    color: var(--m-success);
  }

  .mango-effectiveness-verdict > div {
    display: flex;
    flex-wrap: wrap;
    gap: 4px 12px;
    color: var(--m-muted);
    font-size: 11px;
  }

  .mango-effectiveness-verdict.is-red {
    border-color: color-mix(in srgb, var(--m-danger) 30%, var(--m-border));
    background: color-mix(in srgb, var(--m-danger) 7%, var(--m-surface));
  }

  .mango-effectiveness-verdict.is-red > strong {
    color: var(--m-danger);
  }

  .mango-effectiveness-verdict.is-orange {
    border-color: color-mix(in srgb, var(--m-warning) 32%, var(--m-border));
    background: color-mix(in srgb, var(--m-warning) 8%, var(--m-surface));
  }

  .mango-effectiveness-verdict.is-orange > strong {
    color: var(--m-warning);
  }

  .mango-effectiveness-verdict.is-green {
    border-color: color-mix(in srgb, var(--m-success) 28%, var(--m-border));
    background: color-mix(in srgb, var(--m-success) 7%, var(--m-surface));
  }

  .mango-effectiveness-verdict.is-green > strong {
    color: var(--m-success);
  }

  .mango-effectiveness-report-header__meta {
    display: flex;
    grid-area: meta;
    min-width: 0;
    padding: 9px 0 10px;
    align-items: center;
    flex-wrap: wrap;
    gap: 6px 20px;
    color: var(--m-muted);
    font-size: 11px;
  }

  .mango-effectiveness-report-header__meta span:first-child {
    display: inline-flex;
    align-items: center;
    gap: 5px;
  }

  .mango-effectiveness-filter-popover {
    display: grid;
    width: min(720px, calc(100vw - 48px));
    gap: 12px;
    padding: 2px;
  }

  .mango-effectiveness-filter__heading {
    display: flex;
    min-width: 0;
    align-items: center;
    gap: 12px;
  }

  .mango-effectiveness-filter__heading > div {
    display: flex;
    align-items: center;
    gap: 6px;
    color: var(--m-text);
  }

  .mango-effectiveness-filter__heading > span {
    overflow: hidden;
    color: var(--m-muted);
    font-size: 12px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-effectiveness-filter__fields {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px 16px;
  }

  .mango-effectiveness-filter__field {
    display: grid;
    min-width: 0;
    gap: 5px;
  }

  .mango-effectiveness-filter__field > span {
    color: var(--m-text-2);
    font-size: 12px;
    font-weight: 500;
    line-height: 18px;
  }

  .mango-effectiveness-filter__field :deep(.arco-picker),
  .mango-effectiveness-filter__field :deep(.arco-select),
  .mango-effectiveness-filter__field :deep(.arco-cascader) {
    width: 100%;
  }

  .mango-effectiveness-filter__actions {
    display: flex;
    padding-top: 10px;
    justify-content: flex-end;
    gap: 8px;
    border-top: 1px solid var(--m-border);
  }

  .mango-effectiveness-insight-panel {
    display: grid;
    position: relative;
    overflow: hidden;
    padding: 12px;
    gap: 10px;
    border-left: 3px solid var(--m-primary);
    background: color-mix(in srgb, var(--m-primary) 3%, var(--m-surface));
  }

  .mango-effectiveness-insight-summary {
    display: flex;
    min-width: 0;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
  }

  .mango-effectiveness-insight-summary__content {
    display: grid;
    min-width: 0;
    grid-template-columns: auto minmax(0, 1fr);
    align-items: baseline;
    column-gap: 10px;
    row-gap: 2px;
  }

  .mango-effectiveness-insight-summary__eyebrow {
    display: inline-flex;
    grid-row: 1 / span 2;
    padding: 3px 7px;
    align-items: center;
    align-self: center;
    gap: 4px;
    border-radius: var(--m-radius-sm);
    background: color-mix(in srgb, var(--m-primary) 10%, var(--m-surface));
    color: var(--m-primary);
    font-size: 11px;
    font-weight: 600;
    white-space: nowrap;
  }

  .mango-effectiveness-insight-summary strong {
    color: var(--m-text);
    font-size: 14px;
    line-height: 20px;
  }

  .mango-effectiveness-insight-summary small {
    color: var(--m-muted);
    font-size: 11px;
    line-height: 18px;
  }

  .mango-effectiveness-insight-summary__count {
    flex: 0 0 auto;
    padding: 2px 8px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-pill);
    background: var(--m-surface);
    color: var(--m-text-2);
    font-size: 11px;
    font-variant-numeric: tabular-nums;
  }

  .mango-effectiveness-insights {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: var(--m-page-gap);
  }

  .mango-effectiveness-insight {
    display: grid;
    min-height: 70px;
    grid-template-columns: 3px minmax(0, 1fr);
    gap: 10px;
    padding: 11px 12px;
    background: var(--m-surface);
  }

  .mango-effectiveness-insight__marker {
    border-radius: var(--m-radius-pill);
    background: var(--m-primary);
  }

  .mango-effectiveness-insight.is-danger .mango-effectiveness-insight__marker {
    background: var(--m-danger);
  }

  .mango-effectiveness-insight.is-warning .mango-effectiveness-insight__marker {
    background: var(--m-warning);
  }

  .mango-effectiveness-insight.is-success .mango-effectiveness-insight__marker {
    background: var(--m-success);
  }

  .mango-effectiveness-insight strong {
    color: var(--m-text);
    font-size: 13px;
  }

  .mango-effectiveness-insight p {
    margin: 3px 0 0;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 18px;
  }

  .mango-effectiveness-cards {
    display: grid;
    grid-template-columns: repeat(6, minmax(0, 1fr));
    gap: var(--m-page-gap);
    transition: opacity var(--m-motion-duration-fast);
  }

  .mango-effectiveness-cards__ai {
    grid-column: 1 / -1;
  }

  .mango-effectiveness-cards.is-loading {
    opacity: 0.6;
  }

  .mango-effectiveness-card {
    position: relative;
    display: flex;
    overflow: hidden;
    min-height: 112px;
    padding: 13px 14px 11px;
    flex-direction: column;
    justify-content: space-between;
    gap: 6px;
  }

  .mango-effectiveness-overview-card {
    transition: border-color var(--m-motion-duration-fast), box-shadow var(--m-motion-duration-fast);
  }

  .mango-effectiveness-card::before {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 3px;
    content: '';
    background: var(--m-muted);
  }

  .mango-effectiveness-overview-card:hover {
    border-color: color-mix(in srgb, var(--m-primary) 28%, var(--m-border));
    box-shadow: 0 8px 18px color-mix(in srgb, var(--m-text) 10%, transparent);
  }

  .mango-effectiveness-card__title {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .mango-effectiveness-card__title > span {
    color: var(--m-text-2);
    font-size: 12px;
    font-weight: 500;
  }

  .mango-effectiveness-card__title small {
    padding: 1px 6px;
    border-radius: var(--m-radius-pill);
    background: var(--m-surface-soft);
    color: var(--m-muted);
    font-size: 10px;
    white-space: nowrap;
  }

  .mango-effectiveness-card.is-danger .mango-effectiveness-card__title small {
    background: color-mix(in srgb, var(--m-danger) 9%, var(--m-surface));
    color: var(--m-danger);
  }

  .mango-effectiveness-card.is-warning .mango-effectiveness-card__title small {
    background: color-mix(in srgb, var(--m-warning) 10%, var(--m-surface));
    color: var(--m-warning);
  }

  .mango-effectiveness-card.is-success .mango-effectiveness-card__title small {
    background: color-mix(in srgb, var(--m-success) 9%, var(--m-surface));
    color: var(--m-success);
  }

  .mango-effectiveness-card > strong {
    overflow: hidden;
    color: var(--m-text);
    font-size: 26px;
    font-variant-numeric: tabular-nums;
    font-weight: 650;
    line-height: 34px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-effectiveness-card__comparison {
    overflow: hidden;
    color: var(--m-text-2);
    font-size: 11px;
    line-height: 18px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-effectiveness-card.is-danger::before {
    background: var(--m-danger);
  }
  .mango-effectiveness-card.is-warning::before {
    background: var(--m-warning);
  }
  .mango-effectiveness-card.is-success::before {
    background: var(--m-success);
  }

  .mango-effectiveness-card.is-neutral::before {
    background: var(--m-muted);
  }

  .mango-effectiveness-card__footer {
    display: grid;
    grid-template-columns: 14px minmax(0, 1fr);
    align-items: center;
    gap: 6px;
  }

  .mango-effectiveness-card__footer > span {
    height: 3px;
    border-radius: var(--m-radius-pill);
    background: var(--m-muted);
  }

  .mango-effectiveness-card__footer small {
    overflow: hidden;
    color: var(--m-muted);
    font-size: 11px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-effectiveness-source-card__trigger {
    position: absolute;
    z-index: 2;
    inset: 0;
    width: 100%;
    padding: 0;
    border: 0;
    border-radius: inherit;
    background: transparent;
    cursor: pointer;
  }

  .mango-effectiveness-source-card__trigger:focus-visible {
    outline: 2px solid var(--m-primary);
    outline-offset: -3px;
  }

  .mango-effectiveness-source-popover {
    width: min(760px, calc(100vw - 64px));
    padding: 12px;
  }

  .mango-effectiveness-source-popover > header {
    display: flex;
    padding: 0 2px 10px;
    align-items: flex-end;
    justify-content: space-between;
    gap: 16px;
  }

  .mango-effectiveness-source-popover > header > div {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .mango-effectiveness-source-popover > header strong {
    color: var(--m-text);
    font-size: 14px;
  }

  .mango-effectiveness-source-popover > header small,
  .mango-effectiveness-source-popover > header > span {
    color: var(--m-muted);
    font-size: 11px;
  }

  .mango-effectiveness-source-popover__table-wrap {
    overflow: auto;
    max-height: min(420px, 60vh);
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-sm);
    scrollbar-gutter: stable;
  }

  .mango-effectiveness-source-popover table {
    width: 100%;
    min-width: 640px;
    border-collapse: separate;
    border-spacing: 0;
    color: var(--m-text-2);
    font-size: 12px;
    table-layout: fixed;
  }

  .mango-effectiveness-source-popover th,
  .mango-effectiveness-source-popover td {
    padding: 8px 10px;
    border-right: 1px solid var(--m-border);
    border-bottom: 1px solid var(--m-border);
    text-align: left;
  }

  .mango-effectiveness-source-popover th {
    position: sticky;
    z-index: 1;
    top: 0;
    background: var(--m-surface-soft);
    color: var(--m-text);
    font-weight: 600;
  }

  .mango-effectiveness-source-popover th:first-child {
    width: 330px;
  }

  .mango-effectiveness-source-popover th:not(:first-child) {
    width: 110px;
  }

  .mango-effectiveness-source-popover th:last-child,
  .mango-effectiveness-source-popover td:last-child {
    border-right: 0;
  }

  .mango-effectiveness-source-popover tbody tr:last-child td {
    border-bottom: 0;
  }

  .mango-effectiveness-source-popover tbody tr:hover td {
    background: color-mix(in srgb, var(--m-primary) 3%, var(--m-surface));
  }

  .mango-effectiveness-source-popover td:first-child strong,
  .mango-effectiveness-source-popover td:first-child small {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-effectiveness-source-popover td:first-child small {
    margin-top: 2px;
    color: var(--m-muted);
    font-size: 11px;
  }

  .mango-effectiveness-ai-card {
    position: relative;
    display: flex;
    overflow: hidden;
    min-height: 520px;
    padding: 0;
    flex-direction: column;
  }

  .mango-effectiveness-ai-card::before {
    position: absolute;
    top: -120px;
    right: -80px;
    width: 320px;
    height: 320px;
    border-radius: 50%;
    background: radial-gradient(
      circle,
      color-mix(in srgb, var(--m-primary) 10%, transparent) 0%,
      transparent 70%
    );
    content: '';
    pointer-events: none;
  }

  .mango-effectiveness-ai-card__header {
    position: relative;
    z-index: 1;
    display: flex;
    min-height: 48px;
    padding: 8px 16px;
    align-items: center;
    gap: 12px;
    border-bottom: 1px solid var(--m-border);
    background: linear-gradient(
      90deg,
      color-mix(in srgb, var(--m-primary) 7%, var(--m-surface)) 0%,
      var(--m-surface) 58%
    );
  }

  .mango-effectiveness-ai-card__identity {
    display: flex;
    min-width: 0;
    flex: 1;
    align-items: center;
    gap: 10px;
  }

  .mango-effectiveness-ai-card__identity > div,
  .mango-effectiveness-ai-card__meta {
    display: flex;
    min-width: 0;
    flex-direction: column;
  }

  .mango-effectiveness-ai-card__identity strong {
    color: var(--m-text);
    font-size: 15px;
  }

  .mango-effectiveness-ai-card__identity span,
  .mango-effectiveness-ai-card__meta small {
    color: var(--m-muted);
    font-size: 11px;
  }

  .mango-effectiveness-ai-card__icon {
    display: inline-flex;
    width: 32px;
    height: 32px;
    flex: 0 0 auto;
    align-items: center;
    justify-content: center;
    border: 1px solid color-mix(in srgb, var(--m-primary) 22%, var(--m-border));
    border-radius: var(--m-radius-md);
    background: color-mix(in srgb, var(--m-primary) 10%, var(--m-surface));
    color: var(--m-primary);
    font-size: 18px;
  }

  .mango-effectiveness-ai-card__meta {
    padding-right: 4px;
    align-items: flex-end;
  }

  .mango-effectiveness-ai-card__meta > span {
    color: var(--m-text-2);
    font-size: 11px;
    font-weight: 600;
  }

  .mango-effectiveness-ai-loading {
    display: flex;
    min-height: 450px;
    padding: 26px;
    flex: 1;
    flex-direction: column;
    justify-content: center;
    gap: 20px;
  }

  .mango-effectiveness-ai-loading > span {
    color: var(--m-muted);
    font-size: 12px;
    text-align: center;
  }

  .mango-effectiveness-ai-loading__intro {
    max-width: 760px;
  }

  .mango-effectiveness-ai-loading__columns {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
  }

  .mango-effectiveness-ai-loading__columns > * {
    padding: 16px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
  }

  .mango-effectiveness-ai-result {
    position: relative;
    z-index: 1;
    display: flex;
    min-height: 0;
    padding: 16px;
    flex: 1;
    flex-direction: column;
    gap: 12px;
  }

  .mango-effectiveness-ai-result__hero {
    display: grid;
    grid-template-columns: minmax(0, 1.45fr) minmax(280px, 0.55fr);
    gap: 12px;
  }

  .mango-effectiveness-ai-result__hero > div:first-child,
  .mango-effectiveness-ai-trend {
    padding: 14px 16px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface-soft);
  }

  .mango-effectiveness-ai-result__hero span,
  .mango-effectiveness-ai-trend > span {
    color: var(--m-muted);
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.6px;
    text-transform: uppercase;
  }

  .mango-effectiveness-ai-result__hero h2 {
    margin: 4px 0 6px;
    color: var(--m-text);
    font-size: 20px;
    line-height: 28px;
  }

  .mango-effectiveness-ai-result__hero p,
  .mango-effectiveness-ai-trend p {
    margin: 0;
    color: var(--m-text-2);
    font-size: 12px;
    line-height: 20px;
  }

  .mango-effectiveness-ai-trend {
    position: relative;
    overflow: hidden;
  }

  .mango-effectiveness-ai-trend::before {
    position: absolute;
    top: 0;
    bottom: 0;
    left: 0;
    width: 4px;
    background: var(--m-muted);
    content: '';
  }

  .mango-effectiveness-ai-trend.is-improving::before {
    background: var(--m-success);
  }
  .mango-effectiveness-ai-trend.is-stable::before {
    background: var(--m-primary);
  }
  .mango-effectiveness-ai-trend.is-declining::before {
    background: var(--m-danger);
  }

  .mango-effectiveness-ai-trend strong {
    display: block;
    margin: 5px 0;
    color: var(--m-text);
    font-size: 16px;
  }

  .mango-effectiveness-ai-result__columns {
    display: grid;
    min-height: 0;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    flex: 1;
    gap: 10px;
  }

  .mango-effectiveness-ai-result__columns > section {
    display: flex;
    min-width: 0;
    padding: 12px;
    flex-direction: column;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
  }

  .mango-effectiveness-ai-result__columns > section > div:first-child {
    display: flex;
    min-height: 26px;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .mango-effectiveness-ai-result__columns > section > div:first-child strong {
    color: var(--m-text);
    font-size: 13px;
  }

  .mango-effectiveness-ai-result__columns > section > div:first-child span {
    padding: 1px 6px;
    border-radius: var(--m-radius-pill);
    background: var(--m-surface-soft);
    color: var(--m-muted);
    font-size: 10px;
  }

  .mango-effectiveness-ai-result__columns ul {
    display: flex;
    min-height: 0;
    margin: 4px 0 0;
    padding: 0;
    flex-direction: column;
    list-style: none;
    gap: 3px;
  }

  .mango-effectiveness-ai-result__columns li {
    position: relative;
    padding: 7px 8px 7px 13px;
    border-radius: var(--m-radius-sm);
    background: var(--m-surface-soft);
  }

  .mango-effectiveness-ai-result__columns li::before {
    position: absolute;
    top: 12px;
    left: 5px;
    width: 4px;
    height: 4px;
    border-radius: 50%;
    background: var(--m-primary);
    content: '';
  }

  .mango-effectiveness-ai-result__columns .is-benefit li::before {
    background: var(--m-success);
  }
  .mango-effectiveness-ai-result__columns .is-risk li::before {
    background: var(--m-danger);
  }
  .mango-effectiveness-ai-result__columns .is-action li::before {
    background: var(--m-primary);
  }

  .mango-effectiveness-ai-result__columns li strong,
  .mango-effectiveness-ai-result__columns li small {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .mango-effectiveness-ai-result__columns li strong {
    color: var(--m-text);
    font-size: 11px;
    white-space: nowrap;
  }

  .mango-effectiveness-ai-result__columns li p {
    display: block;
    overflow: visible;
    margin: 2px 0;
    color: var(--m-text-2);
    font-size: 10px;
    line-height: 15px;
    overflow-wrap: anywhere;
    white-space: pre-line;
    word-break: break-word;
  }

  .mango-effectiveness-ai-result__columns li small {
    color: var(--m-muted);
    font-size: 9px;
    white-space: nowrap;
  }

  .mango-effectiveness-ai-result__empty {
    display: flex !important;
    min-height: 100px !important;
    flex: 1;
    align-items: center !important;
    justify-content: center !important;
    color: var(--m-muted);
    font-size: 11px;
  }

  .mango-effectiveness-ai-unavailable {
    position: relative;
    z-index: 1;
    display: grid;
    min-height: 450px;
    grid-template-columns: 180px minmax(0, 560px);
    padding: 32px;
    flex: 1;
    align-content: center;
    justify-content: center;
    gap: 26px;
  }

  .mango-effectiveness-ai-unavailable__visual {
    position: relative;
    display: flex;
    width: 160px;
    height: 160px;
    align-items: center;
    justify-content: center;
    border: 1px dashed color-mix(in srgb, var(--m-primary) 35%, var(--m-border));
    border-radius: 50%;
    background: color-mix(in srgb, var(--m-primary) 5%, var(--m-surface));
  }

  .mango-effectiveness-ai-unavailable__visual::before,
  .mango-effectiveness-ai-unavailable__visual::after {
    position: absolute;
    border: 1px solid color-mix(in srgb, var(--m-primary) 14%, transparent);
    border-radius: 50%;
    content: '';
  }

  .mango-effectiveness-ai-unavailable__visual::before {
    width: 118px;
    height: 118px;
  }

  .mango-effectiveness-ai-unavailable__visual::after {
    width: 78px;
    height: 78px;
  }

  .mango-effectiveness-ai-unavailable__visual > span {
    z-index: 1;
    display: inline-flex;
    width: 52px;
    height: 52px;
    align-items: center;
    justify-content: center;
    border-radius: var(--m-radius-lg);
    background: var(--m-primary);
    color: var(--m-surface);
    font-size: 28px;
    box-shadow: 0 8px 24px color-mix(in srgb, var(--m-primary) 24%, transparent);
  }

  .mango-effectiveness-ai-unavailable__content {
    display: flex;
    flex-direction: column;
    justify-content: center;
  }

  .mango-effectiveness-ai-unavailable__content > span {
    color: var(--m-primary);
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.8px;
  }

  .mango-effectiveness-ai-unavailable__content h2 {
    margin: 6px 0 8px;
    color: var(--m-text);
    font-size: 20px;
    line-height: 28px;
  }

  .mango-effectiveness-ai-unavailable__content p {
    margin: 0;
    color: var(--m-text-2);
    font-size: 12px;
    line-height: 20px;
  }

  .mango-effectiveness-ai-unavailable__content > small {
    margin-top: 8px;
    color: var(--m-danger);
    font-size: 10px;
  }

  .mango-effectiveness-ai-unavailable__content > div {
    display: flex;
    margin-top: 16px;
    align-items: center;
    gap: 10px;
  }

  .mango-effectiveness-ai-unavailable__content > div > span {
    color: var(--m-muted);
    font-size: 10px;
  }

  .mango-effectiveness-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: var(--m-page-gap);
  }

  .mango-effectiveness-grid--primary {
    grid-template-columns: minmax(0, 1.65fr) minmax(330px, 0.85fr);
  }

  .mango-effectiveness-grid--convergence {
    grid-template-columns: minmax(0, 1.45fr) minmax(360px, 0.95fr);
    align-items: stretch;
  }

  .mango-effectiveness-grid--diagnostics {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    align-items: stretch;
  }

  .mango-effectiveness-grid--module-analysis {
    grid-template-columns: repeat(auto-fit, minmax(min(100%, 360px), 1fr));
    align-items: stretch;
  }

  .mango-effectiveness-module-workbench {
    display: grid;
    min-width: 0;
    grid-template-columns: minmax(0, 1fr);
    align-items: stretch;
    gap: var(--m-page-gap);
  }

  .mango-effectiveness-grid--operations {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .mango-effectiveness-grid--module-analysis > .mango-effectiveness-panel {
    min-height: 340px;
  }

  .mango-effectiveness-panel--environment {
    min-width: 0;
  }

  .mango-effectiveness-benefit {
    display: flex;
    flex-direction: column;
  }

  .mango-effectiveness-period-workbench {
    display: grid;
    min-width: 0;
    grid-template-columns: minmax(0, 1fr);
    align-items: stretch;
    gap: var(--m-page-gap);
  }

  .mango-effectiveness-module-quality {
    display: flex;
    min-height: 0;
    margin-bottom: 0;
    padding-bottom: 10px;
    flex-direction: column;
  }

  .mango-effectiveness-module-workbench .mango-effectiveness-module-quality__list {
    max-height: 520px;
  }

  .mango-effectiveness-module-quality__summary {
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 6px !important;
  }

  .mango-effectiveness-module-quality__loading,
  .mango-effectiveness-module-quality__loading :deep(> .mango-panel-spin__content) {
    display: block;
    width: 100%;
    min-height: 180px;
  }

  .mango-effectiveness-module-quality__loading {
    flex: 1;
  }

  .mango-effectiveness-module-quality__toolbar {
    display: flex;
    min-width: 0;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 4px 0 8px;
  }

  .mango-effectiveness-module-quality__tabs {
    min-width: 0;
    flex: 1;
  }

  .mango-effectiveness-module-quality__tabs :deep(.arco-tabs-nav) {
    margin-bottom: 0;
  }

  .mango-effectiveness-module-quality__list {
    display: block;
    overflow: auto;
    max-height: 430px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    scrollbar-gutter: stable;
  }

  .mango-effectiveness-module-row {
    position: relative;
    display: grid;
    min-width: 900px;
    min-height: 56px;
    padding: 7px 10px;
    grid-template-columns:
      minmax(260px, 2fr) 72px minmax(150px, 0.9fr) 80px 126px
      minmax(150px, 0.9fr);
    align-items: center;
    gap: 10px;
    border-bottom: 1px solid var(--m-border-soft);
    background: var(--m-surface);
    transition: background-color 0.16s ease;
  }

  .mango-effectiveness-module-row:last-child {
    border-bottom: 0;
  }

  .mango-effectiveness-module-row:not(.mango-effectiveness-module-row--head):hover {
    background: var(--m-table-row-hover);
  }

  .mango-effectiveness-module-row--head {
    position: sticky;
    z-index: 2;
    top: 0;
    min-height: 34px;
    padding-top: 5px;
    padding-bottom: 5px;
    background: var(--m-surface-soft);
    color: var(--m-muted);
    font-size: 10px;
    font-weight: 600;
  }

  .mango-effectiveness-module-row > :not(:first-child):not(:last-child) {
    text-align: center;
  }

  .mango-effectiveness-module-row > .arco-tag {
    justify-self: center;
  }

  .mango-effectiveness-module-row::before {
    position: absolute;
    top: 8px;
    bottom: 8px;
    left: 0;
    width: 3px;
    border-radius: 0 var(--m-radius-pill) var(--m-radius-pill) 0;
    background: var(--m-primary);
    content: '';
  }

  .mango-effectiveness-module-row--head::before {
    display: none;
  }

  .mango-effectiveness-module-row.is-success::before {
    background: var(--m-success);
  }
  .mango-effectiveness-module-row.is-warning::before {
    background: var(--m-warning);
  }
  .mango-effectiveness-module-row.is-danger::before {
    background: var(--m-danger);
  }

  .mango-effectiveness-module-row__rank {
    color: var(--m-muted);
    font-size: 11px;
    font-variant-numeric: tabular-nums;
  }

  .mango-effectiveness-module-row__identity {
    display: grid;
    min-width: 0;
    grid-template-columns: 28px minmax(0, 1fr);
    align-items: center;
    gap: 8px;
  }

  .mango-effectiveness-module-row__main,
  .mango-effectiveness-module-row__rate {
    display: flex;
    min-width: 0;
    flex-direction: column;
  }

  .mango-effectiveness-module-row__main strong,
  .mango-effectiveness-module-row__main small,
  .mango-effectiveness-module-row__comparison {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-effectiveness-module-row__main strong {
    color: var(--m-text);
    font-size: 12px;
    line-height: 18px;
  }

  .mango-effectiveness-module-row__main small,
  .mango-effectiveness-module-row__issues {
    color: var(--m-muted);
    font-size: 10px;
  }

  .mango-effectiveness-module-row__rate strong,
  .mango-effectiveness-module-row__count,
  .mango-effectiveness-module-row__comparison {
    color: var(--m-text-2);
    font-size: 11px;
    font-variant-numeric: tabular-nums;
  }

  .mango-effectiveness-module-row__rate {
    gap: 3px;
  }

  .mango-effectiveness-module-row__issues {
    display: flex;
    min-width: 0;
    flex-direction: row;
    justify-content: center;
    gap: 6px;
    white-space: nowrap;
  }

  .mango-effectiveness-module-row__issues .is-danger {
    color: var(--m-danger);
    font-weight: 600;
  }

  .mango-effectiveness-module-row__issues .is-warning {
    color: var(--m-warning);
    font-weight: 600;
  }

  .mango-effectiveness-benefit__grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
    padding-top: 12px;
  }

  .mango-effectiveness-benefit__empty {
    min-height: 330px;
    margin-top: 12px;
  }

  .mango-effectiveness-benefit__lead {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
    padding-top: 12px;
  }

  .mango-effectiveness-benefit__lead article {
    position: relative;
    min-width: 0;
    padding: 12px;
    overflow: hidden;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: color-mix(in srgb, var(--m-primary) 5%, var(--m-surface));
  }

  .mango-effectiveness-benefit__lead article::before {
    position: absolute;
    width: 3px;
    inset: 0 auto 0 0;
    background: var(--m-primary);
    content: '';
  }

  .mango-effectiveness-benefit__lead article.is-inspection::before {
    background: var(--m-success);
  }

  .mango-effectiveness-benefit__lead article > div {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .mango-effectiveness-benefit__lead span,
  .mango-effectiveness-benefit__lead small,
  .mango-effectiveness-benefit__lead p {
    color: var(--m-muted);
    font-size: 10px;
    line-height: 16px;
  }

  .mango-effectiveness-benefit__lead strong {
    display: block;
    margin-top: 6px;
    color: var(--m-text);
    font-size: 22px;
    font-variant-numeric: tabular-nums;
    line-height: 28px;
  }

  .mango-effectiveness-benefit__lead p {
    margin: 2px 0;
    color: var(--m-text-2);
  }

  .mango-effectiveness-benefit__grid > div {
    display: flex;
    min-height: 96px;
    padding: 12px;
    flex-direction: column;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface-soft);
  }

  .mango-effectiveness-benefit__grid span,
  .mango-effectiveness-benefit__grid small {
    color: var(--m-muted);
    font-size: 11px;
  }

  .mango-effectiveness-benefit__grid strong {
    margin: 4px 0;
    color: var(--m-text);
    font-size: 20px;
    font-variant-numeric: tabular-nums;
  }

  .mango-effectiveness-benefit__types {
    display: flex;
    margin-top: 10px;
    flex-wrap: wrap;
    gap: 6px;
  }

  .mango-effectiveness-benefit__types > strong {
    width: 100%;
    color: var(--m-text-2);
    font-size: 11px;
  }

  .mango-effectiveness-benefit__types.is-automation {
    margin-top: 7px;
  }

  .mango-effectiveness-benefit__types span {
    padding: 3px 8px;
    border-radius: var(--m-radius-pill);
    background: color-mix(in srgb, var(--m-primary) 7%, var(--m-surface));
    color: var(--m-text-2);
    font-size: 11px;
  }

  .mango-effectiveness-panel {
    display: flex;
    min-width: 0;
    padding: 0 12px 10px;
    flex-direction: column;
  }

  .mango-effectiveness-panel-title {
    display: flex;
    min-height: 54px;
    margin-bottom: 4px;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    border-bottom: 1px solid var(--m-border);
  }

  .mango-effectiveness-panel-title > div {
    display: flex;
    min-width: 0;
    flex-direction: column;
  }

  .mango-effectiveness-panel-title strong {
    color: var(--m-text);
    font-size: 14px;
    line-height: 22px;
  }

  .mango-effectiveness-panel-title span,
  .mango-effectiveness-panel-title small {
    color: var(--m-muted);
    font-size: 11px;
    line-height: 18px;
  }

  .mango-effectiveness-panel-title > small {
    flex: none;
    padding: 2px 7px;
    border-radius: var(--m-radius-pill);
    background: var(--m-surface-soft);
  }

  .mango-effectiveness-panel-title.is-risk strong {
    color: var(--m-danger);
  }

  .mango-effectiveness-report-footer {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    gap: 8px 16px;
    padding: 10px 12px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-lg);
    background: var(--m-surface);
    color: var(--m-muted);
    font-size: 11px;
    line-height: 18px;
  }

  .mango-effectiveness-report-footer strong {
    color: var(--m-text-2);
  }

  .mango-effectiveness-report-footer dl {
    display: grid;
    margin: 0;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 4px 20px;
  }

  .mango-effectiveness-report-footer dl > div {
    display: grid;
    grid-template-columns: 52px minmax(0, 1fr);
    gap: 6px;
  }

  .mango-effectiveness-report-footer dt {
    color: var(--m-text-2);
    font-weight: 500;
  }

  .mango-effectiveness-report-footer dd {
    min-width: 0;
    margin: 0;
  }

  .mango-effectiveness-comparison-positive {
    color: var(--m-success) !important;
  }

  .mango-effectiveness-comparison-negative {
    color: var(--m-danger) !important;
  }

  .mango-effectiveness-state-success {
    color: var(--m-success) !important;
  }

  .mango-effectiveness-state-danger {
    color: var(--m-danger) !important;
  }

  .mango-effectiveness-warning {
    color: var(--m-warning) !important;
  }

  @media (max-width: 1100px) {
    .mango-effectiveness-report-header {
      grid-template-columns: minmax(0, 1fr);
      grid-template-areas: 'main' 'verdict' 'meta';
      row-gap: 12px;
    }

    .mango-effectiveness-verdict {
      width: 100%;
      margin-bottom: 0;
    }

    .mango-effectiveness-grid,
    .mango-effectiveness-grid--primary,
    .mango-effectiveness-grid--convergence {
      grid-template-columns: minmax(0, 1fr);
    }

    .mango-effectiveness-module-workbench {
      grid-template-columns: minmax(0, 1fr);
    }

    .mango-effectiveness-module-quality__toolbar {
      align-items: stretch;
      flex-direction: column;
      gap: 4px;
    }

    .mango-effectiveness-cards {
      grid-template-columns: repeat(6, minmax(0, 1fr));
    }

    .mango-effectiveness-period-workbench {
      grid-template-columns: minmax(0, 1fr);
    }

    .mango-effectiveness-ai-result__hero,
    .mango-effectiveness-ai-result__columns {
      grid-template-columns: minmax(0, 1fr);
    }

    .mango-effectiveness-ai-unavailable {
      grid-template-columns: minmax(0, 560px);
      text-align: center;
    }

    .mango-effectiveness-ai-unavailable__visual {
      margin: 0 auto;
    }

    .mango-effectiveness-ai-unavailable__content > div {
      justify-content: center;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .mango-effectiveness-cards {
      transition: none;
    }
  }
  .is-report-mode :deep(.mango-table-body__content) {
    overflow-x: auto;
    padding: var(--m-page-gap);
    align-items: center;
    gap: 0;
    background: color-mix(in srgb, var(--m-bg) 88%, var(--m-text));
  }

  .is-report-mode .mango-effectiveness-report-document {
    position: relative;
    display: flex;
    width: 297mm;
    max-width: 297mm;
    min-width: 297mm;
    padding: 9mm 10mm 8mm;
    flex: 0 0 auto;
    box-sizing: border-box;
    flex-direction: column;
    gap: var(--m-page-gap);
    border: 1px solid var(--m-border);
    background: var(--m-surface);
    box-shadow: 0 12px 30px color-mix(in srgb, var(--m-text) 18%, transparent);
  }

  .is-report-mode .mango-effectiveness-paper-page {
    width: 100%;
    min-width: 0;
    height: auto;
    min-height: 0;
    padding: 0;
    gap: var(--m-page-gap);
    border: 0;
    background: transparent;
    box-shadow: none;
  }

  .is-report-mode .mango-effectiveness-report-header {
    padding: 14px 16px 0;
  }

  .is-report-mode .mango-effectiveness-report-header__main {
    padding-bottom: 12px;
  }

  .is-report-mode .mango-effectiveness-chapter-heading {
    min-height: 11mm;
    margin: 0;
    padding-bottom: var(--m-page-gap);
    flex: 0 0 auto;
    break-after: avoid-page;
    page-break-after: avoid;
  }

  .is-report-mode .mango-effectiveness-insight,
  .is-report-mode .mango-effectiveness-card,
  .is-report-mode .mango-section-card,
  .is-report-mode .mango-effectiveness-report-header {
    box-shadow: none;
  }

  .is-report-mode .mango-effectiveness-cards {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .is-report-mode .mango-effectiveness-card {
    min-height: 104px;
    padding: 9px 10px;
  }

  .is-report-mode .mango-effectiveness-ai-card {
    min-height: 0;
    flex: 1;
  }

  .is-report-mode .mango-effectiveness-ai-result__hero {
    grid-template-columns: minmax(0, 1.45fr) minmax(280px, 0.55fr);
  }

  .is-report-mode .mango-effectiveness-ai-result__columns,
  .is-report-mode .mango-effectiveness-ai-loading__columns {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .is-report-mode .mango-effectiveness-ai-unavailable {
    grid-template-columns: 180px minmax(0, 560px);
    text-align: left;
  }

  .is-report-mode .mango-effectiveness-ai-unavailable__content > div {
    justify-content: flex-start;
  }

  .is-report-mode .mango-effectiveness-grid,
  .is-report-mode .mango-effectiveness-grid--convergence {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .is-report-mode .mango-effectiveness-grid--convergence {
    grid-template-columns: minmax(0, 1fr);
    align-items: start;
  }

  .mango-effectiveness-output-loading {
    display: block;
    min-width: 0;
  }

  .mango-effectiveness-output-metrics {
    display: grid;
    grid-template-columns: repeat(6, minmax(0, 1fr));
    gap: var(--m-page-gap);
  }

  .mango-effectiveness-output-metrics article {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 6px;
    padding: 10px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-sm);
    background: var(--m-surface-soft);
  }

  .mango-effectiveness-output-metrics span,
  .mango-effectiveness-output-metrics small {
    color: var(--m-muted);
    font-size: var(--m-font-caption);
    overflow-wrap: break-word;
  }

  .mango-effectiveness-output-metrics strong {
    color: var(--m-text);
    font-size: 18px;
    font-variant-numeric: tabular-nums;
  }

  .mango-effectiveness-output-table {
    width: 100%;
    table-layout: fixed;
    border-collapse: collapse;
    font-variant-numeric: tabular-nums;
  }

  .mango-effectiveness-output-table th,
  .mango-effectiveness-output-table td {
    padding: 8px 10px;
    border-bottom: 1px solid var(--m-border);
    text-align: center;
    overflow-wrap: break-word;
  }

  .mango-effectiveness-output-table th {
    color: var(--m-muted);
    background: var(--m-surface-soft);
  }

  .mango-effectiveness-output-table :is(th, td):first-child {
    width: 50%;
    text-align: left;
  }

  .is-report-mode .mango-effectiveness-grid--convergence .is-automation {
    display: flex;
    flex-wrap: wrap;
  }

  .is-report-mode .mango-effectiveness-grid--diagnostics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .is-report-mode .mango-effectiveness-grid--diagnostics > :last-child:nth-child(odd) {
    grid-column: 1 / -1;
  }

  .is-report-mode .mango-effectiveness-grid--module-analysis {
    grid-template-columns: repeat(auto-fit, minmax(min(100%, 360px), 1fr));
  }

  .is-report-mode
    .mango-effectiveness-grid--module-analysis
    > .mango-effectiveness-panel:last-child:nth-child(odd) {
    grid-column: 1 / -1;
  }

  .is-report-mode .mango-effectiveness-module-workbench {
    grid-template-columns: minmax(0, 1fr);
  }

  .is-report-mode .mango-effectiveness-grid--operations {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .is-report-mode .mango-effectiveness-grid--module-analysis > .mango-effectiveness-panel {
    min-height: 0;
  }

  .is-report-mode .mango-effectiveness-period-workbench {
    grid-template-columns: minmax(0, 1fr);
  }

  .is-report-mode .mango-effectiveness-module-quality__list {
    overflow: visible;
    max-height: none;
    width: 100%;
    min-width: 0;
    box-sizing: border-box;
  }

  .is-report-mode .mango-effectiveness-module-row {
    width: 100%;
    min-width: 0;
    box-sizing: border-box;
    grid-template-columns:
      minmax(0, 2.4fr) minmax(0, 0.8fr) minmax(0, 1.3fr)
      minmax(0, 0.8fr) minmax(0, 1.2fr) minmax(0, 1.8fr);
    min-height: 44px;
    padding: 6px 8px;
  }

  .is-report-mode .mango-effectiveness-module-row > * {
    min-width: 0;
  }

  .is-report-mode .mango-effectiveness-module-row__comparison {
    white-space: normal;
    overflow-wrap: anywhere;
    overflow: visible;
    text-overflow: clip;
  }

  .is-report-mode .mango-effectiveness-module-row__issues {
    flex-wrap: wrap;
  }

  .is-report-mode .mango-effectiveness-card {
    min-height: 116px;
  }

  .is-report-mode .mango-effectiveness-card__comparison,
  .is-report-mode .mango-effectiveness-card__footer small {
    overflow: visible;
    text-overflow: clip;
    white-space: normal;
  }

  .is-report-mode .mango-effectiveness-grid--diagnostics .mango-effectiveness-panel-title {
    display: grid;
    min-height: 68px;
    grid-template-columns: minmax(0, 1fr);
    padding: 6px 0;
    align-content: center;
    gap: 2px;
  }

  .is-report-mode .mango-effectiveness-grid--diagnostics .mango-effectiveness-panel-title strong {
    white-space: nowrap;
  }

  .is-report-mode .mango-effectiveness-grid--diagnostics .mango-effectiveness-panel-title > small {
    max-width: 100%;
    justify-self: start;
    white-space: normal;
  }

  .is-printing :deep(.mango-table-header) {
    display: none;
  }

  .is-printing .mango-effectiveness-ai-card__action,
  .is-printing .mango-effectiveness-ai-unavailable .arco-btn {
    display: none;
  }

  @media print {
    @page {
      size: A4 landscape;
      margin: 0;
    }

    :global(html),
    :global(body) {
      width: 297mm !important;
      min-width: 297mm !important;
      margin: 0 !important;
      padding: 0 !important;
      background: var(--m-surface) !important;
    }

    .mango-effectiveness-page {
      width: 297mm !important;
      min-width: 297mm !important;
      margin: 0 !important;
      padding: 0 !important;
      gap: 0;
      color: var(--m-text);
      background: var(--m-surface);
      print-color-adjust: exact;
      -webkit-print-color-adjust: exact;
    }
    .is-report-mode :deep(.mango-table-body__content) {
      overflow: visible !important;
      padding: 0 !important;
      gap: 0 !important;
      background: var(--m-surface) !important;
    }
    :deep(.mango-table-header) {
      display: none !important;
    }
    .mango-effectiveness-report-document {
      width: 297mm !important;
      max-width: 297mm !important;
      min-width: 297mm !important;
      margin: 0 !important;
      padding: 9mm 10mm 8mm !important;
      gap: var(--m-page-gap) !important;
      box-sizing: border-box !important;
      border: 0 !important;
      background: var(--m-surface) !important;
      box-shadow: none !important;
    }

    .mango-effectiveness-paper-page {
      width: 100% !important;
      max-width: none !important;
      min-width: 0 !important;
      height: auto !important;
      max-height: none !important;
      min-height: 0 !important;
      margin: 0 !important;
      padding: 0 !important;
      gap: var(--m-page-gap) !important;
      overflow: visible !important;
      break-after: auto;
      break-inside: auto;
      page-break-after: auto;
      page-break-inside: auto;
      border: 0 !important;
      background: transparent !important;
      box-shadow: none !important;
    }
    .mango-effectiveness-insight,
    .mango-effectiveness-card,
    .mango-section-card {
      break-inside: avoid;
      box-shadow: none;
    }
    .mango-effectiveness-card {
      min-height: 116px;
      padding: 8px;
    }
    .mango-effectiveness-card > strong {
      font-size: 20px;
    }
    .mango-effectiveness-panel {
      break-inside: avoid;
    }
    .mango-effectiveness-module-quality__list {
      max-height: none !important;
      overflow: visible !important;
      scrollbar-gutter: auto !important;
    }
    .mango-effectiveness-task-health__list,
    .mango-effectiveness-case-health__list {
      min-height: 0 !important;
      flex: 1 1 auto !important;
      max-height: none !important;
      overflow: visible !important;
      scrollbar-gutter: auto !important;
    }
    .mango-effectiveness-task-health__list article .arco-btn,
    .mango-effectiveness-case-health__list article .arco-btn {
      display: none !important;
    }
    .mango-effectiveness-grid--health {
      align-items: start !important;
    }
    .mango-effectiveness-grid--health > .mango-effectiveness-panel {
      height: auto !important;
      max-height: none !important;
      box-sizing: border-box !important;
      overflow: visible !important;
    }
    .mango-effectiveness-grid--module-analysis
      > .mango-effectiveness-panel:last-child:nth-child(odd) {
      grid-column: 1 / -1 !important;
    }
    .mango-effectiveness-card__comparison,
    .mango-effectiveness-card__footer small {
      overflow: visible !important;
      text-overflow: clip !important;
      white-space: normal !important;
    }
    .mango-effectiveness-grid--diagnostics .mango-effectiveness-panel-title {
      display: grid !important;
      min-height: 68px !important;
      grid-template-columns: minmax(0, 1fr) !important;
      padding: 6px 0 !important;
      align-content: center !important;
      gap: 2px !important;
    }
    .mango-effectiveness-grid--diagnostics .mango-effectiveness-panel-title strong {
      white-space: nowrap !important;
    }
    .mango-effectiveness-grid--diagnostics .mango-effectiveness-panel-title > small {
      max-width: 100% !important;
      justify-self: start !important;
      white-space: normal !important;
    }
  }
</style>
