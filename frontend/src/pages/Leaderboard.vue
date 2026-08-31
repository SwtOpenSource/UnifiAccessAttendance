<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { attendanceApi, dutyApi, employeeApi, publicBoardApi } from '@/api'
import { useAuthStore } from '@/store/auth'
import type { DutySet, Employee, LeaderboardRow, UnifiUser } from '@/types'

const auth = useAuthStore()

function today(): string {
  return new Date().toISOString().slice(0, 10)
}
function daysAgo(n: number): string {
  const d = new Date()
  d.setDate(d.getDate() - n)
  return d.toISOString().slice(0, 10)
}

const startDate = ref(daysAgo(6))
const endDate = ref(today())
const rows = ref<LeaderboardRow[]>([])
const loading = ref(false)
const errorText = ref('')

async function loadBoard() {
  loading.value = true
  errorText.value = ''
  try {
    rows.value = await attendanceApi.leaderboard(startDate.value, endDate.value)
  } catch (e: any) {
    errorText.value = e?.response?.data?.detail || '載入失敗'
  } finally {
    loading.value = false
  }
}

const totalStaff = computed(() => rows.value.length)
const avgOnTimeRate = computed(() => {
  if (!rows.value.length) return 0
  return Math.round(rows.value.reduce((s, r) => s + r.on_time_rate, 0) / rows.value.length)
})
const topStreak = computed(() => rows.value.reduce((m, r) => Math.max(m, r.streak), 0))

function rankBadgeClass(i: number): string {
  return i === 0 ? 'gold' : i === 1 ? 'silver' : i === 2 ? 'bronze' : ''
}

// ── 管理員設定區 ──────────────────────────────────────────────
const duty = ref<DutySet>({ start_work: '', get_off: '' })
const employees = ref<Employee[]>([])
const newEmp = ref({ username: '', password: '', display_name: '', department: '', unifi_user_id: '' })
const unifiUsers = ref<UnifiUser[]>([])
const publicBoard = ref({ enabled: false, slug: '' })
const adminError = ref('')
const adminOk = ref('')

async function loadAdminData() {
  if (!auth.isAdmin) return
  const [d, emps, pb] = await Promise.all([dutyApi.get(), employeeApi.list(), publicBoardApi.getSetting()])
  duty.value = d
  employees.value = emps
  publicBoard.value = pb
  try {
    unifiUsers.value = await employeeApi.unifiUsers()
  } catch {
    unifiUsers.value = []
  }
}

async function saveDuty() {
  adminError.value = ''
  try {
    await dutyApi.set(duty.value)
    adminOk.value = '上下班時間已更新'
  } catch (e: any) {
    adminError.value = e?.response?.data?.detail || '儲存失敗'
  }
}

async function createEmployee() {
  adminError.value = ''
  try {
    await employeeApi.create(newEmp.value)
    newEmp.value = { username: '', password: '', display_name: '', department: '', unifi_user_id: '' }
    employees.value = await employeeApi.list()
    adminOk.value = '員工帳號已建立'
  } catch (e: any) {
    adminError.value = e?.response?.data?.detail || '建立失敗'
  }
}

async function bindUnifi(emp: Employee, unifiUserId: string) {
  await employeeApi.bindUnifi(emp.id, unifiUserId)
  employees.value = await employeeApi.list()
}

async function togglePublicBoard() {
  publicBoard.value = await publicBoardApi.setSetting(!publicBoard.value.enabled)
}

const publicBoardUrl = computed(() =>
  publicBoard.value.enabled ? `${window.location.origin}/public/${publicBoard.value.slug}` : '',
)

onMounted(async () => {
  await loadBoard()
  await loadAdminData()
})
</script>

<template>
  <div class="card">
    <div style="display:flex; gap:12px; align-items:end; flex-wrap:wrap;">
      <div class="form-row" style="margin:0"><label>起始日期</label><input type="date" v-model="startDate" /></div>
      <div class="form-row" style="margin:0"><label>結束日期</label><input type="date" v-model="endDate" /></div>
      <button class="btn" :disabled="loading" @click="loadBoard">{{ loading ? '載入中…' : '查詢' }}</button>
    </div>
    <div v-if="errorText" class="error-text">{{ errorText }}</div>
  </div>

  <div class="stat-cards">
    <div class="card stat-card"><div class="value">{{ totalStaff }}</div><div class="label">上榜人數</div></div>
    <div class="card stat-card"><div class="value">{{ avgOnTimeRate }}%</div><div class="label">平均準時率</div></div>
    <div class="card stat-card"><div class="value">{{ topStreak }}</div><div class="label">最長連續全勤（天）</div></div>
  </div>

  <div class="card">
    <h3 style="margin-top:0">排行榜</h3>
    <table>
      <thead>
        <tr><th>排名</th><th>姓名</th><th>部門</th><th>準時率</th><th>正常天數</th><th>連續全勤</th></tr>
      </thead>
      <tbody>
        <tr v-for="(r, i) in rows" :key="r.employee_id">
          <td><span class="rank-badge" :class="rankBadgeClass(i)">{{ i + 1 }}</span></td>
          <td>{{ r.display_name }}</td>
          <td>{{ r.department || '-' }}</td>
          <td>{{ r.on_time_rate }}%</td>
          <td>{{ r.normal_days }} / {{ r.total_days }}</td>
          <td>{{ r.streak }} 天</td>
        </tr>
        <tr v-if="!rows.length"><td colspan="6" style="text-align:center;color:var(--muted)">目前查詢區間沒有資料</td></tr>
      </tbody>
    </table>
  </div>

  <template v-if="auth.isAdmin">
    <div class="card">
      <h3 style="margin-top:0">管理設定</h3>
      <div v-if="adminError" class="error-text">{{ adminError }}</div>
      <div v-if="adminOk" style="color:var(--ok);font-size:13px;margin-bottom:8px">{{ adminOk }}</div>

      <h4>上下班時間</h4>
      <div style="display:flex; gap:12px; align-items:end;">
        <div class="form-row" style="margin:0"><label>上班</label><input type="time" v-model="duty.start_work" /></div>
        <div class="form-row" style="margin:0"><label>下班</label><input type="time" v-model="duty.get_off" /></div>
        <button class="btn" @click="saveDuty">儲存</button>
      </div>

      <h4>公開唯讀排行榜</h4>
      <button class="btn" :class="{ secondary: publicBoard.enabled }" @click="togglePublicBoard">
        {{ publicBoard.enabled ? '關閉公開連結' : '開啟公開連結' }}
      </button>
      <div v-if="publicBoardUrl" style="margin-top:8px; font-size:13px;">
        分享連結：<a :href="publicBoardUrl" target="_blank">{{ publicBoardUrl }}</a>
      </div>

      <h4>員工帳號</h4>
      <table>
        <thead><tr><th>帳號</th><th>姓名</th><th>部門</th><th>綁定 UniFi 使用者</th></tr></thead>
        <tbody>
          <tr v-for="e in employees" :key="e.id">
            <td>{{ e.username }}</td>
            <td>{{ e.display_name }}</td>
            <td>{{ e.department }}</td>
            <td>
              <select :value="e.unifi_user_id" @change="bindUnifi(e, ($event.target as HTMLSelectElement).value)">
                <option value="">未綁定</option>
                <option v-for="u in unifiUsers" :key="u.id" :value="u.id">
                  {{ u.first_name }}{{ u.last_name }}
                </option>
              </select>
            </td>
          </tr>
        </tbody>
      </table>

      <h5>新增員工帳號</h5>
      <div style="display:flex; gap:8px; flex-wrap:wrap; align-items:end;">
        <div class="form-row" style="margin:0"><label>帳號</label><input v-model="newEmp.username" /></div>
        <div class="form-row" style="margin:0"><label>密碼</label><input v-model="newEmp.password" type="password" /></div>
        <div class="form-row" style="margin:0"><label>姓名</label><input v-model="newEmp.display_name" /></div>
        <div class="form-row" style="margin:0"><label>部門</label><input v-model="newEmp.department" /></div>
        <button class="btn" :disabled="!newEmp.username || !newEmp.password || !newEmp.display_name" @click="createEmployee">新增</button>
      </div>
    </div>
  </template>
</template>
