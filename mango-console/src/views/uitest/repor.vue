<template>
  <div>
    <div class="main-container">
      <TableHeader :show-filter="true" title="xx时间测试用例报告" />

      <TableBody ref="tableBody">
        <template #header>
          <div class="text-lg flex-sub">
            <a-tree blockNode :data="treeData" @select="(key) => click(key[0])" />
          </div>
        </template>
      </TableBody>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { reactive } from 'vue'

function click(key: number) {
  console.log('被点击了', key)
}

const treeData = reactive([
  {
    title: '新建普通商品并完成购买和售后全流程',
    key: '0-0',
    children: [
      {
        title: 'web后台登录',
        key: '0-0-1',
        children: []
      },
      {
        title: '新建普通商品',
        key: '0-0-2',
        children: []
      },
      {
        title: '小程序下单',
        key: '0-0-3',
        children: []
      },
      {
        title: '申请售后',
        key: '0-0-4',
        children: []
      }
    ]
  },
  {
    title: '定金预售下单',
    key: '0-01',
    children: [
      {
        title: '新建定金预售商品',
        key: '0-01-0',
        children: []
      },
      {
        title: '小程序支付',
        key: '0-01-1',
        children: []
      }
    ]
  }
])
</script>
<style>
.flex {
  display: flex;
}

.flex-sub {
  flex: 1;
}
</style>
