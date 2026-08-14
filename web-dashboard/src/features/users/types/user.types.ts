import type { PaginatedResponse, RoleName, UserStatus } from '@/types/common.types'

export type UserAccount = {
  user_id: string
  email: string
  status: UserStatus
  last_login_at: string | null
  role_name: RoleName
  created_at: string
  updated_at: string
}

export type UserListParams = {
  page: number
  page_size: number
  search?: string
  status?: UserStatus
  role?: RoleName
}

export type UserListResponse = PaginatedResponse<UserAccount>
