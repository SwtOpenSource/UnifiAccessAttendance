<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { hostApi, authApi } from '@/api'
import { useAuthStore } from '@/store/auth'
import type { HostType } from '@/types'

const router = useRouter()
const auth = useAuthStore()

const loading = ref(true)
const hostConfigured = ref(false)
const errorText = ref('')

// 主機設定表單
const hostType = ref<HostType>('unvr')
const baseUrl = ref('')
const credential = ref('')
const settingHost = ref(false)

// 登入表單
const loginMode = ref<'admin' | 'employee'>('admin')
const username = ref('')
const password = ref('')
const loggingIn = ref(false)

async function refreshHost() {
  const cfg = await hostApi.get()
  hostConfigured.value = cfg.configured
  if (cfg.configured) {
    hostType.value = (cfg.host_type || 'unvr') as HostType
    baseUrl.value = cfg.base_url
  }
}

onMounted(async () => {
  try {
    await refreshHost()
  } finally {
    loading.value = false
  }
})

async function submitHost() {
  errorText.value = ''
  settingHost.value = true
  try {
    await hostApi.set({ host_type: hostType.value, base_url: baseUrl.value, credential: credential.value })
    await refreshHost()
  } catch (e: any) {
    errorText.value = e?.response?.data?.detail || '設定失敗，請確認 IP 與憑證'
  } finally {
    settingHost.value = false
  }
}

async function login() {
  errorText.value = ''
  loggingIn.value = true
  try {
    const res = loginMode.value === 'admin'
      ? await authApi.adminLogin(username.value, password.value)
      : await authApi.employeeLogin(username.value, password.value)
    auth.setSession(res)
    router.push({ name: 'board' })
  } catch (e: any) {
    errorText.value = e?.response?.data?.detail || '登入失敗，請確認帳號密碼'
  } finally {
    loggingIn.value = false
  }
}
</script>

<template>
  <div style="max-width: 420px; margin: 60px auto;">
    <h1 style="text-align:center; color: var(--brand); margin-bottom: 24px;">🏆 打卡英雄榜</h1>

    <div v-if="loading" class="card">載入中…</div>

    <!-- 尚未設定主機：管理員第一次進來要先設定 -->
    <div v-else-if="!hostConfigured" class="card">
      <h3 style="margin-top:0">設定 UniFi Access 主機</h3>
      <p style="font-size:13px;color:var(--muted)">第一次使用需先設定要連接的主機，之後才能登入。</p>

      <div class="form-row">
        <label>主機類型</label>
        <select v-model="hostType">
          <option value="unvr">UNVR / UDM（Dream Machine 系列）</option>
          <option value="uckp">UCKP（Cloud Key Gen2 Plus）</option>
        </select>
      </div>
      <div class="form-row">
        <label>主機 IP 或網址</label>
        <input v-model="baseUrl" placeholder="192.168.1.1" />
      </div>
      <div class="form-row">
        <label>{{ hostType === 'uckp' ? 'API Key' : 'API Token' }}</label>
        <input v-model="credential" type="password"
               :placeholder="hostType === 'uckp' ? 'X-API-KEY' : 'Bearer Token'" />
        <small style="color:var(--muted)">
          於 UniFi Access 主控台「Settings → General → Advanced → API Token」建立
        </small>
      </div>
      <button class="btn" :disabled="settingHost || !baseUrl || !credential" @click="submitHost">
        {{ settingHost ? '測試連線中…' : '儲存並測試連線' }}
      </button>
      <div v-if="errorText" class="error-text">{{ errorText }}</div>
    </div>

    <!-- 已設定主機：登入 -->
    <div v-else class="card">
      <div style="display:flex; gap:8px; margin-bottom:16px;">
        <button class="btn" :class="{ secondary: loginMode !== 'admin' }" @click="loginMode = 'admin'">管理員登入</button>
        <button class="btn" :class="{ secondary: loginMode !== 'employee' }" @click="loginMode = 'employee'">員工登入</button>
      </div>

      <div class="form-row">
        <label>帳號</label>
        <input v-model="username" @keyup.enter="login" />
      </div>
      <div class="form-row">
        <label>密碼</label>
        <input v-model="password" type="password" @keyup.enter="login" />
      </div>
      <button class="btn" :disabled="loggingIn || !username || !password" @click="login" style="width:100%">
        {{ loggingIn ? '登入中…' : '登入' }}
      </button>
      <div v-if="errorText" class="error-text">{{ errorText }}</div>

      <p style="font-size:12px;color:var(--muted); margin-top:16px;">
        管理員請用 UniFi Access 帳號登入；員工請用管理員建立的本地帳號登入。
        <a href="javascript:void(0)" @click="hostConfigured = false" style="color:var(--brand)">重新設定主機</a>
      </p>
    </div>
  </div>
</template>
