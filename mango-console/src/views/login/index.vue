<template>
  <div class="login-container">
    <div class="background-animation"></div>
    <div class="particles-container">
      <div class="particle" v-for="i in 20" :key="i"></div>
    </div>
    <div class="floating-elements">
      <div class="floating-element element-1"></div>
      <div class="floating-element element-2"></div>
      <div class="floating-element element-3"></div>
      <div class="floating-element element-4"></div>
    </div>
    <div class="center">
      <div class="left">
        <div class="welcome-content">
          <!-- <div class="logo-placeholder">
            <div class="logo-inner">
              <icon-apps class="logo-icon" />
            </div>
          </div> -->
          <h2 class="welcome-title">欢迎使用</h2>
          <p class="welcome-subtitle">{{ projectName }}</p>
          <div class="welcome-desc">专业的测试平台，助力高效开发</div>
          <div class="features">
            <div class="feature-item">
              <icon-check-circle-fill class="feature-icon" />
              <span>接口测试</span>
            </div>
            <div class="feature-item">
              <icon-check-circle-fill class="feature-icon" />
              <span>UI自动化</span>
            </div>
            <div class="feature-item">
              <icon-check-circle-fill class="feature-icon" />
              <span>Pytest测试</span>
            </div>
          </div>
        </div>
      </div>
      <div class="form-wrapper">
        <div v-if="baseData.isLogin === true" class="form-content">
          <div class="title">账号登录</div>
          <div class="subtitle">请输入您的登录信息</div>
          <div class="item-wrapper mt-8">
            <a-input
              v-model="baseData.username"
              placeholder="请输入用户名/手机号"
              allow-clear
              size="large"
              class="custom-input"
              @focus="handleInputFocus"
              @blur="handleInputBlur"
            >
              <template #prefix>
                <icon-user />
              </template>
            </a-input>
          </div>
          <div class="item-wrapper mt-6">
            <a-input-password
              v-model="baseData.password"
              placeholder="请输入密码"
              allow-clear
              size="large"
              class="custom-input"
              @keyup.enter="onLogin"
              @focus="handleInputFocus"
              @blur="handleInputBlur"
            >
              <template #prefix>
                <icon-lock />
              </template>
            </a-input-password>
          </div>
          <div class="remember-forgot">
            <a-checkbox v-model="baseData.remember">记住我</a-checkbox>
            <a-link @click="forgotPassword">忘记密码？</a-link>
          </div>
          <div class="flex-1"></div>
          <div class="mt-10">
            <a-button type="primary" class="login-btn" :loading="baseData.loading" @click="onLogin">
              登录
            </a-button>
          </div>
        </div>
        <div v-else class="form-content">
          <div class="title">注册用户</div>
          <div class="subtitle">创建您的账户</div>
          <div class="item-wrapper mt-6">
            <a-input
              v-model="baseData.name"
              placeholder="请输入用户昵称"
              allow-clear
              size="large"
              class="custom-input"
              @focus="handleInputFocus"
              @blur="handleInputBlur"
            />
          </div>
          <div class="item-wrapper mt-6">
            <a-input
              v-model="baseData.username"
              placeholder="请输入登录用户名"
              allow-clear
              size="large"
              class="custom-input"
              @focus="handleInputFocus"
              @blur="handleInputBlur"
            >
              <template #prefix>
                <icon-user />
              </template>
            </a-input>
          </div>
          <div class="item-wrapper mt-6">
            <a-input-password
              v-model="baseData.password"
              placeholder="请输入密码"
              allow-clear
              size="large"
              class="custom-input"
              @keyup.enter="onLogin"
              @focus="handleInputFocus"
              @blur="handleInputBlur"
            >
              <template #prefix>
                <icon-lock />
              </template>
            </a-input-password>
          </div>
          <div class="item-wrapper mt-6">
            <a-input-password
              v-model="baseData.confirm_password"
              placeholder="再次输入密码"
              allow-clear
              size="large"
              class="custom-input"
              @keyup.enter="onLogin"
              @focus="handleInputFocus"
              @blur="handleInputBlur"
            >
              <template #prefix>
                <icon-lock />
              </template>
            </a-input-password>
          </div>
          <div class="flex-1"></div>
          <div class="mt-10">
            <a-button
              type="primary"
              class="login-btn"
              :loading="baseData.loading"
              @click="onRegister"
            >
              注册
            </a-button>
          </div>
        </div>
        <div class="links-wrapper mt-6">
          <div class="flex justify-between">
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
    <div class="bottom">芒果测试平台 Copyright © 芒果味 2022-至今 Version：{{ version }}</div>
    <!--    不支持修改平台名称和作者署名！-->
  </div>
</template>

<script lang="ts" setup>
  import { reactive, ref, onMounted } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import { post, Response } from '@/api/http'
  import { md5 } from 'js-md5'

  import { login, register } from '@/api/url'
  import { Message } from '@arco-design/web-vue'
  import { UserState } from '@/store/types'
  import setting from '../../setting'
  import useAppInfo from '@/hooks/useAppInfo'
  import useUserStore from '@/store/modules/user'

  const projectName = setting.projectName
  const { version } = useAppInfo()
  const router = useRouter()
  const route = useRoute()
  const userStore = useUserStore()
  const baseData: any = reactive({
    name: '',
    username: '',
    password: '',
    confirm_password: '',
    remember: false,
    loading: false,
    isLogin: true,
  })
  
  const focusedInput = ref('')

  function handleInputFocus(event: FocusEvent) {
    const target = event.target as HTMLInputElement
    focusedInput.value = target.tagName
  }
  
  function handleInputBlur() {
    focusedInput.value = ''
  }

  function forgotPassword() {
    Message.info('请联系管理员找回密码！')
  }

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
      .then((res: Response) => {
        const data = res.data as UserState
        userStore.saveUser(data, baseData.password).then(() => {
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
        Message.error(error.message)
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
        .then((res: Response) => {
          if (res.code === 200) {
            Message.success(res.msg)
            returnToLogin()
            baseData.loading = false
          }
        })
        .catch(() => {
          baseData.loading = false
        })
    }
  }
  
  onMounted(() => {
    // 初始化粒子动画
    const particles = document.querySelectorAll('.particle')
    particles.forEach((particle, index) => {
      const size = Math.random() * 12 + 6
      const posX = Math.random() * 100
      const posY = Math.random() * 100
      const delay = Math.random() * 5
      const duration = Math.random() * 15 + 15
      
      particle.setAttribute('style', `
        width: ${size}px;
        height: ${size}px;
        left: ${posX}%;
        top: ${posY}%;
        animation-delay: ${delay}s;
        animation-duration: ${duration}s;
      `)
    })
  })
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
    
    .background-animation {
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: linear-gradient(135deg, #e6f7ff 0%, #f0f8ff 100%);
      opacity: 0.9;
      z-index: 1;
      
      &::before {
        content: "";
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle, rgba(255,255,255,0.3) 0%, rgba(255,255,255,0) 70%);
        animation: rotate 25s linear infinite;
      }
      
      &::after {
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: 
          radial-gradient(circle at 10% 20%, rgba(255, 255, 255, 0.2) 0%, transparent 20%),
          radial-gradient(circle at 90% 80%, rgba(255, 255, 255, 0.2) 0%, transparent 20%);
        animation: pulse 8s ease-in-out infinite;
      }
    }
    
    .particles-container {
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      z-index: 2;
      pointer-events: none;
      
      .particle {
        position: absolute;
        background: rgba(173, 216, 230, 0.6);
        border-radius: 50%;
        animation: float 20s infinite ease-in-out;
      }
    }
    
    .floating-elements {
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      z-index: 3;
      pointer-events: none;
      
      .floating-element {
        position: absolute;
        border-radius: 50%;
        background: rgba(176, 224, 230, 0.3);
        animation: float 20s infinite ease-in-out;
        backdrop-filter: blur(2px);
        
        &.element-1 {
          width: 100px;
          height: 100px;
          top: 15%;
          left: 8%;
          animation-delay: 0s;
        }
        
        &.element-2 {
          width: 140px;
          height: 140px;
          top: 65%;
          left: 85%;
          animation-delay: -5s;
        }
        
        &.element-3 {
          width: 70px;
          height: 70px;
          top: 75%;
          left: 15%;
          animation-delay: -10s;
        }
        
        &.element-4 {
          width: 120px;
          height: 120px;
          top: 25%;
          left: 80%;
          animation-delay: -15s;
        }
      }
    }
    
    @keyframes rotate {
      from {
        transform: rotate(0deg);
      }
      to {
        transform: rotate(360deg);
      }
    }
    
    @keyframes float {
      0%, 100% {
        transform: translate(0, 0) rotate(0deg);
      }
      25% {
        transform: translate(30px, 30px) rotate(90deg);
      }
      50% {
        transform: translate(50px, 0) rotate(180deg);
      }
      75% {
        transform: translate(30px, -30px) rotate(270deg);
      }
    }
    
    @keyframes pulse {
      0%, 100% {
        opacity: 0.8;
      }
      50% {
        opacity: 1;
      }
    }

    .bottom {
      position: fixed;
      left: 0;
      right: 0;
      bottom: 3%;
      font-size: 15px;
      font-weight: 500;
      color: rgba(0, 0, 0, 0.7);
      text-align: center;
      z-index: 10;
      text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
      letter-spacing: 0.5px;
    }

    .center {
      position: relative;
      z-index: 9;
      width: 950px;
      height: 620px;
      border-radius: 28px;
      display: flex;
      align-items: center;
      background-color: #fff;
      box-shadow: 0 15px 30px rgba(0, 0, 0, 0.1);

      .left {
        position: relative;
        width: 50%;
        height: 100%;
        background: linear-gradient(135deg, #e6f7ff 0%, #f0f8ff 100%);
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        color: #333;
        padding: 40px;
        text-align: center;
        border-right: 1px solid #e6f7ff;
        
        .welcome-content {
          position: relative;
          z-index: 2;
          
          .logo-placeholder {
            width: 100px;
            height: 100px;
            background: rgba(255, 255, 255, 0.6);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 25px;
            backdrop-filter: blur(8px);
            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.1);
            animation: logo-pulse 3s infinite ease-in-out;
            border: 1px solid #e6f7ff;
            
            .logo-inner {
              width: 70px;
              height: 70px;
              background: rgba(255, 255, 255, 0.8);
              border-radius: 50%;
              display: flex;
              align-items: center;
              justify-content: center;
              border: 1px solid #e6f7ff;
              
              .logo-icon {
                font-size: 45px;
                color: #409eff;
              }
            }
          }
          
          .welcome-title {
            font-size: 42px;
            font-weight: 800;
            margin-bottom: 12px;
            letter-spacing: 2px;
            text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            animation: title-appear 1s ease-out;
            color: #333;
          }
          
          .welcome-subtitle {
            font-size: 30px;
            font-weight: 600;
            margin-bottom: 30px;
            opacity: 0.9;
            animation: subtitle-appear 1.2s ease-out;
            color: #666;
          }
          
          .welcome-desc {
            font-size: 19px;
            opacity: 0.8;
            max-width: 340px;
            line-height: 1.8;
            margin-bottom: 35px;
            animation: desc-appear 1.4s ease-out;
            color: #666;
          }
          
          .features {
            display: flex;
            flex-direction: column;
            gap: 20px;
            width: 100%;

            .feature-item {
              display: flex;
              align-items: center;
              justify-content: center;
              gap: 15px;
              font-size: 18px;
              font-weight: 500;
              animation: feature-appear 1.6s ease-out;
              color: #666;

              .feature-icon {
                color: #409eff;
                font-size: 24px;
                flex-shrink: 0; /* 防止图标压缩 */
                display: flex;
                align-items: center;
                justify-content: center;
              }

              span {
                display: flex;
                align-items: center;
                height: 24px; /* 与图标高度一致 */
              }
            }
          }
        }
      }

      .form-wrapper {
        width: 50%;
        padding: 50px 60px;
        height: 100%;
        display: flex;
        flex-direction: column;
        
        .form-content {
          flex: 1;
          display: flex;
          flex-direction: column;

          .title {
            font-size: 36px;
            font-weight: 800;
            margin-bottom: 10px;
            text-align: center;
            color: #333;
            letter-spacing: 1px;
          }

          .subtitle {
            font-size: 18px;
            color: #666;
            text-align: center;
            margin-bottom: 40px;
          }
          
          .remember-forgot {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 25px;
            
            :deep(.arco-checkbox) {
              font-size: 16px;
              color: #666;
            }
            
            :deep(.arco-link) {
              font-size: 16px;
            }
          }
        }

        .custom-input {
          :deep(.arco-input-wrapper) {
            border-radius: 14px;
            height: 55px;
            border-color: #e6f7ff;
            transition: all 0.4s cubic-bezier(0.645, 0.045, 0.355, 1);
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
            background-color: #f8fbfd;
            
            &:hover {
              border-color: #409eff;
              box-shadow: 0 6px 16px rgba(64, 158, 255, 0.2);
            }
            
            &.arco-input-focus {
              border-color: #409eff;
              box-shadow: 0 0 0 5px rgba(64, 158, 255, 0.15);
              background-color: #fff;
            }
          }
          
          :deep(.arco-input-prefix) {
            color: #409eff;
            font-size: 22px;
          }
        }

        .login-btn {
          width: 100%;
          height: 55px;
          border-radius: 14px;
          font-size: 20px;
          font-weight: 600;
          background: linear-gradient(135deg, #409eff 0%, #52b0ff 100%);
          border: none;
          box-shadow: 0 5px 15px rgba(64, 158, 255, 0.3);
          transition: all 0.3s ease;
          letter-spacing: 2px;
          text-transform: uppercase;
          color: white;
          
          &:hover {
            background: linear-gradient(135deg, #52b0ff 0%, #409eff 100%);
            box-shadow: 0 8px 20px rgba(64, 158, 255, 0.4);
            transform: translateY(-2px);
          }
          
          &:active {
            transform: translateY(0);
          }
        }

        .links-wrapper {
          margin-top: 35px;
          
          :deep(.arco-link) {
            font-size: 18px;
            font-weight: 500;
            transition: all 0.3s ease;
            color: #409eff;
            
            &:hover {
              color: #52b0ff;
              text-decoration: none;
            }
          }
        }
      }
    }
    
    @keyframes logo-pulse {
      0%, 100% {
        transform: scale(1);
      }
      50% {
        transform: scale(1.05);
      }
    }
    
    @keyframes title-appear {
      0% {
        opacity: 0;
        transform: translateY(20px);
      }
      100% {
        opacity: 1;
        transform: translateY(0);
      }
    }
    
    @keyframes subtitle-appear {
      0% {
        opacity: 0;
        transform: translateY(20px);
      }
      100% {
        opacity: 1;
        transform: translateY(0);
      }
    }
    
    @keyframes desc-appear {
      0% {
        opacity: 0;
        transform: translateY(20px);
      }
      100% {
        opacity: 1;
        transform: translateY(0);
      }
    }
    
    @keyframes feature-appear {
      0% {
        opacity: 0;
        transform: translateX(-20px);
      }
      100% {
        opacity: 1;
        transform: translateX(0);
      }
    }
    
    @media (max-width: 768px) {
      .center {
        width: 90%;
        max-width: 500px;
        flex-direction: column;
        height: auto;
        
        .left {
          width: 100%;
          height: 250px;
          padding: 35px;
          border-right: none;
          border-bottom: 1px solid #e6f7ff;
        }
        
        .form-wrapper {
          width: 100%;
          padding: 45px 35px;
        }
      }
    }
    
    @media (max-width: 480px) {
      .center {
        .form-wrapper {
          padding: 40px 30px;
          
          .form-content {
            .title {
              font-size: 32px;
            }
          }
        }
      }
    }
  }
</style>