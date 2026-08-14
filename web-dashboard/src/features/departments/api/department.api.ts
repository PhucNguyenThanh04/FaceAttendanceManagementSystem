import { api } from '@/lib/axios'
import type { CreateDepartmentPayload, Department, UpdateDepartmentPayload } from '@/features/departments/types/department.types'

export const departmentApi = {
  listDepartments: async (search?: string): Promise<Department[]> => {
    const response = await api.get<Department[]>('/departments/', {
      params: { search: search || undefined },
    })
    return response.data
  },
  createDepartment: async (payload: CreateDepartmentPayload): Promise<Department> => {
    const response = await api.post<Department>('/departments/', payload)
    return response.data
  },
  updateDepartment: async (departmentId: number, payload: UpdateDepartmentPayload): Promise<Department> => {
    const response = await api.patch<Department>(`/departments/${departmentId}`, payload)
    return response.data
  },
  deactivateDepartment: async (departmentId: number): Promise<void> => {
    await api.post(`/departments/deactivate/${departmentId}`)
  },
  deleteDepartment: async (departmentId: number): Promise<void> => {
    await api.delete(`/departments/${departmentId}`)
  },
}
