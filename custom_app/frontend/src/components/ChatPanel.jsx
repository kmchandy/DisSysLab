import React, { useEffect, useRef, useState } from 'react'
import { fileToAttachment, CHAT_ATTACHMENT_MAX_BYTES } from '../lib/chatAttachments'

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
    lineHeight: 1.45,
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
    flexDirection: 'column',
    gap: '8px',
  },
  inputToolbar: {
    display: 'flex',
    gap: '8px',
    alignItems: 'flex-end',
  },
  attachBtn: {
    background: 'var(--surface2)',
    color: 'var(--text)',
    border: '1px solid var(--border)',
    padding: '8px 12px',
    fontWeight: '600',
    fontSize: '12px',
    borderRadius: '8px',
    flexShrink: 0,
    cursor: 'pointer',
  },
  attachmentChips: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '6px',
    fontSize: '11px',
  },
  chip: {
    background: 'var(--surface2)',
    border: '1px solid var(--border)',
    borderRadius: '6px',
    padding: '4px 8px',
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    maxWidth: '100%',
  },
  chipName: {
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
    maxWidth: '200px',
  },
  chipRemove: {
    background: 'transparent',
    border: 'none',
    color: 'var(--text-muted)',
    cursor: 'pointer',
    padding: '0 2px',
    fontSize: '14px',
    lineHeight: 1,
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
      content:
        "Hi! I'll help you build a new office. Tell me:\n\n• What topic or domain? (news, finance, research…)\n• What sources? (RSS feeds, Bluesky, Gmail, calendar…)\n• What should your agents do? (filter, summarize, alert…)\n• Where should results go? (live display, file, email…)\n\nYou can attach JPEG/PNG/GIF/WebP images or PDFs (e.g. photos of your wardrobe) — I'll use them as context when designing your agents.",
    },
  ])
  const [input, setInput] = useState('')
  const [pendingAttachments, setPendingAttachments] = useState([])
  const [streaming, setStreaming] = useState(false)
  const [pendingFiles, setPendingFiles] = useState(null)
  const [officeName, setOfficeName] = useState('')
  const [creating, setCreating] = useState(false)
  const [needsGmail, setNeedsGmail] = useState(false)
  const [gmailUser, setGmailUser] = useState('')
  const [gmailPass, setGmailPass] = useState('')
  const bottomRef = useRef(null)
  const esRef = useRef(null)
  const fileInputRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async () => {
    const text = input.trim()
    if ((!text && pendingAttachments.length === 0) || streaming) return
    setInput('')

    const attachmentsPayload = pendingAttachments.map(({ media_type, data, filename }) => ({
      media_type,
      data,
      filename,
    }))
    setPendingAttachments([])

    const userMessage = {
      role: 'user',
      content: text,
      ...(attachmentsPayload.length > 0 ? { attachments: attachmentsPayload } : {}),
    }
    const newMessages = [...messages, userMessage]
    setMessages(newMessages)
    setStreaming(true)

    // placeholder for streaming assistant response
    setMessages(prev => [...prev, { role: 'assistant', content: '', _streaming: true }])

    let accumulated = ''

    const es = new EventSource('/api/chat?' + new URLSearchParams({
      // we pass messages via POST body — SSE with body requires fetch + ReadableStream
    }))
    es.close() // close immediately, we'll use fetch + ReadableStream instead

    const serialize = (m) => {
      const row = { role: m.role, content: m.content || '' }
      if (m.attachments && m.attachments.length > 0) row.attachments = m.attachments
      return row
    }

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: newMessages.map(serialize),
        }),
      })

      if (!res.ok) {
        let detail = `Request failed (${res.status})`
        try {
          const errBody = await res.json()
          if (errBody.detail) detail = typeof errBody.detail === 'string' ? errBody.detail : JSON.stringify(errBody.detail)
        } catch (_) {}
        throw new Error(detail)
      }

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
        setNeedsGmail(
          officeText.includes('gmail_sink') || /\bgmail\s*\(/.test(officeText)
        )
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

  const onPickFiles = async (e) => {
    const files = e.target.files
    if (!files?.length) return
    e.target.value = ''
    const next = [...pendingAttachments]
    for (const file of Array.from(files)) {
      try {
        const att = await fileToAttachment(file)
        next.push({ ...att, id: `${Date.now()}-${Math.random().toString(36).slice(2, 9)}` })
      } catch (err) {
        alert(err.message || String(err))
      }
    }
    setPendingAttachments(next)
  }

  const removeAttachment = (id) => {
    setPendingAttachments((prev) => prev.filter((a) => a.id !== id))
  }

  const canSend = input.trim() || pendingAttachments.length > 0

  return (
    <div style={styles.overlay} onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div style={styles.panel}>
        <div style={styles.header}>
          <div>
            <div style={styles.title}>New Office</div>
            <div style={styles.subtitle}>
              Describe what you want — Claude will build it. Attach images or PDFs (max{' '}
              {CHAT_ATTACHMENT_MAX_BYTES / (1024 * 1024)} MB each) for extra context.
            </div>
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
              {m.role === 'user' && (
                <>
                  {m.content ? <span>{m.content}</span> : null}
                  {m.attachments?.length > 0 && (
                    <div
                      style={{
                        fontSize: '11px',
                        opacity: 0.92,
                        marginTop: m.content ? '8px' : 0,
                      }}
                    >
                      📎 {m.attachments.map((a) => a.filename || a.media_type).join(', ')}
                    </div>
                  )}
                </>
              )}
              {m.role === 'assistant' && (m.content || (m._streaming ? '…' : ''))}
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
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept="image/jpeg,image/png,image/gif,image/webp,.pdf,application/pdf"
              style={{ display: 'none' }}
              onChange={onPickFiles}
            />
            {pendingAttachments.length > 0 && (
              <div style={styles.attachmentChips}>
                {pendingAttachments.map((a) => (
                  <span key={a.id} style={styles.chip}>
                    <span style={styles.chipName} title={a.filename}>
                      {a.filename || a.media_type}
                    </span>
                    <button
                      type="button"
                      style={styles.chipRemove}
                      onClick={() => removeAttachment(a.id)}
                      aria-label="Remove attachment"
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
            )}
            <div style={styles.inputToolbar}>
              <textarea
                style={styles.input}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKey}
                placeholder="Describe your office… (Enter to send, Shift+Enter for new line)"
                disabled={streaming}
                rows={2}
              />
              <button
                type="button"
                style={styles.attachBtn}
                onClick={() => fileInputRef.current?.click()}
                disabled={streaming}
                title="Attach images or PDF"
              >
                📎
              </button>
              <button
                style={styles.sendBtn}
                onClick={sendMessage}
                disabled={streaming || !canSend}
              >
                {streaming ? '…' : 'Send'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
