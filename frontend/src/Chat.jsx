import React, { useEffect, useRef, useState } from 'react'
import { jsPDF } from 'jspdf'
import api from './api.js'

const EMERGENCY_INFO = {
  title: 'Emergency Resources',
  note: 'If this is a life-threatening emergency, call your local emergency number now. AI responses are not a substitute for emergency medical care.',
  items: [
    { label: 'Emergency services (US)', value: '911' },
    { label: 'International emergency number', value: '112' },
    { label: 'Poison control (US)', value: '1-800-222-1222' },
    { label: 'Suicide & crisis lifeline (US)', value: '988' },
  ],
}

const SUGGESTIONS = [
  'What are the symptoms of diabetes?',
  'How can I control high blood pressure?',
  'Explain common medicines for fever',
  'Give me preventive care tips for heart health',
]

const welcomeMessage = (name) =>
  `Hello ${name}! I am MediCare AI. Ask me about symptoms, diseases, medicines or preventive care. Remember, I am not a doctor — always consult a healthcare professional for medical advice.`

const Chat = ({ user }) => {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [typing, setTyping] = useState(false)
  const [showEmergency, setShowEmergency] = useState(false)
  const [listening, setListening] = useState(false)
  const [speaking, setSpeaking] = useState(false)
  const [adminOpen, setAdminOpen] = useState(false)
  const [docs, setDocs] = useState([])
  const [adminMsg, setAdminMsg] = useState('')

  const bottomRef = useRef(null)
  const recognitionRef = useRef(null)

  // Load persisted chat history on mount (or show a welcome message).
  useEffect(() => {
    api
      .get('/history')
      .then((res) => {
        const history = res.data.map((m) => ({
          role: m.role,
          content: m.message,
          sources: m.sources || [],
        }))
        setMessages(
          history.length > 0 ? history : [{ role: 'assistant', content: welcomeMessage(user.username) }],
        )
      })
      .catch(() => setMessages([{ role: 'assistant', content: welcomeMessage(user.username) }]))
  }, [user.username])

  // Keep the newest message in view.
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, typing])

  const send = async (text) => {
    const q = (text ?? input).trim()
    if (!q || loading) return
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: q }])
    setLoading(true)
    setTyping(true)
    try {
      const { data } = await api.post('/chat', { message: q })
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: data.response, sources: data.sources || [] },
      ])
    } catch (err) {
      const detail = err.response?.data?.detail
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: detail || 'Sorry, I could not reach the server. Please try again.',
        },
      ])
    } finally {
      setLoading(false)
      setTyping(false)
    }
  }

  const clearChat = async () => {
    try {
      await api.delete('/history')
    } catch (_) {
      /* ignore network errors - the local view still clears */
    }
    setMessages([{ role: 'assistant', content: 'Chat cleared. How can I help you today?' }])
  }

  // ---------------- Export chat as PDF ----------------
  const exportPdf = () => {
    if (messages.length === 0) return
    const doc = new jsPDF()
    const margin = 16
    const pageWidth = doc.internal.pageSize.getWidth()
    const pageHeight = doc.internal.pageSize.getHeight()
    let y = margin

    // jsPDF's built-in fonts cannot render emoji / non-Latin characters.
    const sanitize = (text) => text.replace(/[^\x00-\x7F]/g, ' ')

    const pushLines = (lines) => {
      lines.forEach((line) => {
        if (y > pageHeight - margin) {
          doc.addPage()
          y = margin
        }
        doc.text(line, margin, y)
        y += 6
      })
    }

    // Header
    doc.setFont('helvetica', 'bold')
    doc.setFontSize(16)
    doc.text('MediCare AI - Chat Transcript', margin, y)
    y += 6
    doc.setFont('helvetica', 'normal')
    doc.setFontSize(9)
    doc.setTextColor(120)
    doc.text(`${user.username} - ${new Date().toLocaleString()}`, margin, y)
    y += 10
    doc.setTextColor(0)

    messages.forEach((m) => {
      doc.setFont('helvetica', 'bold')
      doc.setFontSize(11)
      pushLines([`${m.role === 'user' ? 'You' : 'MediCare AI'}:`])
      doc.setFont('helvetica', 'normal')
      doc.setFontSize(10)
      pushLines(doc.splitTextToSize(sanitize(m.content), pageWidth - margin * 2))
      if (m.role === 'assistant' && m.sources && m.sources.length > 0) {
        doc.setFont('helvetica', 'italic')
        doc.setFontSize(9)
        doc.setTextColor(100)
        pushLines([`Source: ${m.sources.join(', ')}`])
        doc.setFont('helvetica', 'normal')
        doc.setTextColor(0)
      }
      y += 4
    })

    doc.save('medi-care-chat-transcript.pdf')
  }

  // ---------------- Voice input (Web Speech API) ----------------
  const toggleVoice = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognition) {
      setAdminMsg('Voice input is not supported in this browser. Try Chrome or Edge.')
      return
    }
    if (listening) {
      recognitionRef.current?.stop()
      setListening(false)
      return
    }
    const rec = new SpeechRecognition()
    rec.lang = 'en-US'
    rec.interimResults = false
    rec.maxAlternatives = 1
    rec.onresult = (event) => {
      const transcript = event.results[0][0].transcript
      setInput(transcript)
      setListening(false)
    }
    rec.onerror = () => setListening(false)
    rec.onend = () => setListening(false)
    recognitionRef.current = rec
    rec.start()
    setListening(true)
  }

  // ---------------- Text-to-speech ----------------
  const speak = (text) => {
    if (!('speechSynthesis' in window)) return
    if (speaking) {
      window.speechSynthesis.cancel()
      setSpeaking(false)
      return
    }
    // Strip markdown-ish characters so the voice reads cleanly.
    const clean = text.replace(/[#*`_[\]]/g, ' ')
    const utterance = new SpeechSynthesisUtterance(clean)
    utterance.rate = 1
    utterance.pitch = 1
    utterance.onend = () => setSpeaking(false)
    utterance.onerror = () => setSpeaking(false)
    window.speechSynthesis.speak(utterance)
    setSpeaking(true)
  }

  // ---------------- Admin document management ----------------
  const loadDocs = async () => {
    try {
      const { data } = await api.get('/documents')
      setDocs(data)
    } catch (_) {
      /* ignore */
    }
  }

  const uploadFile = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    const form = new FormData()
    form.append('file', file)
    try {
      const { data } = await api.post('/upload', form)
      setAdminMsg(`Indexed "${data.filename}" (${data.chunks} chunks).`)
      loadDocs()
    } catch (err) {
      setAdminMsg(err.response?.data?.detail || 'Upload failed.')
    }
    e.target.value = ''
  }

  const deleteDoc = async (id) => {
    try {
      await api.delete(`/documents/${id}`)
      setAdminMsg('Document deleted.')
      loadDocs()
    } catch (err) {
      setAdminMsg(err.response?.data?.detail || 'Delete failed.')
    }
  }

  useEffect(() => {
    if (adminOpen && user.is_admin) loadDocs()
  }, [adminOpen, user.is_admin])

  return (
    <main className="chat-page">
      <div className="chat-header">
        <h2>Chat with MediCare AI</h2>
        <div className="chat-actions">
          <button className="btn btn-danger btn-sm" onClick={() => setShowEmergency(true)}>
            SOS
          </button>
          {user.is_admin && (
            <button className="btn btn-outline btn-sm" onClick={() => setAdminOpen(true)}>
              Manage Documents
            </button>
          )}
          <button className="btn btn-outline btn-sm" onClick={exportPdf}>
            Export PDF
          </button>
          <button className="btn btn-outline btn-sm" onClick={clearChat}>
            Clear Chat
          </button>
        </div>
      </div>

      <div className="chat-window">
        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            <div className="bubble">
              <p>{m.content}</p>
              {m.role === 'assistant' && m.sources && m.sources.length > 0 && (
                <div className="source-tag">
                  Source: {m.sources.join(', ')}
                </div>
              )}
              {m.role === 'assistant' && (
                <button className="tts-btn" onClick={() => speak(m.content)}>
                  {speaking ? 'Stop' : 'Listen'}
                </button>
              )}
            </div>
          </div>
        ))}

        {typing && (
          <div className="msg assistant">
            <div className="bubble typing">
              <span />
              <span />
              <span />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="suggestions">
        {SUGGESTIONS.map((s) => (
          <button key={s} className="chip" onClick={() => send(s)}>
            {s}
          </button>
        ))}
      </div>

      <form
        className="composer"
        onSubmit={(e) => {
          e.preventDefault()
          send()
        }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your health question..."
          maxLength={2000}
          aria-label="Your health question"
        />
        <button
          type="button"
          className={`btn icon ${listening ? 'active' : ''}`}
          onClick={toggleVoice}
          title="Voice input"
        >
          {listening ? 'Listening...' : 'Voice'}
        </button>
        <button className="btn btn-primary" disabled={loading || !input.trim()}>
          Send
        </button>
      </form>

      {showEmergency && (
        <div className="modal-overlay" onClick={() => setShowEmergency(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>{EMERGENCY_INFO.title}</h3>
            <p className="emergency-note">{EMERGENCY_INFO.note}</p>
            <ul className="emergency-list">
              {EMERGENCY_INFO.items.map((it) => (
                <li key={it.label}>
                  <strong>{it.label}:</strong> {it.value}
                </li>
              ))}
            </ul>
            <button className="btn btn-primary" onClick={() => setShowEmergency(false)}>
              Close
            </button>
          </div>
        </div>
      )}

      {adminOpen && user.is_admin && (
        <div className="modal-overlay" onClick={() => setAdminOpen(false)}>
          <div className="modal wide" onClick={(e) => e.stopPropagation()}>
            <h3>Document Management</h3>
            <label className="upload-box">
              Upload medical document (PDF / TXT / DOCX)
              <input type="file" accept=".pdf,.txt,.docx" onChange={uploadFile} />
            </label>
            {adminMsg && <div className="error">{adminMsg}</div>}
            <ul className="doc-list">
              {docs.map((d) => (
                <li key={d.id}>
                  <div>
                    <strong>{d.filename}</strong>
                    <span>
                      {d.chunk_count} chunks &middot; {d.uploaded_at} &middot; by {d.uploader}
                    </span>
                  </div>
                  <button className="btn btn-danger btn-sm" onClick={() => deleteDoc(d.id)}>
                    Delete
                  </button>
                </li>
              ))}
              {docs.length === 0 && <li className="muted">No documents uploaded yet.</li>}
            </ul>
            <button className="btn btn-outline" onClick={() => setAdminOpen(false)}>
              Close
            </button>
          </div>
        </div>
      )}
    </main>
  )
}

export default Chat
