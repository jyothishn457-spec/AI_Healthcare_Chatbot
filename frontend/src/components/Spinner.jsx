// Spinner - small loading indicator used for async actions.
import React from 'react'

export default function Spinner({ label = 'Loading…', inline }) {
  return (
    <div className={`spinner-wrap${inline ? ' inline' : ''}`} role="status">
      <span className="spinner" />
      {label && <span className="spinner-label">{label}</span>}
    </div>
  )
}
