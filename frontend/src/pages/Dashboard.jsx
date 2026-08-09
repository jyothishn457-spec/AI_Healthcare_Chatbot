// Dashboard - landing page with quick stats, CTAs and upcoming data previews.
import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api.js'
import StatCard from '../components/StatCard.jsx'
import EmptyState from '../components/EmptyState.jsx'
import Spinner from '../components/Spinner.jsx'
import { formatDate, formatTime, statusLabel } from '../utils.js'

const Dashboard = ({ user }) => {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState({ upcoming: 0, pending: 0, completed: 0, prescriptions: 0 })
  const [upcoming, setUpcoming] = useState([])
  const [prescriptions, setPrescriptions] = useState([])

  useEffect(() => {
    let active = true
    // Load the three data slices the dashboard previews in parallel.
    Promise.all([
      api.get('/appointments?upcoming=true'),
      api.get('/appointments'),
      api.get('/records/prescriptions?active=true'),
    ])
      .then(([up, all, rx]) => {
        if (!active) return
        setUpcoming(up.data.appointments)
        setPrescriptions(rx.data.prescriptions)
        setStats({
          upcoming: up.data.appointments.length,
          pending: all.data.appointments.filter((a) => a.status === 'pending').length,
          completed: all.data.appointments.filter((a) => a.status === 'completed').length,
          prescriptions: rx.data.prescriptions.length,
        })
      })
      .catch(() => { /* non-critical - the page still renders with zeros */ })
      .finally(() => active && setLoading(false))
    return () => { active = false }
  }, [])

  return (
    <main className="page">
      <header className="page-head">
        <div>
          <h1>Welcome back, {user?.full_name || user?.username} 👋</h1>
          <p className="muted">Here's your health at a glance.</p>
        </div>
      </header>

      {loading ? (
        <Spinner />
      ) : (
        <>
          <section className="stat-grid">
            <StatCard label="Upcoming" value={stats.upcoming} icon="🕒" accent="#0e7c86" onClick={() => navigate('/appointments')} />
            <StatCard label="Pending requests" value={stats.pending} icon="⏳" accent="#d97706" onClick={() => navigate('/appointments')} />
            <StatCard label="Completed" value={stats.completed} icon="✔" accent="#16a34a" onClick={() => navigate('/appointments')} />
            <StatCard label="Active prescriptions" value={stats.prescriptions} icon="💊" accent="#7c3aed" onClick={() => navigate('/records')} />
          </section>

          <section className="cta-row">
            <button className="btn btn-primary btn-lg" onClick={() => navigate('/chat')}>
              ✥ Ask the AI Doctor
            </button>
            <button className="btn btn-outline btn-lg" onClick={() => navigate('/predict')}>
              ◉ Predict Symptoms
            </button>
            <button className="btn btn-outline btn-lg" onClick={() => navigate('/book')}>
              ✚ Book Appointment
            </button>
          </section>

          <div className="dash-grid">
            <section className="card dash-panel">
              <div className="panel-head">
                <h3>Upcoming Appointments</h3>
                <button className="link-btn" onClick={() => navigate('/appointments')}>
                  View all →
                </button>
              </div>
              {upcoming.length === 0 ? (
                <EmptyState
                  icon="🕒"
                  title="No upcoming appointments"
                  hint="Book a consultation with one of our doctors."
                  action={
                    <button className="btn btn-primary btn-sm" onClick={() => navigate('/book')}>
                      Book Appointment
                    </button>
                  }
                />
              ) : (
                <ul className="row-list">
                  {upcoming.slice(0, 3).map((a) => (
                    <li key={a.id} className="row-item">
                      <span className={`status-dot ${a.status}`} />
                      <div className="row-main">
                        <strong>{a.doctor_name}</strong>
                        <span className="muted">{a.specialty}</span>
                      </div>
                      <span className="row-side">
                        {formatDate(a.date)} · {formatTime(a.time)}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section className="card dash-panel">
              <div className="panel-head">
                <h3>Recent Prescriptions</h3>
                <button className="link-btn" onClick={() => navigate('/records')}>
                  View all →
                </button>
              </div>
              {prescriptions.length === 0 ? (
                <EmptyState
                  icon="💊"
                  title="No active prescriptions"
                  hint="Your medication list will appear here."
                  action={
                    <button className="btn btn-outline btn-sm" onClick={() => navigate('/records')}>
                      Add Prescription
                    </button>
                  }
                />
              ) : (
                <ul className="row-list">
                  {prescriptions.slice(0, 3).map((p) => (
                    <li key={p.id} className="row-item">
                      <span className="status-dot active" />
                      <div className="row-main">
                        <strong>{p.medication}</strong>
                        <span className="muted">{p.dosage} · {p.frequency}</span>
                      </div>
                      <span className="row-side">{statusLabel('active')}</span>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        </>
      )}
    </main>
  )
}

export default Dashboard
