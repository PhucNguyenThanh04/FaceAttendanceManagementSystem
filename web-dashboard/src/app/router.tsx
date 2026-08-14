import { Navigate, createBrowserRouter } from 'react-router-dom'
import { Suspense, type ReactElement } from 'react'
import { AppLayout } from '@/components/layout/AppLayout'
import { ProtectedRoute } from '@/components/layout/ProtectedRoute'
import { RoleRoute } from '@/components/layout/RoleRoute'
import { routePaths, routeSegments } from '@/constants/routes'
import { ForgotPasswordPage } from '@/features/auth/pages/ForgotPasswordPage'
import { LoginPage } from '@/features/auth/pages/LoginPage'
import { Loading } from '@/components/ui/Loading'
import type { RoleName } from '@/types/common.types'
import {
  AttendancePage, AuditLogsPage, ChatboxPage, CorrectionsPage, DashboardPage,
  DepartmentListPage, DocumentManagementPage, EmployeeListPage, EmployeeOnboardingPage,
  FaceProfileListPage, LeavePage, PositionListPage, ReportsPage, SettingsPage, ShiftManagementPage,
} from '@/app/lazy-pages'

const loadPage = (element: ReactElement) => <Suspense fallback={<Loading label="Đang mở trang" />}>{element}</Suspense>

const withRoles = (allowedRoles: RoleName[], element: ReactElement) => (
  <RoleRoute allowedRoles={allowedRoles}>{element}</RoleRoute>
)

const adminOnly: RoleName[] = ['admin']
const adminHr: RoleName[] = ['admin', 'hr']
const staffDashboard: RoleName[] = ['admin', 'hr', 'manager']

export const router = createBrowserRouter([
  {
    path: routePaths.login,
    element: <LoginPage />,
  },
  {
    path: routePaths.forgotPassword,
    element: <ForgotPasswordPage />,
  },
  {
    element: <ProtectedRoute />,
    children: [
      {
        path: routePaths.dashboard,
        element: <AppLayout />,
        children: [
          { index: true, element: loadPage(<DashboardPage />) },
          { path: routeSegments.employees, element: withRoles(staffDashboard, loadPage(<EmployeeListPage />)) },
          { path: routeSegments.departments, element: withRoles(adminHr, loadPage(<DepartmentListPage />)) },
          { path: routeSegments.positions, element: withRoles(adminHr, loadPage(<PositionListPage />)) },
          { path: routeSegments.shifts, element: withRoles(staffDashboard, loadPage(<ShiftManagementPage />)) },
          { path: routeSegments.faceProfiles, element: withRoles(adminHr, loadPage(<FaceProfileListPage />)) },
          { path: routeSegments.onboarding, element: withRoles(adminHr, loadPage(<EmployeeOnboardingPage />)) },
          { path: routeSegments.attendance, element: withRoles(staffDashboard, loadPage(<AttendancePage />)) },
          { path: routeSegments.reports, element: withRoles(staffDashboard, loadPage(<ReportsPage />)) },
          { path: routeSegments.leave, element: withRoles(staffDashboard, loadPage(<LeavePage />)) },
          { path: routeSegments.corrections, element: withRoles(staffDashboard, loadPage(<CorrectionsPage />)) },
          { path: routeSegments.auditLogs, element: withRoles(adminOnly, loadPage(<AuditLogsPage />)) },
          { path: routeSegments.documents, element: withRoles(adminOnly, loadPage(<DocumentManagementPage />)) },
          { path: routeSegments.chatbox, element: withRoles(staffDashboard, loadPage(<ChatboxPage />)) },
          { path: routeSegments.settings, element: withRoles(adminHr, loadPage(<SettingsPage />)) },
        ],
      },
    ],
  },
  {
    path: '*',
    element: <Navigate to={routePaths.dashboard} replace />,
  },
])
