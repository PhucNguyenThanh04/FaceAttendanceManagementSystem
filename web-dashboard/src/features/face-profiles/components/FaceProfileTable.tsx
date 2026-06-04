import { Table } from '@/components/ui/Table'
import { FaceProfileStatusBadge } from '@/features/face-profiles/components/FaceProfileStatusBadge'
import type { FaceProfile } from '@/features/face-profiles/types/face-profile.types'
import { formatDateTime } from '@/lib/utils'

type FaceProfileTableProps = {
  profiles: FaceProfile[]
}

export function FaceProfileTable({ profiles }: FaceProfileTableProps) {
  return (
    <Table>
      <thead>
        <tr>
          <th>Profile ID</th>
          <th>Employee ID</th>
          <th>Collection</th>
          <th>Model</th>
          <th>Trạng thái</th>
          <th>Cập nhật</th>
        </tr>
      </thead>
      <tbody>
        {profiles.map((profile) => (
          <tr key={profile.profile_id}>
            <td className="mono-cell">{profile.profile_id.slice(0, 8)}</td>
            <td className="mono-cell">{profile.employee_id.slice(0, 8)}</td>
            <td>{profile.qdrant_collection}</td>
            <td>{profile.embedding_model ?? '-'}</td>
            <td>
              <FaceProfileStatusBadge status={profile.status} />
            </td>
            <td>{formatDateTime(profile.updated_at)}</td>
          </tr>
        ))}
      </tbody>
    </Table>
  )
}
