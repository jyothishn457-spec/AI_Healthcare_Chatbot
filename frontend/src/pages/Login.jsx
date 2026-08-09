// Login / Register - auth page that stores access + refresh tokens.
import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api, { saveSession } from '../api.js'

const Login = () => {
  const navigate = useNavigate()
  const [mode, setMode] = useState('login') // 'login' | 'register'
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const url = mode === 'login' ? '/login' : '/register'
      const { data } = await api.post(url, { username, password })
      saveSession(data)
      navigate('/', { replace: true })
    } catch (err) {
      setError(err.response?.data?.detail || 'Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-head">
          <div className="logo large">+</div>
          <h1>HealthPilot AI</h1>
          <p>Your AI-powered medical assistant</p>
        </div>

        <form onSubmit={submit} className="auth-form">
          <label>
            Username
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              minLength={3}
              maxLength={50}
              autoFocus
            />
          </label>
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
              maxLength={128}
            />
          </label>
          {error && <div className="error">{error}</div>}
          <button className="btn btn-primary" disabled={loading}>
            {loading ? 'Please wait…' : mode === 'login' ? 'Sign In' : 'Create Account'}
          </button>
        </form>

        <button
          className="switch-mode"
          onClick={() => {
            setMode(mode === 'login' ? 'register' : 'login')
            setError('')
          }}
        >
          {mode === 'login'
            ? "Don't have an account? Register"
            : 'Already have an account? Sign in'}
        </button>

        <p className="disclaimer">Demo admin login: admin / admin123</p>
      </div>
    </div>
  )
}

export default Login
