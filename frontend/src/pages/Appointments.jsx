// Appointments - list of the user's appointments with status filters and
// cancel / reschedule actions.
import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api.js'
import EmptyState from '../components/EmptyState.jsx'
import Modal from '../components/Modal.jsx'
import Spinner from '../components/Spinner.jsx'
import { formatDate, formatTime, statusLabel, todayISO } from '../utils.js'

const FILTERS = ['all', 'upcoming', 'pending', 'confirmed', 'completed', 'cancelled']

const Appointments = () => {
  const navigate = useNavigate()
  const [appointments, setAppointments] = useState([])
  const [filter, setFilter] = useState('all')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [reschedule, setReschedule] = useState(null) // appointment being rescheduled
  const [newDate, setNewDate] = useState('')
  const [newTime, setNewTime] = useState('')

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const { data } = await api.get(`/appointments${filter === 'upcoming' ? '?upcoming=true' : ''}`)
      setAppointments(data.appointments)
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not load appointments.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter])

  const changeStatus = async (id, status) => {
    try {
      await api.patch(`/appointments/${id}`, { status })
      load()
    } catch (err) {
      setError(err.response?.data?.detail || 'Update failed.')
    }
  }

  const openReschedule = (appt) => {
    setReschedule(appt)
    setNewDate(appt.date)
    setNewTime(appt.time)
  }

  const saveReschedule = async (e) => {
    e.preventDefault()
    if (!newDate || !newTime) return
    try {
      await api.patch(`/appointments/${reschedule.id}`, { date: newDate, time: newTime })
      setReschedule(null)
      load()
    } catch (err) {
      setError(err.response?.data?.detail || 'Reschedule failed.')
    }
  }

  const cancel = async (appt) => {
    if (!window.confirm(`Cancel the appointment with ${appt.doctor_name}?`)) return
    await changeStatus(appt.id, 'cancelled')
  }

  return (
    <main className="page">
      <header className="page-head">
        <div>
          <h1>Appointments</h1>
          <p className="muted">Manage your consultations and follow-ups.</p>
        </div>
        <button className="btn btn-primary" onClick={() => navigate('/book')}>
          ✚ Book Appointment
        </button>
      </header>

      <div className="filter-bar">
        {FILTERS.map((f) => (
          <button
            key={f}
            className={`chip${filter === f ? ' chip-active' : ''}`}
            onClick={() => setFilter(f)}
          >
            {statusLabel(f)}
          </button>
        ))}
      </div>

      {error && <div className="error">{error}</div>}
      {loading ? (
        <Spinner />
      ) : appointments.length === 0 ? (
        <div className="card">
          <EmptyState
            icon="🕒"
            title={`No ${filter === 'all' ? '' : filter} appointments`}
            hint="Book a consultation to see it here."
            action={
              <button className="btn btn-primary" onClick={() => navigate('/book')}>
                Book Appointment
              </button>
            }
          />
        </div>
      ) : (
        <ul className="appointment-list">
          {appointments.map((a) => (
            <li key={a.id} className="card appointment-card">
              <div className="appointment-main">
                <span className={`status-badge ${a.status}`}>{statusLabel(a.status)}</span>
                <h3>{a.doctor_name}</h3>
                <p className="muted">{a.specialty}</p>
                <p className="appointment-when">
                  <strong>{formatDate(a.date)}</strong> at <strong>{formatTime(a.time)}</strong>
                </p>
                {a.notes && <p className="muted appointment-notes">{a.notes}</p>}
              </div>
              <div className="appointment-actions">
                {a.status !== 'cancelled' && a.status !== 'completed' && (
                  <>
                    <button className="btn btn-outline btn-sm" onClick={() => openReschedule(a)}>
                      Reschedule
                    </button>
                    <button className="btn btn-outline btn-sm" onClick={() => changeStatus(a.id, 'confirmed')}>
                      Confirm
                    </button>
                  </>
                )}
                {a.status !== 'cancelled' && a.status !== 'completed' && (
                  <button className="btn btn-danger btn-sm" onClick={() => cancel(a)}>
                    Cancel
                  </button>
                )}
                {a.status === 'confirmed' && (
                  <button className="btn btn-outline btn-sm" onClick={() => changeStatus(a.id, 'completed')}>
                    Mark completed
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}

      <Modal open={!!reschedule} title="Reschedule appointment" onClose={() => setReschedule(null)}>
        <form onSubmit={saveReschedule} className="auth-form">
          <label>
            Date
            <input type="date" min={todayISO()} value={newDate} onChange={(e) => setNewDate(e.target.value)} required />
          </label>
          <label>
            Time
            <input type="time" value={newTime} onChange={(e) => setNewTime(e.target.value)} required />
          </label>
          <div className="form-actions">
            <button type="button" className="btn btn-outline" onClick={() => setReschedule(null)}>
              Cancel
            </button>
            <button className="btn btn-primary">Save changes</button>
          </div>
        </form>
      </Modal>
    </main>
  )
}

export default Appointments
