<template>
  <section class="mango-callback-assertions">
    <header class="mango-section-title"
      ><h2>回调断言（{{ callbackAssertionCount(runs) }} 项）</h2></header
    >
    <div v-if="!runs.length" class="mango-empty-state">本次执行暂无回调断言结果。</div>
    <section v-for="run in displayRuns" :key="run.id" class="mango-callback-assertions-run">
      <header class="mango-callback-assertions-heading">
        <strong>{{ run.name }}</strong>
        <a-tag
          :color="run.status === 'passed' ? 'green' : run.status === 'waiting' ? 'orange' : 'red'"
          size="small"
        >
          {{ statusTitle(run.status) }}
        </a-tag>
        <span class="mango-section-description"
          >{{ run.events || 0 }} 个事件 · {{ run.deliveries || 0 }} 次投递</span
        >
        <MangoTableActions
          :actions="[
            {
              label: '投递证据',
              onClick: () => emit('evidence', run),
            },
          ]"
        />
      </header>
      <p v-if="run.error_message" class="mango-callback-assertions-error">{{
        run.error_message
      }}</p>
      <p
        v-if="!definitionLoading[run.id] && callbackNeedsDefinitions(run)"
        class="mango-section-description"
      >
        历史结果缺少检查定义，暂无法还原名称和字段。已保留原判定，可展开查看规则标识或查看投递证据。
      </p>
      <a-table
        v-if="callbackCheckRows(run).length"
        :columns="callbackCheckResultColumns"
        :data="callbackCheckRows(run)"
        row-key="rowKey"
        :expandable="{}"
        :pagination="false"
        :loading="Boolean(definitionLoading[run.id])"
        :scroll="{ x: 990 }"
        size="small"
      >
        <template #check="{ record }"
          ><span class="mango-callback-assertions-text">{{
            presentation(record).title
          }}</span></template
        >
        <template #target="{ record }">
          <span class="mango-callback-assertions-text">{{ presentation(record).target }}</span>
          <span v-if="presentation(record).source" class="mango-section-description">{{
            presentation(record).source
          }}</span>
        </template>
        <template #requirement="{ record }">
          <span class="mango-callback-assertions-text">{{ presentation(record).requirement }}</span>
        </template>
        <template #status="{ record }"
          ><a-tag
            :color="record.diagnostic ? 'orange' : record.passed ? 'green' : 'red'"
            size="small"
          >
            {{ record.diagnostic ? '仅诊断' : record.passed ? '通过' : '失败' }}
          </a-tag></template
        >
        <template #message="{ record }"
          ><a-tooltip :content="record.message || (record.passed ? '检查通过' : '检查未通过')">
            <span class="mango-callback-assertions-text">{{
              record.message || (record.passed ? '检查通过' : '检查未通过')
            }}</span>
          </a-tooltip></template
        >
        <template #expand-row="{ record }">
          <dl class="mango-callback-assertions-evidence">
            <dt>规则标识</dt><dd>{{ record.key }}</dd> <dt>投递记录</dt
            ><dd>{{ record.deliveryId || '未提供' }}</dd> <dt>事件 ID</dt
            ><dd>{{ record.eventId || '未提供' }}</dd> <dt>接收时间</dt
            ><dd>{{ record.receivedAt || '未提供' }}</dd>
          </dl>
          <template v-if="record.assertions?.length">
            <p class="mango-section-description"
              >通用断言明细仅归档方法、关系和判定结果；实际值与预期值未归档，避免泄露凭证。</p
            >
            <AssertionResult :data="record.assertions" />
          </template>
          <p v-else class="mango-section-description">{{
            record.diagnostic
              ? '诊断项不参与 Case 成败判定。'
              : '该检查项没有独立的通用字段断言明细。'
          }}</p>
        </template>
      </a-table>
      <p v-else class="mango-section-description">{{
        run.status === 'waiting'
          ? '等待回调投递，尚未生成检查结果。'
          : '未收到可供检查的回调，详见上方验证状态及失败原因。'
      }}</p>
    </section>
  </section>
</template>
<script setup lang="ts">
  import { computed, onScopeDispose, ref, watch } from 'vue'
  import { useEnum } from '@/store/modules/get-enum'
  import { getCallbackResults } from '@/api/apitest/callback'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import AssertionResult from '@/components/feedback/AssertionResult.vue'
  import {
    callbackAssertionCount,
    callbackCheckRows,
    callbackCheckResultColumns,
    callbackCheckPresentation,
    callbackNeedsDefinitions,
  } from './callback-results'
  const props = defineProps<{ runs: any[]; caseId?: number | string }>()
  const emit = defineEmits<{ (event: 'evidence', run: any): void }>()
  const enums = useEnum()
  const presentation = (check: any) => callbackCheckPresentation(check, enums)
  const definitions = ref<Record<string, any[]>>({})
  const definitionLoading = ref<Record<string, boolean>>({})
  const displayRuns = computed(() =>
    props.runs.map((run) => ({
      ...run,
      check_definitions: definitions.value[run.id] || run.check_definitions,
    }))
  )
  let requestVersion = 0
  onScopeDispose(() => {
    requestVersion++
  })
  watch(
    [
      () => props.caseId,
      () => props.runs.filter(callbackNeedsDefinitions).map((run) => run.id).join('|'),
    ],
    async () => {
      const version = ++requestVersion
      definitions.value = {}
      definitionLoading.value = {}
      if (!props.caseId) return
      const caseId = props.caseId
      const missing = props.runs.filter((run) => run.id && callbackNeedsDefinitions(run))
      await Promise.all(
        missing.map(async (run) => {
          definitionLoading.value[run.id] = true
          try {
            const response = await getCallbackResults({
              case_id: caseId,
              run_id: run.id,
              page: 1,
              page_size: 1,
            })
            if (version !== requestVersion) return
            const snapshot = response.data?.items?.find(
              (item: any) => String(item.id) === String(run.id)
            )
            if (snapshot?.check_definitions) definitions.value[run.id] = snapshot.check_definitions
          } catch {
            // 旧运行已清理或无读取权限时，保留归档判定，不借用当前编辑态定义。
          } finally {
            if (version === requestVersion) definitionLoading.value[run.id] = false
          }
        })
      )
    },
    { immediate: true }
  )
  const statusTitle = (status: string) =>
    (enums as any).api_callback_status?.find((item: any) => item.key === status)?.title || status
</script>
<style scoped>
  .mango-callback-assertions {
    min-width: 0;
  }
  .mango-callback-assertions-run + .mango-callback-assertions-run {
    margin-top: var(--m-page-gap);
  }
  .mango-callback-assertions-heading {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: var(--m-page-gap);
    margin-bottom: var(--m-page-gap);
  }
  .mango-callback-assertions-error {
    color: var(--m-danger);
    overflow-wrap: anywhere;
  }
  .mango-callback-assertions-text {
    display: block;
    overflow-wrap: anywhere;
  }
  .mango-callback-assertions-evidence {
    display: grid;
    grid-template-columns: max-content minmax(0, 1fr);
    gap: var(--m-page-gap);
    margin: 0 0 var(--m-page-gap);
  }
  .mango-callback-assertions-evidence dt {
    color: var(--m-muted);
  }
  .mango-callback-assertions-evidence dd {
    margin: 0;
    overflow-wrap: anywhere;
  }
</style>
