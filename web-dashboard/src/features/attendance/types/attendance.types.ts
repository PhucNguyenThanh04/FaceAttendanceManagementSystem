import type { UUID } from '@/types/common.types'

export type AttendanceEventType = 'check_in' | 'check_out'

export type AttendanceEvent = {
  event_id: UUID
  employee_id: UUID | null
  event_type: AttendanceEventType
  event_time: string
  confidence_score: number | null
  anti_spoof_score: number | null
  image_url: string | null
  raw_result: Record<string, unknown> | null
  is_accepted: boolean
  rejection_reason: string | null
  created_at: string
}

export type AttendanceEventListParams = {
  page?: number
  page_size?: number
  employee_id?: string
  event_type?: AttendanceEventType
  accepted?: boolean
  event_time_from?: string
  event_time_to?: string
}

export type AttendanceRecordStatus =
  | 'present'
  | 'late'
  | 'early_leave'
  | 'late_and_early_leave'
  | 'absent'
  | 'on_leave'
  | 'holiday'
  | 'missing_check_in'
  | 'missing_check_out'
  | 'manually_edited'

export type AttendanceSource = 'face_recognition' | 'manual' | 'edited' | 'system'

export type AttendanceRecord = {
  record_id: UUID
  employee_id: UUID
  shift_id: number | null
  work_date: string
  check_in_time: string | null
  check_out_time: string | null
  status: AttendanceRecordStatus
  late_minutes: number
  early_leave_minutes: number
  worked_minutes: number
  source: AttendanceSource
  notes: string | null
  created_at: string
  updated_at: string
}

export type AttendanceRecordParams = {
  page?: number
  page_size?: number
  employee_id?: string
  shift_id?: number
  work_date_from?: string
  work_date_to?: string
  status?: AttendanceRecordStatus
  source?: AttendanceSource
}

export type AttendanceRecordSummary = {
  total_records: number
  present_days: number
  late_days: number
  absent_days: number
}

export type AttendanceRecordUpdate = Partial<Pick<
  AttendanceRecord,
  'check_in_time' | 'check_out_time' | 'status' | 'notes'
>>
