<template>
  <div class="vaw-avatar-container">
    <a-dropdown trigger="hover" size="large" @select="handleSelect">
      <div class="action-wrapper">
        <span class="nick-name"> {{ testObj.selectTitle }} </span>
        <icon-caret-down class="tip" />
      </div>
      <template #content>
        <a-doption v-for="item of testObjList" :key="item.key" :value="item.key">
          {{ item.title }}
        </a-doption>
      </template>
    </a-dropdown>
  </div>
</template>

<script lang="ts">
import { Message } from '@arco-design/web-vue'
import { defineComponent, onMounted, reactive, watchEffect } from 'vue'
import useUserStore from '@/store/modules/user'
import { useTestObj } from '@/store/modules/get-test-obj'
import { get, put } from '@/api/http'
import { putEnvironment, sendCommonParameters } from '@/api/url'

export default defineComponent({
  name: 'TestEnvironment',
  setup() {
    const userStore = useUserStore()
    const testObj = useTestObj()
    let testObjList = reactive([])
    function handleSelect(key: any) {
      if (key === '选择测试环境') {
        key = null
      }
      put({
        url: putEnvironment,
        data: () => {
          return { id: userStore.userId, selected_environment: key }
        }
      })
        .then((res) => {
          userStore.selected_environment = res.data.selected_environment
          setTitle(key)
        })
        .catch(console.log)
      if (key !== null) {
        get({
          url: sendCommonParameters,
          data: () => {
            return {
              test_obj_id: key
            }
          }
        })
          .then((res) => {
            if (res.code === 200 && res.msg.includes('处理参数完成')) Message.success(res.msg)
          })
          .catch()
      }
    }
    function setTitle(key: any) {
      testObjList.push({ key: null, title: '选择测试环境' })
      testObj.data.forEach((item) => {
        testObjList.push(item)
      })
      testObjList.forEach((item: any) => {
        testObj.selectValue = key
        if (item.key === testObj.selectValue) testObj.selectTitle = item.title
      })
    }
    watchEffect(() => {
      if (testObj.data.length > 0) {
        setTitle(userStore.selected_environment)
      }
    })
    onMounted(() => {
      testObj.getEnvironment()
    })

    return {
      userStore,
      testObj,
      testObjList,
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
