import type { FaceProfileStatus, PaginatedResponse, UUID } from '@/types/common.types'

export type FaceProfile = {
  profile_id: UUID
  employee_id: UUID
  status: FaceProfileStatus
  created_at: string
  updated_at: string
}

export type FaceProfileListParams = {
  page?: number
  page_size?: number
  employee_id?: UUID
  status?: FaceProfileStatus
}

export type FaceProfileListResponse = PaginatedResponse<FaceProfile>
