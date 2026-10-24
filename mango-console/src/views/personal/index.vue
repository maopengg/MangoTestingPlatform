<template>
  <TableBody ref="tableBody">
    <main class="mango-personal-page">
      <section class="mango-section-card mango-personal-profile">
        <header class="mango-personal-profile__header">
          <div class="mango-personal-profile__identity">
            <a-avatar :size="72" class="mango-personal-profile__avatar">
              <icon-user />
            </a-avatar>
            <div class="mango-personal-profile__name">
              <h2>{{ personalCenterData.data.name || userStore.nickName || '-' }}</h2>
              <p>{{ personalCenterData.data.username || '-' }}</p>
              <a-tag size="small">{{ personalCenterData.data.role?.name || '未分配角色' }}</a-tag>
            </div>
          </div>
        </header>

        <dl class="mango-personal-profile__details">
          <div class="mango-personal-profile__detail">
            <dt>最近登录时间</dt>
            <dd>{{ personalCenterData.data.last_login_time || '-' }}</dd>
          </div>
          <div class="mango-personal-profile__detail">
            <dt>登录 IP</dt>
            <dd>{{ personalCenterData.data.ip || '-' }}</dd>
          </div>
        </dl>

        <div class="mango-personal-profile__actions">
          <a-button
            long
            size="small"
            @click="onUpdate"
            data-testid="qa-views-personal-button-修改密码"
          >
            修改密码
          </a-button>
        </div>
      </section>

      <UserCachePanel />
    </main>
  </TableBody>
  <ModalDialog ref="modalDialogRef" :title="personalCenterData.actionTitle" @confirm="onDataForm">
    <template #content>
      <a-form :model="formModel">
        <a-form-item
          v-for="item of visibleFormItems"
          :key="item.key"
          :class="[item.required ? 'mango-form-item__require' : 'mango-form-item__no_require']"
          :label="item.label"
        >
          <template v-if="item.key === 'email'">
            <a-input v-model="item.value" :placeholder="item.placeholder" allow-clear>
              <template #prefix><icon-email /></template>
            </a-input>
          </template>
          <template v-else-if="item.type === 'input'">
            <a-input-password v-model="item.value" :placeholder="item.placeholder" allow-clear />
          </template>
          <template v-if="item.key === 'email' || item.key === 'new_password'" #extra>
            <span v-if="item.key === 'email'"> 修改成功后，原账号将停用，请使用该邮箱登录。 </span>
            <span v-else>至少8位，并包含大写字母、小写字母、数字和特殊字符。</span>
          </template>
        </a-form-item>
      </a-form>
    </template>
  </ModalDialog>
</template>

<script lang="ts" setup>
  import useUserStore from '@/store/modules/user'
  import { computed, nextTick, onMounted, reactive, ref } from 'vue'

  import { FormItem, ModalDialogType } from '@/types/components'
  import { Message } from '@arco-design/web-vue'
  import { getFormItems } from '@/utils/datacleaning'
  import { getUserInfo, postUserPassword } from '@/api/user/user'
  import UserCachePanel from './components/UserCachePanel.vue'

  const userStore = useUserStore()
  const formModel = ref({})
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const personalCenterData = reactive({
    actionTitle: '修改密码',
    data: {} as any,
  })
  const formItems: FormItem[] = reactive([
    {
      label: '原始密码',
      key: 'password',
      value: '',
      placeholder: '请输入原始密码',
      required: true,
      type: 'input',
      validator: function () {
        if (!this.value) {
          Message.error(this.placeholder || '')
          return false
        }
        return true
      },
    },
    {
      label: '登录邮箱',
      key: 'email',
      value: '',
      placeholder: '请输入新的登录邮箱',
      required: true,
      type: 'input',
      validator: function () {
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(this.value || ''))) {
          Message.error('请输入正确的邮箱地址')
          return false
        }
        return true
      },
    },
    {
      label: '新密码',
      key: 'new_password',
      value: null,
      type: 'input',
      required: true,
      placeholder: '请输入新密码',
      validator: function () {
        if (!this.value && this.value !== 0) {
          Message.error(this.placeholder || '')
          return false
        }
        return true
      },
    },
    {
      label: '确认密码',
      key: 'confirm_password',
      value: '',
      type: 'input',
      required: true,
      placeholder: '请输入确认密码',
      validator: function () {
        if (!this.value) {
          Message.error(this.placeholder || '')
          return false
        }
        return true
      },
    },
  ])
  const visibleFormItems = computed(() =>
    formItems.filter(
      (item) => item.key !== 'email' || personalCenterData.data.requires_email_login_migration
    )
  )

  function onUpdate() {
    modalDialogRef.value?.toggle()
    nextTick(() => {
      formItems.forEach((it) => {
        it.value = ''
      })
    })
  }

  function doRefresh() {
    getUserInfo({
      id: userStore.userId,
    })
      .then((res) => {
        if (res.data) {
          personalCenterData.data = res.data[0]
        }
      })
      .catch(console.log)
  }

  function onDataForm() {
    if (visibleFormItems.value.every((it) => (it.validator ? it.validator() : true))) {
      let value = getFormItems(visibleFormItems.value)
      value['id'] = userStore.userId
      postUserPassword(value)
        .then((res) => {
          modalDialogRef.value?.toggle()
          Message.success(res.msg)
          userStore.logout().then(() => {
            window.localStorage.removeItem('visited-routes')
            window.location.reload()
            localStorage.clear()
          })
        })
        .catch((error) => {
          console.log(error)
        })
        .finally(() => {
          modalDialogRef.value?.setConfirmLoading(false)
        })
    } else {
      modalDialogRef.value?.setConfirmLoading(false)
    }
  }

  onMounted(() => {
    nextTick(async () => {
      doRefresh()
    })
  })
</script>
<style lang="less" scoped>
  .mango-personal-page {
    display: grid;
    grid-template-columns: 320px minmax(0, 1fr);
    align-items: start;
    gap: var(--m-page-gap);
    width: 100%;
  }

  .mango-personal-profile {
    padding: 20px;
  }

  .mango-personal-profile__header,
  .mango-personal-profile__identity {
    display: flex;
    align-items: center;
  }

  .mango-personal-profile__header {
    justify-content: center;
    padding-bottom: 20px;
    border-bottom: 1px solid var(--m-border);
  }

  .mango-personal-profile__identity {
    flex-direction: column;
    min-width: 0;
    width: 100%;
    gap: 10px;
    text-align: center;
  }

  .mango-personal-profile__avatar {
    flex: 0 0 auto;
    color: var(--m-primary);
    background: var(--m-surface-soft);
    border: 1px solid var(--m-primary-border);
    font-size: 28px;
  }

  .mango-personal-profile__name {
    width: 100%;
    min-width: 0;

    h2,
    p {
      overflow: hidden;
      margin: 0;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    h2 {
      color: var(--m-text);
      font-size: 20px;
      line-height: 28px;
    }

    p {
      margin-top: 2px;
      margin-bottom: 8px;
      color: var(--m-muted);
      font-size: 13px;
    }
  }

  .mango-personal-profile__details {
    margin: 8px 0 0;
  }

  .mango-personal-profile__detail {
    display: grid;
    grid-template-columns: 88px minmax(0, 1fr);
    align-items: center;
    min-width: 0;
    padding: 12px 0;
    border-bottom: 1px solid var(--m-border);

    dt {
      color: var(--m-muted);
      font-size: 13px;
    }

    dd {
      overflow: hidden;
      margin: 0;
      color: var(--m-text);
      font-size: 13px;
      text-align: right;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .mango-personal-profile__actions {
    margin-top: 16px;
  }

  @media (max-width: 960px) {
    .mango-personal-page {
      grid-template-columns: 1fr;
    }

    .mango-personal-profile__identity {
      flex-direction: row;
      text-align: left;
    }

    .mango-personal-profile__name p {
      margin-bottom: 4px;
    }
  }
</style>
