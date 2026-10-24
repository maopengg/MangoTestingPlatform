<template>
  <TableBody ref="tableBody" content-flush>
    <template #header>
      <TableHeader
        :show-filter="true"
        title="用户管理"
        @search="doRefresh"
        @reset-search="onResetSearch"
      >
        <template #search-content>
          <a-form layout="inline" :model="{}" @keyup.enter="doRefresh">
            <a-form-item v-for="item of conditionItems" :key="item.key" :label="item.label">
              <template v-if="item.type === 'input'">
                <a-input v-model="item.value" :placeholder="item.placeholder" @blur="doRefresh" />
              </template>
              <template v-else-if="item.type === 'select'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :placeholder="item.placeholder"
                  :options="project.data"
                  :field-names="fieldNames"
                  value-key="key"
                  allow-clear
                  allow-search
                  @change="doRefresh"
                />
              </template>
              <template v-if="item.type === 'date'">
                <a-date-picker v-model="item.value" />
              </template>
              <template v-if="item.type === 'time'">
                <a-time-picker v-model="item.value" value-format="HH:mm:ss" />
              </template>
              <template v-if="item.type === 'check-group'">
                <a-checkbox-group v-model="item.value">
                  <a-checkbox v-for="it of item.optionItems" :value="it.value" :key="it.value">
                    {{ item.label }}
                  </a-checkbox>
                </a-checkbox-group>
              </template>
            </a-form-item>
          </a-form>
        </template>
      </TableHeader>
    </template>

    <template #default>
      <TableTabs>
        <template #extra>
          <a-space>
            <div>
              <a-button
                type="primary"
                size="small"
                @click="onRegisterUser"
                data-testid="qa-views-system-user-button-注册用户"
                >注册用户</a-button
              >
            </div>
          </a-space>
        </template>
      </TableTabs>
      <a-table
        :scroll="{ x: tableScrollX }"
        :bordered="false"
        :row-selection="{ selectedRowKeys, showCheckedAll }"
        :loading="table.tableLoading.value"
        :data="table.dataList"
        :columns="tableColumns"
        :pagination="false"
        :rowKey="rowKey"
        @selection-change="onSelectionChange"
      >
        <template #columns>
          <a-table-column
            v-for="item of tableColumns"
            :key="item.key"
            :align="item.align"
            :title="item.title"
            :width="item.width"
            :data-index="item.key"
            :fixed="item.fixed"
            :ellipsis="item.ellipsis"
            :tooltip="item.tooltip"
          >
            <template v-if="item.key === 'index'" #cell="{ record }">
              {{ record.id }}
            </template>
            <template v-else-if="item.key === 'role'" #cell="{ record }">
              {{ record.role?.name || '游客' }}
            </template>
            <template v-else-if="item.key === 'is_super_admin'" #cell="{ record }">
              <a-switch v-permission="'system.user:edit'"
                :model-value="record.is_super_admin"
                :checked-value="true"
                :unchecked-value="false"
                :loading="superAdminLoadingIds.includes(record.id)"
                size="small"
                @change="(checked) => onSuperAdminChange(record, checked)"
              />
            </template>
            <template v-else-if="item.key === 'departments'" #cell="{ record }">
              <span v-if="record.departments?.length">
                {{ record.departments.map((department: any) => department.name).join('、') }}
              </span>
              <span v-else>-</span>
            </template>
            <template v-else-if="item.key === 'update_user'" #cell="{ record }">
              {{ record.update_user?.name || record.update_user?.username || '-' }}
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <MangoTableActions
                :actions="[
                  { permission: 'system.user:edit', label: '编辑', onClick: () => onUpdate(record) },
                  { permission: 'system.user:edit', label: '重置密码', onClick: () => onResetPassword(record) },
                  { permission: 'system.user:edit', label: '重置 MCP Key', danger: true, onClick: () => onResetApiKey(record) },
                  { permission: 'system.user:delete', label: '删除', danger: true, onClick: () => onDelete(record) },
                ]"
              />
            </template>
          </a-table-column>
        </template>
      </a-table>
    </template>
    <template #footer>
      <TableFooter :pagination="pagination" />
    </template>
  </TableBody>
  <ModalDialog ref="modalDialogRef" :title="userData.actionTitle" @confirm="onDataForm">
    <template #content>
      <a-form :model="formModel">
        <a-form-item
          :class="[item.required ? 'mango-form-item__require' : 'mango-form-item__no_require']"
          :label="item.label"
          v-for="item of visibleFormItems()"
          :key="item.key"
        >
          <template v-if="item.type === 'input' && item.key === 'password'">
            <a-input-password :placeholder="item.placeholder" v-model="item.value" allow-clear />
          </template>
          <template v-else-if="item.type === 'input'">
            <a-input :placeholder="item.placeholder" v-model="item.value" />
          </template>
          <template v-else-if="item.type === 'textarea'">
            <a-textarea
              v-model="item.value"
              :placeholder="item.placeholder"
              :auto-size="{ minRows: 3, maxRows: 5 }"
            />
          </template>
          <template v-else-if="item.type === 'input-tag'">
            <a-input-tag v-model="item.value" :placeholder="item.placeholder" allow-clear />
          </template>
          <template v-else-if="item.type === 'switch'">
            <a-switch v-model="item.value" />
          </template>
          <template v-else-if="item.type === 'department-select'">
            <a-select
              v-model="item.value"
              :placeholder="item.placeholder"
              :options="userData.allDepartment"
              :loading="userData.departmentOptionsLoading"
              :field-names="fieldNames"
              value-key="key"
              multiple
              allow-clear
              allow-search
            />
          </template>
          <template v-else-if="item.type === 'select' && item.key === 'role'">
            <a-select
              v-model="item.value"
              :placeholder="item.placeholder"
              :options="userData.allRole"
              :loading="userData.roleOptionsLoading"
              :field-names="fieldNames"
              value-key="key"
              allow-clear
              allow-search
            />
          </template>
          <template
            v-if="
              (item.key === 'email' && userData.isRegister) ||
              (item.key === 'username' && userData.requiresEmailLoginMigration)
            "
            #extra
          >
            <template v-if="item.key === 'email'">
              注册成功后，系统将生成随机密码并发送至该邮箱；请先完成
              <a-link @click="goToEmailConfig">邮箱配置</a-link>。
            </template>
            <template v-else>
              该用户仍使用历史账号登录，本次编辑必须填写登录邮箱，保存后将改用邮箱登录。
            </template>
          </template>
        </a-form-item>
      </a-form>
    </template>
  </ModalDialog>
  <ModalDialog
    ref="resetPasswordDialogRef"
    title="重置密码"
    width="560px"
    @confirm="onResetPasswordConfirm"
  >
    <template #content>
      <a-form :model="resetPasswordForm">
        <a-form-item label="用户账号">
          <a-input :model-value="resetPasswordForm.username" disabled />
        </a-form-item>
        <a-form-item label="发送方式">
          <span>系统生成随机密码并发送到该用户的登录邮箱。</span>
          <template #extra>
            历史账号需先由用户在个人中心修改密码并切换为邮箱登录；发送前请确认已完成
            <a-link @click="goToEmailConfig">邮箱配置</a-link>。
          </template>
        </a-form-item>
      </a-form>
    </template>
  </ModalDialog>
</template>

<script lang="ts" setup>
  import { usePagination, useRowKey, useRowSelection, useTable } from '@/hooks/table'
  import { ModalDialogType } from '@/types/components'
  import { Message, Modal } from '@arco-design/web-vue'
  import { onMounted, ref, nextTick, reactive } from 'vue'
  import { useRouter } from 'vue-router'
  import { useProject } from '@/store/modules/get-project'
  import useUserStore from '@/store/modules/user'
  import { fieldNames } from '@/setting'
  import { getFormItems } from '@/utils/datacleaning'
  import { conditionItems, formItems, tableColumns, tableScrollX } from './config'
  import {
    deleteUserInfo,
    getUserInfo,
    getUserDepartmentName,
    postUserInfo,
    putUserInfo,
    registerUser,
    resetUserApiKey,
    resetUserPassword,
  } from '@/api/user/user'
  import { getUserAllRole } from '@/api/user/role'
  import TableTabs from '@/components/table/TableTabs.vue'

  const modalDialogRef = ref<ModalDialogType | null>(null)
  const resetPasswordDialogRef = ref<ModalDialogType | null>(null)
  const pagination = usePagination(doRefresh, () => table.tableLoading)
  const { selectedRowKeys, onSelectionChange, showCheckedAll } = useRowSelection()
  const table = useTable()
  const rowKey = useRowKey('id')
  const project = useProject()
  const currentUser = useUserStore()
  const router = useRouter()
  const formModel = ref({})
  const superAdminLoadingIds = ref<number[]>([])
  const resetPasswordForm = reactive({
    userId: 0,
    username: '',
  })
  const userData = reactive({
    isAdd: false,
    isRegister: false,
    updateId: 0,
    actionTitle: '新增',
    requiresEmailLoginMigration: false,
    roleOptionsLoading: false,
    departmentOptionsLoading: false,
    allRole: [],
    allDepartment: [],
  })

  function doRefresh() {
    table.tableLoading.value = true
    let value = getFormItems(conditionItems)
    value['page'] = pagination.page
    value['pageSize'] = pagination.pageSize
    getUserInfo(value)
      .then((res) => {
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
      })
      .catch(() => {
        table.tableLoading.value = false
      })
  }

  function getRole() {
    userData.roleOptionsLoading = true
    getUserAllRole()
      .then((res) => {
        userData.allRole = res.data
      })
      .catch(console.log)
      .finally(() => {
        userData.roleOptionsLoading = false
      })
  }

  function getDepartment() {
    userData.departmentOptionsLoading = true
    getUserDepartmentName()
      .then((res) => {
        userData.allDepartment = res.data
      })
      .catch(console.log)
      .finally(() => {
        userData.departmentOptionsLoading = false
      })
  }

  function onResetSearch() {
    conditionItems.forEach((it) => {
      it.value = it.multiple ? [] : ''
    })
    doRefresh()
  }

  function visibleFormItems() {
    if (userData.isRegister) {
      const registerKeys = ['name', 'email', 'role']
      if (currentUser.is_super_admin) registerKeys.push('is_super_admin')
      return formItems.filter((it) => registerKeys.includes(it.key))
    }
    return formItems.filter((it) => !['password', 'email'].includes(it.key))
  }

  function resetFormItems() {
    formItems.forEach((it) => {
      if (it.reset) {
        it.reset()
      } else {
        it.value = Array.isArray(it.value) ? [] : ''
      }
    })
  }

  function onRegisterUser() {
    userData.actionTitle = '注册用户'
    userData.isAdd = false
    userData.isRegister = true
    userData.requiresEmailLoginMigration = false
    resetFormItems()
    const roleItem = formItems.find((item) => item.key === 'role')
    const superAdminItem = formItems.find((item) => item.key === 'is_super_admin')
    if (roleItem) roleItem.value = ''
    if (superAdminItem) superAdminItem.value = false
    modalDialogRef.value?.toggle()
  }

  function onDelete(record: any) {
    Modal.confirm({
      title: '提示',
      content: '是否要删除此用户？',
      cancelText: '取消',
      okText: '删除',
      onBeforeOk: () => {
        return deleteUserInfo(record.id)
          .then((res) => {
            Message.success(res.msg)
          })
          .catch(console.log)
          .finally(() => {
            doRefresh()
          })
      },
    })
  }

  function onResetPassword(record: any) {
    if (record.requires_email_login_migration) {
      Modal.warning({
        title: '请先切换为邮箱登录',
        content:
          '该用户仍使用历史账号登录。请通知用户先在“个人中心”修改密码并绑定登录邮箱，完成后再重置密码。',
        okText: '知道了',
      })
      return
    }
    resetPasswordForm.userId = record.id
    resetPasswordForm.username = record.username || ''
    resetPasswordDialogRef.value?.toggle()
  }

  function onResetPasswordConfirm() {
    resetUserPassword({
      id: resetPasswordForm.userId,
    })
      .then((res) => {
        resetPasswordDialogRef.value?.toggle()
        Message.success(res.msg)
        doRefresh()
      })
      .catch(console.log)
      .finally(() => {
        resetPasswordDialogRef.value?.setConfirmLoading(false)
      })
  }

  function goToEmailConfig() {
    modalDialogRef.value?.close()
    resetPasswordDialogRef.value?.close()
    router.push({ path: '/system/settings/index', query: { group: 'email' } })
  }

  function onResetApiKey(record: any) {
    const userName = record.name || record.username || `用户 ${record.id}`
    Modal.confirm({
      title: '重置 MCP Key',
      content: `重置后，${userName} 当前使用的 MCP Key 将立即失效，是否继续？`,
      cancelText: '取消',
      okText: '确认重置',
      okButtonProps: { status: 'danger' },
      onBeforeOk: () =>
        resetUserApiKey({ id: record.id })
          .then((res) => {
            Message.success(res.msg)
            return true
          })
          .catch(() => false),
    })
  }

  function buildUserUpdatePayload(record: any, isSuperAdmin: boolean) {
    return {
      id: record.id,
      name: record.name,
      username: record.username,
      role: record.role?.id ?? record.role ?? null,
      is_super_admin: isSuperAdmin,
      department_ids: Array.isArray(record.department_ids) ? record.department_ids : [],
    }
  }

  function setSuperAdminLoading(id: number, loading: boolean) {
    if (loading) {
      superAdminLoadingIds.value = [...new Set([...superAdminLoadingIds.value, id])]
      return
    }
    superAdminLoadingIds.value = superAdminLoadingIds.value.filter((item) => item !== id)
  }

  function onSuperAdminChange(record: any, checked: string | number | boolean) {
    const nextValue = checked === true
    setSuperAdminLoading(record.id, true)
    putUserInfo(buildUserUpdatePayload(record, nextValue))
      .then((res) => {
        if (res.code === 200) {
          record.is_super_admin = nextValue
          Message.success(res.msg)
        } else {
          Message.error(res.msg)
        }
      })
      .catch(console.log)
      .finally(() => {
        setSuperAdminLoading(record.id, false)
      })
  }

  function onUpdate(item: any) {
    userData.actionTitle = '编辑'
    userData.isAdd = false
    userData.isRegister = false
    userData.requiresEmailLoginMigration = Boolean(item.requires_email_login_migration)
    userData.updateId = item.id
    modalDialogRef.value?.toggle()
    nextTick(() => {
      formItems.forEach((it) => {
        const propName = item[it.key]
        if (it.key === 'department_ids') {
          it.value = Array.isArray(propName) ? [...propName] : []
        } else if (typeof propName === 'object' && propName !== null) {
          it.value = propName.id
        } else {
          it.value = propName
        }
      })
    })
  }

  function onDataForm() {
    const items = visibleFormItems()
    if (items.every((it) => (it.validator ? it.validator() : true))) {
      let value = getFormItems(items)
      if (userData.isRegister) {
        value = {
          name: value.name?.trim() || '',
          email: value.email?.trim().toLowerCase() || '',
          role: value.role || null,
          is_super_admin: value.is_super_admin === true,
        }
        registerUser({
          name: value.name,
          email: value.email,
          role: value.role,
          is_super_admin: value.is_super_admin,
        })
          .then((res) => {
            modalDialogRef.value?.toggle()
            Message.success(res.msg)
            doRefresh()
          })
          .catch((error) => {
            console.log(error)
          })
          .finally(() => {
            modalDialogRef.value?.setConfirmLoading(false)
          })
      } else if (userData.isAdd) {
        postUserInfo(value)
          .then((res) => {
            modalDialogRef.value?.toggle()
            Message.success(res.msg)
            doRefresh()
          })
          .catch((error) => {
            console.log(error)
          })
          .finally(() => {
            modalDialogRef.value?.setConfirmLoading(false)
          })
      } else {
        value['id'] = userData.updateId
        putUserInfo(value)
          .then((res) => {
            modalDialogRef.value?.toggle()
            Message.success(res.msg)
            doRefresh()
          })
          .catch((error) => {
            console.log(error)
          })
          .finally(() => {
            modalDialogRef.value?.setConfirmLoading(false)
          })
      }
    } else {
      modalDialogRef.value?.setConfirmLoading(false)
    }
  }

  onMounted(() => {
    nextTick(async () => {
      doRefresh()
      getRole()
      getDepartment()
    })
  })
</script>
