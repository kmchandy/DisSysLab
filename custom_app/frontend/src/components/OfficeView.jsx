import React, { useEffect, useRef, useState, useCallback } from 'react'

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    overflow: 'hidden',
  },
  header: {
    padding: '20px 24px 16px',
    borderBottom: '1px solid var(--border)',
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: '16px',
  },
  title: {
    fontSize: '18px',
    fontWeight: '700',
    color: 'var(--text)',
  },
  badge: {
    display: 'inline-block',
    fontSize: '10px',
    padding: '2px 8px',
    borderRadius: '999px',
    marginLeft: '8px',
    verticalAlign: 'middle',
    fontWeight: '600',
    letterSpacing: '0.05em',
  },
  actions: {
    display: 'flex',
    gap: '8px',
    flexShrink: 0,
  },
  runBtn: {
    background: 'var(--success)',
    color: '#fff',
    padding: '8px 18px',
    fontWeight: '600',
  },
  stopBtn: {
    background: 'var(--danger)',
    color: '#fff',
    padding: '8px 18px',
    fontWeight: '600',
  },
  editBtn: {
    background: 'var(--surface2)',
    color: 'var(--text)',
    border: '1px solid var(--border)',
    padding: '8px 18px',
  },
  cloneBtn: {
    background: 'rgba(108,99,255,0.15)',
    color: 'var(--accent)',
    border: '1px solid rgba(108,99,255,0.3)',
    padding: '8px 18px',
  },
  meta: {
    padding: '12px 24px',
    borderBottom: '1px solid var(--border)',
    background: 'var(--surface)',
  },
  officeCode: {
    fontFamily: 'var(--font-mono)',
    fontSize: '12px',
    color: 'var(--text-dim)',
    whiteSpace: 'pre-wrap',
    lineHeight: '1.7',
  },
  terminal: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
    padding: '0 24px 24px',
    marginTop: '16px',
  },
  termLabel: {
    fontSize: '11px',
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
    color: 'var(--text-muted)',
    marginBottom: '8px',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  termBox: {
    flex: 1,
    background: '#0a0c12',
    borderRadius: '8px',
    border: '1px solid var(--border)',
    overflowY: 'auto',
    padding: '12px 14px',
    fontFamily: 'var(--font-mono)',
    fontSize: '12px',
    lineHeight: '1.65',
    color: '#c9d1d9',
  },
  termLine: {
    display: 'block',
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-all',
  },
  placeholder: {
    color: 'var(--text-muted)',
    fontStyle: 'italic',
    fontSize: '12px',
  },
  pulse: {
    display: 'inline-block',
    width: '7px',
    height: '7px',
    borderRadius: '50%',
    background: 'var(--success)',
    animation: 'pulse 1.2s infinite',
  },
}

const cloneModalStyles = {
  overlay: {
    position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)',
    zIndex: 200, display: 'flex', alignItems: 'center', justifyContent: 'center',
  },
  box: {
    background: 'var(--surface)', border: '1px solid var(--border)',
    borderRadius: '10px', padding: '24px', width: '340px',
  },
  title: { fontSize: '15px', fontWeight: '700', marginBottom: '8px' },
  sub: { fontSize: '12px', color: 'var(--text-muted)', marginBottom: '16px' },
  input: { width: '100%', marginBottom: '14px', fontFamily: 'var(--font-mono)' },
  row: { display: 'flex', gap: '8px', justifyContent: 'flex-end' },
  cancel: { background: 'transparent', border: '1px solid var(--border)', color: 'var(--text-muted)', padding: '7px 14px' },
  confirm: { background: 'var(--accent)', color: '#fff', fontWeight: '600', padding: '7px 14px' },
}

export default function OfficeView({ office, officeDetail, running, onRun, onStop, onEdit, onAIEdit, onClone, onDelete }) {
  const [lines, setLines] = useState([])
  const termRef = useRef(null)
  const esRef = useRef(null)
  const [showCloneModal, setShowCloneModal] = useState(false)
  const [cloneName, setCloneName] = useState('')
  const [cloneMode, setCloneMode] = useState('edit') // 'edit' | 'ai'
  const [showGmailModal, setShowGmailModal] = useState(false)
  const [gmailUser, setGmailUser] = useState('')
  const [gmailPass, setGmailPass] = useState('')

  const needsGmail = officeDetail?.office_md?.includes('gmail_sink') ?? false

  const handleRunClick = useCallback(async () => {
    if (!needsGmail) { onRun(); return }
    try {
      const res = await fetch('/api/env')
      const data = await res.json()
      if (data.set?.GMAIL_USER && data.set?.GMAIL_APP_PASSWORD) {
        onRun()
      } else {
        setShowGmailModal(true)
      }
    } catch {
      onRun() // if check fails just try to run anyway
    }
  }, [needsGmail, onRun])

  const handleGmailSubmit = useCallback(async () => {
    if (!gmailUser.trim() || !gmailPass.trim()) return
    await fetch('/api/env', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ vars: { GMAIL_USER: gmailUser.trim(), GMAIL_APP_PASSWORD: gmailPass.trim() } }),
    })
    setShowGmailModal(false)
    onRun()
  }, [gmailUser, gmailPass, onRun])

  useEffect(() => {
    if (!office) return
    setLines([])

    if (esRef.current) {
      esRef.current.close()
      esRef.current = null
    }

    if (running) {
      const es = new EventSource(`/api/offices/${office.name}/output`)
      esRef.current = es
      es.onmessage = (e) => {
        setLines(prev => [...prev, e.data])
      }
      es.onerror = () => {
        es.close()
        esRef.current = null
      }
    }

    return () => {
      esRef.current?.close()
    }
  }, [office?.name, running])

  useEffect(() => {
    if (termRef.current) {
      termRef.current.scrollTop = termRef.current.scrollHeight
    }
  }, [lines])

  if (!office) {
    return (
      <div style={{ ...styles.container, alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ color: 'var(--text-muted)', textAlign: 'center' }}>
          <div style={{ fontSize: '32px', marginBottom: '12px' }}>🏢</div>
          <div style={{ fontSize: '15px', fontWeight: '500' }}>Select an office to get started</div>
          <div style={{ fontSize: '12px', marginTop: '6px', color: 'var(--text-muted)' }}>
            or create a new one with the button below
          </div>
        </div>
      </div>
    )
  }

  const colorLine = (line) => {
    if (line.includes('ERROR') || line.includes('Error') || line.includes('error')) return '#f87171'
    if (line.includes('CRITICAL')) return '#f97316'
    if (line.includes('HIGH')) return '#facc15'
    if (line.includes('MEDIUM')) return '#60a5fa'
    if (line.includes('✓') || line.includes('started') || line.includes('Fetching')) return '#4ade80'
    if (line.includes('✗') || line.includes('failed') || line.includes('Timeout')) return '#f87171'
    if (line.startsWith('//') || line.startsWith('#')) return '#94a3b8'
    return '#c9d1d9'
  }

  return (
    <div style={styles.container}>
      <style>{`@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }`}</style>

      <div style={styles.header}>
        <div>
          <span style={styles.title}>{office.name}</span>
          <span style={{
            ...styles.badge,
            background: office.builtin ? 'rgba(108,99,255,0.15)' : 'rgba(34,197,94,0.15)',
            color: office.builtin ? 'var(--accent)' : 'var(--success)',
          }}>
            {office.builtin ? 'built-in' : 'custom'}
          </span>
        </div>
        <div style={styles.actions}>
          {office.builtin ? (
            <button
              style={styles.cloneBtn}
              onClick={() => { setCloneName(office.name + '_custom'); setShowCloneModal(true) }}
              title="Copy to Your Offices to edit"
            >
              Clone & Edit
            </button>
          ) : (
            <>
              <button
                style={{ ...styles.editBtn, color: 'var(--danger)', borderColor: 'rgba(239,68,68,0.3)' }}
                onClick={onDelete}
                title="Delete this office"
              >
                Delete
              </button>
              <button
                style={{ ...styles.cloneBtn }}
                onClick={onAIEdit}
                title="Let AI edit this office"
              >
                AI Customize
              </button>
              <button style={styles.editBtn} onClick={onEdit}>Edit</button>
            </>
          )}
          {running ? (
            <button style={styles.stopBtn} onClick={onStop}>Stop</button>
          ) : (
            <button style={styles.runBtn} onClick={handleRunClick}>
              {needsGmail ? '✉ Run' : 'Run'}
            </button>
          )}
        </div>
      </div>

      {officeDetail?.office_md && (
        <div style={styles.meta}>
          <pre style={styles.officeCode}>{officeDetail.office_md}</pre>
        </div>
      )}

      <div style={styles.terminal}>
        <div style={styles.termLabel}>
          {running && <span style={styles.pulse} />}
          Output
          {running && <span style={{ color: 'var(--success)' }}>— running</span>}
        </div>
        <div style={styles.termBox} ref={termRef}>
          {lines.length === 0 && !running && (
            <span style={styles.placeholder}>
              Press Run to start this office. Output will appear here.
            </span>
          )}
          {lines.length === 0 && running && (
            <span style={styles.placeholder}>Starting…</span>
          )}
          {lines.map((line, i) => (
            <span key={i} style={{ ...styles.termLine, color: colorLine(line) }}>
              {line + '\n'}
            </span>
          ))}
        </div>
      </div>

      {showGmailModal && (
        <div style={cloneModalStyles.overlay} onClick={e => { if (e.target === e.currentTarget) setShowGmailModal(false) }}>
          <div style={cloneModalStyles.box}>
            <div style={cloneModalStyles.title}>Gmail credentials required</div>
            <div style={cloneModalStyles.sub}>
              This office sends emails. Enter your Gmail address and an App Password
              (<a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noreferrer"
                style={{ color: 'var(--accent)' }}>generate one here</a>).
            </div>
            <input
              style={{ ...cloneModalStyles.input, marginBottom: '8px' }}
              value={gmailUser}
              onChange={e => setGmailUser(e.target.value)}
              placeholder="you@gmail.com"
              type="email"
              autoFocus
            />
            <input
              style={cloneModalStyles.input}
              value={gmailPass}
              onChange={e => setGmailPass(e.target.value)}
              placeholder="App password (16 chars)"
              type="password"
              onKeyDown={e => { if (e.key === 'Enter') handleGmailSubmit() }}
            />
            <div style={cloneModalStyles.row}>
              <button style={cloneModalStyles.cancel} onClick={() => setShowGmailModal(false)}>Cancel</button>
              <button
                style={cloneModalStyles.confirm}
                disabled={!gmailUser.trim() || !gmailPass.trim()}
                onClick={handleGmailSubmit}
              >
                Save & Run
              </button>
            </div>
          </div>
        </div>
      )}

      {showCloneModal && (
        <div style={cloneModalStyles.overlay} onClick={e => { if (e.target === e.currentTarget) setShowCloneModal(false) }}>
          <div style={cloneModalStyles.box}>
            <div style={cloneModalStyles.title}>Clone "{office.name}"</div>
            <div style={cloneModalStyles.sub}>Give your copy a name, then choose how to customize it.</div>
            <input
              style={cloneModalStyles.input}
              value={cloneName}
              onChange={e => setCloneName(e.target.value.replace(/[^a-z0-9_]/gi, '_').toLowerCase())}
              placeholder="my_office_name"
              autoFocus
            />
            {/* Mode toggle */}
            <div style={{ display: 'flex', gap: '8px', marginBottom: '14px' }}>
              {['edit', 'ai'].map(m => (
                <button
                  key={m}
                  onClick={() => setCloneMode(m)}
                  style={{
                    flex: 1, padding: '8px', borderRadius: '6px', fontSize: '12px', fontWeight: '600',
                    background: cloneMode === m ? 'var(--accent)' : 'var(--surface2)',
                    color: cloneMode === m ? '#fff' : 'var(--text-muted)',
                    border: '1px solid ' + (cloneMode === m ? 'var(--accent)' : 'var(--border)'),
                  }}
                >
                  {m === 'edit' ? 'Edit files manually' : 'AI Customize'}
                </button>
              ))}
            </div>
            <div style={cloneModalStyles.row}>
              <button style={cloneModalStyles.cancel} onClick={() => setShowCloneModal(false)}>Cancel</button>
              <button
                style={cloneModalStyles.confirm}
                disabled={!cloneName.trim()}
                onClick={() => {
                  setShowCloneModal(false)
                  onClone(cloneName.trim(), cloneMode)
                }}
              >
                {cloneMode === 'ai' ? 'Clone & AI Customize' : 'Clone & Edit'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
