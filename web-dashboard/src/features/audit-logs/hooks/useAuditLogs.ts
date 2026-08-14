import { useQuery } from '@tanstack/react-query'
import { auditLogApi } from '@/features/audit-logs/api/audit-log.api'
import type { AuditLogParams } from '@/features/audit-logs/types/audit-log.types'

export function useAuditLogs(params: AuditLogParams) {
  return useQuery({
    queryFn: () => auditLogApi.list(params),
    queryKey: ['audit-logs', params],
  })
}
