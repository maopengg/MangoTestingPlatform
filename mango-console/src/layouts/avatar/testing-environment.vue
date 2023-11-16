<template>
  <div class="vaw-avatar-container">
    <a-dropdown trigger="hover" size="large" @select="handleSelect">
      <div class="action-wrapper">
        <span class="nick-name"> {{ title.title }} </span>
        <icon-caret-down class="tip" />
      </div>
      <template #content>
        <a-doption v-for="item of testObj.data" :key="item.key" :value="item.key">
          {{ item.title }}
        </a-doption>
      </template>
    </a-dropdown>
  </div>
</template>

<script lang="ts">
import { Message } from '@arco-design/web-vue'
import { defineComponent, onMounted, reactive } from 'vue'
import useUserStore from '@/store/modules/user'
import { useTestObj } from '@/store/modules/get-test-obj'
import { get } from '@/api/http'
import { sendCommonParameters } from '@/api/url'

export default defineComponent({
  name: 'TestEnvironment',
  setup() {
    const userStore = useUserStore()
    const testObj = useTestObj()
    const title = reactive({
      title: '选择测试环境'
    })
    function handleSelect(key: number) {
      get({
        url: sendCommonParameters,
        data: () => {
          return {
            test_obj_id: key
          }
        }
      })
        .then((res) => {
          Message.success(res.msg)
          testObj.selectValue = key
          testObj.data.forEach((item: any) => {
            if (item.key === testObj.selectValue) title.title = item.title
          })
        })
        .catch()
    }

    onMounted(() => {
      testObj.getEnvironment()
    })

    return {
      userStore,
      testObj,
      title,
      handleSelect
    }
  }
})
</script>

<style lang="less" scoped>
.vaw-avatar-container {
  .action-wrapper {
    display: flex;
    align-items: center;

    .avatar {
      display: flex;
      align-items: center;

      & > img {
        border: 1px solid #f6f6f6;
        width: 100%;
        height: 100%;
        object-fit: cover;
        border-radius: 50%;
      }
    }

    .nick-name {
      margin: 0 5px;

      .tip {
        transform: rotate(0);
        transition: transform @transitionTime;
        margin-left: 2px;
      }
    }
  }
}

.vaw-avatar-container:hover {
  cursor: pointer;
  color: var(--primary-color);

  .tip {
    transform: rotate(180deg);
    transition: transform @transitionTime;
  }
}
</style>
