import type { PaginatedResponse } from '@/types/common.types'

export type AuditAction =
  | 'create'
  | 'update'
  | 'delete'
  | 'approve'
  | 'reject'
  | 'login'
  | 'logout'
  | 'revoke'
  | 'manual_edit'

export type AuditLog = {
  log_id: string
  performed_by: string | null
  action: AuditAction
  object_type: string
  object_id: string | null
  old_value: Record<string, unknown> | null
  new_value: Record<string, unknown> | null
  reason: string | null
  ip_address: string | null
  user_agent: string | null
  created_at: string
}

export type AuditLogParams = {
  page: number
  page_size: number
  performed_by?: string
  action?: AuditAction
  object_type?: string
  object_id?: string
  created_from?: string
  created_to?: string
}

export type AuditLogListResponse = PaginatedResponse<AuditLog>
