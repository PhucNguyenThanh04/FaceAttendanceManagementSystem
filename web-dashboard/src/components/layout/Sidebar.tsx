import { NavLink } from 'react-router-dom'
import { getNavigationItemsForRole } from '@/constants/routes'
import { useAuthStore } from '@/stores/auth.store'

export function Sidebar({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const role = useAuthStore((state) => state.user?.role_name)
  const navigationItems = getNavigationItemsForRole(role)

  return (
    <>
    {isOpen ? <button aria-label="Đóng điều hướng" className="sidebar-backdrop" onClick={onClose} type="button" /> : null}
    <aside className={isOpen ? 'sidebar sidebar--open' : 'sidebar'}>
      <div className="sidebar__brand">
        <span className="sidebar__brand-mark">FA</span>
        <span>
          <strong>Face Attendance</strong>
          <small>Management System</small>
        </span>
        <button aria-label="Đóng điều hướng" className="sidebar__close" onClick={onClose} type="button">×</button>
      </div>
      <nav className="sidebar__nav" aria-label="Điều hướng chính">
        {navigationItems.length > 0 ? (
          navigationItems.map((item) => (
            <NavLink
              className={({ isActive }) => (isActive ? 'sidebar__link sidebar__link--active' : 'sidebar__link')}
              end={item.path === '/'}
              key={item.path}
              onClick={onClose}
              to={item.path}
            >
              {item.label}
            </NavLink>
          ))
        ) : (
          <span className="sidebar__empty">Không có dashboard web</span>
        )}
      </nav>
    </aside>
    </>
  )
}
