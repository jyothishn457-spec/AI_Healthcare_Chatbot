// EmptyState - friendly placeholder shown when a list has no items yet.
import React from 'react'

export default function EmptyState({ icon = '📭', title, hint, action }) {
  return (
    <div className="empty-state">
      <span className="empty-icon">{icon}</span>
      <h4>{title}</h4>
      {hint && <p>{hint}</p>}
      {action}
    </div>
  )
}
