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
  title: { fontSize: '15px', fontWeight: '700' },
  subtitle: { fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px', lineHeight: 1.45 },
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
  savedBox: {
    background: 'rgba(34,197,94,0.1)',
    border: '1px solid rgba(34,197,94,0.3)',
    borderRadius: '8px',
    padding: '10px 14px',
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
}

export default function AIEditPanel({ office, onClose, onSaved }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: `I have the current files for "${office.name}" loaded. Tell me what you'd like to change — I'll update the files automatically.\n\nYou can attach JPEG/PNG/GIF/WebP images or PDFs for reference (e.g. style guides or screenshots).\n\nExamples:\n• "Add a third agent that formats results as bullet points"\n• "Change the sources to only use BBC and NPR"\n• "Make the analyst stricter — only pass CRITICAL items"`,
    },
  ])
  const [input, setInput] = useState('')
  const [pendingAttachments, setPendingAttachments] = useState([])
  const [streaming, setStreaming] = useState(false)
  const bottomRef = useRef(null)
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
    setMessages(prev => [...prev, { role: 'assistant', content: '', _streaming: true }])

    let accumulated = ''
    let savedFiles = null

    const serialize = (m) => {
      const row = { role: m.role, content: m.content || '' }
      if (m.attachments && m.attachments.length > 0) row.attachments = m.attachments
      return row
    }

    try {
      const res = await fetch(`/api/offices/${office.name}/chat`, {
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
              if (last._streaming) next[next.length - 1] = { ...last, content: accumulated }
              return next
            })
          } else if (eventType === 'saved') {
            try { savedFiles = JSON.parse(data) } catch (_) {}
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

      setMessages(prev => {
        const next = [...prev]
        const last = next[next.length - 1]
        if (last._streaming) next[next.length - 1] = { role: 'assistant', content: accumulated }
        return next
      })

      if (savedFiles) {
        setMessages(prev => [...prev, { _saved: true, files: savedFiles }])
        onSaved()
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
            <div style={styles.title}>AI Customize — {office.name}</div>
            <div style={styles.subtitle}>
              Describe changes — Claude updates the files. Attach images or PDFs (max{' '}
              {CHAT_ATTACHMENT_MAX_BYTES / (1024 * 1024)} MB each) when helpful.
            </div>
          </div>
          <button style={styles.closeBtn} onClick={onClose}>✕</button>
        </div>

        <div style={styles.messages}>
          {messages.map((m, i) => {
            if (m._saved) return (
              <div key={i} style={styles.savedBox}>
                Files updated: {m.files.join(', ')}
              </div>
            )
            return (
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
            )
          })}
          <div ref={bottomRef} />
        </div>

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
              placeholder="Describe what you want to change… (Enter to send)"
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
      </div>
    </div>
  )
}
