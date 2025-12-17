<template>
  <TableBody ref="tableBody" title="在线执行器">
    <template #header></template>

    <template #default>
      <!-- 卡片列表替代表格 -->
      <div class="cards-container"> <!-- 添加容器 -->
        <a-spin :loading="tableLoading" style="width: 100%;">
          <a-row :gutter="[16, 16]">
            <a-col 
              v-for="record in dataList" 
              :key="record.id" 
              :span="24" 
              :md="12" 
              :lg="8" 
              :xl="6"
            >
              <a-card 
                class="executor-card"
                :bordered="true"
                hoverable
              >
                <template #title>
                  <div class="card-header">
                    <a-avatar :size="24" class="avatar">
                      <icon-user />
                    </a-avatar>
                    <div class="header-info">
                      <span class="owner-name">{{ record.name }} ({{ record.username }})</span>
                    </div>
                    <div class="online-status" title="在线"></div>
                  </div>
                </template>
                
                <div class="card-content">
                  <!-- IP地址 -->
                  <div class="info-item">
                    <icon-desktop class="info-icon" />
                    <span class="info-label">IP地址:</span>
                    <span class="info-value">{{ record.ip }}</span>
                  </div>
                  
                  <!-- 类型 -->
                  <div class="info-item">
                    <icon-tag class="info-icon" />
                    <span class="info-label">类型:</span>
                    <span class="info-value type-badge" :class="getTypeClass(record.type)">{{ getTypeLabel(record.type) }}</span>
                  </div>
                  
                  <!-- OPEN状态 -->
                  <div class="status-item">
                    <icon-link class="status-icon" />
                    <span class="status-label">OPEN状态:</span>
                    <a-switch
                      :beforeChange="(newValue) => onModifyStatus(newValue, record.username)"
                      :default-checked="record.is_open === true"
                      size="small"
                    />
                  </div>
                  
                  <!-- DEBUG状态 -->
                  <div class="status-item">
                    <icon-bug class="status-icon" />
                    <span class="status-label">DEBUG状态:</span>
                    <a-switch
                      :beforeChange="(newValue) => onModifyDebug(newValue, record.username)"
                      :default-checked="record.debug === true"
                      size="small"
                    />
                  </div>
                </div>
                
                <template #actions>
                  <a-button
                    disabled
                    size="small"
                    status="danger"
                    type="text"
                    @click="onDelete(record)"
                  >
                    下线
                  </a-button>
                </template>
              </a-card>
            </a-col>
            
            <!-- 空状态 -->
            <a-col v-if="dataList.length === 0" :span="24">
              <a-empty description="暂无在线执行器" />
            </a-col>
          </a-row>
        </a-spin>
      </div>
    </template>
  </TableBody>
</template>

<script lang="ts" setup>
  import { useTable } from '@/hooks/table'
  import { Message, Modal } from '@arco-design/web-vue'
  import { onMounted, nextTick } from 'vue'
  import {
    getSystemSocketUserList,
    getSystemSocketPutOpenStatus,
    getSystemSocketPutDebug,
  } from '@/api/system/socket_api'
  import { IconUser, IconDesktop, IconLink, IconBug, IconTag } from '@arco-design/web-vue/es/icon'

  const { dataList, tableLoading, handleSuccess } = useTable()

  // 获取类型标签文本
  const getTypeLabel = (type: string) => {
    const typeMap: Record<string, string> = {
      'pytest': 'Pytest',
      'pytest_web': 'Pytest Web',
      'web_ui': 'Web UI',
      'android_ui': 'Android UI'
    }
    return typeMap[type] || 'Pytest Web' // 默认值
  }

  // 获取类型标签样式类
  const getTypeClass = (type: string) => {
    const typeClassMap: Record<string, string> = {
      'pytest': 'type-pytest',
      'pytest_web': 'type-pytest-web',
      'web_ui': 'type-web-ui',
      'android_ui': 'type-android-ui'
    }
    return typeClassMap[type] || 'type-pytest-web' // 默认值
  }

  function doRefresh() {
    getSystemSocketUserList({
      page: 1,
      pageSize: 100, // 获取所有数据
    })
      .then((res) => {
        handleSuccess(res)
      })
      .catch(console.log)
  }

  function onReceive() {
    Message.warning('开发中.....')
  }

  // 添加删除方法
  function onDelete(record: any) {
    Modal.confirm({
      title: '提示',
      content: '是否要下线此执行器？',
      cancelText: '取消',
      okText: '下线',
      onOk: () => {
        // 这里应该调用实际的下线接口，但由于按钮是禁用的，这里只是示例
        Message.info('此功能暂未开放')
      },
    })
  }

  const onModifyStatus = async (newValue: any, id: string) => {
    return new Promise<any>((resolve, reject) => {
      setTimeout(async () => {
        try {
          let value: any = false
          await getSystemSocketPutOpenStatus(id, newValue ? 1 : 0)
            .then((res) => {
              Message.success(res.msg)
              value = res.code === 200
            })
            .catch(reject)
          resolve(value)
        } catch (error) {
          reject(error)
        }
      }, 300)
    })
  }

  const onModifyDebug = async (newValue: any, id: string) => {
    return new Promise<any>((resolve, reject) => {
      setTimeout(async () => {
        try {
          let value: any = false
          await getSystemSocketPutDebug(id, newValue ? 1 : 0)
            .then((res) => {
              Message.success(res.msg)
              value = res.code === 200
            })
            .catch(reject)
          resolve(value)
        } catch (error) {
          reject(error)
        }
      }, 300)
    })
  }
  
  onMounted(() => {
    nextTick(async () => {
      doRefresh()
    })
  })
</script>

<style lang="less" scoped>
.cards-container {
  margin-top: 20px; // 添加与标题的距离
}

.executor-card {
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
  
  &:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    transform: translateY(-2px);
  }
  
  :deep(.arco-card-header) {
    padding: 12px 16px;
    border-bottom: 1px solid var(--color-neutral-3);
    border-radius: 12px 12px 0 0;
  }
  
  :deep(.arco-card-body) {
    padding: 12px 16px;
  }
  
  :deep(.arco-card-footer) {
    border-top: 1px solid var(--color-neutral-3);
    padding: 4px 16px;
    border-radius: 0 0 12px 12px;
  }
  
  .card-header {
    display: flex;
    align-items: center;
    
    .avatar {
      background-color: var(--color-primary-light-1);
      margin-right: 12px;
    }
    
    .header-info {
      display: flex;
      flex-direction: column;
      flex: 1;
      
      .owner-name {
        font-size: 16px;
        font-weight: 500;
        color: var(--color-text-1);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
    }
    
    .online-status {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background-color: var(--color-success-light-4);
      border: 2px solid var(--color-success-light-2);
      margin-left: 12px;
      flex-shrink: 0;
    }
  }
  
  .card-content {
    .info-item, .status-item {
      display: flex;
      align-items: center;
      margin-bottom: 10px;
      
      &:last-child {
        margin-bottom: 4px;
      }
      
      .info-icon, .status-icon {
        font-size: 16px;
        margin-right: 8px;
        color: var(--color-text-3);
      }
      
      .info-label, .status-label {
        font-size: 14px;
        color: var(--color-text-2);
        margin-right: 8px;
        flex-shrink: 0;
      }
      
      .info-value {
        font-size: 14px;
        color: var(--color-text-1);
        flex: 1;
        text-align: right;
        
        &.type-badge {
          display: inline-block;
          padding: 2px 8px;
          border-radius: 4px;
          font-size: 12px;
          font-weight: 500;
          
          &.type-pytest {
            background-color: var(--color-purple-1);
            color: var(--color-purple-6);
          }
          
          &.type-pytest-web {
            background-color: var(--color-blue-1);
            color: var(--color-blue-6);
          }
          
          &.type-web-ui {
            background-color: var(--color-green-1);
            color: var(--color-green-6);
          }
          
          &.type-android-ui {
            background-color: var(--color-red-1);
            color: var(--color-red-6);
          }
        }
      }
      
      :deep(.arco-switch) {
        flex-shrink: 0;
        margin-left: auto;
      }
    }
    
    .status-item {
      .status-icon {
        color: var(--color-primary-light-4);
      }
    }
  }
  
  :deep(.arco-card-actions) {
    display: flex;
    justify-content: flex-end;
    padding: 2px 0 0;
  }
}

// 响应式调整
@media (max-width: 768px) {
  .cards-container {
    margin-top: 16px; // 在小屏幕上稍微减少距离
  }
  
  :deep(.arco-col) {
    .executor-card {
      :deep(.arco-card-body) {
        padding: 10px 12px;
      }
      
      :deep(.arco-card-footer) {
        padding: 3px 12px;
      }
      
      .card-header {
        .header-info {
          .owner-name {
            font-size: 14px;
          }
        }
        
        .online-status {
          width: 8px;
          height: 8px;
          margin-left: 10px;
        }
      }
      
      .card-content {
        .info-item, .status-item {
          margin-bottom: 8px;
          
          &:last-child {
            margin-bottom: 3px;
          }
          
          .info-label, .status-label {
            font-size: 13px;
          }
          
          .info-value {
            font-size: 13px;
            
            &.type-badge {
              font-size: 11px;
              padding: 1px 6px;
            }
          }
        }
      }
      
      :deep(.arco-card-actions) {
        padding: 1px 0 0;
      }
    }
  }
}
</style>