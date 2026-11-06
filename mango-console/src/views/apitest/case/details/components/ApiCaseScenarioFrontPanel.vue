<!-- eslint-disable vue/no-mutating-props -->
<template>
  <a-tabs :active-key="activeKey" @tab-click="emit('change', String($event))">
    <template #extra>
      <a-button v-if="canAdd" size="small" type="primary" :disabled="editLocked" @click="addItem"
        >增加</a-button
      >
    </template>
    <a-tab-pane key="10" title="前置数据库">
      <div class="m-2">
        <DataSourceOperationList
          :data-list="item.front_sql"
          :datasource-options="datasourceOptions"
          :environment-options="environmentOptions"
          :project-product-id="projectProductId"
          :test-env="testEnv"
          :on-delete-item="removeSql"
          :on-save="saveSql"
          @update:item="updateSql"
          empty-text="暂无数据库操作配置，点击上方“增加”按钮添加"
        />
      </div>
    </a-tab-pane>
    <a-tab-pane key="11" title="前置函数">
      <div class="m-2">
        <CodeEditor
          v-model="item.front_func"
          :readonly="editLocked"
          :line-height="280"
          :code-style="{ width: '100%' }"
          placeholder="根据帮助文档，输入自定义前置函数"
          @blur="saveCode"
        />
      </div>
    </a-tab-pane>
    <a-tab-pane key="12" title="数据工厂">
      <div class="m-2">
        <DataFactoryCaseConfigPanel
          v-if="active"
          ref="factoryPanel"
          :case-id="item.id"
          :project-product-id="String(projectProductId || '')"
          :source-type="3"
          @count-change="emit('count-change', item.id, $event)"
        />
      </div>
    </a-tab-pane>
  </a-tabs>
</template>

<script setup lang="ts">
  /* eslint-disable vue/no-mutating-props */
  import { computed, ref } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { useApiCaseParameterSave } from '../composables/useApiCaseAutoSave'
  import CodeEditor from '@/components/editors/CodeEditor.vue'
  import DataFactoryCaseConfigPanel from '@/components/DataFactory/CaseConfigPanel.vue'
  import DataSourceOperationList from '@/components/forms/DataSourceOperationList.vue'

  const props = withDefaults(
    defineProps<{
      item: any
      activeKey: string
      active: boolean
      editLocked: boolean
      datasourceOptions?: any[]
      environmentOptions?: any[]
      projectProductId?: string | number
      testEnv?: string | number
    }>(),
    {
      datasourceOptions: () => [],
      environmentOptions: () => [],
    }
  )
  const emit = defineEmits<{
    (event: 'change', value: string): void
    (event: 'count-change', id: number, count: number): void
  }>()
  const factoryPanel = ref<InstanceType<typeof DataFactoryCaseConfigPanel> | null>(null)
  const putApiCaseDetailedParameter = useApiCaseParameterSave()
  const canAdd = computed(() => ['10', '12'].includes(props.activeKey))

  async function save(field: 'front_sql' | 'front_func') {
    if (props.editLocked) return
    try {
      const response = await putApiCaseDetailedParameter({
        id: props.item.id,
        [field]: props.item[field],
      })
      if (response) Message.success(response.msg)
    } catch (error: any) {
      Message.error(error?.msg || '前置处理保存失败')
    }
  }
  function addItem() {
    if (props.editLocked) return
    if (props.activeKey === '10')
      props.item.front_sql.push({ key: '', value: '', datasource_alias: null, test_envs: [] })
    if (props.activeKey === '12') factoryPanel.value?.open()
  }
  function removeSql(index: number) {
    if (props.editLocked) return
    props.item.front_sql.splice(index, 1)
    void save('front_sql')
  }
  function updateSql(index: number, value: any) {
    if (props.editLocked) return
    props.item.front_sql[index] = value
    void save('front_sql')
  }
  function saveSql() {
    void save('front_sql')
  }
  function saveCode() {
    void save('front_func')
  }
</script>
