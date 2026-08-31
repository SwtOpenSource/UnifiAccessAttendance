import { api } from './client'
import type {
  DayRecord, DutySet, Employee, HostConfigOut, LeaderboardRow, LeaveRequestOut,
  PublicBoardRow, Role, TokenOut, UnifiUser,
} from '@/types'

export const hostApi = {
  get: () => api.get<HostConfigOut>('/host').then((r) => r.data),
  set: (body: { host_type: string; base_url: string; credential: string }) =>
    api.post('/host', body).then((r) => r.data),
}

export const authApi = {
  adminLogin: (username: string, password: string) =>
    api.post<TokenOut>('/auth/admin/login', { username, password }).then((r) => r.data),
  employeeLogin: (username: string, password: string) =>
    api.post<TokenOut>('/auth/employee/login', { username, password }).then((r) => r.data),
}

export const dutyApi = {
  get: () => api.get<DutySet>('/duty').then((r) => r.data),
  set: (body: DutySet) => api.post('/duty', body).then((r) => r.data),
}

export const employeeApi = {
  list: () => api.get<Employee[]>('/employees').then((r) => r.data),
  create: (body: { username: string; password: string; display_name: string; unifi_user_id?: string; department?: string }) =>
    api.post<Employee>('/employees', body).then((r) => r.data),
  bindUnifi: (id: string, unifi_user_id: string) =>
    api.post<Employee>(`/employees/${id}/bind-unifi`, { unifi_user_id }).then((r) => r.data),
  unifiUsers: () => api.get<UnifiUser[]>('/unifi/users').then((r) => r.data),
}

export const leaveApi = {
  submit: (body: { leave_type: string; start_date: string; end_date: string; reason: string }) =>
    api.post<LeaveRequestOut>('/leaves', body).then((r) => r.data),
  mine: () => api.get<LeaveRequestOut[]>('/leaves/mine').then((r) => r.data),
  list: (status?: string) => api.get<LeaveRequestOut[]>('/leaves', { params: { status } }).then((r) => r.data),
  decide: (id: string, approve: boolean, note: string) =>
    api.post<LeaveRequestOut>(`/leaves/${id}/decision`, { approve, note }).then((r) => r.data),
}

export const attendanceApi = {
  ledger: (start_date: string, end_date: string) =>
    api.get<Record<string, { employee_id: string; display_name: string; department: string; days: Record<string, DayRecord> }>>(
      '/attendance/ledger', { params: { start_date, end_date } },
    ).then((r) => r.data),
  leaderboard: (start_date: string, end_date: string) =>
    api.get<LeaderboardRow[]>('/attendance/leaderboard', { params: { start_date, end_date } }).then((r) => r.data),
}

export const publicBoardApi = {
  getSetting: () => api.get<{ enabled: boolean; slug: string }>('/public-board/setting').then((r) => r.data),
  setSetting: (enabled: boolean) => api.post<{ enabled: boolean; slug: string }>('/public-board/setting', { enabled }).then((r) => r.data),
  fetch: (slug: string, start_date: string, end_date: string) =>
    api.get<PublicBoardRow[]>(`/public-board/${slug}`, { params: { start_date, end_date } }).then((r) => r.data),
}

export type { Role }
