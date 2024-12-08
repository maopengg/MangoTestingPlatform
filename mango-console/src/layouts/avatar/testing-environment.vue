<template>
  <div class="vaw-avatar-container">
    <a-dropdown trigger="hover" size="large" @select="handleSelect">
      <div class="action-wrapper">
        <span class="nick-name"> {{ userStore.selected_environment_title }} </span>
        <icon-caret-down class="tip" />
      </div>
      <template #content>
        <a-doption v-for="item of enumStore.environment_type" :key="item.key" :value="item.key">
          {{ item.title }}
        </a-doption>
      </template>
    </a-dropdown>
  </div>
</template>

<script lang="ts" setup>
  import { onMounted, watchEffect } from 'vue'
  import useUserStore from '@/store/modules/user'

  import { putUserEnvironment } from '@/api/user/user'
  import { useEnum } from '@/store/modules/get-enum'
  const enumStore = useEnum()

  const userStore = useUserStore()
  function handleSelect(key: any) {
    putUserEnvironment(userStore.userId, key)
      .then((res) => {
        userStore.selected_environment = res.data.selected_environment
        setTitle(key)
      })
      .catch(console.log)
  }
  function setTitle(key: any) {
    userStore.selected_environment = key
    if (key === null) {
      userStore.selected_environment_title = '请选择测试环境'
      return
    }
    if (!enumStore.environment_type) {
      enumStore.getEnum()
    }
    enumStore.environment_type.forEach((item: any) => {
      if (item.key === key) {
        userStore.selected_environment_title = item.title
      }
    })
  }
  watchEffect(() => {
    setTitle(userStore.selected_environment)
  })
  onMounted(() => {})
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
