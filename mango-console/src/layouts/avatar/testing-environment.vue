<template>
  <div class="vaw-avatar-container">
    <a-dropdown trigger="hover" size="large" @select="handleSelect">
      <div class="action-wrapper">
        <span class="nick-name"> {{ testObj.selectTitle }} </span>
        <icon-caret-down class="tip" />
      </div>
      <template #content>
        <template v-for="item of testObj.data">
          <template v-if="item.children && item.children.length > 0">
            <a-dsubmenu :value="item.label" :key="item.value">
              <template #default>
                {{ item.label }}
              </template>
              <template #content>
                <a-doption v-for="n of item.children" :key="n.value" :value="n.value">
                  {{ n.label }}
                </a-doption>
              </template>
            </a-dsubmenu>
          </template>
          <template v-else-if="item.value === -1">
            <a-doption :key="item.value" :value="item.value">
              {{ item.label }}
            </a-doption>
          </template>
          <template v-else>
            <a-doption :key="item.value" :value="item.value" disabled>
              {{ item.label }}
            </a-doption>
          </template>
        </template>
      </template>
    </a-dropdown>
  </div>
</template>

<script lang="ts" setup>
  import { onMounted, watchEffect } from 'vue'
  import useUserStore from '@/store/modules/user'
  import { useTestObj } from '@/store/modules/get-test-obj'

  import { putUserEnvironment } from '@/api/user'

  const userStore = useUserStore()
  const testObj = useTestObj()
  function handleSelect(key: any) {
    if (key === -1) {
      key = null
    }
    putUserEnvironment(userStore.userId, key)
      .then((res) => {
        userStore.selected_environment = res.data.selected_environment
        testObj.selectValue = key
        setTitle(key)
      })
      .catch(console.log)
  }
  function setTitle(key: any) {
    if (key === null) {
      testObj.selectTitle = '请选择测试环境'
      testObj.selectValue = null
      return
    }
    testObj.data.forEach((item: any) => {
      if (item.children.length > 0) {
        testObj.selectValue = key
        item.children.forEach((children: any) => {
          if (children.value === key) testObj.selectTitle = `${item.label}/${children.label}`
        })
      }
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
