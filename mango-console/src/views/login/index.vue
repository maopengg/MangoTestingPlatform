<template>
  <div class="login-container">
    <img class="bg-img" src="../../assets/bg.png" />
    <div class="center">
      <div class="left">
        <img class="left-bg-img" src="../../assets/bg_left.png" />
      </div>
      <div class="form-wrapper">
        <div v-if="baseData.isLogin === true">
          <div class="title">账号登录</div>
          <div class="item-wrapper mt-6">
            <a-input
              v-model="baseData.username"
              allow-clear
              placeholder="请输入用户名/手机号"
              size="large"
            >
              <template #prefix>
                <icon-mobile />
              </template>
            </a-input>
          </div>
          <div class="item-wrapper mt-4">
            <a-input-password
              v-model="baseData.password"
              allow-clear
              placeholder="请输入密码"
              size="large"
              @keyup.enter="onLogin"
            >
              <template #prefix>
                <icon-lock />
              </template>
            </a-input-password>
          </div>
          <div class="flex-1"></div>
          <div class="mt-10">
            <a-button :loading="baseData.loading" class="login" type="primary" @click="onLogin">
              登录
            </a-button>
          </div>
        </div>
        <div v-else>
          <div class="title">注册用户</div>
          <div class="item-wrapper mt-6">
            <a-input
              v-model="baseData.name"
              allow-clear
              placeholder="请输入用户昵称"
              size="large"
            />
          </div>
          <div class="item-wrapper mt-6">
            <a-input
              v-model="baseData.username"
              allow-clear
              placeholder="请输入登录用户名"
              size="large"
            >
              <template #prefix>
                <icon-mobile />
              </template>
            </a-input>
          </div>
          <div class="item-wrapper mt-4">
            <a-input-password
              v-model="baseData.password"
              allow-clear
              placeholder="请输入密码"
              size="large"
              @keyup.enter="onLogin"
            >
              <template #prefix>
                <icon-lock />
              </template>
            </a-input-password>
          </div>
          <div class="item-wrapper mt-4">
            <a-input-password
              v-model="baseData.confirm_password"
              allow-clear
              placeholder="再次输入密码"
              size="large"
              @keyup.enter="onLogin"
            >
              <template #prefix>
                <icon-lock />
              </template>
            </a-input-password>
          </div>
          <div class="flex-1"></div>
          <div class="mt-10">
            <a-button :loading="baseData.loading" class="login" type="primary" @click="onRegister">
              注册
            </a-button>
          </div>
        </div>
        <div class="my-width flex-1 mt-4 mb-8">
          <div class="flex justify-between">
            <a-link :underline="false" type="primary">忘记密码？</a-link>
            <a-link
              v-if="baseData.isLogin === true"
              :underline="false"
              type="primary"
              @click="register1"
              >注册用户
            </a-link>
            <a-link
              v-if="baseData.isLogin === false"
              :underline="false"
              type="primary"
              @click="returnToLogin"
              >返回登录
            </a-link>
          </div>
        </div>
      </div>
    </div>
    <div class="bottom"> Copyright © 芒果味 2022-至今 Version：{{ version }} </div>
    <!--  禁止修改作者署名-->
  </div>
</template>

<script lang="ts" setup>
  import { reactive } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import { post, Response } from '@/api/http'
  import { md5 } from 'js-md5'

  import { login, register } from '@/api/url'
  import { Message } from '@arco-design/web-vue'
  import { UserState } from '@/store/types'
  import useAppInfo from '@/hooks/useAppInfo'
  import useUserStore from '@/store/modules/user'

  const { version } = useAppInfo()
  const router = useRouter()
  const route = useRoute()
  const userStore = useUserStore()
  const baseData: any = reactive({
    name: '',
    username: '',
    password: '',
    confirm_password: '',
    loading: false,
    isLogin: true,
  })

  const onLogin = () => {
    baseData.loading = true
    post({
      url: login,
      data: {
        username: baseData.username,
        password: md5(baseData.password),
        type: 1,
      },
    })
      .then(({ data }: Response) => {
        userStore.saveUser(data as UserState, md5(baseData.password)).then(() => {
          router
            .replace({
              path: route.query.redirect ? (route.query.redirect as string) : '/index/home',
            })
            .then(() => {
              Message.success('登录成功，欢迎：' + data.name)
              baseData.loading = false
            })
        })
      })
      .catch((error) => {
        baseData.loading = false
      })
  }

  function register1() {
    baseData.isLogin = false
  }

  function returnToLogin() {
    baseData.isLogin = true
  }

  function onRegister() {
    if (
      baseData.username === '' ||
      baseData.name === '' ||
      baseData.password === '' ||
      baseData.confirm_password === ''
    ) {
      Message.error('用户昵称，用户名，密码不允许为空')
      return
    } else {
      if (baseData.password !== baseData.confirm_password) {
        Message.error('两次密码输入不一致')
        return
      }
      baseData.loading = true
      post({
        url: register,
        data: {
          name: baseData.name,
          username: baseData.username,
          password: md5(baseData.password),
        },
      })
        .then((data) => {
          if (data.code === 200) {
            Message.success(data.msg)
            returnToLogin()
            baseData.loading = false
          }
        })
        .catch(() => {
          baseData.loading = false
        })
    }
  }
</script>

<style lang="less" scoped>
  @leftWith: 35%;
  .login-container {
    position: relative;
    overflow: hidden;
    height: 100vh;
    width: 100vw;
    display: flex;
    justify-content: center;
    align-items: center;

    .bg-img {
      width: 100%;
      height: 100%;
      position: absolute;
      top: 0;
      left: 0;
    }

    .bottom {
      position: fixed;
      left: 0;
      right: 0;
      bottom: 3%;
      font-size: 14px;
      font-weight: bold;
      color: #333;
      text-align: center;
    }

    .center {
      position: relative;
      z-index: 9;
      width: 70%;
      height: 60%;
      border-radius: 10px;
      border: 1px solid #f5f5f5;
      display: flex;
      align-items: center;
      background-color: #fff;
      box-shadow: 0 0 5px #ececec;

      .left {
        position: relative;
        width: 50%;
        height: 100%;
        padding: 20px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        text-align: center;

        .left-bg-img {
          width: 100%;
          height: 100%;
          position: absolute;
          top: 0;
          left: 0;
        }

        .proj-name {
          font-size: 30px;
          font-weight: bold;
          flex: 1;
          display: flex;
          align-items: center;
          justify-content: center;
        }
      }

      .form-wrapper {
        width: 50%;
        padding: 2% 5%;
        height: 100%;
        display: flex;
        flex-direction: column;

        .title {
          font-size: 25px;
          font-weight: bold;
          margin-bottom: 20px;
          text-align: center;
        }

        .login {
          width: 100%;
        }
      }
    }
  }
</style>
