import axios from 'axios'
import { useAuthStore } from '@/store/auth'

// 後端網址：優先讀 config.json（跟舊版一樣，讓同一份 build 產物可以指到不同後端，
// 不用因為換部署環境重新 build 前端），開發模式退回 vite proxy 的相對路徑。
let cachedBase: string | null = null

async function apiBase(): Promise<string> {
  if (cachedBase) return cachedBase
  try {
    const res = await fetch('/config.json', { cache: 'no-store' })
    const cfg = await res.json()
    cachedBase = cfg.API_BASE || ''
  } catch {
    cachedBase = ''
  }
  return cachedBase ?? ''
}

export const api = axios.create()

api.interceptors.request.use(async (config) => {
  config.baseURL = await apiBase()
  const auth = useAuthStore()
  if (auth.token) {
    config.headers = config.headers ?? {}
    config.headers.Authorization = `Bearer ${auth.token}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err?.response?.status === 401) {
      const auth = useAuthStore()
      auth.logout()
    }
    return Promise.reject(err)
  },
)
