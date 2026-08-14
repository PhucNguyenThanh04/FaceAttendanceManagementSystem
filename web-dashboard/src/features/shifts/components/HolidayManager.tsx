import { useState } from 'react'
import { Button } from '@/components/ui/Button'
import { EmptyState } from '@/components/ui/EmptyState'
import { Input } from '@/components/ui/Input'
import { Loading } from '@/components/ui/Loading'
import { StatusMessage } from '@/components/ui/StatusMessage'
import { Table } from '@/components/ui/Table'
import { Textarea } from '@/components/ui/Textarea'
import { useCreateHoliday, useDeleteHoliday, useHolidays, useUpdateHoliday } from '@/features/shifts/hooks/useHolidays'
import type { Holiday } from '@/features/shifts/types/shift.types'
import { formatDate, getApiErrorMessage } from '@/lib/utils'

export function HolidayManager({ onClose }: { onClose: () => void }) {
  const [year, setYear] = useState(new Date().getFullYear())
  const [selected, setSelected] = useState<Holiday | null>(null)
  const [name, setName] = useState('')
  const [holidayDate, setHolidayDate] = useState('')
  const [description, setDescription] = useState('')
  const query = useHolidays(year)
  const createMutation = useCreateHoliday()
  const updateMutation = useUpdateHoliday()
  const deleteMutation = useDeleteHoliday()
  const mutation = selected ? updateMutation : createMutation
  const reset = () => { setSelected(null); setName(''); setHolidayDate(''); setDescription('') }
  const edit = (item: Holiday) => { setSelected(item); setName(item.name); setHolidayDate(item.holiday_date); setDescription(item.description ?? '') }
  const submit = () => {
    const payload = { description: description || null, holiday_date: holidayDate, name: name.trim() }
    if (selected) updateMutation.mutate({ holidayId: selected.holiday_id, payload }, { onSuccess: reset })
    else createMutation.mutate(payload, { onSuccess: reset })
  }
  const remove = (item: Holiday) => {
    if (window.confirm(`Xóa ngày lễ “${item.name}”?`)) deleteMutation.mutate(item.holiday_id, { onSuccess: () => selected?.holiday_id === item.holiday_id && reset() })
  }
  const error = mutation.error || deleteMutation.error

  return <div className="modal-backdrop" role="presentation" onMouseDown={onClose}><div className="modal modal--wide" role="dialog" aria-modal="true" aria-labelledby="holiday-title" onMouseDown={(e) => e.stopPropagation()}>
    <div className="panel__header"><div><p className="eyebrow">Lịch làm việc</p><h2 id="holiday-title">Ngày lễ</h2></div><Button variant="ghost" onClick={onClose}>Đóng</Button></div>
    <div className="split-editor">
      <div className="page-stack">
        <Input label="Năm" min={1900} max={9999} type="number" value={year} onChange={(e) => setYear(Number(e.target.value))} />
        {query.isLoading ? <Loading /> : null}
        {query.isError ? <StatusMessage tone="error">{getApiErrorMessage(query.error, 'Không thể tải ngày lễ.')}</StatusMessage> : null}
        {!query.isLoading && (query.data ?? []).length === 0 ? <EmptyState title="Chưa có ngày lễ" description={`Chưa cấu hình lịch nghỉ năm ${year}.`} /> : null}
        {(query.data ?? []).length > 0 ? <Table><thead><tr><th>Ngày</th><th>Tên ngày lễ</th><th>Thao tác</th></tr></thead><tbody>{(query.data ?? []).map((item) => <tr key={item.holiday_id}><td>{formatDate(item.holiday_date)}</td><td><strong>{item.name}</strong><div className="muted-text">{item.description ?? 'Không có mô tả'}</div></td><td><div className="table-actions"><Button size="sm" variant="secondary" onClick={() => edit(item)}>Sửa</Button><Button size="sm" variant="danger" onClick={() => remove(item)}>Xóa</Button></div></td></tr>)}</tbody></Table> : null}
      </div>
      <div className="form-card resource-form"><div><p className="eyebrow">{selected ? 'Chỉnh sửa' : 'Thêm mới'}</p><h3>{selected?.name ?? 'Ngày lễ mới'}</h3></div>
        <Input label="Tên ngày lễ" value={name} onChange={(e) => setName(e.target.value)} />
        <Input label="Ngày" type="date" value={holidayDate} onChange={(e) => setHolidayDate(e.target.value)} />
        <Textarea label="Mô tả" value={description} onChange={(e) => setDescription(e.target.value)} />
        {error ? <StatusMessage tone="error">{getApiErrorMessage(error, 'Không thể lưu ngày lễ.')}</StatusMessage> : null}
        <div className="action-row"><Button disabled={!name.trim() || !holidayDate} isLoading={mutation.isPending} onClick={submit}>{selected ? 'Lưu thay đổi' : 'Thêm ngày lễ'}</Button>{selected ? <Button variant="secondary" onClick={reset}>Hủy sửa</Button> : null}</div>
      </div>
    </div>
  </div></div>
}
