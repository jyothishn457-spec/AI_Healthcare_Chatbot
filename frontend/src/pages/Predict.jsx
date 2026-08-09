// Disease Prediction - structured symptom checklist intake with ranked
// possible conditions, confidence labels, next-step guidance and a persistent
// "informational, not diagnostic" disclaimer.
import React, { useEffect, useMemo, useState } from 'react'
import api from '../api.js'
import DisclaimerBanner from '../components/DisclaimerBanner.jsx'
import EmptyState from '../components/EmptyState.jsx'
import Spinner from '../components/Spinner.jsx'
import { confidenceClass, formatDateTime } from '../utils.js'

const AGE_GROUPS = [
  { value: 'child', label: 'Child (under 12)' },
  { value: 'teen', label: 'Teen (13–19)' },
  { value: 'adult', label: 'Adult (20–64)' },
  { value: 'senior', label: 'Senior (65+)' },
]

const SEXES = [
  { value: 'male', label: 'Male' },
  { value: 'female', label: 'Female' },
  { value: 'other', label: 'Other' },
  { value: 'prefer not to say', label: 'Prefer not to say' },
]

const DURATIONS = [
  { value: 'less_than_24h', label: 'Less than 24 hours' },
  { value: '1_3_days', label: '1–3 days' },
  { value: '3_7_days', label: '3–7 days' },
  { value: 'over_week', label: 'More than a week' },
]

const Predict = () => {
  const [symptomOptions, setSymptomOptions] = useState([])
  const [selected, setSelected] = useState([])
  const [ageGroup, setAgeGroup] = useState('adult')
  const [sex, setSex] = useState('prefer not to say')
  const [duration, setDuration] = useState('1_3_days')
  const [result, setResult] = useState(null)
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // Group symptom options by category for a readable checklist.
  const groups = useMemo(() => {
    const map = {}
    symptomOptions.forEach((s) => {
      if (!map[s.group]) map[s.group] = []
      map[s.group].push(s)
    })
    return map
  }, [symptomOptions])

  const toggle = (id) => {
    setSelected((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))
  }

  useEffect(() => {
    // Load the checklist catalogue and past predictions in parallel.
    api.get('/predict/symptoms').then(({ data }) => setSymptomOptions(data.symptoms || []))
    api.get('/predict/history').then(({ data }) => setHistory(data.predictions || []))
  }, [])

  const submit = async (e) => {
    e.preventDefault()
    if (selected.length === 0) {
      setError('Please select at least one symptom.')
      return
    }
    setError('')
    setLoading(true)
    try {
      const { data } = await api.post('/predict', {
        symptoms: selected,
        age_group: ageGroup,
        sex,
        duration,
      })
      setResult(data)
      setHistory((prev) => [data, ...prev])
    } catch (err) {
      setError(err.response?.data?.detail || 'Prediction failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const reset = () => {
    setSelected([])
    setResult(null)
    setError('')
  }

  return (
    <main className="page">
      <header className="page-head">
        <div>
          <h1>Symptom Prediction</h1>
          <p className="muted">Select your symptoms for a ranked list of possible conditions.</p>
        </div>
      </header>

      <DisclaimerBanner />

      <form className="predict-form" onSubmit={submit}>
        <div className="predict-meta">
          <label>
            Age group
            <select value={ageGroup} onChange={(e) => setAgeGroup(e.target.value)}>
              {AGE_GROUPS.map((a) => (
                <option key={a.value} value={a.value}>{a.label}</option>
              ))}
            </select>
          </label>
          <label>
            Sex
            <select value={sex} onChange={(e) => setSex(e.target.value)}>
              {SEXES.map((a) => (
                <option key={a.value} value={a.value}>{a.label}</option>
              ))}
            </select>
          </label>
          <label>
            How long have you felt this way?
            <select value={duration} onChange={(e) => setDuration(e.target.value)}>
              {DURATIONS.map((a) => (
                <option key={a.value} value={a.value}>{a.label}</option>
              ))}
            </select>
          </label>
        </div>

        <div className="checklist">
          {Object.entries(groups).map(([group, symptoms]) => (
            <fieldset key={group} className="checklist-group">
              <legend>{group}</legend>
              <div className="checklist-grid">
                {symptoms.map((s) => (
                  <label key={s.id} className={`check-item${selected.includes(s.id) ? ' checked' : ''}`}>
                    <input
                      type="checkbox"
                      checked={selected.includes(s.id)}
                      onChange={() => toggle(s.id)}
                    />
                    {s.label}
                  </label>
                ))}
              </div>
            </fieldset>
          ))}
        </div>

        {error && <div className="error">{error}</div>}

        <div className="form-actions">
          <button type="button" className="btn btn-outline" onClick={reset}>
            Reset
          </button>
          <button className="btn btn-primary" disabled={loading}>
            {loading ? 'Analyzing…' : 'Analyze Symptoms'}
          </button>
        </div>
      </form>

      {result && (
        <section className="predict-results">
          <div className="panel-head">
            <h3>Possible conditions</h3>
            <span className="info-chip">Informational only</span>
          </div>

          {result.urgent_care_advice?.length > 0 && (
            <div className="urgent-box">
              <strong>Please seek care now</strong>
              {result.urgent_care_advice.map((advice, i) => (
                <p key={i}>{advice}</p>
              ))}
            </div>
          )}

          {result.ranked_conditions.length === 0 ? (
            <EmptyState icon="🔍" title="No clear match" hint={result.general_advice} />
          ) : (
            <ol className="condition-list">
              {result.ranked_conditions.map((c) => (
                <li key={c.id} className="card condition-card">
                  <div className="condition-top">
                    <strong>{c.name}</strong>
                    <span className={`confidence ${confidenceClass(c.confidence)}`}>
                      {c.confidence}
                    </span>
                  </div>
                  <div className="match-bar">
                    <span style={{ width: `${Math.round(c.match * 100)}%` }} />
                  </div>
                  <p className="muted">{c.explanation}</p>
                  <p className="next-steps"><strong>Next steps:</strong> {c.next_steps}</p>
                </li>
              ))}
            </ol>
          )}

          <p className="muted general-advice">{result.general_advice}</p>
        </section>
      )}

      {history.length > 0 && (
        <section className="card predict-history">
          <div className="panel-head">
            <h3>Prediction history</h3>
          </div>
          <ul className="row-list">
            {history.map((h) => (
              <li key={h.id} className="row-item" onClick={() => setResult(h.result || h)}>
                <div className="row-main">
                  <strong>
                    {(h.result?.ranked_conditions?.[0]?.name) || 'No clear match'}
                  </strong>
                  <span className="muted">
                    {h.symptoms?.length || 0} symptoms ·{' '}
                    {(h.result?.meta?.duration || '')?.replace(/_/g, ' ')}
                  </span>
                </div>
                <span className="row-side">{formatDateTime(h.created_at)}</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </main>
  )
}

export default Predict
