<template>
  <div class="vaw-avatar-container">
    <a-dropdown trigger="hover" size="large" @select="handleSelect">
      <div class="action-wrapper">
        <span class="nick-name"> {{ uEnvironment.selectTitle }} </span>
        <icon-caret-down class="tip" />
      </div>
      <template #content>
        <a-doption v-for="item of uEnvironment.data" :key="item.key" :value="item.key">
          {{ item.title }}
        </a-doption>
      </template>
    </a-dropdown>
  </div>
</template>

<script lang="ts" setup>
  import { onMounted, watchEffect } from 'vue'
  import useUserStore from '@/store/modules/user'

  import { putUserEnvironment } from '@/api/user'
  import { useEnvironment } from '@/store/modules/get-environment'

  const userStore = useUserStore()
  const uEnvironment = useEnvironment()
  function handleSelect(key: any) {
    putUserEnvironment(userStore.userId, key)
      .then((res) => {
        userStore.selected_environment = res.data.selected_environment
        setTitle(key)
      })
      .catch(console.log)
  }
  function setTitle(key: any) {
    uEnvironment.selectValue = key
    if (key === null) {
      uEnvironment.selectTitle = '请选择测试环境'
      return
    }
    uEnvironment.data.forEach((item: any) => {
      if (item.key === key) {
        uEnvironment.selectTitle = item.title
      }
    })
  }
  watchEffect(() => {
    setTitle(userStore.selected_environment)
  })
  onMounted(() => {
    uEnvironment.getEnvironment()
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
