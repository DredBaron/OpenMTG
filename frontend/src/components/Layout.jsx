import { useState } from 'react'
import { Book, Layers, Search, BarChart2, UserCog, Settings, Star, Menu, LogOut, Eye } from 'lucide-react'
import { Outlet, NavLink } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { useIsMobile } from '../hooks/useIsMobile'

const BASE_NAV_LINKS = [
  { to: '/collection', icon: Book,     label: 'Collection' },
  { to: '/decks',      icon: Layers,   label: 'Decks' },
  { to: '/wishlist',   icon: Star,     label: 'Wishlist' },
  { to: '/stats',      icon: BarChart2,label: 'Stats' },
]
const SCANNER_LINK = { to: '/scanner', icon: Search, label: 'Card Search' }

const ADMIN_LINKS = [
  { to: '/admin',    icon: UserCog,  label: 'Admin' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

export default function Layout() {
  const { user, logout, showroomEnabled, scannerEnabled } = useAuth()
  const showroomLink = { to: `/showroom/edit/${user?.username?.toLowerCase()}`, icon: Eye, label: 'Showroom' }
  const isMobile = useIsMobile()
  const [menuOpen, setMenuOpen] = useState(false)

  const navLinks = scannerEnabled
    ? [...BASE_NAV_LINKS.slice(0, 3), SCANNER_LINK, ...BASE_NAV_LINKS.slice(3)]
    : BASE_NAV_LINKS
  const baseLinks = showroomEnabled ? [...navLinks, showroomLink] : navLinks
  const links = user?.is_admin ? [...baseLinks, ...ADMIN_LINKS] : baseLinks
  const close = () => setMenuOpen(false)

  if (isMobile) {
    return (
      <div className="app-shell mobile">
        <nav className="mobile-topbar">
          <span className="logo">OpenMTG</span>
          <button className="hamburger-btn" onClick={() => setMenuOpen(o => !o)}>
            <Menu size={22} />
          </button>
        </nav>

        {menuOpen && <>
          <div className="mobile-menu-backdrop" onClick={close} />
          <div className="mobile-menu">
            {links.map(({ to, icon: Icon, label }) => (
              <NavLink key={to} to={to}
                className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}
                onClick={close}>
                <Icon size={16} /> {label}
              </NavLink>
            ))}
            <div className="mobile-menu-divider" />
            <button className="logout-btn" onClick={() => { logout(); close() }}>
              <LogOut size={16} /> Logout
            </button>
          </div>
        </>}

        <main className="main-content">
          <Outlet />
        </main>
      </div>
    )
  }

  return (
    <div className="app-shell">
      <nav className="sidebar">
        <div className="sidebar-header">
          <span className="logo">{user?.username}</span>
        </div>
        <div className="nav-links">
          {links.map(({ to, icon: Icon, label }) => (
            <NavLink key={to} to={to}
              className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
              <Icon className="nav-icon" /> {label}
            </NavLink>
          ))}
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
