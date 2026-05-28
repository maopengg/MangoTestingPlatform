<template>
  <TableBody ref="tableBody" title="在线执行器">
    <template #header></template>

    <template #default>
      <div class="mango-equipment-page">
        <a-spin :loading="tableLoading" class="mango-equipment-spin mango-panel-loading">
          <div class="mango-equipment-grid">
            <div v-for="record in dataList" :key="record.id" class="mango-equipment-grid-item">
              <a-card class="executor-card" :bordered="false" hoverable>
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
                    <span class="info-label">IP地址：</span>
                    <span class="info-value">{{ record.ip }}</span>
                  </div>

                  <!-- 类型 -->
                  <div class="info-item">
                    <icon-tag class="info-icon" />
                    <span class="info-label">类型：</span>
                    <span class="info-value type-badge" :class="getTypeClass(record.type)">{{
                      getTypeLabel(record.type)
                    }}</span>
                  </div>

                  <!-- OPEN状态 -->
                  <div class="status-item">
                    <icon-link class="status-icon" />
                    <span class="status-label">OPEN状态：</span>
                    <a-switch
                      :beforeChange="(newValue) => onModifyStatus(newValue, record.username)"
                      :default-checked="record.is_open === true"
                      size="small"
                    />
                  </div>

                  <!-- DEBUG状态 -->
                  <div class="status-item">
                    <icon-bug class="status-icon" />
                    <span class="status-label">DEBUG状态：</span>
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
            </div>

            <div v-if="dataList.length === 0" class="mango-equipment-empty">
              <div class="mango-empty-state">暂无在线执行器</div>
            </div>
          </div>
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
      pytest: 'Pytest',
      pytest_web: 'Pytest Web',
      web_ui: 'Web UI',
      android_ui: 'Android UI',
    }
    return typeMap[type] || 'Pytest Web' // 默认值
  }

  // 获取类型标签样式类
  const getTypeClass = (type: string) => {
    const typeClassMap: Record<string, string> = {
      pytest: 'type-pytest',
      pytest_web: 'type-pytest-web',
      web_ui: 'type-web-ui',
      android_ui: 'type-android-ui',
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
      onBeforeOk: () => {
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
  .mango-equipment-page {
    width: 100%;
    min-width: 0;
  }

  .mango-equipment-spin {
    display: block;
    width: 100%;
    margin-top: 8px;
  }

  .mango-equipment-spin :deep(.arco-spin-children) {
    display: block;
    width: 100%;
  }

  .mango-equipment-grid {
    display: grid;
    width: 100%;
    min-width: 0;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 12px;
  }

  .mango-equipment-grid-item {
    min-width: 0;
  }

  .mango-equipment-empty {
    grid-column: 1 / -1;
  }

  .executor-card {
    display: flex;
    width: 100%;
    min-width: 0;
    height: 100%;
    flex-direction: column;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-lg);
    background: var(--m-surface);
    overflow: hidden;
    transition: border-color 0.15s ease, box-shadow 0.15s ease;

    &:hover {
      border-color: var(--m-primary-border);
      box-shadow: var(--m-shadow);
    }

    :deep(.arco-card-header) {
      padding: 12px 16px;
      border-bottom: 1px solid var(--m-border);
    }

    :deep(.arco-card-body) {
      flex: 1;
      padding: 12px 16px;
    }

    :deep(.arco-card-footer) {
      border-top: 1px solid var(--m-border);
      padding: 4px 16px;
    }

    .card-header {
      display: flex;
      align-items: center;

      .avatar {
        background-color: var(--m-primary-soft);
        margin-right: 12px;
      }

      .header-info {
        display: flex;
        flex-direction: column;
        flex: 1;

        .owner-name {
          font-size: 16px;
          font-weight: 500;
          color: var(--m-text);
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
      }

      .online-status {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background-color: color-mix(in srgb, var(--m-success) 24%, var(--m-surface));
        border: 2px solid color-mix(in srgb, var(--m-success) 34%, transparent);
        margin-left: 12px;
        flex-shrink: 0;
      }
    }

    .card-content {
      .info-item,
      .status-item {
        display: flex;
        align-items: center;
        margin-bottom: 10px;

        &:last-child {
          margin-bottom: 4px;
        }

        .info-icon,
        .status-icon {
          font-size: 16px;
          margin-right: 8px;
          color: var(--m-muted);
        }

        .info-label,
        .status-label {
          font-size: 14px;
          color: var(--m-text-2);
          margin-right: 8px;
          flex-shrink: 0;
        }

        .info-value {
          font-size: 14px;
          color: var(--m-text);
          flex: 1;
          text-align: right;

          &.type-badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 500;

            &.type-pytest {
              background-color: color-mix(in srgb, var(--m-chart-5) 16%, var(--m-surface));
              color: var(--m-chart-5);
            }

            &.type-pytest-web {
              background-color: var(--m-primary-soft);
              color: var(--m-primary);
            }

            &.type-web-ui {
              background-color: color-mix(in srgb, var(--m-success) 16%, var(--m-surface));
              color: var(--m-success);
            }

            &.type-android-ui {
              background-color: color-mix(in srgb, var(--m-danger) 14%, var(--m-surface));
              color: var(--m-danger);
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
          color: var(--m-primary);
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
  @media (max-width: 1200px) {
    .mango-equipment-grid {
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    }
  }

  @media (max-width: 640px) {
    .mango-equipment-grid {
      grid-template-columns: 1fr;
    }

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
        .info-item,
        .status-item {
          margin-bottom: 8px;

          &:last-child {
            margin-bottom: 3px;
          }

          .info-label,
          .status-label {
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
</style>
