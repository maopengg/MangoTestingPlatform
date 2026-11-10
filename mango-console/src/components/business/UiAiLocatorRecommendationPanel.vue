<template>
  <a-modal
    :visible="visible"
    title="AI 推荐定位器"
    width="760px"
    :footer="false"
    unmount-on-close
    @update:visible="emit('update:visible', $event)"
    @cancel="emit('update:visible', false)"
  >
    <div class="mango-ai-locator-panel">
      <a-spin :loading="loading || validating" class="mango-ai-locator-panel__loading">
        <a-alert
          v-if="batchMessage"
          :type="batchMessage.type"
          class="mango-ai-locator-panel__batch-message"
        >
          {{ batchMessage.text }}
        </a-alert>
        <Scrollbar
          v-if="candidates.length > 3"
          always
          class="mango-ai-locator-panel__candidate-scroll"
        >
          <div class="mango-ai-locator-panel__list">
            <section
              v-for="(candidate, index) in candidates"
              :key="candidate.candidate_id || `${candidate.exp}-${candidate.loc}`"
              class="mango-section-card mango-ai-locator-panel__candidate"
            >
              <div class="mango-ai-locator-panel__candidate-head">
                <a-space size="mini">
                  <a-checkbox
                    :model-value="isSelected(candidate)"
                    :disabled="!candidate.verified"
                    @change="toggleCandidate(candidate, $event)"
                  />
                  <strong>{{ index + 1 }}. {{ locatorType(candidate.exp) }}</strong>
                  <a-tag size="small">置信度 {{ candidate.confidence || 0 }}</a-tag>
                  <a-tag
                    v-if="candidate.validation_done"
                    size="small"
                    :color="
                      candidate.verified && candidate.count === 1
                        ? 'green'
                        : candidate.verified
                        ? 'orange'
                        : 'red'
                    "
                  >
                    {{ validationText(candidate) }}
                  </a-tag>
                  <a-tag v-else size="small">待验证</a-tag>
                </a-space>
                <span class="mango-ai-locator-panel__group-hint">
                  {{ selectedGroupText(candidate) }}
                </span>
              </div>
              <div class="mango-code-panel mango-ai-locator-panel__expression">
                {{ candidate.loc }}
              </div>
              <div class="mango-ai-locator-panel__meta">
                <span>{{ candidate.reason || 'AI 语义推荐' }}</span>
                <span v-if="candidate.validation_done">
                  匹配 {{ candidate.count || 0 }} · 定位 {{ candidate.duration_ms || 0 }} ms
                </span>
                <span
                  v-if="candidateFailureReason(candidate)"
                  role="alert"
                  class="mango-ai-locator-panel__error"
                >
                  {{ candidateFailureReason(candidate) }}
                </span>
              </div>
            </section>
          </div>
        </Scrollbar>
        <div v-else-if="candidates.length" class="mango-ai-locator-panel__list">
          <section
            v-for="(candidate, index) in candidates"
            :key="candidate.candidate_id || `${candidate.exp}-${candidate.loc}`"
            class="mango-section-card mango-ai-locator-panel__candidate"
          >
            <div class="mango-ai-locator-panel__candidate-head">
              <a-space size="mini">
                <a-checkbox
                  :model-value="isSelected(candidate)"
                  :disabled="!candidate.verified"
                  @change="toggleCandidate(candidate, $event)"
                />
                <strong>{{ index + 1 }}. {{ locatorType(candidate.exp) }}</strong>
                <a-tag size="small">置信度 {{ candidate.confidence || 0 }}</a-tag>
                <a-tag
                  v-if="candidate.validation_done"
                  size="small"
                  :color="
                    candidate.verified && candidate.count === 1
                      ? 'green'
                      : candidate.verified
                      ? 'orange'
                      : 'red'
                  "
                >
                  {{ validationText(candidate) }}
                </a-tag>
                <a-tag v-else size="small">待验证</a-tag>
              </a-space>
              <span class="mango-ai-locator-panel__group-hint">
                {{ selectedGroupText(candidate) }}
              </span>
            </div>
            <div class="mango-code-panel mango-ai-locator-panel__expression">
              {{ candidate.loc }}
            </div>
            <div class="mango-ai-locator-panel__meta">
              <span>{{ candidate.reason || 'AI 语义推荐' }}</span>
              <span v-if="candidate.validation_done">
                匹配 {{ candidate.count || 0 }} · 定位 {{ candidate.duration_ms || 0 }} ms
              </span>
              <span
                v-if="candidateFailureReason(candidate)"
                role="alert"
                class="mango-ai-locator-panel__error"
              >
                {{ candidateFailureReason(candidate) }}
              </span>
            </div>
          </section>
        </div>
        <div v-else-if="!loading" class="mango-empty-state mango-ai-locator-panel__empty">
          本批暂无可展示候选，可以点击下方“换一批”继续生成。
        </div>
      </a-spin>
      <section v-if="showGuidance" class="mango-soft-panel mango-ai-locator-panel__guidance">
        <div class="mango-ai-locator-panel__guidance-head">
          <div>
            <strong>补充定位描述</strong>
            <span>可选；填写后点击“换一批”，AI 会结合描述重新生成候选。</span>
          </div>
          <a-space size="mini">
            <a-tag v-if="batch" size="small">第 {{ batch }} 批</a-tag>
            <a-button
              size="small"
              :loading="loading"
              :disabled="validating"
              @click="refreshBatch"
              data-testid="qa-components-business-uiailocatorrecommendationpanel-button-换一批"
            >
              换一批
            </a-button>
          </a-space>
        </div>
        <label class="mango-ai-locator-panel__guidance-row">
          <span>元素位置与周边文字</span>
          <a-input
            v-model="guidance.locationDescription"
            :max-length="1000"
            placeholder="例如：删除确认弹窗中，附近有“删除后无法恢复”"
            allow-clear
          />
        </label>
        <label class="mango-ai-locator-panel__guidance-row">
          <span>排除项</span>
          <a-input
            v-model="guidance.surroundingText"
            :max-length="500"
            placeholder="例如：排除列表操作列中的同名按钮"
            allow-clear
          />
        </label>
      </section>
      <div class="mango-ai-locator-panel__actions">
        <div>
          <span>已选 {{ selectedCandidates.length }}/3 个</span>
          <a-button
            v-if="verifiedCandidates.length"
            type="text"
            size="small"
            @click="selectAllVerified"
          >
            {{ allVerifiedSelected ? '取消全选' : '全选可用' }}
          </a-button>
        </div>
        <a-space size="small">
          <a-button @click="emit('update:visible', false)" data-testid="qa-components-business-uiailocatorrecommendationpanel-button-取消">取消</a-button>
          <a-button
            type="primary"
            :disabled="!selectedCandidates.length || loading || validating"
            @click="applySelected" data-testid="qa-components-business-uiailocatorrecommendationpanel-button-替换-组定位器"
          >
            替换 {{ selectedCandidates.length || 0 }} 组定位器
          </a-button>
        </a-space>
      </div>
    </div>
  </a-modal>
</template>

<script lang="ts" setup>
  import { computed, ref, watch } from 'vue'
  import { Scrollbar } from '@/components/Scrollbar'
  import type { LiveLocator } from './ui-live-workbench'

  const props = defineProps<{
    visible: boolean
    loading: boolean
    validating: boolean
    candidates: LiveLocator[]
    batch: number
    targetName?: string
    emptyReason?: string
  }>()

  const emit = defineEmits<{
    (event: 'update:visible', value: boolean): void
    (
      event: 'refresh',
      guidance: { location_description: string; surrounding_text: string }
    ): void
    (event: 'use-many', candidates: LiveLocator[]): void
  }>()

  const selectedKeys = ref<string[]>([])
  const guidance = ref({
    locationDescription: '',
    surroundingText: '',
  })
  const verifiedCandidates = computed(() =>
    props.candidates.filter((candidate) => candidate.verified).slice(0, 3)
  )
  const selectedCandidates = computed(() =>
    props.candidates
      .filter((candidate) => selectedKeys.value.includes(candidateKey(candidate)))
      .slice(0, 3)
  )
  const allVerifiedSelected = computed(
    () =>
      verifiedCandidates.value.length > 0 &&
      verifiedCandidates.value.every((candidate) => isSelected(candidate))
  )
  const validationCompleted = computed(
    () => props.candidates.length > 0 && props.candidates.every((item) => item.validation_done)
  )
  const showGuidance = computed(
    () => props.batch > 0 || Boolean(props.emptyReason) || validationCompleted.value
  )
  const batchMessage = computed(() => {
    if (props.loading || props.validating) return null
    if (!props.candidates.length) {
      return {
        type: 'warning' as const,
        text:
          props.emptyReason ||
          'AI 没有生成定位器候选，也没有返回具体原因。可以补充元素上下文或点击“换一批”。',
      }
    }
    if (!validationCompleted.value) return null
    if (!verifiedCandidates.value.length) {
      return {
        type: 'warning' as const,
        text: `AI 已生成 ${props.candidates.length} 个候选，但浏览器校验全部失败。失败候选已保留，可查看原因后点击“换一批”。`,
      }
    }
    return null
  })

  watch(
    () => [props.visible, props.batch, props.candidates],
    () => {
      selectedKeys.value = []
    }
  )

  watch(
    () => ({ visible: props.visible, targetName: props.targetName }),
    (current, previous) => {
      if (
        current.visible &&
        (!previous?.visible || previous.targetName !== current.targetName)
      ) {
        guidance.value = {
          locationDescription: '',
          surroundingText: '',
        }
      }
    }
  )

  function candidateKey(candidate: LiveLocator) {
    return String(candidate.candidate_id || `${candidate.exp}:${candidate.loc}`)
  }

  function isSelected(candidate: LiveLocator) {
    return selectedKeys.value.includes(candidateKey(candidate))
  }

  function toggleCandidate(candidate: LiveLocator, checked: boolean) {
    const key = candidateKey(candidate)
    if (!checked) {
      selectedKeys.value = selectedKeys.value.filter((item) => item !== key)
      return
    }
    if (!candidate.verified || selectedKeys.value.includes(key)) return
    if (selectedKeys.value.length >= 3) return
    selectedKeys.value = [...selectedKeys.value, key]
  }

  function selectedGroupText(candidate: LiveLocator) {
    const index = selectedCandidates.value.findIndex(
      (item) => candidateKey(item) === candidateKey(candidate)
    )
    return index >= 0 ? `替换第 ${index + 1} 组` : '未选择'
  }

  function selectAllVerified() {
    selectedKeys.value = allVerifiedSelected.value ? [] : verifiedCandidates.value.map(candidateKey)
  }

  function applySelected() {
    if (props.loading || props.validating || !selectedCandidates.value.length || selectedCandidates.value.some(item => !item.verified)) return
    emit('use-many', selectedCandidates.value)
  }

  function refreshBatch() {
    if (props.loading || props.validating) return
    emit('refresh', {
      location_description: guidance.value.locationDescription.trim(),
      surrounding_text: guidance.value.surroundingText.trim(),
    })
  }

  function locatorType(exp: unknown) {
    const names: Record<number, string> = { 0: 'XPATH', 2: '通用定位器', 9: 'CSS' }
    return names[Number(exp)] || `类型 ${exp}`
  }

  function validationText(candidate: LiveLocator) {
    if (!candidate.verified) return '验证失败'
    return Number(candidate.count) === 1 ? '唯一匹配' : `匹配 ${candidate.count || 0}`
  }

  function candidateFailureReason(candidate: LiveLocator) {
    if (!candidate.validation_done || candidate.verified) return ''
    if (candidate.error_message) return candidate.error_message
    const count = Number(candidate.count || 0)
    if (count === 0) return '当前页面未匹配到该候选定位器'
    if (count > 1) return `匹配到 ${count} 个元素，不满足唯一定位要求`
    if (!candidate.visible) return '已匹配到元素，但元素当前不可见'
    return '候选未通过浏览器可用性校验'
  }
</script>

<style scoped>
  .mango-ai-locator-panel {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .mango-ai-locator-panel__candidate-head,
  .mango-ai-locator-panel__meta,
  .mango-ai-locator-panel__actions {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  .mango-ai-locator-panel__meta {
    min-width: 0;
  }

  .mango-ai-locator-panel__meta {
    margin-top: 4px;
    color: var(--m-muted);
    font-size: 12px;
  }

  .mango-ai-locator-panel__loading {
    width: 100%;
    min-height: 180px;
  }

  .mango-ai-locator-panel__list {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .mango-ai-locator-panel__candidate-scroll {
    height: min(520px, calc(100vh - 360px));
    min-height: 360px;
  }

  .mango-ai-locator-panel__candidate-scroll .mango-ai-locator-panel__list {
    padding-right: 10px;
  }

  .mango-ai-locator-panel__batch-message {
    margin-bottom: 10px;
  }

  .mango-ai-locator-panel__candidate {
    padding: 12px;
  }

  .mango-ai-locator-panel__guidance {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 12px;
  }

  .mango-ai-locator-panel__guidance-head strong,
  .mango-ai-locator-panel__guidance-head span {
    display: block;
  }

  .mango-ai-locator-panel__guidance-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
  }

  .mango-ai-locator-panel__guidance-head > div {
    min-width: 0;
  }

  .mango-ai-locator-panel__guidance-head span {
    margin-top: 4px;
    color: var(--m-muted);
    font-size: 12px;
  }

  .mango-ai-locator-panel__guidance-row {
    display: grid;
    grid-template-columns: 76px minmax(0, 1fr);
    gap: 10px;
    align-items: center;
  }

  .mango-ai-locator-panel__guidance-row > span {
    color: var(--m-text-2);
  }

  .mango-ai-locator-panel__expression {
    margin-top: 8px;
    padding: 8px 10px;
    overflow-x: auto;
    white-space: nowrap;
  }

  .mango-ai-locator-panel__meta {
    flex-wrap: wrap;
  }

  .mango-ai-locator-panel__error {
    color: var(--m-danger);
  }

  .mango-ai-locator-panel__group-hint,
  .mango-ai-locator-panel__actions > div > span {
    color: var(--m-text-3);
    font-size: 12px;
  }

  .mango-ai-locator-panel__actions {
    padding-top: 12px;
    border-top: 1px solid var(--m-border);
  }

  .mango-ai-locator-panel__actions > div {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .mango-ai-locator-panel__empty {
    min-height: 160px;
  }
</style>
