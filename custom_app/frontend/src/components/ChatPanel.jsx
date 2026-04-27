import React, { useEffect, useRef, useState } from 'react'

const styles = {
  overlay: {
    position: 'fixed',
    inset: 0,
    background: 'rgba(0,0,0,0.6)',
    zIndex: 100,
    display: 'flex',
    alignItems: 'stretch',
    justifyContent: 'flex-end',
  },
  panel: {
    width: '480px',
    background: 'var(--surface)',
    borderLeft: '1px solid var(--border)',
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
  },
  header: {
    padding: '18px 20px',
    borderBottom: '1px solid var(--border)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  title: {
    fontSize: '15px',
    fontWeight: '700',
  },
  subtitle: {
    fontSize: '11px',
    color: 'var(--text-muted)',
    marginTop: '2px',
  },
  closeBtn: {
    background: 'transparent',
    color: 'var(--text-muted)',
    fontSize: '18px',
    padding: '4px 8px',
    border: '1px solid var(--border)',
    borderRadius: '6px',
  },
  messages: {
    flex: 1,
    overflowY: 'auto',
    padding: '16px',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  bubble: {
    maxWidth: '90%',
    padding: '10px 14px',
    borderRadius: '10px',
    fontSize: '13px',
    lineHeight: '1.6',
    whiteSpace: 'pre-wrap',
  },
  userBubble: {
    background: 'var(--accent)',
    color: '#fff',
    alignSelf: 'flex-end',
    borderBottomRightRadius: '2px',
  },
  assistantBubble: {
    background: 'var(--surface2)',
    color: 'var(--text)',
    alignSelf: 'flex-start',
    borderBottomLeftRadius: '2px',
  },
  successBox: {
    background: 'rgba(34,197,94,0.1)',
    border: '1px solid rgba(34,197,94,0.3)',
    borderRadius: '8px',
    padding: '12px 14px',
    fontSize: '12px',
    color: 'var(--success)',
    alignSelf: 'flex-start',
    maxWidth: '90%',
  },
  inputRow: {
    padding: '12px 16px',
    borderTop: '1px solid var(--border)',
    display: 'flex',
    gap: '8px',
  },
  input: {
    flex: 1,
    resize: 'none',
    maxHeight: '120px',
    borderRadius: '8px',
    fontSize: '13px',
    lineHeight: '1.5',
    padding: '10px 12px',
  },
  sendBtn: {
    background: 'var(--accent)',
    color: '#fff',
    padding: '10px 16px',
    fontWeight: '600',
    alignSelf: 'flex-end',
  },
  namingBox: {
    padding: '12px 16px',
    borderTop: '1px solid var(--border)',
    background: 'var(--surface2)',
  },
  namingLabel: {
    fontSize: '12px',
    color: 'var(--text-muted)',
    marginBottom: '8px',
  },
  namingRow: {
    display: 'flex',
    gap: '8px',
  },
  nameInput: {
    flex: 1,
    fontFamily: 'var(--font-mono)',
  },
  createBtn: {
    background: 'var(--success)',
    color: '#fff',
    fontWeight: '600',
  },
}

export default function ChatPanel({ onClose, onOfficeCreated }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: "Hi! I'll help you build a new office. Tell me:\n\n• What topic or domain? (news, finance, research…)\n• What sources? (RSS feeds, Bluesky, Gmail, calendar…)\n• What should your agents do? (filter, summarize, alert…)\n• Where should results go? (live display, file, email…)",
    },
  ])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [pendingFiles, setPendingFiles] = useState(null)
  const [officeName, setOfficeName] = useState('')
  const [creating, setCreating] = useState(false)
  const [needsGmail, setNeedsGmail] = useState(false)
  const [gmailUser, setGmailUser] = useState('')
  const [gmailPass, setGmailPass] = useState('')
  const bottomRef = useRef(null)
  const esRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async () => {
    const text = input.trim()
    if (!text || streaming) return
    setInput('')

    const newMessages = [...messages, { role: 'user', content: text }]
    setMessages(newMessages)
    setStreaming(true)

    // placeholder for streaming assistant response
    setMessages(prev => [...prev, { role: 'assistant', content: '', _streaming: true }])

    let accumulated = ''

    const es = new EventSource('/api/chat?' + new URLSearchParams({
      // we pass messages via POST body — SSE with body requires fetch + ReadableStream
    }))
    es.close() // close immediately, we'll use fetch + ReadableStream instead

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: newMessages.map(m => ({ role: m.role, content: m.content })),
        }),
      })

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let detectedFiles = null

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        const parts = buffer.split('\n\n')
        buffer = parts.pop()

        for (const part of parts) {
          const lines = part.trim().split('\n')
          let eventType = 'text'
          let data = ''
          for (const line of lines) {
            if (line.startsWith('event: ')) eventType = line.slice(7).trim()
            if (line.startsWith('data: ')) data = line.slice(6)
          }

          if (eventType === 'text') {
            accumulated += data.replace(/\\n/g, '\n')
            setMessages(prev => {
              const next = [...prev]
              const last = next[next.length - 1]
              if (last._streaming) {
                next[next.length - 1] = { ...last, content: accumulated }
              }
              return next
            })
          } else if (eventType === 'files') {
            try { detectedFiles = JSON.parse(data) } catch (_) {}
          } else if (eventType === 'error') {
            accumulated += `\n[Error: ${data}]`
            setMessages(prev => {
              const next = [...prev]
              const last = next[next.length - 1]
              if (last._streaming) next[next.length - 1] = { ...last, content: accumulated }
              return next
            })
          }
        }
      }

      // finalise streaming message
      setMessages(prev => {
        const next = [...prev]
        const last = next[next.length - 1]
        if (last._streaming) next[next.length - 1] = { role: 'assistant', content: accumulated }
        return next
      })

      if (detectedFiles) {
        setPendingFiles(detectedFiles)
        const suggested = detectedFiles['office.md']
          ?.match(/^#\s*Office:\s*(.+)/m)?.[1]
          ?.toLowerCase()
          ?.replace(/\s+/g, '_')
          ?.replace(/[^a-z0-9_]/g, '') || 'my_office'
        setOfficeName(suggested)
        // Check if gmail_sink is used — prompt for credentials
        const officeText = Object.values(detectedFiles).join('\n')
        setNeedsGmail(officeText.includes('gmail_sink') || officeText.includes('gmail_sink'))
      }
    } catch (err) {
      setMessages(prev => {
        const next = [...prev]
        const last = next[next.length - 1]
        if (last._streaming) next[next.length - 1] = { role: 'assistant', content: '[Connection error]' }
        return next
      })
    } finally {
      setStreaming(false)
    }
  }

  const createOffice = async () => {
    if (!officeName.trim() || !pendingFiles) return
    setCreating(true)

    // Save Gmail credentials if provided
    if (needsGmail && gmailUser && gmailPass) {
      await fetch('/api/env', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ vars: { GMAIL_USER: gmailUser, GMAIL_APP_PASSWORD: gmailPass } }),
      })
    }

    const roles = {}
    for (const [path, content] of Object.entries(pendingFiles)) {
      if (path.startsWith('roles/')) {
        const roleName = path.replace('roles/', '').replace('.md', '')
        roles[roleName] = content
      }
    }

    try {
      const res = await fetch('/api/offices', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: officeName.trim(),
          office_md: pendingFiles['office.md'] || '',
          roles,
        }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Failed to create office')
      }
      setPendingFiles(null)
      onOfficeCreated(officeName.trim())
    } catch (err) {
      alert('Error: ' + err.message)
    } finally {
      setCreating(false)
    }
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div style={styles.overlay} onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div style={styles.panel}>
        <div style={styles.header}>
          <div>
            <div style={styles.title}>New Office</div>
            <div style={styles.subtitle}>Describe what you want — Claude will build it</div>
          </div>
          <button style={styles.closeBtn} onClick={onClose}>✕</button>
        </div>

        <div style={styles.messages}>
          {messages.map((m, i) => (
            <div
              key={i}
              style={{
                ...styles.bubble,
                ...(m.role === 'user' ? styles.userBubble : styles.assistantBubble),
              }}
            >
              {m.content || (m._streaming ? '…' : '')}
            </div>
          ))}

          {pendingFiles && (
            <div style={styles.successBox}>
              Office files are ready. Give it a name and click Create.
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {pendingFiles ? (
          <div style={styles.namingBox}>
            <div style={styles.namingLabel}>Name your office (letters, numbers, underscores only)</div>
            <div style={styles.namingRow}>
              <input
                style={styles.nameInput}
                value={officeName}
                onChange={e => setOfficeName(e.target.value.replace(/[^a-z0-9_]/gi, '_').toLowerCase())}
                placeholder="my_office"
              />
            </div>
            {needsGmail && (
              <div style={{ marginTop: '10px' }}>
                <div style={{ ...styles.namingLabel, color: '#f59e0b', marginBottom: '6px' }}>
                  Gmail credentials required for email alerts
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginBottom: '8px' }}>
                  <input
                    style={{ ...styles.nameInput, fontFamily: 'inherit' }}
                    value={gmailUser}
                    onChange={e => setGmailUser(e.target.value)}
                    placeholder="your@gmail.com"
                    type="email"
                  />
                  <input
                    style={{ ...styles.nameInput, fontFamily: 'inherit' }}
                    value={gmailPass}
                    onChange={e => setGmailPass(e.target.value)}
                    placeholder="Gmail App Password (16 chars)"
                    type="password"
                  />
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                    Get an app password: Google Account → Security → 2-Step Verification → App passwords
                  </div>
                </div>
              </div>
            )}
            <div style={{ marginTop: '8px' }}>
              <button
                style={{ ...styles.createBtn, width: '100%', padding: '10px' }}
                onClick={createOffice}
                disabled={creating || !officeName.trim() || (needsGmail && (!gmailUser || !gmailPass))}
              >
                {creating ? 'Creating…' : 'Create Office'}
              </button>
            </div>
          </div>
        ) : (
          <div style={styles.inputRow}>
            <textarea
              style={styles.input}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKey}
              placeholder="Describe your office… (Enter to send, Shift+Enter for new line)"
              disabled={streaming}
              rows={2}
            />
            <button style={styles.sendBtn} onClick={sendMessage} disabled={streaming || !input.trim()}>
              {streaming ? '…' : 'Send'}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
