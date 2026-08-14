import { useState } from 'react'
import { PageHeader } from '@/components/layout/PageHeader'
import { EmptyState } from '@/components/ui/EmptyState'
import { Input } from '@/components/ui/Input'
import { Loading } from '@/components/ui/Loading'
import { StatusMessage } from '@/components/ui/StatusMessage'
import { PositionForm } from '@/features/positions/components/PositionForm'
import { PositionTable } from '@/features/positions/components/PositionTable'
import { usePositions } from '@/features/positions/hooks/usePositions'
import { getApiErrorMessage } from '@/lib/utils'
import { useAuthStore } from '@/stores/auth.store'
import type { Position } from '@/features/positions/types/position.types'
import { useDeactivatePosition, useDeletePosition } from '@/features/positions/hooks/useCreatePosition'

export function PositionListPage() {
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState<Position | null>(null)
  const isAdmin = useAuthStore((state) => state.user?.role_name === 'admin')
  const positionsQuery = usePositions(search)
  const positions = positionsQuery.data ?? []
  const deactivateMutation = useDeactivatePosition()
  const deleteMutation = useDeletePosition()
  const mutationError = deactivateMutation.error || deleteMutation.error

  const deactivate = (position: Position) => {
    if (window.confirm(`Tạm ngưng chức vụ “${position.name}”?`)) deactivateMutation.mutate(position.position_id)
  }
  const remove = (position: Position) => {
    if (window.confirm(`Xóa vĩnh viễn chức vụ “${position.name}”? Chỉ thực hiện được khi không còn dữ liệu liên quan.`)) {
      deleteMutation.mutate(position.position_id, { onSuccess: () => selected?.position_id === position.position_id && setSelected(null) })
    }
  }

  return (
    <section className="page-grid">
      <div className="page-stack">
        <PageHeader
          description="Danh mục chức vụ từ /positions."
          eyebrow="Staff"
          title="Chức vụ"
        />
        <Input
          label="Tìm kiếm"
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Tên hoặc mã chức vụ"
          value={search}
        />
        {positionsQuery.isLoading ? <Loading /> : null}
        {positionsQuery.isError ? (
          <StatusMessage tone="error">
            {getApiErrorMessage(positionsQuery.error, 'Không thể tải danh sách chức vụ.')}
          </StatusMessage>
        ) : null}
        {mutationError ? <StatusMessage tone="error">{getApiErrorMessage(mutationError, 'Không thể cập nhật chức vụ.')}</StatusMessage> : null}
        {!positionsQuery.isLoading && !positionsQuery.isError && positions.length === 0 ? (
          <EmptyState title="Chưa có chức vụ" />
        ) : null}
        {positions.length > 0 ? <PositionTable canManage={isAdmin} isMutating={deactivateMutation.isPending || deleteMutation.isPending} onDeactivate={deactivate} onDelete={remove} onEdit={setSelected} positions={positions} /> : null}
      </div>
      <aside className="side-panel">
        <h2>{selected ? 'Cập nhật chức vụ' : 'Tạo chức vụ'}</h2>
        {isAdmin ? <PositionForm onCancel={() => setSelected(null)} onSaved={() => setSelected(null)} position={selected} /> : <StatusMessage>HR có quyền tra cứu. Chỉ admin được thay đổi danh mục chức vụ.</StatusMessage>}
      </aside>
    </section>
  )
}
