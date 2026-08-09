// utils.js - small formatting helpers shared across pages.

// "2026-08-20" -> "Aug 20, 2026"
export const formatDate = (dateStr) => {
  if (!dateStr) return ''
  const d = new Date(`${dateStr}T00:00:00`)
  if (Number.isNaN(d.getTime())) return dateStr
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

// "2026-08-20T10:30:00" or "2026-08-20 10:30" -> human string
export const formatDateTime = (iso) => {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString(undefined, {
    month: 'short', day: 'numeric', year: 'numeric',
    hour: 'numeric', minute: '2-digit',
  })
}

// "10:30" -> "10:30 AM"
export const formatTime = (time) => {
  if (!time) return ''
  const [h, m] = time.split(':').map(Number)
  if (Number.isNaN(h)) return time
  const ampm = h >= 12 ? 'PM' : 'AM'
  const hour = h % 12 || 12
  return `${hour}:${String(m).padStart(2, '0')} ${ampm}`
}

// Today's date as YYYY-MM-DD (used for min attributes on date inputs).
export const todayISO = () => {
  const d = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

export const statusLabel = (status) =>
  ({ pending: 'Pending', confirmed: 'Confirmed', completed: 'Completed', cancelled: 'Cancelled' })[status] || status

export const confidenceClass = (confidence) =>
  ({ High: 'high', Moderate: 'moderate', Low: 'low' })[confidence] || 'low'
