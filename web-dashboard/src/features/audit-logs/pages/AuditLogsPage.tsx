import { useState } from 'react'
import { PageHeader } from '@/components/layout/PageHeader'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { EmptyState } from '@/components/ui/EmptyState'
import { Input } from '@/components/ui/Input'
import { Loading } from '@/components/ui/Loading'
import { Pagination } from '@/components/ui/Pagination'
import { Select } from '@/components/ui/Select'
import { StatusMessage } from '@/components/ui/StatusMessage'
import { Table } from '@/components/ui/Table'
import { useAuditLogs } from '@/features/audit-logs/hooks/useAuditLogs'
import type { AuditAction, AuditLog } from '@/features/audit-logs/types/audit-log.types'
import { formatDateTime, getApiErrorMessage } from '@/lib/utils'

const PAGE_SIZE = 20
const actions: AuditAction[] = ['create', 'update', 'delete', 'approve', 'reject', 'login', 'logout', 'revoke', 'manual_edit']

const actionTone = (action: AuditAction) => {
  if (action === 'delete' || action === 'reject' || action === 'revoke') return 'red' as const
  if (action === 'create' || action === 'approve' || action === 'login') return 'green' as const
  return 'blue' as const
}

export function AuditLogsPage() {
  const [page, setPage] = useState(1)
  const [action, setAction] = useState<AuditAction | ''>('')
  const [objectType, setObjectType] = useState('')
  const [createdFrom, setCreatedFrom] = useState('')
  const [createdTo, setCreatedTo] = useState('')
  const [selected, setSelected] = useState<AuditLog | null>(null)
  const query = useAuditLogs({
    action: action || undefined,
    created_from: createdFrom ? new Date(`${createdFrom}T00:00:00`).toISOString() : undefined,
    created_to: createdTo ? new Date(`${createdTo}T23:59:59`).toISOString() : undefined,
    object_type: objectType || undefined,
    page,
    page_size: PAGE_SIZE,
  })
  const logs = query.data?.items ?? []

  return (
    <section className="page-stack">
      <PageHeader
        description="Tra cứu ai đã thay đổi dữ liệu gì, vào thời điểm nào và giá trị trước/sau."
        eyebrow="Security & compliance"
        title="Nhật ký kiểm toán"
      />
      <div className="toolbar toolbar--four">
        <Input label="Loại đối tượng" placeholder="employee, leave_request..." value={objectType} onChange={(event) => { setObjectType(event.target.value); setPage(1) }} />
        <Select label="Hành động" value={action} onChange={(event) => { setAction(event.target.value as AuditAction | ''); setPage(1) }}>
          <option value="">Tất cả</option>
          {actions.map((item) => <option key={item} value={item}>{item}</option>)}
        </Select>
        <Input label="Từ ngày" type="date" value={createdFrom} onChange={(event) => { setCreatedFrom(event.target.value); setPage(1) }} />
        <Input label="Đến ngày" type="date" value={createdTo} onChange={(event) => { setCreatedTo(event.target.value); setPage(1) }} />
      </div>
      {query.isLoading ? <Loading /> : null}
      {query.isError ? <StatusMessage tone="error">{getApiErrorMessage(query.error, 'Không thể tải audit logs.')}</StatusMessage> : null}
      {!query.isLoading && !query.isError && logs.length === 0 ? <EmptyState title="Chưa có audit log phù hợp" /> : null}
      {logs.length > 0 ? (
        <>
          <Table>
            <thead><tr><th>Thời gian</th><th>Hành động</th><th>Đối tượng</th><th>Người thực hiện</th><th>Lý do</th><th>Chi tiết</th></tr></thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.log_id}>
                  <td>{formatDateTime(log.created_at)}</td>
                  <td><Badge tone={actionTone(log.action)}>{log.action}</Badge></td>
                  <td><strong>{log.object_type}</strong><div className="mono-cell">{log.object_id ?? '-'}</div></td>
                  <td className="mono-cell">{log.performed_by?.slice(0, 8) ?? 'system'}</td>
                  <td>{log.reason ?? '-'}</td>
                  <td><Button size="sm" variant="secondary" onClick={() => setSelected(log)}>Xem</Button></td>
                </tr>
              ))}
            </tbody>
          </Table>
          <Pagination currentPage={query.data?.page ?? page} isFetching={query.isFetching} onPageChange={setPage} pageSize={query.data?.page_size ?? PAGE_SIZE} total={query.data?.total ?? 0} />
        </>
      ) : null}
      {selected ? (
        <div className="modal-backdrop" role="presentation" onMouseDown={() => setSelected(null)}>
          <div className="modal modal--wide" role="dialog" aria-modal="true" onMouseDown={(event) => event.stopPropagation()}>
            <div className="panel__header"><h2>Chi tiết thay đổi</h2></div>
            <div className="detail-list">
              <div><span>Audit ID</span><strong className="mono-cell">{selected.log_id}</strong></div>
              <div><span>IP / User agent</span><strong>{selected.ip_address ?? '-'} · {selected.user_agent ?? '-'}</strong></div>
            </div>
            <div className="diff-grid">
              <div><h3>Giá trị cũ</h3><pre>{JSON.stringify(selected.old_value, null, 2) || 'Không có'}</pre></div>
              <div><h3>Giá trị mới</h3><pre>{JSON.stringify(selected.new_value, null, 2) || 'Không có'}</pre></div>
            </div>
            <Button variant="secondary" onClick={() => setSelected(null)}>Đóng</Button>
          </div>
        </div>
      ) : null}
    </section>
  )
}
