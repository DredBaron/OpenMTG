import { useState } from 'react'
import { Book, Layers, Search, BarChart2, UserCog, Settings, Star, Menu, LogOut, Eye, ArrowLeftRight } from 'lucide-react'
import { Outlet, NavLink } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '../hooks/useAuth'
import { useIsMobile } from '../hooks/useIsMobile'
import api from '../api'

const BASE_NAV_LINKS = [
  { to: '/collection', icon: Book,      label: 'Collection' },
  { to: '/decks',      icon: Layers,    label: 'Decks' },
  { to: '/wishlist',   icon: Star,      label: 'Wishlist' },
  { to: '/stats',      icon: BarChart2, label: 'Stats' },
]
const SCANNER_LINK = { to: '/card-search',  icon: Search,         label: 'Card Search' }
const TRADES_LINK  = { to: '/trades',       icon: ArrowLeftRight, label: 'Trades', pendingKey: true }

const ADMIN_LINKS = [
  { to: '/admin',    icon: UserCog,  label: 'Admin' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

function NavItem({ to, icon: Icon, label, hasPending, onClick }) {
  return (
    <NavLink to={to}
      className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}
      onClick={onClick}>
      <Icon className="nav-icon" />
      {label}
      {hasPending && <span className="nav-pending-badge">!</span>}
    </NavLink>
  )
}

export default function Layout() {
  const { user, logout, showroomEnabled, scannerEnabled, tradesEnabled } = useAuth()
  const showroomLink = { to: `/showroom/edit/${user?.username?.toLowerCase()}`, icon: Eye, label: 'Showroom' }
  const isMobile = useIsMobile()
  const [menuOpen, setMenuOpen] = useState(false)

  const { data: pendingData } = useQuery({
    queryKey: ['trades-pending'],
    queryFn: () => api.get('/trades/pending-count').then(r => r.data),
    refetchInterval: 30000,
    staleTime: 20000,
  })
  const hasPendingTrade = (pendingData?.count ?? 0) > 0

  const navLinks = scannerEnabled
    ? [...BASE_NAV_LINKS.slice(0, 3), SCANNER_LINK, ...BASE_NAV_LINKS.slice(3)]
    : BASE_NAV_LINKS
  const withTrades    = tradesEnabled  ? [...navLinks, TRADES_LINK]    : navLinks
  const baseLinks     = showroomEnabled ? [...withTrades, showroomLink] : withTrades
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
            {links.map(({ to, icon: Icon, label, pendingKey }) => (
              <NavItem key={to} to={to} icon={Icon} label={label}
                hasPending={pendingKey && hasPendingTrade}
                onClick={close} />
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
          {links.map(({ to, icon: Icon, label, pendingKey }) => (
            <NavItem key={to} to={to} icon={Icon} label={label}
              hasPending={pendingKey && hasPendingTrade} />
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
