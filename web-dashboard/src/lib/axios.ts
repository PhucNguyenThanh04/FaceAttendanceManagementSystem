import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { tokenStorage } from '@/lib/storage'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || '/api/v1'

type RetryableRequest = InternalAxiosRequestConfig & { _retry?: boolean }
type QueuedRequest = {
  reject: (error: unknown) => void
  resolve: (token: string) => void
}

let isRefreshing = false
let refreshQueue: QueuedRequest[] = []

function settleRefreshQueue(error: unknown, token?: string) {
  refreshQueue.forEach(({ reject, resolve }) => {
    if (error || !token) reject(error)
    else resolve(token)
  })
  refreshQueue = []
}

function expireSession() {
  tokenStorage.clearSession()
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new Event('face-attendance:session-expired'))
  }
}

export const api = axios.create({
  baseURL: apiBaseUrl,
  withCredentials: true,
})

api.interceptors.request.use((config) => {
  const token = tokenStorage.getAccessToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const request = error.config as RetryableRequest | undefined
    const isAuthRequest = request?.url?.includes('/auth/login') || request?.url?.includes('/auth/refresh')

    if (error.response?.status !== 401 || !request || request._retry || isAuthRequest) {
      return Promise.reject(error)
    }

    const refreshToken = tokenStorage.getRefreshToken()
    if (!refreshToken) {
      expireSession()
      return Promise.reject(error)
    }

    if (isRefreshing) {
      return new Promise<string>((resolve, reject) => {
        refreshQueue.push({ reject, resolve })
      }).then((token) => {
        request._retry = true
        request.headers.Authorization = `Bearer ${token}`
        return api(request)
      })
    }

    request._retry = true
    isRefreshing = true

    try {
      const response = await axios.post(`${apiBaseUrl}/auth/refresh`, {
        refresh_token: refreshToken,
      })
      const accessToken = response.data.access_token as string
      const nextRefreshToken = response.data.refresh_token as string | undefined
      tokenStorage.setAccessToken(accessToken)
      if (nextRefreshToken) tokenStorage.setRefreshToken(nextRefreshToken)
      request.headers.Authorization = `Bearer ${accessToken}`
      settleRefreshQueue(null, accessToken)
      return api(request)
    } catch (refreshError) {
      settleRefreshQueue(refreshError)
      expireSession()
      return Promise.reject(refreshError)
    } finally {
      isRefreshing = false
    }
  },
)
