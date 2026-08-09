// Book Appointment - doctor/specialty selection, date/time picker and a
// confirmation state after booking.
import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api.js'
import DisclaimerBanner from '../components/DisclaimerBanner.jsx'
import Spinner from '../components/Spinner.jsx'
import { formatDate, formatTime, todayISO } from '../utils.js'

const BookAppointment = () => {
  const navigate = useNavigate()
  const [doctors, setDoctors] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [doctor, setDoctor] = useState('')
  const [specialty, setSpecialty] = useState('')
  const [date, setDate] = useState('')
  const [time, setTime] = useState('09:00')
  const [notes, setNotes] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [booked, setBooked] = useState(null)

  useEffect(() => {
    api
      .get('/appointments/doctors')
      .then(({ data }) => {
        setDoctors(data.doctors || [])
        if (data.doctors?.length) {
          setDoctor(data.doctors[0].name)
          setSpecialty(data.doctors[0].specialty)
        }
      })
      .catch((err) => setError(err.response?.data?.detail || 'Could not load doctors.'))
      .finally(() => setLoading(false))
  }, [])

  const selectDoctor = (name) => {
    setDoctor(name)
    const d = doctors.find((x) => x.name === name)
    if (d) setSpecialty(d.specialty)
  }

  const submit = async (e) => {
    e.preventDefault()
    if (!doctor || !date || !time) return
    setSubmitting(true)
    setError('')
    try {
      const { data } = await api.post('/appointments', {
        doctor_name: doctor,
        specialty,
        date,
        time,
        notes,
      })
      setBooked(data.appointment)
    } catch (err) {
      setError(err.response?.data?.detail || 'Booking failed. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  if (booked) {
    return (
      <main className="page">
        <div className="card booking-confirmed">
          <div className="confirmed-icon">✓</div>
          <h1>Appointment requested</h1>
          <p className="muted">
            {booked.doctor_name} ({booked.specialty}) on {formatDate(booked.date)} at{' '}
            {formatTime(booked.time)}.
          </p>
          <p className="muted">
            Status: <strong>{booked.status}</strong>. Our team will confirm your booking shortly.
          </p>
          <div className="form-actions">
            <button className="btn btn-outline" onClick={() => navigate('/appointments')}>
              View appointments
            </button>
            <button className="btn btn-primary" onClick={() => { setBooked(null); setDate(''); setNotes('') }}>
              Book another
            </button>
          </div>
        </div>
      </main>
    )
  }

  return (
    <main className="page">
      <header className="page-head">
        <div>
          <h1>Book an Appointment</h1>
          <p className="muted">Choose a doctor, pick a slot and we'll confirm it.</p>
        </div>
      </header>

      <DisclaimerBanner />

      {loading ? (
        <Spinner />
      ) : (
        <form className="card booking-form" onSubmit={submit}>
          <label>
            Doctor / Specialty
            <select value={doctor} onChange={(e) => selectDoctor(e.target.value)} required>
              {doctors.map((d) => (
                <option key={d.name} value={d.name}>
                  {d.name} — {d.specialty}
                </option>
              ))}
            </select>
          </label>

          <div className="booking-grid">
            <label>
              Date
              <input type="date" min={todayISO()} value={date} onChange={(e) => setDate(e.target.value)} required />
            </label>
            <label>
              Time
              <input type="time" value={time} onChange={(e) => setTime(e.target.value)} required />
            </label>
          </div>

          <label>
            Notes (optional)
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows="3"
              maxLength={1000}
              placeholder="Anything the doctor should know ahead of time…"
            />
          </label>

          {error && <div className="error">{error}</div>}

          <div className="form-actions">
            <button type="button" className="btn btn-outline" onClick={() => navigate('/appointments')}>
              Back
            </button>
            <button className="btn btn-primary" disabled={submitting || !date}>
              {submitting ? 'Booking…' : 'Request Appointment'}
            </button>
          </div>
        </form>
      )}
    </main>
  )
}

export default BookAppointment
