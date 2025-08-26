<template>
  <div class="vaw-avatar-container">
    <a-dropdown size="large" trigger="hover" @select="handleSelect">
      <div class="action-wrapper">
        <span class="nick-name"> {{ project.selectTitle }} </span>
        <icon-caret-down class="tip" />
      </div>
      <template #content>
        <a-doption v-for="item of project.data" :key="item.key" :value="item.key">
          {{ item.title }}
        </a-doption>
      </template>
    </a-dropdown>
  </div>
</template>

<script lang="ts" setup>
  import { onMounted, watchEffect } from 'vue'
  import useUserStore from '@/store/modules/user'
  import { useProject } from '@/store/modules/get-project'
  import { useDebounceFn } from '@vueuse/core'
  import { useRoute, useRouter } from 'vue-router'
  import { useProductModule } from '@/store/modules/project_module'
  import { putUserPutProject } from '@/api/user/user'

  const userStore = useUserStore()
  const project = useProject()
  const productModule = useProductModule()

  const router = useRouter()
  const route = useRoute()

  function handleSelect(key: any) {
    if (key === '选择项目') {
      key = null
    }
    putUserPutProject(userStore.userId, key)
      .then((res) => {
        userStore.selected_project = res.data.selected_project
        setTitle(key)
        productModule.getProjectModule()
      })
      .catch(console.log)
    debouncedFn()
  }

  const debouncedFn = useDebounceFn(() => {
    router.replace({ path: '/redirect' + route.path, query: route.query })
  }, 200)

  function setTitle(key: any) {
    if (key === null) {
      project.selectTitle = '选择项目'
      project.selectValue = null
      return
    }
    project.data.forEach((item: any) => {
      project.selectValue = key
      if (item.key === project.selectValue) project.selectTitle = item.title
    })
    // project.projectProductNameList(project.selectValue)
  }

  watchEffect(() => {
    if (project.data.length > 0) {
      setTitle(userStore.selected_project)
    }
  })

  onMounted(async () => {
    project.getProject()
    project.projectPytestName()
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
