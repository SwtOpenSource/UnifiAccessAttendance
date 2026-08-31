import { defineStore } from 'pinia'
import type { Role } from '@/types'

const STORAGE_KEY = 'uaa_session'

interface Session {
  token: string
  role: Role
  display_name: string
}

function loadSession(): Session | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as Session) : null
  } catch {
    return null
  }
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    session: loadSession() as Session | null,
  }),
  getters: {
    token: (state) => state.session?.token ?? '',
    role: (state) => state.session?.role ?? null,
    displayName: (state) => state.session?.display_name ?? '',
    isAdmin: (state) => state.session?.role === 'admin',
    isLoggedIn: (state) => !!state.session,
  },
  actions: {
    setSession(session: Session) {
      this.session = session
      localStorage.setItem(STORAGE_KEY, JSON.stringify(session))
    },
    logout() {
      this.session = null
      localStorage.removeItem(STORAGE_KEY)
    },
  },
})
