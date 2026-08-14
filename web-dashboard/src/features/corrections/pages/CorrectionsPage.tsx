import { useMemo, useState } from 'react'
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
import { Textarea } from '@/components/ui/Textarea'
import {
  useCorrectionLogs,
  useCorrectionRequests,
  useReviewCorrection,
} from '@/features/corrections/hooks/useCorrections'
import type {
  CorrectionRequest,
  CorrectionStatus,
} from '@/features/corrections/types/correction.types'
import { useEmployees } from '@/features/employees/hooks/useEmployees'
import { formatDateTime, getApiErrorMessage } from '@/lib/utils'

const PAGE_SIZE = 15
const statusLabels: Record<CorrectionStatus, string> = {
  approved: 'Đã duyệt',
  cancelled: 'Đã hủy',
  pending: 'Chờ duyệt',
  rejected: 'Từ chối',
}

const statusTones: Record<CorrectionStatus, 'green' | 'gray' | 'amber' | 'red'> = {
  approved: 'green',
  cancelled: 'gray',
  pending: 'amber',
  rejected: 'red',
}

function toLocalDateTime(value?: string | null) {
  if (!value) return ''
  const date = new Date(value)
  const offset = date.getTimezoneOffset() * 60_000
  return new Date(date.getTime() - offset).toISOString().slice(0, 16)
}

export function CorrectionsPage() {
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState<CorrectionStatus | ''>('pending')
  const [employeeId, setEmployeeId] = useState('')
  const [selected, setSelected] = useState<CorrectionRequest | null>(null)
  const [decision, setDecision] = useState<'approved' | 'rejected'>('approved')
  const [checkIn, setCheckIn] = useState('')
  const [checkOut, setCheckOut] = useState('')
  const [comment, setComment] = useState('')
  const [rejectionReason, setRejectionReason] = useState('')
  const employeesQuery = useEmployees({ page: 1, page_size: 200 })
  const requestsQuery = useCorrectionRequests({
    employee_id: employeeId || undefined,
    page,
    page_size: PAGE_SIZE,
    status: status || undefined,
  })
  const reviewMutation = useReviewCorrection()
  const logsQuery = useCorrectionLogs(selected?.request_id)
  const employeeNames = useMemo(
    () => new Map((employeesQuery.data?.items ?? []).map((item) => [item.employee_id, item.full_name])),
    [employeesQuery.data],
  )
  const requests = requestsQuery.data?.items ?? []

  const openReview = (request: CorrectionRequest) => {
    setSelected(request)
    setDecision('approved')
    setCheckIn(toLocalDateTime(request.requested_check_in))
    setCheckOut(toLocalDateTime(request.requested_check_out))
    setComment('')
    setRejectionReason('')
  }

  const submitReview = () => {
    if (!selected) return
    reviewMutation.mutate(
      {
        payload: {
          action: decision,
          approved_check_in: decision === 'approved' && checkIn ? new Date(checkIn).toISOString() : undefined,
          approved_check_out: decision === 'approved' && checkOut ? new Date(checkOut).toISOString() : undefined,
          comment: comment || undefined,
          rejection_reason: decision === 'rejected' ? rejectionReason : undefined,
        },
        requestId: selected.request_id,
      },
      { onSuccess: () => setSelected(null) },
    )
  }

  return (
    <section className="page-stack">
      <PageHeader
        description="Duyệt yêu cầu điều chỉnh giờ vào/ra, theo dõi lý do và lịch sử xử lý."
        eyebrow="Attendance operations"
        title="Điều chỉnh công"
      />
      <div className="toolbar toolbar--three">
        <Select
          label="Nhân viên"
          onChange={(event) => {
            setEmployeeId(event.target.value)
            setPage(1)
          }}
          value={employeeId}
        >
          <option value="">Tất cả nhân viên</option>
          {(employeesQuery.data?.items ?? []).map((employee) => (
            <option key={employee.employee_id} value={employee.employee_id}>
              {employee.full_name} ({employee.employee_code})
            </option>
          ))}
        </Select>
        <Select
          label="Trạng thái"
          onChange={(event) => {
            setStatus(event.target.value as CorrectionStatus | '')
            setPage(1)
          }}
          value={status}
        >
          <option value="">Tất cả</option>
          {Object.entries(statusLabels).map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </Select>
      </div>
      {requestsQuery.isLoading || employeesQuery.isLoading ? <Loading /> : null}
      {requestsQuery.isError || employeesQuery.isError ? (
        <StatusMessage tone="error">
          {getApiErrorMessage(requestsQuery.error || employeesQuery.error, 'Không thể tải yêu cầu sửa công.')}
        </StatusMessage>
      ) : null}
      {!requestsQuery.isLoading && !requestsQuery.isError && requests.length === 0 ? (
        <EmptyState title="Không có yêu cầu phù hợp" description="Thử chọn trạng thái hoặc nhân viên khác." />
      ) : null}
      {requests.length > 0 ? (
        <>
          <Table>
            <thead>
              <tr>
                <th>Nhân viên</th>
                <th>Giờ đề nghị</th>
                <th>Lý do</th>
                <th>Ngày gửi</th>
                <th>Trạng thái</th>
                <th>Thao tác</th>
              </tr>
            </thead>
            <tbody>
              {requests.map((request) => (
                <tr key={request.request_id}>
                  <td>
                    <strong>{employeeNames.get(request.employee_id) ?? 'Không xác định'}</strong>
                    <div className="mono-cell">{request.employee_id.slice(0, 8)}</div>
                  </td>
                  <td>
                    <div>Vào: {formatDateTime(request.requested_check_in)}</div>
                    <div>Ra: {formatDateTime(request.requested_check_out)}</div>
                  </td>
                  <td>{request.reason}</td>
                  <td>{formatDateTime(request.created_at)}</td>
                  <td><Badge tone={statusTones[request.status]}>{statusLabels[request.status]}</Badge></td>
                  <td>
                    <Button
                      onClick={() => openReview(request)}
                      size="sm"
                      variant={request.status === 'pending' ? 'primary' : 'secondary'}
                    >
                      {request.status === 'pending' ? 'Duyệt' : 'Chi tiết'}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
          <Pagination
            currentPage={requestsQuery.data?.page ?? page}
            isFetching={requestsQuery.isFetching}
            onPageChange={setPage}
            pageSize={requestsQuery.data?.page_size ?? PAGE_SIZE}
            total={requestsQuery.data?.total ?? 0}
          />
        </>
      ) : null}
      {selected ? (
        <div className="modal-backdrop" role="presentation" onMouseDown={() => setSelected(null)}>
          <div className="modal" role="dialog" aria-modal="true" onMouseDown={(event) => event.stopPropagation()}>
            <div className="panel__header">
              <h2>{selected.status === 'pending' ? 'Duyệt yêu cầu sửa công' : 'Chi tiết yêu cầu'}</h2>
            </div>
            <div className="detail-list">
              <div><span>Nhân viên</span><strong>{employeeNames.get(selected.employee_id) ?? selected.employee_id}</strong></div>
              <div><span>Lý do</span><strong>{selected.reason}</strong></div>
            </div>
            {selected.status === 'pending' ? (
              <div className="resource-form">
                <Select label="Quyết định" value={decision} onChange={(event) => setDecision(event.target.value as 'approved' | 'rejected')}>
                  <option value="approved">Phê duyệt</option>
                  <option value="rejected">Từ chối</option>
                </Select>
                {decision === 'approved' ? (
                  <>
                    <Input label="Giờ vào được duyệt" type="datetime-local" value={checkIn} onChange={(event) => setCheckIn(event.target.value)} />
                    <Input label="Giờ ra được duyệt" type="datetime-local" value={checkOut} onChange={(event) => setCheckOut(event.target.value)} />
                  </>
                ) : (
                  <Textarea label="Lý do từ chối" value={rejectionReason} onChange={(event) => setRejectionReason(event.target.value)} />
                )}
                <Textarea label="Ghi chú người duyệt" value={comment} onChange={(event) => setComment(event.target.value)} />
                {reviewMutation.isError ? (
                  <StatusMessage tone="error">{getApiErrorMessage(reviewMutation.error, 'Không thể xử lý yêu cầu.')}</StatusMessage>
                ) : null}
                <div className="action-row">
                  <Button
                    disabled={decision === 'approved' ? !checkIn && !checkOut : !rejectionReason.trim()}
                    isLoading={reviewMutation.isPending}
                    onClick={submitReview}
                    variant={decision === 'rejected' ? 'danger' : 'primary'}
                  >
                    Xác nhận
                  </Button>
                  <Button onClick={() => setSelected(null)} variant="secondary">Đóng</Button>
                </div>
              </div>
            ) : null}
            <div className="panel-divider" />
            <h3>Lịch sử xử lý</h3>
            {logsQuery.isLoading ? <Loading /> : null}
            {(logsQuery.data ?? []).length === 0 && !logsQuery.isLoading ? <p className="muted-text">Chưa có nhật ký xử lý.</p> : null}
            <div className="detail-list">
              {(logsQuery.data ?? []).map((log) => (
                <div key={log.log_id}>
                  <span>{formatDateTime(log.created_at)}</span>
                  <strong>{log.action} {log.comment ? `— ${log.comment}` : ''}</strong>
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : null}
    </section>
  )
}
