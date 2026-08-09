// App - application shell: auth state, dark mode, sidebar layout and routing.
// All non-auth routes are protected and rendered inside the sidebar shell.
import React, { useCallback, useEffect, useState } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { clearSession } from './api.js'
import Sidebar from './components/Sidebar.jsx'
import Login from './pages/Login.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Chat from './pages/Chat.jsx'
import Predict from './pages/Predict.jsx'
import Appointments from './pages/Appointments.jsx'
import BookAppointment from './pages/BookAppointment.jsx'
import Records from './pages/Records.jsx'
import Profile from './pages/Profile.jsx'

// Read the logged-in user from localStorage (kept in sync with api.js).
const readUser = () => {
  try {
    return JSON.parse(localStorage.getItem('user') || 'null')
  } catch {
    return null
  }
}

function ProtectedLayout({ user, dark, onToggleDark, onLogout, onUserUpdated, children }) {
  const location = useLocation()
  return (
    <div className="app-shell">
      <Sidebar
        user={user}
        dark={dark}
        onToggleDark={onToggleDark}
        onLogout={onLogout}
        onNavigate={() => {
          /* close mobile drawer when route changes */
        }}
      />
      <div className="app-content" key={location.pathname}>
        {children}
      </div>
    </div>
  )
}

export default function App() {
  const [user, setUser] = useState(readUser)

  // Dark mode: use the saved choice if present, otherwise fall back to the
  // operating system preference so first-time visitors get a consistent theme.
  const [dark, setDark] = useState(() => {
    const saved = localStorage.getItem('theme')
    if (saved === 'dark' || saved === 'light') return saved === 'dark'
    return window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false
  })

  // Toggle the .dark class on <html> so the CSS variables switch theme.
  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
    localStorage.setItem('theme', dark ? 'dark' : 'light')
  }, [dark])

  const refreshUser = useCallback((profile) => {
    const next = { ...readUser(), ...profile }
    localStorage.setItem('user', JSON.stringify(next))
    setUser(next)
  }, [])

  const handleLogout = () => {
    clearSession()
    setUser(null)
  }

  return (
    <Routes>
      <Route
        path="/login"
        element={user ? <Navigate to="/" replace /> : <Login />}
      />
      <Route
        path="/*"
        element={
          user ? (
            <ProtectedLayout user={user} dark={dark} onToggleDark={() => setDark((d) => !d)} onLogout={handleLogout} onUserUpdated={refreshUser}>
              <Routes>
                <Route path="/" element={<Dashboard user={user} />} />
                <Route path="/chat" element={<Chat user={user} />} />
                <Route path="/predict" element={<Predict />} />
                <Route path="/appointments" element={<Appointments />} />
                <Route path="/book" element={<BookAppointment />} />
                <Route path="/records" element={<Records />} />
                <Route
                  path="/profile"
                  element={<Profile user={user} dark={dark} onToggleDark={() => setDark((d) => !d)} onLogout={handleLogout} refreshUser={refreshUser} />}
                />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </ProtectedLayout>
          ) : (
            <Navigate to="/login" replace />
          )
        }
      />
    </Routes>
  )
}
