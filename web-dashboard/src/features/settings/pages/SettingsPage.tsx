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
import {
  useAssignUserRole,
  useResetUserPassword,
  useUpdateUserStatus,
  useUsers,
} from '@/features/users/hooks/useUsers'
import type { UserAccount } from '@/features/users/types/user.types'
import { formatDateTime, getApiErrorMessage } from '@/lib/utils'
import { useAuthStore } from '@/stores/auth.store'
import type { RoleName, UserStatus } from '@/types/common.types'

const PAGE_SIZE = 15
const roleLabels: Record<RoleName, string> = { admin: 'Admin', employee: 'Employee', hr: 'HR', manager: 'Manager' }
const statusLabels: Record<UserStatus, string> = { active: 'Hoạt động', inactive: 'Tạm khóa', locked: 'Bị khóa' }

export function SettingsPage() {
  const currentRole = useAuthStore((state) => state.user?.role_name)
  const isAdmin = currentRole === 'admin'
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [role, setRole] = useState<RoleName | ''>('')
  const [status, setStatus] = useState<UserStatus | ''>('')
  const [selected, setSelected] = useState<UserAccount | null>(null)
  const [nextRole, setNextRole] = useState<RoleName>('employee')
  const [nextStatus, setNextStatus] = useState<UserStatus>('active')
  const [password, setPassword] = useState('')
  const query = useUsers({ page, page_size: PAGE_SIZE, role: role || undefined, search: search || undefined, status: status || undefined })
  const roleMutation = useAssignUserRole()
  const statusMutation = useUpdateUserStatus()
  const passwordMutation = useResetUserPassword()
  const users = query.data?.items ?? []
  const mutationError = roleMutation.error || statusMutation.error || passwordMutation.error

  const openAccount = (user: UserAccount) => {
    setSelected(user)
    setNextRole(user.role_name)
    setNextStatus(user.status)
    setPassword('')
  }

  return (
    <section className="page-stack">
      <PageHeader
        description="Tra cứu tài khoản đăng nhập; admin có thể đổi vai trò, trạng thái và đặt lại mật khẩu."
        eyebrow="Access control"
        title="Tài khoản & phân quyền"
      />
      <div className="toolbar toolbar--three">
        <Input label="Tìm kiếm email" value={search} onChange={(event) => { setSearch(event.target.value); setPage(1) }} />
        <Select label="Vai trò" value={role} onChange={(event) => { setRole(event.target.value as RoleName | ''); setPage(1) }}>
          <option value="">Tất cả</option>
          {Object.entries(roleLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </Select>
        <Select label="Trạng thái" value={status} onChange={(event) => { setStatus(event.target.value as UserStatus | ''); setPage(1) }}>
          <option value="">Tất cả</option>
          {Object.entries(statusLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </Select>
      </div>
      {!isAdmin ? <StatusMessage>HR có quyền tra cứu tài khoản. Các thay đổi vai trò, trạng thái và mật khẩu chỉ dành cho admin.</StatusMessage> : null}
      {query.isLoading ? <Loading /> : null}
      {query.isError ? <StatusMessage tone="error">{getApiErrorMessage(query.error, 'Không thể tải tài khoản.')}</StatusMessage> : null}
      {!query.isLoading && !query.isError && users.length === 0 ? <EmptyState title="Không có tài khoản phù hợp" /> : null}
      {users.length > 0 ? (
        <>
          <Table>
            <thead><tr><th>Email</th><th>Vai trò</th><th>Trạng thái</th><th>Đăng nhập gần nhất</th><th>Ngày tạo</th><th>Thao tác</th></tr></thead>
            <tbody>{users.map((user) => (
              <tr key={user.user_id}>
                <td><strong>{user.email}</strong><div className="mono-cell">{user.user_id.slice(0, 8)}</div></td>
                <td><Badge tone={user.role_name === 'admin' ? 'red' : user.role_name === 'hr' ? 'teal' : 'blue'}>{roleLabels[user.role_name]}</Badge></td>
                <td><Badge tone={user.status === 'active' ? 'green' : user.status === 'locked' ? 'red' : 'gray'}>{statusLabels[user.status]}</Badge></td>
                <td>{formatDateTime(user.last_login_at)}</td>
                <td>{formatDateTime(user.created_at)}</td>
                <td><Button size="sm" variant="secondary" onClick={() => openAccount(user)}>{isAdmin ? 'Quản lý' : 'Chi tiết'}</Button></td>
              </tr>
            ))}</tbody>
          </Table>
          <Pagination currentPage={query.data?.page ?? page} isFetching={query.isFetching} onPageChange={setPage} pageSize={query.data?.page_size ?? PAGE_SIZE} total={query.data?.total ?? 0} />
        </>
      ) : null}
      {selected ? (
        <div className="modal-backdrop" role="presentation" onMouseDown={() => setSelected(null)}>
          <div className="modal" role="dialog" aria-modal="true" onMouseDown={(event) => event.stopPropagation()}>
            <div className="panel__header"><h2>{selected.email}</h2></div>
            <div className="detail-list"><div><span>User ID</span><strong className="mono-cell">{selected.user_id}</strong></div></div>
            {isAdmin ? (
              <div className="resource-form">
                <Select label="Vai trò" value={nextRole} onChange={(event) => setNextRole(event.target.value as RoleName)}>
                  {Object.entries(roleLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                </Select>
                <Button isLoading={roleMutation.isPending} disabled={nextRole === selected.role_name} onClick={() => roleMutation.mutate({ role: nextRole, userId: selected.user_id }, { onSuccess: (user) => setSelected(user as UserAccount) })}>Cập nhật vai trò</Button>
                <div className="panel-divider" />
                <Select label="Trạng thái" value={nextStatus} onChange={(event) => setNextStatus(event.target.value as UserStatus)}>
                  {Object.entries(statusLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                </Select>
                <Button isLoading={statusMutation.isPending} disabled={nextStatus === selected.status} onClick={() => statusMutation.mutate({ status: nextStatus, userId: selected.user_id }, { onSuccess: (user) => setSelected(user as UserAccount) })}>Cập nhật trạng thái</Button>
                <div className="panel-divider" />
                <Input label="Mật khẩu mới" type="password" minLength={8} value={password} onChange={(event) => setPassword(event.target.value)} />
                <Button variant="danger" isLoading={passwordMutation.isPending} disabled={password.length < 8 || !/[A-Za-z]/.test(password) || !/\d/.test(password)} onClick={() => passwordMutation.mutate({ password, userId: selected.user_id }, { onSuccess: () => setPassword('') })}>Đặt lại mật khẩu</Button>
                {mutationError ? <StatusMessage tone="error">{getApiErrorMessage(mutationError, 'Không thể cập nhật tài khoản.')}</StatusMessage> : null}
              </div>
            ) : null}
            <div className="action-row"><Button variant="secondary" onClick={() => setSelected(null)}>Đóng</Button></div>
          </div>
        </div>
      ) : null}
    </section>
  )
}
