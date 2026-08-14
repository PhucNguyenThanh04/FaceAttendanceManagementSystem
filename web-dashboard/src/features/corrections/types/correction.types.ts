import type { PaginatedResponse } from '@/types/common.types'

export type CorrectionStatus = 'pending' | 'approved' | 'rejected' | 'cancelled'
export type CorrectionAction = 'approved' | 'rejected' | 'forwarded' | 'cancelled'

export type CorrectionRequest = {
  request_id: string
  employee_id: string
  attendance_record_id: string | null
  requested_check_in: string | null
  requested_check_out: string | null
  reason: string
  status: CorrectionStatus
  reviewed_by: string | null
  reviewed_at: string | null
  rejection_reason: string | null
  created_at: string
  updated_at: string
}

export type CorrectionLog = {
  log_id: number
  correction_request_id: string
  reviewer_id: string
  action: CorrectionAction
  comment: string | null
  old_check_in: string | null
  old_check_out: string | null
  new_check_in: string | null
  new_check_out: string | null
  created_at: string
}

export type CorrectionListParams = {
  page: number
  page_size: number
  employee_id?: string
  status?: CorrectionStatus
  requested_from?: string
  requested_to?: string
}

export type CorrectionListResponse = PaginatedResponse<CorrectionRequest>

export type ReviewCorrectionPayload = {
  action: 'approved' | 'rejected'
  comment?: string
  approved_check_in?: string
  approved_check_out?: string
  rejection_reason?: string
}
