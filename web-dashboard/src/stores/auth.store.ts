import { create } from 'zustand'
import type { AuthUser } from '@/features/auth/types/auth.types'
import { tokenStorage } from '@/lib/storage'

type LoginSession = {
  accessToken: string
  refreshToken: string
  user: AuthUser
}

type AuthState = {
  accessToken: string | null
  isAuthenticated: boolean
  login: (session: LoginSession) => void
  logout: () => void
  setAccessToken: (token: string) => void
  setUser: (user: AuthUser | null) => void
  user: AuthUser | null
}

const storedToken = tokenStorage.getAccessToken()

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: storedToken,
  isAuthenticated: Boolean(storedToken),
  user: null,
  login: ({ accessToken, refreshToken, user }) => {
    tokenStorage.setAccessToken(accessToken)
    tokenStorage.setRefreshToken(refreshToken)
    set({ accessToken, isAuthenticated: true, user })
  },
  logout: () => {
    tokenStorage.clearSession()
    set({ accessToken: null, isAuthenticated: false, user: null })
  },
  setAccessToken: (token) => {
    tokenStorage.setAccessToken(token)
    set({ accessToken: token, isAuthenticated: true })
  },
  setUser: (user) => set({ user }),
}))
