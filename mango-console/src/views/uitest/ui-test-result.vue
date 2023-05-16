<template>
  <div>
    <div class="main-container">
      <TableBody ref="tableBody">
        <template #header>
          <TableHeader :show-filter="true" title="xx时间测试用例报告" />
          <div>
            <a-split
              :style="{
                height: '750px',
                width: '100%',
                minWidth: '500px',
                border: '1px solid var(--color-border)'
              }"
              v-model:size="size"
              min="80px"
            >
              <template #first>
                <a-typography-paragraph>
                  <div>
                    <a-tree blockNode :data="treeData" @select="(key) => click(key[0])" />
                  </div>
                </a-typography-paragraph>
              </template>
              <template #second>
                <a-typography-paragraph>
                  <a-spin dot loading="true" />
                </a-typography-paragraph>
              </template>
            </a-split>
          </div>
        </template>

        <template #default></template>
        <template #footer></template>
      </TableBody>
    </div>
  </div>
</template>
<script lang="ts" setup>
import { reactive, ref } from 'vue'

const size = ref(0.4)

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

.flex-23 {
  width: 33.33%;
}

.flex-24 {
  width: 66.67%;
}
</style>
