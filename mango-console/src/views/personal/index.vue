<template>
  <TableBody ref="tableBody">
    <div class="main-container">
      <div class="box-wrapper">
        <div class="flex">
          <a-card
            :body-style="{ padding: '10px' }"
            :bordered="false"
            class="card-border-radius personal-box"
          >
            <div class="info-wrapper">
              <div class="avatar-wrapper">
                <!--              <div-->
                <!--                class="avatar"-->
                <!--                :class="{ 'avatar-touch': touched, 'avatar-end': uploaded }"-->
                <!--                @mouseenter="avatarTouchStart"-->
                <!--              >-->
                <!--                <img :src="userStore.avatar" />-->
                <!--              </div>-->
                <div class="flex items-center justify-center camera-layer" @click="uploadAvatar">
                  <icon-camera style="color: #fff; font-size: 30px" />
                </div>
              </div>
              <div class="text-xl">
                {{ userStore.nickName }}
              </div>
              <div class="text-wrapper">
                <div class="label">昵称：</div>
                <div class="value">{{ personalCenterData.data.name }}</div>
              </div>
              <div class="text-wrapper">
                <div class="label">账号：</div>
                <div class="value">{{ personalCenterData.data.username }}</div>
              </div>
              <div class="text-wrapper">
                <div class="label">角色：</div>
                <div class="value">{{ personalCenterData.data.role?.name }}</div>
              </div>
              <div class="text-wrapper">
                <div class="label">最近登录时间：</div>
                <div class="value">{{ personalCenterData.data?.last_login_time }}</div>
              </div>
              <div class="text-wrapper">
                <div class="label">socketIP断言：</div>
                <div class="value">{{ personalCenterData.data.ip }}</div>
              </div>
              <div class="text-wrapper">
                <div class="label">邮箱：</div>
                <div class="value">{{ personalCenterData.data.mailbox }}</div>
              </div>
              <div class="mt-4">
                <a-button size="mini" type="text" @click="onUpdate">修改密码</a-button>
              </div>
            </div>
          </a-card>
        </div>
      </div>
    </div>
  </TableBody>
  <ModalDialog ref="modalDialogRef" :title="personalCenterData.actionTitle" @confirm="onDataForm">
    <template #content>
      <a-form :model="formModel">
        <a-form-item
          v-for="item of formItems"
          :key="item.key"
          :class="[item.required ? 'form-item__require' : 'form-item__no_require']"
          :label="item.label"
        >
          <template v-if="item.type === 'input'">
            <a-input v-model="item.value" :placeholder="item.placeholder" />
          </template>
        </a-form-item>
      </a-form>
    </template>
  </ModalDialog>
</template>

<script lang="ts" setup>
  import useUserStore from '@/store/modules/user'
  import { nextTick, onMounted, reactive, ref } from 'vue'

  import { FormItem, ModalDialogType } from '@/types/components'
  import { Message } from '@arco-design/web-vue'
  import { getFormItems } from '@/utils/datacleaning'
  import { websocket } from '@/utils/socket'
  import { getUserInfo, postUserPassword } from '@/api/user/user'

  const userStore = useUserStore()
  const touched = ref(false)
  const uploaded = ref(false)
  const formModel = ref({})
  const modalDialogRef = ref<ModalDialogType | null>(null)
  const personalCenterData = reactive({
    actionTitle: '修改密码',
    data: {},
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

  const avatarTouchStart = () => {
    touched.value = true
  }
  const uploadAvatar = () => {
    uploaded.value = true
    setTimeout(() => {
      touched.value = false
      uploaded.value = false
    }, 1000)
  }

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
    if (formItems.every((it) => (it.validator ? it.validator() : true))) {
      let value = getFormItems(formItems)
      value['id'] = userStore.userId
      postUserPassword(value)
        .then((res) => {
          modalDialogRef.value?.toggle()
          Message.success(res.msg)
          userStore.logout().then(() => {
            window.localStorage.removeItem('visited-routes')
            window.location.reload()
            localStorage.clear()
            websocket(13213, '231', false)
          })
        })
        .catch(console.log)
    }
  }

  onMounted(() => {
    nextTick(async () => {
      doRefresh()
    })
  })
</script>
<style lang="less" scoped>
  .box-wrapper {
    .personal-box {
      width: 100%;

      .info-wrapper {
        text-align: center;

        .avatar-wrapper {
          display: inline-block;
          width: 6rem;
          height: 6rem;
          margin-top: 20px;
          position: relative;

          .avatar {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            transform-origin: bottom;
            transform: rotate(0deg);
            z-index: 1;
            transition: all 0.5s ease-in-out;

            & > img {
              width: 100%;
              height: 100%;
              border-radius: 50%;
              border: 2px solid rgb(245, 241, 7);
            }
          }

          .avatar-touch {
            transform: rotate(180deg);
          }

          .avatar-end {
            transform: rotate(0deg);
          }

          .camera-layer {
            position: absolute;
            top: 0;
            bottom: 0;
            left: 0;
            right: 0;
            background: rgba(0, 0, 0, 0.6);
            border-radius: 50%;
          }
        }

        .des-wrapper {
          width: 70%;
          margin: 0 auto;
          font-size: 14px;
          padding: 15px;
        }

        .text-wrapper {
          font-size: 0.8rem;
          margin-top: 20px;
          width: 50%;
          margin: 0 auto;

          .label {
            display: inline-block;
            width: 40%;
            text-align: right;
          }

          .value {
            display: inline-block;
            width: 60%;
            text-align: left;
          }
        }

        .text-wrapper + .text-wrapper {
          margin-top: 15px;
        }
      }
    }

    .message-wrapper {
      border-bottom: 1px solid #f5f5f5;
      padding-bottom: 10px;

      .notify {
        width: 10px;
        height: 10px;
        border-radius: 50%;
      }

      .message-title {
        font-size: 14px;
      }

      .content {
        font-size: 12px;
        margin-top: 10px;
        line-height: 1rem;
      }
    }

    .message-wrapper + .message-wrapper {
      margin-top: 10px;
    }

    .wating-box {
      width: 30%;
      margin-left: 10px;

      .wating-item {
        padding: 10px;
        border-bottom: 1px solid #f5f5f5;
      }
    }
  }
</style>
