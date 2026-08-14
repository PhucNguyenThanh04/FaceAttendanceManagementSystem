import { useState } from 'react'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Loading } from '@/components/ui/Loading'
import { StatusMessage } from '@/components/ui/StatusMessage'
import { Table } from '@/components/ui/Table'
import { Textarea } from '@/components/ui/Textarea'
import { useCreateLeaveType, useLeaveTypes, useUpdateLeaveType } from '@/features/leave/hooks/useLeave'
import type { LeaveType } from '@/features/leave/types/leave.types'
import { getApiErrorMessage } from '@/lib/utils'

const emptyForm = { code: '', description: '', is_active: true, is_paid: true, max_days_per_year: '', name: '' }

export function LeaveTypeManager({ onClose }: { onClose: () => void }) {
  const query = useLeaveTypes()
  const createMutation = useCreateLeaveType()
  const updateMutation = useUpdateLeaveType()
  const [selected, setSelected] = useState<LeaveType | null>(null)
  const [form, setForm] = useState(emptyForm)
  const mutation = selected ? updateMutation : createMutation
  const set = (key: keyof typeof form, value: string | boolean) => setForm((current) => ({ ...current, [key]: value }))
  const edit = (item: LeaveType) => {
    setSelected(item)
    setForm({
      code: item.code ?? '', description: item.description ?? '', is_active: item.is_active,
      is_paid: item.is_paid, max_days_per_year: item.max_days_per_year?.toString() ?? '', name: item.name,
    })
  }
  const reset = () => { setSelected(null); setForm(emptyForm) }
  const submit = () => {
    const payload = {
      code: form.code || null, description: form.description || null, is_active: form.is_active,
      is_paid: form.is_paid, max_days_per_year: form.max_days_per_year ? Number(form.max_days_per_year) : null,
      name: form.name.trim(),
    }
    if (selected) updateMutation.mutate({ id: selected.leave_type_id, payload }, { onSuccess: reset })
    else createMutation.mutate(payload, { onSuccess: reset })
  }

  return <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
    <div className="modal modal--wide" role="dialog" aria-modal="true" aria-labelledby="leave-type-title" onMouseDown={(event) => event.stopPropagation()}>
      <div className="panel__header"><div><p className="eyebrow">Chính sách nghỉ</p><h2 id="leave-type-title">Loại phép</h2></div><Button variant="ghost" onClick={onClose}>Đóng</Button></div>
      <div className="split-editor">
        <div className="page-stack">
          {query.isLoading ? <Loading /> : null}
          {query.isError ? <StatusMessage tone="error">{getApiErrorMessage(query.error, 'Không thể tải loại phép.')}</StatusMessage> : null}
          {(query.data ?? []).length > 0 ? <Table><thead><tr><th>Loại phép</th><th>Hạn mức</th><th>Trạng thái</th><th /></tr></thead><tbody>
            {(query.data ?? []).map((item) => <tr key={item.leave_type_id}><td><strong>{item.name}</strong><div className="mono-cell">{item.code ?? 'Không có mã'} · {item.is_paid ? 'Có lương' : 'Không lương'}</div></td><td>{item.max_days_per_year ?? 'Không giới hạn'}</td><td><Badge tone={item.is_active ? 'green' : 'gray'}>{item.is_active ? 'Áp dụng' : 'Tạm ngưng'}</Badge></td><td><Button size="sm" variant="secondary" onClick={() => edit(item)}>Sửa</Button></td></tr>)}
          </tbody></Table> : null}
        </div>
        <div className="form-card resource-form">
          <div><p className="eyebrow">{selected ? 'Chỉnh sửa' : 'Thêm mới'}</p><h3>{selected?.name ?? 'Loại phép mới'}</h3></div>
          <Input label="Tên loại phép" value={form.name} onChange={(e) => set('name', e.target.value)} />
          <Input label="Mã" value={form.code} onChange={(e) => set('code', e.target.value)} />
          <Input label="Số ngày tối đa/năm" min={0} type="number" value={form.max_days_per_year} onChange={(e) => set('max_days_per_year', e.target.value)} />
          <Textarea label="Mô tả" value={form.description} onChange={(e) => set('description', e.target.value)} />
          <label className="checkbox-field"><input checked={form.is_paid} type="checkbox" onChange={(e) => set('is_paid', e.target.checked)} /><span>Nghỉ có lương</span></label>
          <label className="checkbox-field"><input checked={form.is_active} type="checkbox" onChange={(e) => set('is_active', e.target.checked)} /><span>Đang áp dụng</span></label>
          {mutation.isError ? <StatusMessage tone="error">{getApiErrorMessage(mutation.error, 'Không thể lưu loại phép.')}</StatusMessage> : null}
          <div className="action-row"><Button disabled={!form.name.trim()} isLoading={mutation.isPending} onClick={submit}>{selected ? 'Lưu thay đổi' : 'Thêm loại phép'}</Button>{selected ? <Button variant="secondary" onClick={reset}>Hủy sửa</Button> : null}</div>
        </div>
      </div>
    </div>
  </div>
}
