<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { leaveApi } from '@/api'
import { useAuthStore } from '@/store/auth'
import type { LeaveRequestOut } from '@/types'

const auth = useAuthStore()

const form = ref({ leave_type: '事假', start_date: '', end_date: '', reason: '' })
const submitting = ref(false)
const errorText = ref('')
const okText = ref('')

const mine = ref<LeaveRequestOut[]>([])
const pending = ref<LeaveRequestOut[]>([])

async function loadMine() {
  mine.value = await leaveApi.mine()
}
async function loadPending() {
  if (!auth.isAdmin) return
  pending.value = await leaveApi.list('pending')
}

async function submit() {
  errorText.value = ''
  okText.value = ''
  submitting.value = true
  try {
    await leaveApi.submit(form.value)
    form.value = { leave_type: '事假', start_date: '', end_date: '', reason: '' }
    okText.value = '已送出，等待管理員審核'
    await loadMine()
  } catch (e: any) {
    errorText.value = e?.response?.data?.detail || '送出失敗'
  } finally {
    submitting.value = false
  }
}

async function decide(row: LeaveRequestOut, approve: boolean) {
  await leaveApi.decide(row.id, approve, '')
  await loadPending()
}

onMounted(async () => {
  if (auth.role === 'employee') await loadMine()
  await loadPending()
})
</script>

<template>
  <div v-if="auth.role === 'employee'" class="card">
    <h3 style="margin-top:0">申請請假</h3>
    <div class="form-row"><label>假別</label>
      <select v-model="form.leave_type">
        <option>事假</option><option>病假</option><option>特休</option><option>其他</option>
      </select>
    </div>
    <div style="display:flex; gap:12px;">
      <div class="form-row"><label>起始日期</label><input type="date" v-model="form.start_date" /></div>
      <div class="form-row"><label>結束日期</label><input type="date" v-model="form.end_date" /></div>
    </div>
    <div class="form-row"><label>原因</label><input v-model="form.reason" placeholder="選填" /></div>
    <button class="btn" :disabled="submitting || !form.start_date || !form.end_date" @click="submit">
      {{ submitting ? '送出中…' : '送出申請' }}
    </button>
    <div v-if="errorText" class="error-text">{{ errorText }}</div>
    <div v-if="okText" style="color:var(--ok);font-size:13px;margin-top:6px">{{ okText }}</div>
  </div>

  <div v-if="auth.role === 'employee'" class="card">
    <h3 style="margin-top:0">我的請假紀錄</h3>
    <table>
      <thead><tr><th>假別</th><th>期間</th><th>原因</th><th>狀態</th></tr></thead>
      <tbody>
        <tr v-for="r in mine" :key="r.id">
          <td>{{ r.leave_type }}</td>
          <td>{{ r.start_date }} ~ {{ r.end_date }}</td>
          <td>{{ r.reason || '-' }}</td>
          <td><span class="status-chip" :class="r.status">{{ r.status === 'pending' ? '審核中' : r.status === 'approved' ? '已核准' : '已駁回' }}</span></td>
        </tr>
        <tr v-if="!mine.length"><td colspan="4" style="text-align:center;color:var(--muted)">尚無請假紀錄</td></tr>
      </tbody>
    </table>
  </div>

  <div v-if="auth.isAdmin" class="card">
    <h3 style="margin-top:0">待審核請假</h3>
    <table>
      <thead><tr><th>員工</th><th>假別</th><th>期間</th><th>原因</th><th></th></tr></thead>
      <tbody>
        <tr v-for="r in pending" :key="r.id">
          <td>{{ r.employee_name }}</td>
          <td>{{ r.leave_type }}</td>
          <td>{{ r.start_date }} ~ {{ r.end_date }}</td>
          <td>{{ r.reason || '-' }}</td>
          <td style="display:flex; gap:6px;">
            <button class="btn" @click="decide(r, true)">核准</button>
            <button class="btn danger" @click="decide(r, false)">駁回</button>
          </td>
        </tr>
        <tr v-if="!pending.length"><td colspan="5" style="text-align:center;color:var(--muted)">目前沒有待審核申請</td></tr>
      </tbody>
    </table>
  </div>
</template>
