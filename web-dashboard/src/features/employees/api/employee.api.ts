import { api } from '@/lib/axios'
import type {
  Employee,
  EmployeeListParams,
  EmployeeListResponse,
  EmployeeUpdatePayload,
} from '@/features/employees/types/employee.types'

export const employeeApi = {
  listEmployees: async (params: EmployeeListParams): Promise<EmployeeListResponse> => {
    const response = await api.get<EmployeeListResponse>('/employees/', { params })
    return response.data
  },
  getEmployeeById: async (employeeId: string): Promise<Employee> => {
    const response = await api.get<Employee>(`/employees/${employeeId}`)
    return response.data
  },
  getMyEmployeeProfile: async (): Promise<Employee> => {
    const response = await api.get<Employee>('/employees/me')
    return response.data
  },
  updateEmployee: async (employeeId: string, payload: EmployeeUpdatePayload): Promise<Employee> => {
    const response = await api.patch<Employee>(`/employees/${employeeId}`, payload)
    return response.data
  },
  activateEmployee: async (employeeId: string): Promise<Employee> => {
    const response = await api.post<Employee>(`/employees/activate/${employeeId}`)
    return response.data
  },
  deleteEmployee: async (employeeId: string): Promise<void> => {
    await api.delete(`/employees/${employeeId}`)
  },
}
