import type { RoleName } from '@/types/common.types'

export const routeSegments = {
  employees: 'employees',
  departments: 'departments',
  positions: 'positions',
  shifts: 'work-shifts',
  faceProfiles: 'face-profiles',
  onboarding: 'employee-onboarding',
  attendance: 'attendance',
  leave: 'leave',
  corrections: 'corrections',
  auditLogs: 'audit-logs',
  notifications: 'notifications',
  settings: 'settings',
  forgotPassword: 'forgot-password',
} as const

export const routePaths = {
  login: '/login',
  forgotPassword: `/${routeSegments.forgotPassword}`,
  dashboard: '/',
  employees: `/${routeSegments.employees}`,
  departments: `/${routeSegments.departments}`,
  positions: `/${routeSegments.positions}`,
  shifts: `/${routeSegments.shifts}`,
  faceProfiles: `/${routeSegments.faceProfiles}`,
  onboarding: `/${routeSegments.onboarding}`,
  attendance: `/${routeSegments.attendance}`,
  leave: `/${routeSegments.leave}`,
  corrections: `/${routeSegments.corrections}`,
  auditLogs: `/${routeSegments.auditLogs}`,
  notifications: `/${routeSegments.notifications}`,
  settings: `/${routeSegments.settings}`,
} as const

export type NavigationItem = {
  label: string
  path: string
}

const adminNavigationItems: NavigationItem[] = [
  { label: 'Admin dashboard', path: routePaths.dashboard },
  { label: 'Nhân viên', path: routePaths.employees },
  { label: 'Đăng ký khuôn mặt', path: routePaths.onboarding },
  { label: 'Phòng ban', path: routePaths.departments },
  { label: 'Chức vụ', path: routePaths.positions },
  { label: 'Ca làm việc', path: routePaths.shifts },
  { label: 'Face profiles', path: routePaths.faceProfiles },
  { label: 'Chấm công', path: routePaths.attendance },
  { label: 'Sửa công', path: routePaths.corrections },
  { label: 'Nghỉ phép', path: routePaths.leave },
  { label: 'Audit logs', path: routePaths.auditLogs },
  { label: 'Thông báo', path: routePaths.notifications },
  { label: 'Cài đặt', path: routePaths.settings },
]

const hrNavigationItems: NavigationItem[] = [
  { label: 'HR dashboard', path: routePaths.dashboard },
  { label: 'Nhân viên', path: routePaths.employees },
  { label: 'Đăng ký khuôn mặt', path: routePaths.onboarding },
  { label: 'Phòng ban', path: routePaths.departments },
  { label: 'Chức vụ', path: routePaths.positions },
  { label: 'Ca làm việc', path: routePaths.shifts },
  { label: 'Face profiles', path: routePaths.faceProfiles },
  { label: 'Chấm công công ty', path: routePaths.attendance },
  { label: 'Duyệt sửa công', path: routePaths.corrections },
  { label: 'Đơn nghỉ phép', path: routePaths.leave },
  { label: 'Audit logs', path: routePaths.auditLogs },
  { label: 'Thông báo', path: routePaths.notifications },
]

const managerNavigationItems: NavigationItem[] = [
  { label: 'Manager dashboard', path: routePaths.dashboard },
  { label: 'Team của tôi', path: routePaths.employees },
  { label: 'Ca làm việc', path: routePaths.shifts },
  { label: 'Chấm công team', path: routePaths.attendance },
  { label: 'Duyệt nghỉ phép', path: routePaths.leave },
  { label: 'Xác nhận sửa công', path: routePaths.corrections },
  { label: 'Thông báo', path: routePaths.notifications },
]

export function getNavigationItemsForRole(role: RoleName | null | undefined): NavigationItem[] {
  if (role === 'admin') {
    return adminNavigationItems
  }

  if (role === 'hr') {
    return hrNavigationItems
  }

  if (role === 'manager') {
    return managerNavigationItems
  }

  return []
}
