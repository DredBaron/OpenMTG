import { Outlet, NavLink } from 'react-router-dom'
import { useAuth } from './hooks/useAuth'
import { useIsMobile } from '../hooks/useIsMobile'

export default function Layout() {
  const { user, logout } = useAuth()
  const isMobile = useIsMobile()

  return (
    <div className={isMobile ? 'app-shell mobile' : 'app-shell'}>
      <nav className="sidebar">
        <div className="sidebar-header">
          <span className="logo">{user?.username}</span>
        </div>
        <div className="nav-links">
          <NavLink to="/collection" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
            Collection
          </NavLink>
          <NavLink to="/decks" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
            Decks
          </NavLink>
          <NavLink to="/scanner" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
            Card Search
          </NavLink>
          <NavLink to="/stats" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
            Stats
          </NavLink>
          {user?.is_admin && (
            <NavLink to="/admin" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
              Admin
            </NavLink>
          )}
          {user?.is_admin && (
            <NavLink to="/settings" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
              Settings
            </NavLink>
          )}
        </div>
        <button className="logout-btn" onClick={logout}>
          Logout
        </button>
      </nav>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  )
}
