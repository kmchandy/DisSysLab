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
  title: { fontSize: '15px', fontWeight: '700' },
  subtitle: { fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' },
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
}

export default function AIEditPanel({ office, onClose, onSaved }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: `I have the current files for "${office.name}" loaded. Tell me what you'd like to change — I'll update the files automatically.\n\nExamples:\n• "Add a third agent that formats results as bullet points"\n• "Change the sources to only use BBC and NPR"\n• "Make the analyst stricter — only pass CRITICAL items"`,
    },
  ])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const bottomRef = useRef(null)

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
    setMessages(prev => [...prev, { role: 'assistant', content: '', _streaming: true }])

    let accumulated = ''
    let savedFiles = null

    try {
      const res = await fetch(`/api/offices/${office.name}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: newMessages.map(m => ({ role: m.role, content: m.content })),
        }),
      })

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

  return (
    <div style={styles.overlay} onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div style={styles.panel}>
        <div style={styles.header}>
          <div>
            <div style={styles.title}>AI Customize — {office.name}</div>
            <div style={styles.subtitle}>Describe changes and Claude updates the files</div>
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
                {m.content || (m._streaming ? '…' : '')}
              </div>
            )
          })}
          <div ref={bottomRef} />
        </div>

        <div style={styles.inputRow}>
          <textarea
            style={styles.input}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Describe what you want to change… (Enter to send)"
            disabled={streaming}
            rows={2}
          />
          <button style={styles.sendBtn} onClick={sendMessage} disabled={streaming || !input.trim()}>
            {streaming ? '…' : 'Send'}
          </button>
        </div>
      </div>
    </div>
  )
}
