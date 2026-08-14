import { api } from '@/lib/axios'
import type {
  AttendanceEvent,
  AttendanceEventListParams,
  AttendanceRecord,
  AttendanceRecordParams,
  AttendanceRecordSummary,
  AttendanceRecordUpdate,
} from '@/features/attendance/types/attendance.types'

export const attendanceApi = {
  listEvents: async (params: AttendanceEventListParams): Promise<AttendanceEvent[]> => {
    const response = await api.get<AttendanceEvent[]>('/attendance/events', { params })
    return response.data
  },
  getEventById: async (eventId: string): Promise<AttendanceEvent> => {
    const response = await api.get<AttendanceEvent>(`/attendance/events/${eventId}`)
    return response.data
  },
  listRecords: async (params: AttendanceRecordParams): Promise<AttendanceRecord[]> => {
    const response = await api.get<AttendanceRecord[]>('/attendance/records', { params })
    return response.data
  },
  summarizeRecords: async (params: AttendanceRecordParams): Promise<AttendanceRecordSummary> => {
    const response = await api.get<AttendanceRecordSummary>('/attendance/records/summary', { params })
    return response.data
  },
  updateRecord: async (
    recordId: string,
    payload: AttendanceRecordUpdate,
  ): Promise<AttendanceRecord> => {
    const response = await api.patch<AttendanceRecord>(`/attendance/records/${recordId}`, payload)
    return response.data
  },
}
