import React, { useEffect, useState } from 'react'
import { Link, Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import Login from './Login.jsx'
import Dashboard from './Dashboard.jsx'
import Chat from './Chat.jsx'

function Navbar({ user, dark, onToggleDark, onLogout }) {
  const navigate = useNavigate()
  return (
    <header className="navbar">
      <div className="navbar-brand" onClick={() => navigate(user ? '/' : '/login')}>
        <span className="logo">+</span>
        <span>MediCare AI</span>
      </div>
      {user && (
        <nav className="navbar-actions">
          <Link className="nav-link" to="/">Home</Link>
          <Link className="nav-link" to="/chat">Chat</Link>
          <button className="btn btn-outline btn-sm" onClick={onToggleDark} title="Toggle dark mode">
            {dark ? 'Light Mode' : 'Dark Mode'}
          </button>
          <button className="btn btn-danger btn-sm" onClick={onLogout}>Logout</button>
        </nav>
      )}
    </header>
  )
}

export default function App() {
  const [user, setUser] = useState(() => JSON.parse(localStorage.getItem('user') || 'null'))
  const [dark, setDark] = useState(() => localStorage.getItem('theme') === 'dark')

  // Toggle the .dark class on <html> so the CSS variables switch theme.
  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
    localStorage.setItem('theme', dark ? 'dark' : 'light')
  }, [dark])

  const handleLogin = (userData, token) => {
    localStorage.setItem('token', token)
    localStorage.setItem('user', JSON.stringify(userData))
    setUser(userData)
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    setUser(null)
  }

  return (
    <div className="app">
      <Navbar
        user={user}
        dark={dark}
        onToggleDark={() => setDark((d) => !d)}
        onLogout={handleLogout}
      />
      <Routes>
        <Route
          path="/login"
          element={user ? <Navigate to="/" replace /> : <Login onLogin={handleLogin} />}
        />
        <Route
          path="/"
          element={user ? <Dashboard user={user} /> : <Navigate to="/login" replace />}
        />
        <Route
          path="/chat"
          element={user ? <Chat user={user} /> : <Navigate to="/login" replace />}
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  )
}
