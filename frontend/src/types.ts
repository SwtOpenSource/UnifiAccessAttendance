export type HostType = 'uckp' | 'unvr'
export type Role = 'admin' | 'employee'

export interface HostConfigOut {
  host_type: HostType | ''
  base_url: string
  configured: boolean
}

export interface TokenOut {
  token: string
  role: Role
  display_name: string
}

export interface DutySet {
  start_work: string
  get_off: string
}

export interface Employee {
  id: string
  username: string
  display_name: string
  unifi_user_id: string
  department: string
  is_active: boolean
}

export interface UnifiUser {
  id: string
  first_name: string
  last_name: string
  employee_number: string
  status: string
}

export interface LeaveRequestOut {
  id: string
  employee_id: string
  employee_name: string
  leave_type: string
  start_date: string
  end_date: string
  reason: string
  status: 'pending' | 'approved' | 'rejected'
  reviewer_note: string
  created_at: string
  reviewed_at: string | null
}

export interface DayRecord {
  date: string
  first_punch: string | null
  last_punch: string | null
  status: string
}

export interface LeaderboardRow {
  employee_id: string
  display_name: string
  department: string
  total_days: number
  normal_days: number
  on_time_rate: number
  streak: number
}

export interface PublicBoardRow {
  display_name: string
  department: string
  on_time_rate: number
  streak: number
}
