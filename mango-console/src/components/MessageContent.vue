<template>
  <a-list :bordered="false" size="small" :style="{ width: '350px' }">
    <a-list-item v-for="(item, index) of data" :key="index">
      <a-list-item-meta :title="item.title" :description="item.description">
        <template #avatar>
          <template v-if="item.status === 1">
            <a-avatar :style="{ backgroundColor: '#2ECC71' }">
              <icon-check />
            </a-avatar>
          </template>
          <template v-else>
            <a-avatar :style="{ backgroundColor: '#E74C3C' }">
              <icon-close />
            </a-avatar>
          </template>
        </template>
      </a-list-item-meta>
    </a-list-item>
  </a-list>
</template>

<script lang="ts" setup>
  import { reactive } from 'vue'

  const data = reactive([
    {
      title: '功能未完善',
      description: '示例内容示例内容示例内容示例内容示例内容示例内容示例内容示例内容示例内容',
      status: 0,
    },
    {
      title: '前端自动化',
      description:
        '用例运行总数: 83 个\n' +
        '            通过用例个数: 58 个\n' +
        '            失败用例个数: 0 个\n' +
        '            异常用例个数: 0 个\n' +
        '            跳过用例个数: 暂不统计 个\n' +
        '            成  功   率: 69.88 %',
      status: 1,
    },
    {
      title: '接口自动化',
      description:
        '用例运行总数: 83 个\n' +
        '            通过用例个数: 58 个\n' +
        '            失败用例个数: 0 个\n' +
        '            异常用例个数: 0 个\n' +
        '            跳过用例个数: 暂不统计 个\n' +
        '            成  功   率: 69.88 %',
      status: 0,
    },
    {
      title: '性能自动化',
      description: '响应时间: 83 个\n',
      status: 1,
    },
  ])
</script>
<style lang="less" scoped>
  :deep(.arco-list-medium > .arco-list-content > .arco-list-item) {
    padding: 0 !important;
  }
</style>
