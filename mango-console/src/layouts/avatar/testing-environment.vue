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
  import { ref, watch, watchEffect } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import useUserStore from '@/store/modules/user'

  import { updateUserConfig } from '@/api/user/user'
  import { readUserSelectedEnvironment } from '@/utils/interface-preferences'
  import { reportLoadError } from '@/utils/load-error'
  import { useEnum } from '@/store/modules/get-enum'

  const enumStore = useEnum()

  const userStore = useUserStore()
  const switching = ref(false)
  let version = 0
  watch(() => [userStore.userId, userStore.token], () => {
    version++
    switching.value = false
  }, { flush: 'sync' })

  async function handleSelect(key: number | string) {
    if (switching.value) return
    const current = version
    switching.value = true
    try {
      const res = await updateUserConfig([{ key: 'selected_environment', value: Number(key) }])
      if (current !== version) return
      setTitle(readUserSelectedEnvironment(res))
      Message.success(res.msg)
    } catch (error) {
      if (current === version) reportLoadError(error, '测试环境切换失败，请重试')
    } finally {
      if (current === version) switching.value = false
    }
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
