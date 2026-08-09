// Sidebar - collapsible navigation shown on the left of the app shell.
// Collapses to an overlay drawer on mobile. Highlights the active route.
import React, { useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'

const LINKS = [
  { to: '/', label: 'Dashboard', icon: '◈', end: true },
  { to: '/chat', label: 'AI Doctor', icon: '✥' },
  { to: '/predict', label: 'Predict Symptoms', icon: '◉' },
  { to: '/appointments', label: 'Appointments', icon: '🕒' },
  { to: '/book', label: 'Book Appointment', icon: '✚' },
  { to: '/records', label: 'Health Records', icon: '☰' },
  { to: '/profile', label: 'Profile & Settings', icon: '⚙' },
]

export default function Sidebar({ user, dark, onToggleDark, onLogout, onNavigate }) {
  const [open, setOpen] = useState(false)
  const navigate = useNavigate()

  const close = () => {
    setOpen(false)
    onNavigate?.()
  }

  const go = (to) => {
    close()
    navigate(to)
  }

  return (
    <>
      {/* Mobile hamburger */}
      <button
        className="sidebar-toggle"
        onClick={() => setOpen((o) => !o)}
        aria-label="Toggle navigation menu"
      >
        {open ? '✕' : '☰'}
      </button>

      {open && <div className="sidebar-scrim" onClick={close} />}

      <aside className={`sidebar ${open ? 'open' : ''}`}>
        <div className="sidebar-brand" onClick={() => go('/')}>
          <span className="logo">+</span>
          <div>
            <span className="brand-name">HealthPilot AI</span>
            <span className="brand-sub">Medical assistant</span>
          </div>
        </div>

        <nav className="sidebar-nav">
          {LINKS.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.end}
              className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
              onClick={close}
            >
              <span className="sidebar-icon">{l.icon}</span>
              {l.label}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="sidebar-user">
            <span className="avatar" style={{ background: user?.avatar_color || '#0e7c86' }}>
              {(user?.full_name || user?.username || '?').slice(0, 1).toUpperCase()}
            </span>
            <div className="sidebar-user-info">
              <strong>{user?.full_name || user?.username}</strong>
              <span className="muted">{user?.is_admin ? 'Admin' : 'Patient'}</span>
            </div>
          </div>
          <button className="btn btn-outline btn-sm sidebar-actions" onClick={onToggleDark}>
            {dark ? '☀ Light Mode' : '🌙 Dark Mode'}
          </button>
          <button className="btn btn-danger btn-sm sidebar-actions" onClick={onLogout}>
            Logout
          </button>
        </div>
      </aside>
    </>
  )
}
