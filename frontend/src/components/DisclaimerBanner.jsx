// DisclaimerBanner - persistent medical disclaimer shown on AI-powered pages.
// It must appear in the chat AND prediction features, not just a footer.
import React from 'react'

const DEFAULT_TEXT =
  'HealthPilot AI is for informational and educational purposes only. It is NOT a substitute for professional medical advice, diagnosis or treatment. Always consult a qualified healthcare provider for medical concerns.'

export default function DisclaimerBanner({ text, urgent }) {
  return (
    <div className={`disclaimer-banner${urgent ? ' urgent' : ''}`} role="note">
      <span className="disclaimer-icon">ℹ</span>
      <p>{text || DEFAULT_TEXT}</p>
    </div>
  )
}
