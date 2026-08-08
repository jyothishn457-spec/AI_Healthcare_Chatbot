import React from 'react'
import { useNavigate } from 'react-router-dom'

const FEATURES = [
  {
    title: 'Ask about symptoms',
    desc: 'Get general guidance on symptoms and conditions, grounded in your medical knowledge base.',
  },
  {
    title: 'Understand medicines',
    desc: 'Learn about common medicines and their uses from uploaded documents.',
  },
  {
    title: 'Preventive care',
    desc: 'Evidence-based tips for a healthier lifestyle and disease prevention.',
  },
  {
    title: 'Health FAQs',
    desc: 'Instant answers to everyday health questions with reliable context.',
  },
]

const Dashboard = ({ user }) => {
  const navigate = useNavigate()

  return (
    <main className="dashboard">
      <section className="hero">
        <h2>Welcome back, {user.username}!</h2>
        <p>
          I am MediCare AI — your 24/7 health companion. Ask me about symptoms, medicines,
          conditions and preventive care. My answers are generated from your uploaded medical
          documents, but I am not a substitute for a qualified doctor.
        </p>
        <div className="hero-actions">
          <button className="btn btn-lg hero-btn" onClick={() => navigate('/chat')}>
            Start a Consultation
          </button>
          <button className="btn btn-lg hero-btn ghost" onClick={() => navigate('/chat')}>
            Ask a Question
          </button>
        </div>
      </section>

      <section className="cards">
        {FEATURES.map((f) => (
          <div className="card" key={f.title}>
            <h3>{f.title}</h3>
            <p>{f.desc}</p>
          </div>
        ))}
      </section>

      <section className="emergency-strip">
        <div>
          <h3>In an emergency?</h3>
          <p>Call emergency services immediately. Do not wait for an AI response.</p>
        </div>
        <button className="btn btn-danger btn-lg" onClick={() => navigate('/chat')}>
          Emergency Info
        </button>
      </section>
    </main>
  )
}

export default Dashboard
