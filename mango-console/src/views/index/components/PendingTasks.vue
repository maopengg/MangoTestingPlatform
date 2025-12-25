<template>
  <div style="height: 433px">
    <a-table
      :bordered="true"
      :columns="(tableColumns as any)"
      :data="(dataList as any)"
      :loading="(loading as any)"
      :pagination="false"
      :rowKey="(rowKey as any)"
      :scrollbar="true"
      :scroll="{ y: '100%' }"
      class="pending-tasks-table"
    >
      <template #columns>
        <a-table-column
          v-for="item of (tableColumns as any)"
          :key="(item.key as any)"
          :align="(item.align as any)"
          :data-index="(item.key as any)"
          :ellipsis="(item.ellipsis as any)"
          :fixed="(item.fixed as any)"
          :title="(item.title as any)"
          :tooltip="(item.tooltip as any)"
          :width="(item.width as any)"
        >
          <template v-if="(item.key as any) === 'index'" #cell="{ record }">
            <span style="width: 110px; display: inline-block">{{ record.id }}</span>
          </template>
          <template v-else-if="(item.key as any) === 'timing_strategy'" #cell="{ record }">
            {{ record.timing_strategy?.name }}
          </template>
          <template v-else-if="(item.key as any) === 'case_people'" #cell="{ record }">
            {{ record.case_people?.name }}
          </template>
          <template v-else-if="(item.key as any) === 'test_env'" #cell="{ record }">
            <a-tag :color="(enumStore as any).colors[record.test_env]" size="small">
              {{
                record.test_env !== null
                  ? (enumStore as any).environment_type[record.test_env].title
                  : ''
              }}
            </a-tag>
          </template>
        </a-table-column>
      </template>
    </a-table>
  </div>
</template>
<script lang="ts" setup>
  import { useRowKey, useTableColumn } from '@/hooks/table'
  import { useEnum } from '@/store/modules/get-enum'
  import { getSystemTasks } from '@/api/system/tasks'
  import { ref, onMounted } from 'vue'

  const rowKey = useRowKey('id')
  const enumStore = useEnum()
  // 组件内部数据
  const dataList = ref([])
  const loading = ref(true)

  // 组件内部定义表格列
  const tableColumns = useTableColumn([
    {
      title: 'ID',
      key: 'index',
      width: 100,
      dataIndex: 'index',
      align: 'center',
    },
    {
      title: '任务名称',
      key: 'name',
      dataIndex: 'name',
      align: 'left',
      ellipsis: true,
      tooltip: true,
    },
    {
      title: '定时策略',
      key: 'timing_strategy',
      dataIndex: 'timing_strategy',
      align: 'left',
      ellipsis: true,
      tooltip: true,
    },
    {
      title: '测试对象',
      key: 'test_env',
      dataIndex: 'test_env',
      width: 100,
    },
    {
      title: '负责人',
      key: 'case_people',
      dataIndex: 'case_people',
      width: 120,
    },
  ])

  // 获取数据的方法
  function fetchData() {
    loading.value = true
    getSystemTasks({
      pageSize: 100,
      page: 1,
    })
      .then((res) => {
        dataList.value = res.data
        loading.value = false
      })
      .catch((error) => {
        console.log(error)
        loading.value = false
      })
  }

  // 组件挂载时获取数据
  onMounted(() => {
    fetchData()
  })

  // 暴露刷新方法给父组件
  defineExpose({
    refresh: fetchData,
  })
</script>
