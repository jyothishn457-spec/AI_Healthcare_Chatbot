// Health Records - timeline-style Medical History and Prescriptions with
// add / edit / delete. All data is user-scoped on the server.
import React, { useEffect, useState } from 'react'
import api from '../api.js'
import EmptyState from '../components/EmptyState.jsx'
import Modal from '../components/Modal.jsx'
import Spinner from '../components/Spinner.jsx'
import { formatDate } from '../utils.js'

const EMPTY_HISTORY = { title: '', description: '', event_date: '' }
const EMPTY_RX = {
  medication: '', dosage: '', frequency: '', prescriber: '', start_date: '', notes: '', active: true,
}

const Records = () => {
  const [tab, setTab] = useState('history') // 'history' | 'prescriptions'
  const [history, setHistory] = useState([])
  const [prescriptions, setPrescriptions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [editing, setEditing] = useState(null) // form object when modal open
  const [editId, setEditId] = useState(null)

  const load = async () => {
    setLoading(true)
    try {
      const [h, p] = await Promise.all([
        api.get('/records/history'),
        api.get('/records/prescriptions'),
      ])
      setHistory(h.data.history)
      setPrescriptions(p.data.prescriptions)
      setError('')
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not load records.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const openAdd = () => {
    setEditId(null)
    setEditing(tab === 'history' ? { ...EMPTY_HISTORY, event_date: new Date().toISOString().slice(0, 10) } : { ...EMPTY_RX, start_date: new Date().toISOString().slice(0, 10) })
  }

  const openEdit = (item) => {
    setEditId(item.id)
    setEditing(tab === 'history'
      ? { title: item.title, description: item.description, event_date: item.event_date }
      : {
          medication: item.medication, dosage: item.dosage, frequency: item.frequency,
          prescriber: item.prescriber, start_date: item.start_date, notes: item.notes,
          active: !!item.active,
        })
  }

  const save = async (e) => {
    e.preventDefault()
    if (!editing) return
    const base = tab === 'history' ? '/records/history' : '/records/prescriptions'
    try {
      if (editId) {
        await api.patch(`${base}/${editId}`, editing)
      } else {
        await api.post(base, editing)
      }
      setEditing(null)
      setError('')
      load()
    } catch (err) {
      setError(err.response?.data?.detail || 'Save failed.')
    }
  }

  const remove = async (item) => {
    if (!window.confirm('Delete this record permanently?')) return
    const base = tab === 'history' ? '/records/history' : '/records/prescriptions'
    try {
      await api.delete(`${base}/${item.id}`)
      load()
    } catch (err) {
      setError(err.response?.data?.detail || 'Delete failed.')
    }
  }

  return (
    <main className="page">
      <header className="page-head">
        <div>
          <h1>Health Records</h1>
          <p className="muted">Your medical history and prescriptions.</p>
        </div>
        <button className="btn btn-primary" onClick={openAdd}>
          + Add {tab === 'history' ? 'entry' : 'prescription'}
        </button>
      </header>

      <div className="filter-bar">
        <button className={`chip${tab === 'history' ? ' chip-active' : ''}`} onClick={() => setTab('history')}>
          Medical History
        </button>
        <button className={`chip${tab === 'prescriptions' ? ' chip-active' : ''}`} onClick={() => setTab('prescriptions')}>
          Prescriptions
        </button>
      </div>

      {error && <div className="error">{error}</div>}
      {loading ? (
        <Spinner />
      ) : tab === 'history' ? (
        history.length === 0 ? (
          <div className="card">
            <EmptyState
              icon="📋"
              title="No medical history yet"
              hint="Add surgeries, diagnoses or notable events to build your timeline."
              action={<button className="btn btn-primary" onClick={openAdd}>Add entry</button>}
            />
          </div>
        ) : (
          <ul className="timeline">
            {history.map((h) => (
              <li key={h.id} className="timeline-item">
                <span className="timeline-dot" />
                <div className="card timeline-card">
                  <div className="timeline-top">
                    <span className="timeline-date">{formatDate(h.event_date)}</span>
                    <div className="appointment-actions">
                      <button className="btn btn-outline btn-sm" onClick={() => openEdit(h)}>Edit</button>
                      <button className="btn btn-danger btn-sm" onClick={() => remove(h)}>Delete</button>
                    </div>
                  </div>
                  <h3>{h.title}</h3>
                  {h.description && <p className="muted">{h.description}</p>}
                </div>
              </li>
            ))}
          </ul>
        )
      ) : prescriptions.length === 0 ? (
        <div className="card">
          <EmptyState
            icon="💊"
            title="No prescriptions yet"
            hint="Add your current medications to keep track of dosages."
            action={<button className="btn btn-primary" onClick={openAdd}>Add prescription</button>}
          />
        </div>
      ) : (
        <ul className="row-list">
          {prescriptions.map((p) => (
            <li key={p.id} className="card row-item">
              <span className={`status-dot ${p.active ? 'active' : ''}`} />
              <div className="row-main">
                <strong>{p.medication}</strong>
                <span className="muted">
                  {[p.dosage, p.frequency, p.prescriber && `by ${p.prescriber}`].filter(Boolean).join(' · ')}
                </span>
                {p.notes && <span className="muted">{p.notes}</span>}
              </div>
              <div className="row-side">
                <span className="muted">Since {formatDate(p.start_date)}</span>
                <div className="appointment-actions">
                  <button className="btn btn-outline btn-sm" onClick={() => openEdit(p)}>Edit</button>
                  <button className="btn btn-danger btn-sm" onClick={() => remove(p)}>Delete</button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}

      <Modal
        open={!!editing}
        title={editId ? `Edit ${tab === 'history' ? 'entry' : 'prescription'}` : `Add ${tab === 'history' ? 'entry' : 'prescription'}`}
        onClose={() => setEditing(null)}
      >
        <form onSubmit={save} className="auth-form">
          {tab === 'history' ? (
            <>
              <label>
                Title
                <input value={editing?.title || ''} onChange={(e) => setEditing({ ...editing, title: e.target.value })} required maxLength={200} />
              </label>
              <label>
                Date
                <input type="date" value={editing?.event_date || ''} onChange={(e) => setEditing({ ...editing, event_date: e.target.value })} required />
              </label>
              <label>
                Description
                <textarea rows="4" value={editing?.description || ''} onChange={(e) => setEditing({ ...editing, description: e.target.value })} maxLength={2000} />
              </label>
            </>
          ) : (
            <>
              <label>
                Medication
                <input value={editing?.medication || ''} onChange={(e) => setEditing({ ...editing, medication: e.target.value })} required maxLength={200} />
              </label>
              <div className="booking-grid">
                <label>
                  Dosage
                  <input value={editing?.dosage || ''} onChange={(e) => setEditing({ ...editing, dosage: e.target.value })} placeholder="e.g. 500mg" />
                </label>
                <label>
                  Frequency
                  <input value={editing?.frequency || ''} onChange={(e) => setEditing({ ...editing, frequency: e.target.value })} placeholder="e.g. twice daily" />
                </label>
              </div>
              <div className="booking-grid">
                <label>
                  Prescriber
                  <input value={editing?.prescriber || ''} onChange={(e) => setEditing({ ...editing, prescriber: e.target.value })} />
                </label>
                <label>
                  Start date
                  <input type="date" value={editing?.start_date || ''} onChange={(e) => setEditing({ ...editing, start_date: e.target.value })} required />
                </label>
              </div>
              <label>
                Notes
                <textarea rows="2" value={editing?.notes || ''} onChange={(e) => setEditing({ ...editing, notes: e.target.value })} maxLength={1000} />
              </label>
              <label className="check-inline">
                <input type="checkbox" checked={!!editing?.active} onChange={(e) => setEditing({ ...editing, active: e.target.checked })} />
                Currently active
              </label>
            </>
          )}
          <div className="form-actions">
            <button type="button" className="btn btn-outline" onClick={() => setEditing(null)}>
              Cancel
            </button>
            <button className="btn btn-primary">Save</button>
          </div>
        </form>
      </Modal>
    </main>
  )
}

export default Records
