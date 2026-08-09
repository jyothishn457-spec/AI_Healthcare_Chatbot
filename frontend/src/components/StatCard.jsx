// StatCard - compact KPI card used on the dashboard (upcoming, pending,
// completed appointments, active prescriptions, etc.)
import React from 'react'

export default function StatCard({ label, value, icon, accent, onClick }) {
  return (
    <button
      className={`stat-card${onClick ? ' clickable' : ''}`}
      style={{ '--accent': accent || 'var(--primary)' }}
      onClick={onClick}
    >
      <div className="stat-icon">{icon || '•'}</div>
      <div className="stat-body">
        <span className="stat-value">{value}</span>
        <span className="stat-label">{label}</span>
      </div>
    </button>
  )
}
