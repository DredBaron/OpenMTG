import { Outlet, NavLink } from 'react-router-dom'
import { useAuth } from '../AuthContext'
import { Library, Layers, Search, BarChart2, ShieldCheck, Settings, LogOut } from 'lucide-react'

export default function Layout() {
  const { user, logout } = useAuth()

  return (
    <div className="app-shell">
      <nav className="sidebar">
        <div className="sidebar-header">
          <span className="logo">OpenMTG</span>
          <span className="username">{user?.username}</span>
        </div>
        <div className="nav-links">
          <NavLink to="/collection" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
            <Library size={18} /> Collection
          </NavLink>
          <NavLink to="/decks" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
            <Layers size={18} /> Decks
          </NavLink>
          <NavLink to="/scanner" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
            <Search size={18} /> Quick Add
          </NavLink>
          <NavLink to="/stats" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
            <BarChart2 size={18} /> Stats
          </NavLink>
          {user?.is_admin && (
            <NavLink to="/admin" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
              <ShieldCheck size={18} /> Admin
            </NavLink>
          )}
          {user?.is_admin && (
            <NavLink to="/settings" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
              <Settings size={18} /> Settings
            </NavLink>
          )}
        </div>
        <button className="logout-btn" onClick={logout}>
          <LogOut size={18} /> Logout
        </button>
      </nav>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  )
}
