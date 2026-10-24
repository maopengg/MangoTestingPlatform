<template>
  <div class="mango-avatar-container">
    <a-dropdown size="large" trigger="hover" :disabled="switching" @select="handleSelect">
      <div class="mango-action-wrapper">
        <span class="mango-nick-name"> {{ userStore.selected_environment_title }} </span>
        <a-spin v-if="switching" :size="12" />
        <icon-caret-down v-else class="mango-tip" />
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
  import { ref, watchEffect } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import useUserStore from '@/store/modules/user'

  import { putUserEnvironment } from '@/api/user/user'
  import { useEnum } from '@/store/modules/get-enum'

  const enumStore = useEnum()

  const userStore = useUserStore()
  const switching = ref(false)

  function handleSelect(key: any) {
    if (switching.value) return
    switching.value = true
    putUserEnvironment(userStore.userId, key)
      .then((res) => {
        userStore.selected_environment = res.data.selected_environment
        setTitle(res.data.selected_environment)
        Message.success(res.msg)
      })
      .catch(console.log)
      .finally(() => {
        switching.value = false
      })
  }

  function setTitle(key: any) {
    userStore.selected_environment = key
    if (key === null) {
      userStore.selected_environment_title = '请选择测试环境'
      return
    }
    if (enumStore.environment_type) {
      enumStore.environment_type.forEach((item: any) => {
        if (item.key === key) {
          userStore.selected_environment_title = item.title
        }
      })
    }
  }

  watchEffect(() => {
    setTitle(userStore.selected_environment)
  })
</script>

<style lang="less" scoped>
  .mango-avatar-container {
    .mango-action-wrapper {
      display: flex;
      align-items: center;

      .mango-avatar {
        display: flex;
        align-items: center;

        & > img {
          border: 1px solid var(--m-border);
          width: 100%;
          height: 100%;
          object-fit: cover;
          border-radius: 50%;
        }
      }

      .mango-nick-name {
        margin: 0 4px;
        font-size: 14px;

        .mango-tip {
          transform: rotate(0);
          transition: transform @transitionTime;
          margin-left: 2px;
        }
      }
    }
  }

  .mango-avatar-container:hover {
    cursor: pointer;
    color: var(--m-primary);

    .mango-tip {
      transform: rotate(180deg);
      transition: transform @transitionTime;
    }
  }
</style>
