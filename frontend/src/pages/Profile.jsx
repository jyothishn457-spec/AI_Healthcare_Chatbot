// Profile & Settings - edit profile, notification preferences, dark mode,
// change password, logout and account deletion.
import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api, { clearSession } from '../api.js'
import Modal from '../components/Modal.jsx'
import { formatDate } from '../utils.js'

const GENDERS = ['male', 'female', 'non-binary', 'prefer not to say']

const NOTIF_OPTIONS = [
  { key: 'appointment_reminders', label: 'Appointment reminders', desc: 'Get notified before your appointments.' },
  { key: 'prescription_updates', label: 'Prescription updates', desc: 'Alerts when prescriptions change or expire.' },
  { key: 'health_tips', label: 'Health tips', desc: 'Occasional preventive-care tips from our team.' },
  { key: 'email_summary', label: 'Email summary', desc: 'A monthly summary of your health activity.' },
]

const Profile = ({ user, dark, onToggleDark, onLogout, refreshUser }) => {
  const navigate = useNavigate()
  const [profile, setProfile] = useState(user || {})
  const [form, setForm] = useState({})
  const [prefs, setPrefs] = useState({})
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [showDelete, setShowDelete] = useState(false)
  const [deletePassword, setDeletePassword] = useState('')
  const [passwordForm, setPasswordForm] = useState({ current: '', next: '' })

  // Sync local form state whenever the profile arrives or changes.
  useEffect(() => {
    api.get('/profile').then(({ data }) => {
      setProfile(data.profile)
      setForm({
        full_name: data.profile.full_name || '',
        email: data.profile.email || '',
        phone: data.profile.phone || '',
        date_of_birth: data.profile.date_of_birth || '',
        gender: data.profile.gender || 'prefer not to say',
      })
      setPrefs(data.profile.notification_prefs || {})
    })
  }, [])

  const saveProfile = async (e) => {
    e.preventDefault()
    setSaving(true)
    setError('')
    setNotice('')
    try {
      const { data } = await api.patch('/profile', form)
      setProfile(data.profile)
      setNotice('Profile saved.')
      refreshUser?.(data.profile)
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not save profile.')
    } finally {
      setSaving(false)
    }
  }

  const savePrefs = async () => {
    setError('')
    setNotice('')
    try {
      const { data } = await api.patch('/profile', { notification_prefs: prefs })
      setPrefs(data.profile.notification_prefs)
      setNotice('Notification preferences saved.')
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not save preferences.')
    }
  }

  const changePassword = async (e) => {
    e.preventDefault()
    setError('')
    setNotice('')
    if (!passwordForm.next) return
    try {
      await api.patch('/profile', { password: passwordForm.next })
      setPasswordForm({ current: '', next: '' })
      setNotice('Password updated. Please sign in again.')
      // Other sessions are revoked; force a clean re-login.
      clearSession()
      navigate('/login', { replace: true })
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not change password.')
    }
  }

  const deleteAccount = async (e) => {
    e.preventDefault()
    setError('')
    try {
      await api.request({ method: 'DELETE', url: '/profile', data: { password: deletePassword } })
      clearSession()
      navigate('/login', { replace: true })
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not delete account.')
    }
  }

  const logout = async () => {
    // Best effort server-side revocation, then clear locally regardless.
    try {
      await api.post('/logout', { refresh_token: localStorage.getItem('refreshToken') })
    } catch (_) {
      /* ignore */
    }
    onLogout?.()
    navigate('/login', { replace: true })
  }

  return (
    <main className="page">
      <header className="page-head">
        <div>
          <h1>Profile & Settings</h1>
          <p className="muted">Manage your account and preferences.</p>
        </div>
        <button className="btn btn-danger" onClick={logout}>Logout</button>
      </header>

      {error && <div className="error">{error}</div>}
      {notice && <div className="notice">{notice}</div>}

      <div className="profile-grid">
        <form className="card profile-card" onSubmit={saveProfile}>
          <h3>Personal information</h3>
          <label>
            Full name
            <input value={form.full_name || ''} onChange={(e) => setForm({ ...form, full_name: e.target.value })} maxLength={120} />
          </label>
          <div className="booking-grid">
            <label>
              Email
              <input type="email" value={form.email || ''} onChange={(e) => setForm({ ...form, email: e.target.value })} />
            </label>
            <label>
              Phone
              <input value={form.phone || ''} onChange={(e) => setForm({ ...form, phone: e.target.value })} maxLength={30} />
            </label>
          </div>
          <div className="booking-grid">
            <label>
              Date of birth
              <input type="date" value={form.date_of_birth || ''} onChange={(e) => setForm({ ...form, date_of_birth: e.target.value })} />
            </label>
            <label>
              Gender
              <select value={form.gender || 'prefer not to say'} onChange={(e) => setForm({ ...form, gender: e.target.value })}>
                {GENDERS.map((g) => (
                  <option key={g} value={g}>{g}</option>
                ))}
              </select>
            </label>
          </div>
          <div className="form-actions">
            <button className="btn btn-primary" disabled={saving}>
              {saving ? 'Saving…' : 'Save profile'}
            </button>
          </div>
        </form>

        <div className="profile-side">
          <section className="card profile-card">
            <div className="panel-head">
              <h3>Appearance</h3>
            </div>
            <label className="setting-row">
              <div>
                <strong>Dark mode</strong>
                <span className="muted">Switch between light and dark theme.</span>
              </div>
              <button className="btn btn-outline btn-sm" onClick={onToggleDark}>
                {dark ? '☀ Light' : '🌙 Dark'}
              </button>
            </label>
          </section>

          <section className="card profile-card">
            <div className="panel-head">
              <h3>Notifications</h3>
              <button className="btn btn-outline btn-sm" onClick={savePrefs}>
                Save
              </button>
            </div>
            {NOTIF_OPTIONS.map((n) => (
              <label key={n.key} className="setting-row">
                <div>
                  <strong>{n.label}</strong>
                  <span className="muted">{n.desc}</span>
                </div>
                <input
                  type="checkbox"
                  className="toggle"
                  checked={!!prefs[n.key]}
                  onChange={(e) => setPrefs({ ...prefs, [n.key]: e.target.checked })}
                />
              </label>
            ))}
          </section>
        </div>
      </div>

      <div className="profile-grid">
        <form className="card profile-card" onSubmit={changePassword}>
          <h3>Change password</h3>
          <p className="muted">Changing your password signs out all other sessions.</p>
          <label>
            New password
            <input type="password" minLength={6} value={passwordForm.next} onChange={(e) => setPasswordForm({ ...passwordForm, next: e.target.value })} required />
          </label>
          <div className="form-actions">
            <button className="btn btn-outline">Update password</button>
          </div>
        </form>

        <section className="card profile-card danger-zone">
          <h3>Danger zone</h3>
          <p className="muted">Permanently delete your account and all medical data. This cannot be undone.</p>
          <button className="btn btn-danger" onClick={() => setShowDelete(true)}>
            Delete account
          </button>
        </section>
      </div>

      <Modal open={showDelete} title="Delete your account?" onClose={() => setShowDelete(false)}>
        <form onSubmit={deleteAccount} className="auth-form">
          <p className="muted">
            This will permanently remove your appointments, records, prescriptions and chat history.
          </p>
          <label>
            Enter your password to confirm
            <input type="password" value={deletePassword} onChange={(e) => setDeletePassword(e.target.value)} required />
          </label>
          <div className="form-actions">
            <button type="button" className="btn btn-outline" onClick={() => setShowDelete(false)}>
              Keep account
            </button>
            <button className="btn btn-danger">Delete permanently</button>
          </div>
        </form>
      </Modal>

      <p className="muted meta-line">Member since {formatDate((profile.created_at || '').slice(0, 10))}</p>
    </main>
  )
}

export default Profile
