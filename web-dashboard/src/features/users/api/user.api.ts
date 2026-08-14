import { api } from '@/lib/axios'
import type { RoleName, UserStatus } from '@/types/common.types'
import type {
  UserAccount,
  UserListParams,
  UserListResponse,
} from '@/features/users/types/user.types'

export const userApi = {
  list: async (params: UserListParams): Promise<UserListResponse> => {
    const response = await api.get<UserListResponse>('/users/', { params })
    return response.data
  },
  assignRole: async (userId: string, role_name: RoleName): Promise<UserAccount> => {
    const response = await api.patch<UserAccount>(`/users/${userId}/role`, { role_name })
    return response.data
  },
  updateStatus: async (userId: string, status: UserStatus): Promise<UserAccount> => {
    const response = await api.patch<UserAccount>(`/users/${userId}/status`, { status })
    return response.data
  },
  resetPassword: async (userId: string, new_password: string): Promise<UserAccount> => {
    const response = await api.patch<UserAccount>(`/users/${userId}/password/reset`, { new_password })
    return response.data
  },
}
