<template>
  <a-modal
    v-model:visible="visible"
    @cancel="close"
    :title="`${entityRuleRecord?.name || ''} 字段规则`"
    :width="1180"
    :footer="false"
  >

    <div class="mango-entity-rule-toolbar">
      <a-tag color="arcoblue">当前表：{{ entityRuleRecord?.table_name || '-' }}</a-tag>
    </div>
    <div class="mango-entity-rule-table-region">
      <a-table
        class="mango-native-scroll-table"
        size="small"
        :columns="entityRuleColumns"
        :data="entityRuleRows"
        :loading="entityRuleLoading"
        :pagination="false"
        :scroll="{ x: entityRuleTableScrollWidth, y: '100%' }"
        row-key="id"
      >
        <template #columns>
          <a-table-column
            v-for="item of entityRuleColumns"
            :key="item.key"
            :align="item.align"
            :data-index="item.key"
            :fixed="item.fixed"
            :ellipsis="item.ellipsis"
            :tooltip="item.tooltip"
            :title="item.title"
            :width="item.width"
          >
            <template v-if="item.key === 'generator_type'" #cell="{ record }">
              <a-select
                :model-value="generatorTypeTitle(record.generator_type)"
                :options="[generatorTypeTitle(record.generator_type)]"
                disabled
                :title="generatorTypeTitle(record.generator_type)"
                :aria-label="`${record.name} 生成方式（只读）`"
              />
            </template>
            <template v-else-if="item.key === 'generator_config'" #cell="{ record }">
              <a-tooltip :content="getGeneratorDisplay(record).text">
                <a-select
                  v-if="getGeneratorDisplay(record).enum"
                  :model-value="getGeneratorDisplay(record).text"
                  :options="[getGeneratorDisplay(record).text]"
                  disabled
                  :aria-label="`${record.name} 枚举配置（只读）`"
                />
                <a-input
                  v-else
                  :model-value="getGeneratorDisplay(record).text"
                  readonly
                  :disabled="getGeneratorDisplay(record).automatic"
                  :aria-label="`${record.name} 生成配置（只读）`"
                />
              </a-tooltip>
            </template>
            <template
              v-else-if="
                ['nullable', 'primary_key', 'autoincrement', 'db_type', 'platform_type'].includes(
                  item.key
                )
              "
              #cell="{ record }"
            >
              <DataFactoryFieldTag :record="record" :field="item.key" />
            </template>
          </a-table-column>
        </template>
      </a-table>
    </div>
  </a-modal>
</template>
<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { ref, watch } from 'vue'
  import { useRoute } from 'vue-router'
  import { Message } from '@arco-design/web-vue'
  import { getDataFactoryEntity, getDataFactoryField } from '@/api/data-factory'
  import { useEnum } from '@/store/modules/get-enum'
  import DataFactoryFieldTag from '@/components/display/DataFactoryFieldTag.vue'
  import { entityRuleColumns, entityRuleTableScrollWidth } from '../config'
  import { getGeneratorDisplay } from '../generatorDisplay'
  import type { EntityRecord, FieldRecord, Id } from '../types'
  import { useTemplateScope } from '../../composables/useTemplateScope'
  const enumStore = useEnum(),
    visible = ref(false),
    entityRuleLoading = ref(false),
    loadError = ref(false)
  const entityRuleRecord = ref<EntityRecord | null>(null),
    entityRuleRows = ref<FieldRecord[]>([])
  const entityId = ref<Id | null>(null)
  let sequence = 0
  const scope = useTemplateScope(close)
  const route = useRoute()
  watch(() => [route.query.template_id, route.query.test_env], close, { flush: 'sync' })
  function close() {
    ++sequence
    visible.value = false
    entityId.value = null
    entityRuleRecord.value = null
    entityRuleRows.value = []
    entityRuleLoading.value = false
    loadError.value = false
  }
  function open(id: Id) {
    if (!scope.isActive()) return
    close()
    entityId.value = id
    visible.value = true
    void loadRules()
  }
  async function loadRules() {
    if (!scope.isActive() || !visible.value || entityId.value === null) return
    const id = entityId.value,
      request = ++sequence,
      version = scope.snapshot()
    entityRuleLoading.value = true
    loadError.value = false
    try {
      const [entity, fields] = await Promise.all([
        getDataFactoryEntity({ id, page: 1, pageSize: 1 }),
        getDataFactoryField({ entity: id }),
      ])
      if (request !== sequence || !scope.current(version)) return
      entityRuleRecord.value = entity.data?.[0] ?? null
      entityRuleRows.value = fields.data || []
      if (!entityRuleRecord.value) Message.warning('数据实体不存在或已被删除')
    } catch (loadFailure0) {
      if (request === sequence && scope.current(version)) (reportLoadError(loadFailure0, "加载失败，请重试", false), loadError.value = true)
    } finally {
      if (request === sequence) entityRuleLoading.value = false
    }
  }
  function generatorTypeTitle(value?: string | number) {
    return (
      enumStore.data_factory_generator_type?.find(
        (item: { key: string | number; title: string }) => String(item.key) === String(value)
      )?.title ?? String(value ?? '-')
    )
  }
  defineExpose({ open, close })
</script>
<style scoped>
  .mango-entity-rule-toolbar {
    margin-bottom: var(--m-page-gap);
  }
  .mango-entity-rule-table-region {
    height: min(460px, 65vh);
    min-width: 0;
    min-height: 0;
    overflow: hidden;
  }
</style>
