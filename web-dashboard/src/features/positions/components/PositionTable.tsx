import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Table } from '@/components/ui/Table'
import type { Position } from '@/features/positions/types/position.types'
import { formatDateTime } from '@/lib/utils'

type PositionTableProps = {
  canManage?: boolean
  isMutating?: boolean
  onDeactivate?: (position: Position) => void
  onDelete?: (position: Position) => void
  onEdit?: (position: Position) => void
  positions: Position[]
}

export function PositionTable({ canManage, isMutating, onDeactivate, onDelete, onEdit, positions }: PositionTableProps) {
  return (
    <Table>
      <thead>
        <tr>
          <th>Tên chức vụ</th>
          <th>Mã</th>
          <th>Mô tả</th>
          <th>Trạng thái</th>
          <th>Cập nhật</th>
          {canManage ? <th>Thao tác</th> : null}
        </tr>
      </thead>
      <tbody>
        {positions.map((position) => (
          <tr key={position.position_id}>
            <td>
              <strong>{position.name}</strong>
            </td>
            <td>{position.code ?? '-'}</td>
            <td>{position.description ?? '-'}</td>
            <td>
              <Badge tone={position.is_active ? 'green' : 'gray'}>
                {position.is_active ? 'Hoạt động' : 'Tạm ngưng'}
              </Badge>
            </td>
            <td>{formatDateTime(position.updated_at)}</td>
            {canManage ? <td><div className="table-actions">
              <Button size="sm" variant="secondary" onClick={() => onEdit?.(position)}>Sửa</Button>
              {position.is_active ? <Button disabled={isMutating} size="sm" variant="ghost" onClick={() => onDeactivate?.(position)}>Tạm ngưng</Button> : null}
              <Button disabled={isMutating} size="sm" variant="danger" onClick={() => onDelete?.(position)}>Xóa</Button>
            </div></td> : null}
          </tr>
        ))}
      </tbody>
    </Table>
  )
}
