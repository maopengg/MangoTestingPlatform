<template>
  <div class="vaw-avatar-container">
    <a-dropdown trigger="hover" size="large" @select="handleSelect">
      <div class="action-wrapper">
        <span class="nick-name"> {{ project.selectTitle }} </span>
        <icon-caret-down class="tip" />
      </div>
      <template #content>
        <a-doption v-for="item of projectList" :key="item.key" :value="item.key">
          {{ item.title }}
        </a-doption>
      </template>
    </a-dropdown>
  </div>
</template>

<script lang="ts">
  import { defineComponent, onMounted, reactive, watchEffect } from 'vue'
  import useUserStore from '@/store/modules/user'
  import { useProject } from '@/store/modules/get-project'
  import { useDebounceFn } from '@vueuse/core'
  import { useRoute, useRouter } from 'vue-router'
  import { get, put } from '@/api/http'
  import { userProjectEnvironment, userPutProject } from '@/api/url'
  import { useProjectModule } from '@/store/modules/project_module'

  export default defineComponent({
    name: 'Project',
    setup() {
      const userStore = useUserStore()
      const project = useProject()
      const projectModule = useProjectModule()

      const router = useRouter()
      const route = useRoute()
      let projectList = reactive([])
      function handleSelect(key: any) {
        if (key === '选择项目') {
          key = null
        }
        put({
          url: userPutProject,
          data: () => {
            return { id: userStore.userId, selected_project: key }
          },
        })
          .then((res) => {
            userStore.selected_project = res.data.selected_project
            setTitle(key)
            projectModule.getProjectModule()
          })
          .catch(console.log)
        debouncedFn()
      }
      const debouncedFn = useDebounceFn(() => {
        router.replace({ path: '/redirect' + route.path, query: route.query })
      }, 200)

      function setTitle(key: any) {
        projectList.push({ key: null, title: '选择项目' })
        project.data.forEach((item) => {
          projectList.push(item)
        })
        projectList.forEach((item: any) => {
          project.selectValue = key
          if (item.key === project.selectValue) project.selectTitle = item.title
        })
      }
      watchEffect(() => {
        if (project.data.length > 0) {
          setTitle(userStore.selected_project)
        }
      })

      function doRefresh() {
        get({
          url: userProjectEnvironment,
          data: () => {
            return {
              id: userStore.userId,
            }
          },
        })
          .then((res) => {
            userStore.selected_environment = res.data.selected_environment
            userStore.selected_project = res.data.selected_project
          })
          .catch(console.log)
      }
      onMounted(async () => {
        await project.getProject()
        await doRefresh()
      })

      return {
        userStore,
        projectList,
        project,
        handleSelect,
      }
    },
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
