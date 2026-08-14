import { api } from '@/lib/axios'
import type {
  AuditLog,
  AuditLogListResponse,
  AuditLogParams,
} from '@/features/audit-logs/types/audit-log.types'

export const auditLogApi = {
  list: async (params: AuditLogParams): Promise<AuditLogListResponse> => {
    const response = await api.get<AuditLogListResponse>('/audit-logs', { params })
    return response.data
  },
  getById: async (logId: string): Promise<AuditLog> => {
    const response = await api.get<AuditLog>(`/audit-logs/${logId}`)
    return response.data
  },
}
