<template>
  <ModalDialog modal-class="mango-simple-form-modal" ref="dialog" :title="record === null ? '注册用户' : '编辑'" :width="560" @confirm="save" @cancel="closeEditor">
    <template #content>
      <a-form auto-label-width class="mango-simple-form" :model="draft" layout="horizontal">
        <a-form-item label="昵称" class="mango-form-item__require mango-simple-form-item">
          <a-input v-model="draft.name" placeholder="请输入用户昵称" />
        </a-form-item>
        <a-form-item label="登录邮箱" class="mango-form-item__require mango-simple-form-item">
          <a-input v-model="draft.username" placeholder="请输入登录邮箱" />
          <template #extra>
            <template v-if="record === null">注册成功后，系统将生成随机密码并发送至该邮箱；请先完成 <a-link @click="emailSettings">邮箱配置</a-link>。</template>
            <template v-else-if="record.requires_email_login_migration">该用户仍使用历史账号登录，本次编辑必须填写登录邮箱，保存后将改用邮箱登录。</template>
          </template>
        </a-form-item>
        <a-form-item class="mango-simple-form-item" label="绑定角色">
          <a-select v-model="draft.role" :options="roleOptions" :field-names="fieldNames" :loading="roleLoading" placeholder="请选择用户角色，留空为游客" allow-clear allow-search />
          <template v-if="roleError" #extra><span class="mango-user-editor__error">{{ roleError }}</span> <a-link @click="loadRoles">重试</a-link></template>
        </a-form-item>
        <a-form-item class="mango-simple-form-item" label="超级管理员"><a-switch v-model="draft.is_super_admin" size="small" /></a-form-item>
        <a-form-item class="mango-simple-form-item" v-if="record !== null" label="所属部门">
          <a-select v-model="draft.department_ids" :options="departmentOptions" :field-names="fieldNames" :loading="departmentLoading" placeholder="请选择用户所属部门" multiple allow-clear allow-search />
          <template v-if="departmentError" #extra><span class="mango-user-editor__error">{{ departmentError }}</span> <a-link @click="loadDepartments">重试</a-link></template>
        </a-form-item>
        <a-alert v-if="saveError" type="error">{{ saveError }}</a-alert>
      </a-form>
    </template>
  </ModalDialog>
</template>

<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { fieldNames } from '@/setting'
  import type { ModalDialogType } from '@/types/components'
  import { getUserDepartmentName, putUserInfo, registerUser } from '@/api/user/user'
  import { getUserAllRole } from '@/api/user/role'
  import { copyUserRecord, createUserDraft, mergeUserOptions, parseUserOptions, userRegistrationPayload, userSuccess, userUpdatePayload, validateUserDraft } from '../user-records'
  import type { UserEditorHandle, UserId, UserOption, UserRecord } from '../user-records'

  const props = defineProps<{ contextKey: string; locked: boolean }>()
  const emit = defineEmits<{ (event: 'saved', id: UserId | null): void; (event: 'committed', id: UserId | null, context: string): void; (event: 'busy', value: boolean): void; (event: 'email-settings'): void }>()
  const dialog = ref<ModalDialogType | null>(null)
  const draft = reactive(createUserDraft()), record = ref<UserRecord | null>(null), visible = ref(false), saving = ref(false)
  const roles = ref<UserOption[]>([]), departments = ref<UserOption[]>([])
  const roleLoading = ref(false), departmentLoading = ref(false), roleError = ref(''), departmentError = ref(''), saveError = ref('')
  const roleOptions = computed(() => mergeUserOptions(roles.value, record.value?.role ? [record.value.role] : []))
  const departmentOptions = computed(() => mergeUserOptions(departments.value, record.value?.departments ?? []))
  let generation = 0, roleVersion = 0, departmentVersion = 0, disposed = false
  let pendingRoles: Promise<void> | null = null, pendingDepartments: Promise<void> | null = null
  function guard() {
    const version = generation, key = props.contextKey
    return () => !disposed && visible.value && version === generation && key === props.contextKey
  }
  function closeEditor() {
    generation++; roleVersion++; departmentVersion++; visible.value = false
    pendingRoles = null; pendingDepartments = null
    roleLoading.value = false; departmentLoading.value = false
    roles.value = []; departments.value = []; record.value = null
    roleError.value = ''; departmentError.value = ''; saveError.value = ''
    Object.assign(draft, createUserDraft()); void dialog.value?.close()
  }
  function openEditor(row: UserRecord | null): void {
    if (disposed || saving.value || props.locked) return
    closeEditor(); record.value = row === null ? null : copyUserRecord(row)
    Object.assign(draft, createUserDraft(record.value)); visible.value = true
    void dialog.value?.show(); void loadRoles()
    if (row !== null) void loadDepartments()
  }
  function openRegister() { openEditor(null) }
  function openEdit(row: UserRecord) { openEditor(row) }
  function loadRoles(): Promise<void> {
    if (!visible.value || disposed) return Promise.resolve()
    if (pendingRoles) return pendingRoles
    const valid = guard(), version = ++roleVersion
    roleLoading.value = true; roleError.value = ''
    const task = Promise.resolve().then(async () => {
      try { if (valid()) { const result = await getUserAllRole(); if (valid() && version === roleVersion) roles.value = parseUserOptions(result) } }
      catch (loadFailure0) { if (valid() && version === roleVersion) (reportLoadError(loadFailure0, "角色加载失败，请重试", false), roleError.value = '角色加载失败，请重试') }
      finally { if (valid() && version === roleVersion) { roleLoading.value = false; pendingRoles = null } }
    })
    pendingRoles = task; return task
  }
  function loadDepartments(): Promise<void> {
    if (!visible.value || record.value === null || disposed) return Promise.resolve()
    if (pendingDepartments) return pendingDepartments
    const valid = guard(), version = ++departmentVersion
    departmentLoading.value = true; departmentError.value = ''
    const task = Promise.resolve().then(async () => {
      try { if (valid()) { const result = await getUserDepartmentName(); if (valid() && version === departmentVersion) departments.value = parseUserOptions(result) } }
      catch (loadFailure1) { if (valid() && version === departmentVersion) (reportLoadError(loadFailure1, "部门加载失败，请重试", false), departmentError.value = '部门加载失败，请重试') }
      finally { if (valid() && version === departmentVersion) { departmentLoading.value = false; pendingDepartments = null } }
    })
    pendingDepartments = task; return task
  }
  async function save(): Promise<void> {
    if (saving.value) return
    if (!visible.value || disposed || props.locked) { dialog.value?.setConfirmLoading(false); return }
    const error = validateUserDraft(draft)
    if (error) { Message.error(error); dialog.value?.setConfirmLoading(false); return }
    const valid = guard(), id = record.value?.id ?? null, context = props.contextKey
    try {
      const payload = id === null ? userRegistrationPayload(draft) : userUpdatePayload(id, draft)
      saving.value = true; emit('busy', true); saveError.value = ''; dialog.value?.setConfirmLoading(true)
      const response = id === null ? await registerUser(payload) : await putUserInfo(payload)
      const message = userSuccess(response, id === null ? '注册成功' : '保存成功')
      emit('committed', id, context)
      if (!valid()) return
      closeEditor(); Message.success(message); emit('saved', id)
    } catch { if (valid()) saveError.value = '保存失败，请检查输入并重试' }
    finally {
      saving.value = false; emit('busy', false)
      if (valid()) dialog.value?.setConfirmLoading(false)
    }
  }
  function emailSettings() { closeEditor(); emit('email-settings') }
  watch(() => props.contextKey, closeEditor)
  onBeforeUnmount(() => { disposed = true; closeEditor() })
  defineExpose<UserEditorHandle>({ openRegister, openEdit, close: closeEditor })
</script>

<style scoped>
  .mango-user-editor__error { color: var(--m-danger); }
</style>
