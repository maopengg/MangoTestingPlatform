<template>
  <div class="stats-container">
    <!-- UI自动化统计 -->
    <div class="stats-category">
      <div class="category-title">UI自动化</div>
      <a-grid :cols="4" :colGap="8" :rowGap="8">
        <a-grid-item>
          <a-statistic
            title="元素个数"
            :value="uiStats.elementCount || 0"
            :value-style="{ color: 'var(--m-chart-1)' }"
          />
        </a-grid-item>
        <a-grid-item>
          <a-statistic
            title="页面个数"
            :value="uiStats.pageCount || 0"
            :value-style="{ color: 'var(--m-chart-3)' }"
          />
        </a-grid-item>
        <a-grid-item>
          <a-statistic
            title="步骤个数"
            :value="uiStats.stepCount || 0"
            :value-style="{ color: 'var(--m-success)' }"
          />
        </a-grid-item>
        <a-grid-item>
          <a-statistic
            title="用例个数"
            :value="uiStats.caseCount || 0"
            :value-style="{ color: 'var(--m-chart-5)' }"
          />
        </a-grid-item>
      </a-grid>
    </div>

    <!-- API自动化统计 -->
    <div class="stats-category">
      <div class="category-title">API自动化</div>
      <a-grid :cols="3" :colGap="8" :rowGap="8">
        <a-grid-item>
          <a-statistic
            title="接口个数"
            :value="apiStats.interfaceCount || 0"
            :value-style="{ color: 'var(--m-chart-1)' }"
          />
        </a-grid-item>
        <a-grid-item>
          <a-statistic
            title="用例个数"
            :value="apiStats.caseCount || 0"
            :value-style="{ color: 'var(--m-chart-3)' }"
          />
        </a-grid-item>
        <a-grid-item>
          <a-statistic
            title="Headers个数"
            :value="apiStats.headersCount || 0"
            :value-style="{ color: 'var(--m-success)' }"
          />
        </a-grid-item>
      </a-grid>
    </div>

    <!-- Pytest自动化统计 -->
    <div class="stats-category">
      <div class="category-title">Pytest自动化</div>
      <a-grid :cols="4" :colGap="8" :rowGap="8">
        <a-grid-item>
          <a-statistic
            title="过程对象"
            :value="pytestStats.processObjects || 0"
            :value-style="{ color: 'var(--m-chart-1)' }"
          />
        </a-grid-item>
        <a-grid-item>
          <a-statistic
            title="用例个数"
            :value="pytestStats.caseCount || 0"
            :value-style="{ color: 'var(--m-chart-3)' }"
          />
        </a-grid-item>
        <a-grid-item>
          <a-statistic
            title="工具文件"
            :value="pytestStats.toolFiles || 0"
            :value-style="{ color: 'var(--m-success)' }"
          />
        </a-grid-item>
        <a-grid-item>
          <a-statistic
            title="测试文件"
            :value="pytestStats.testFiles || 0"
            :value-style="{ color: 'var(--m-chart-5)' }"
          />
        </a-grid-item>
      </a-grid>
    </div>

    <!-- 数据工厂统计 -->
    <div class="stats-category">
      <div class="category-title">数据工厂</div>
      <a-grid :cols="4" :colGap="8" :rowGap="8">
        <a-grid-item>
          <a-statistic
            title="数据源"
            :value="dataFactoryStats.datasourceCount || 0"
            :value-style="{ color: 'var(--m-chart-1)' }"
          />
        </a-grid-item>
        <a-grid-item>
          <a-statistic
            title="工厂实体"
            :value="dataFactoryStats.entityCount || 0"
            :value-style="{ color: 'var(--m-chart-3)' }"
          />
        </a-grid-item>
        <a-grid-item>
          <a-statistic
            title="场景模板"
            :value="dataFactoryStats.templateCount || 0"
            :value-style="{ color: 'var(--m-success)' }"
          />
        </a-grid-item>
        <a-grid-item>
          <a-statistic
            title="执行记录"
            :value="dataFactoryStats.executionCount || 0"
            :value-style="{ color: 'var(--m-chart-5)' }"
          />
        </a-grid-item>
      </a-grid>
    </div>
  </div>
</template>

<script lang="ts" setup>
  import { ref, onMounted } from 'vue'
  import { getSystemIndexStatistics } from '@/api/system'

  // 定义响应式数据
  const uiStats = ref({
    elementCount: 0,
    pageCount: 0,
    stepCount: 0,
    caseCount: 0,
  })

  const apiStats = ref({
    interfaceCount: 0,
    caseCount: 0,
    headersCount: 0,
  })

  const pytestStats = ref({
    processObjects: 0,
    caseCount: 0,
    toolFiles: 0,
    testFiles: 0,
  })

  const dataFactoryStats = ref({
    datasourceCount: 0,
    entityCount: 0,
    templateCount: 0,
    executionCount: 0,
  })

  // 获取统计数据
  const fetchStatistics = async () => {
    try {
      const res = await getSystemIndexStatistics()
      uiStats.value = res.data.uiStats
      apiStats.value = res.data.apiStats
      pytestStats.value = res.data.pytestStats
      dataFactoryStats.value = res.data.dataFactoryStats || dataFactoryStats.value
    } catch (error) {
      console.log(error)
    }
  }

  onMounted(() => {
    fetchStatistics()
  })

  // 暴露刷新方法
  defineExpose({
    refresh: fetchStatistics,
  })
</script>

<style lang="less" scoped>
  // 自动化测试统计容器样式
  .stats-container {
    padding: 6px;
    margin-top: 6px;
    max-height: 300px;
    overflow-y: auto;
    border-radius: 6px;
    background-color: var(--m-surface-soft);
    // 隐藏滚动条但保持滚动功能
    &::-webkit-scrollbar {
      display: none; // Chrome Safari
    }
    scrollbar-width: none; // Firefox
    -ms-overflow-style: none; // IE 10+
  }

  .stats-category {
    padding: 6px;
    margin-top: 6px;
    border-radius: 6px;
    background-color: var(--m-surface);
    border: 1px solid var(--m-border);

    .category-title {
      font-size: 13px;
      font-weight: 600;
      color: var(--m-text);
      margin-bottom: 5px;
      padding-bottom: 2px;
      border-bottom: 1px solid var(--m-border);
    }
  }

  .stats-category:first-child {
    margin-top: 0;
  }

  :deep(.arco-statistic) {
    .arco-statistic-title {
      font-size: 11px;
      color: var(--m-muted);
      margin-bottom: 2px;
    }

    .arco-statistic-content {
      font-size: 14px;
      font-weight: 600;
    }
  }

  :deep(.arco-grid-item) {
    padding: 4px;
    border-radius: 4px;
    background-color: var(--m-surface);
    transition: all 0.2s ease;

    &:hover {
      background-color: var(--m-primary-soft);
      transform: translateY(-1px);
    }
  }
</style>
