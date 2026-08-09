// Modal - accessible overlay dialog with a scrim and close on backdrop click.
import React from 'react'

export default function Modal({ open, title, onClose, children, wide }) {
  if (!open) return null
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className={`modal${wide ? ' wide' : ''}`} onClick={(e) => e.stopPropagation()}>
        {title && (
          <div className="modal-head">
            <h3>{title}</h3>
            <button className="modal-close" onClick={onClose} aria-label="Close">
              ✕
            </button>
          </div>
        )}
        {children}
      </div>
    </div>
  )
}
