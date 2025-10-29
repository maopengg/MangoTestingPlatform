<template>
  <div class="login-container">
    <div class="container">
      <div class="drop">
        <div class="content">
          <h2> {{ baseData.isLogin ? '欢迎登录' : '欢迎注册' }} </h2>
          <form @keyup.enter="baseData.isLogin ? onLogin() : onRegister()">
            <div class="inputBox" v-if="!baseData.isLogin">
              <input type="text" placeholder="请输入昵称" v-model="baseData.name" />
            </div>
            <div class="inputBox">
              <input type="text" placeholder="请输入账号" v-model="baseData.username" />
            </div>
            <div class="inputBox">
              <input type="password" placeholder="请输入密码" v-model="baseData.password" />
            </div>
            <div class="inputBox" v-if="!baseData.isLogin">
              <input
                type="password"
                placeholder="请输入二次确认密码"
                v-model="baseData.confirm_password"
              />
            </div>
            <div
              class="inputBox"
              style="
                display: flex;
                justify-content: center;
                align-items: center;
                height: 35px;
                cursor: pointer;
              "
              @click="baseData.isLogin ? onLogin() : onRegister()"
            >
              <a type="submit">{{ baseData.isLogin ? '登录' : '注册' }}</a>
            </div>
          </form>
        </div>
      </div>
      <a-button @click="register1" class="btns">注册</a-button>
      <a-button class="btns signup" @click="Message.warning('请联系管理修改密码！')"
        >忘记密码
      </a-button>
    </div>
    <div class="bottom">芒果测试平台 Copyright © 芒果味 2022-至今 Version：{{ version }}</div>
    <!--    不支持修改平台名称和作者署名！-->
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
      .catch((error: Error) => {
        if (error.message === '请求失败，未知异常') {
          Message.error('后端服务可能未启动！')
        }
        baseData.loading = false
      })
  }

  function register1() {
    baseData.isLogin = !baseData.isLogin
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
      Message.error('用户昵称、用户名、密码不允许为空')
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
  .login-container {
    position: relative;
    overflow: hidden;
    height: 100vh;
    width: 100vw;
    display: flex;
    justify-content: center;
    align-items: center;

    .bottom {
      position: fixed;
      left: 0;
      right: 0;
      bottom: 3%;
      font-size: 14px;
      font-weight: bold;
      color: #111;
      text-align: center;
    }
  }

  * {
    margin: 0;
    padding: 0;
    font-family: 'Poppins', sans-serif;
  }

  body {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 100vh;
    background-color: #eff0f4;
  }

  .container {
    display: flex;
    position: relative;
    justify-content: center;
    align-items: center;
    width: 100%;
    height: 100vh;
    left: 0;
  }

  .container .drop {
    position: relative;
    width: 450px;
    height: 450px;
    box-shadow: inset 20px 20px 20px rgba(0, 0, 0, 0.05), 25px 35px 20px rgba(0, 0, 0, 0.05),
      25px 30px 30px rgba(0, 0, 0, 0.05), inset -20px -20px 25px rgba(255, 255, 255, 0.9);
    transition: 0.5s ease-in-out;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 52% 48% 33% 67% / 38% 45% 55% 62%;
  }

  .container .drop:hover {
    border-radius: 50%;
  }

  .container .drop::before {
    content: '';
    position: absolute;
    top: 50px;
    left: 85px;
    width: 35px;
    height: 35px;
    border-radius: 50%;
    background-color: #fff;
    opacity: 0.9;
  }

  .container .drop::after {
    content: '';
    position: absolute;
    top: 90px;
    left: 110px;
    width: 15px;
    height: 15px;
    border-radius: 50%;
    background-color: #fff;
    opacity: 0.9;
  }

  .container .drop .content {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-direction: column;
    text-align: center;
    padding: 40px;
    gap: 15px;
  }

  .container .drop .content h2 {
    position: relative;
    color: #333;
    font-size: 1.5em;
  }

  .container .drop .content form {
    display: flex;
    flex-direction: column;
    gap: 20px;
    justify-content: center;
    align-items: center;
  }

  .container .drop .content form .inputBox {
    position: relative;
    width: 225px;
    box-shadow: inset 2px 5px 10px rgba(0, 0, 0, 0.1), inset -2px -5px 10px rgba(255, 255, 255, 1),
      15px 15px 10px rgba(0, 0, 0, 0.05), 15px 10px 15px rgba(0, 0, 0, 0.05);
    border-radius: 25px;
  }

  .container .drop .content form .inputBox::before {
    content: '';
    position: absolute;
    top: 8px;
    left: 50%;
    transform: translateX(-50%);
    width: 65%;
    height: 5px;
    background-color: rgba(255, 255, 255, 0.5);
    border-radius: 5px;
  }

  .container .drop .content form .inputBox input {
    border: none;
    outline: none;
    background-color: transparent;
    width: 100%;
    font-size: 1em;
    padding: 10px 15px;
  }

  .container .drop .content form .inputBox input[type='submit'] {
    color: #fff;
    text-transform: uppercase;
    cursor: pointer;
    letter-spacing: 0.1em;
    font-weight: 500;
  }

  .container .drop .content form .inputBox:last-child {
    width: 120px;
    background-color: #ff0f5b;
    box-shadow: inset 2px 5px 10px rgba(0, 0, 0, 0.1), 15px 15px 10px rgba(0, 0, 0, 0.05),
      15px 10px 15px rgba(0, 0, 0, 0.05);
    transition: 0.5s;
  }

  .container .drop .content form .inputBox:last-child:hover {
    width: 150px;
  }

  .btns {
    width: 120px;
    height: 120px;
    right: -120px;
    bottom: 0;
    background-color: #c61dff;
    display: flex;
    justify-content: center;
    align-items: center;
    cursor: pointer;
    text-decoration: none;
    color: #fff;
    line-height: 1.2em;
    letter-spacing: 0.1em;
    font-size: 0.8em;
    transition: 0.25s;
    text-align: center;
    box-shadow: inset 10px 10px 10px rgba(190, 1, 254, 0.05), 15px 25px 10px rgba(190, 1, 254, 0.1),
      15px 20px 20px rgba(190, 1, 254, 0.1), inset -10px -10px 15px rgba(255, 255, 255, 0.5);
    border-radius: 44% 56% 65% 35% / 57% 58% 42% 43%;
  }

  .btns:hover {
    border-radius: 50%;
  }

  .btns::before {
    content: '';
    position: absolute;
    top: 15px;
    left: 30px;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background-color: #fff;
    opacity: 0.45;
  }

  .btns.signup {
    bottom: 150px;
    right: -140px;
    width: 80px;
    height: 80px;
    border-radius: 49% 51% 52% 48% / 63% 59% 41% 37%;
    background-color: #01b4ff;
    box-shadow: inset 10px 10px 10px rgba(1, 180, 255, 0.05), 15px 25px 10px rgba(1, 180, 255, 0.1),
      15px 20px 20px rgba(1, 180, 255, 0.1), inset -10px -10px 15px rgba(255, 255, 255, 0.5);
  }

  .btns.signup::before {
    left: 20%;
    width: 15px;
    height: 15px;
  }

  .btns:hover {
    border-radius: 50%;
  }

  .login-container {
    position: relative;
    height: 100vh;
    width: 100vw;
    display: flex;
    justify-content: center;
    align-items: center;
    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);

    .bg-img {
      width: 100%;
      height: 100%;
      position: absolute;
      top: 0;
      left: 0;
      object-fit: cover;
      opacity: 0.2;
    }

    .center {
      position: relative;
      z-index: 9;
      width: 900px;
      height: 500px;
      border-radius: 12px;
      display: flex;
      background-color: #fff;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
      overflow: hidden;

      .left {
        width: 45%;
        height: 100%;
        position: relative;

        .left-bg-img {
          width: 100%;
          height: 100%;
          object-fit: cover;
        }
      }

      .form-wrapper {
        width: 55%;
        padding: 40px;
        display: flex;
        flex-direction: column;
        justify-content: center;

        .title {
          font-size: 24px;
          font-weight: 600;
          margin-bottom: 30px;
          color: #333;
          text-align: center;
        }

        .item-wrapper {
          margin-bottom: 20px;

          :deep(.arco-input) {
            border-radius: 6px;
            height: 46px;
          }
        }

        .login {
          width: 100%;
          height: 46px;
          border-radius: 6px;
          font-size: 16px;
          margin-top: 10px;
        }
      }
    }

    .bottom {
      position: absolute;
      bottom: 20px;
      width: 100%;
      text-align: center;
      font-size: 14px;
      color: #666;
    }
  }
</style>
