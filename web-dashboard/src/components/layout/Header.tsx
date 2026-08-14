import { useLocation, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/Button'
import { getNavigationItemsForRole, routePaths } from '@/constants/routes'
import { useLogout } from '@/features/auth/hooks/useLogout'
import { getInitials } from '@/lib/utils'
import { useAuthStore } from '@/stores/auth.store'

export function Header({ onMenuToggle }: { onMenuToggle: () => void }) {
  const navigate = useNavigate()
  const location = useLocation()
  const user = useAuthStore((state) => state.user)
  const logoutMutation = useLogout()
  const currentPage = getNavigationItemsForRole(user?.role_name).find((item) => item.path === location.pathname)

  const handleLogout = () => {
    logoutMutation.mutate(undefined, {
      onSettled: () => navigate(routePaths.login, { replace: true }),
    })
  }

  return (
    <header className="header">
      <div className="header__title">
        <button aria-label="Mở điều hướng" className="header__menu" onClick={onMenuToggle} type="button">☰</button>
        <div><p className="eyebrow">Face Attendance</p><h1>{currentPage?.label ?? 'Tổng quan'}</h1></div>
      </div>
      <div className="header__account">
        <div className="avatar" aria-hidden="true">
          {getInitials(user?.email)}
        </div>
        <div className="header__user">
          <strong>{user?.email ?? 'Đang xác thực'}</strong>
          <span>{user?.role_name === 'admin' ? 'Quản trị viên' : user?.role_name === 'hr' ? 'Nhân sự' : user?.role_name === 'manager' ? 'Quản lý' : 'Nhân viên'}</span>
        </div>
        <Button
          isLoading={logoutMutation.isPending}
          onClick={handleLogout}
          size="sm"
          variant="secondary"
        >
          Đăng xuất
        </Button>
      </div>
    </header>
  )
}
