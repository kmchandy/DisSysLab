import React, { useEffect, useRef, useState, useCallback } from 'react'
import OfficeOutputFeed from './OfficeOutputFeed'

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
    background: 'var(--surface)',
  },
  body: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    minHeight: 0,
    overflow: 'hidden',
  },
  resizeHandle: {
    flexShrink: 0,
    height: 8,
    cursor: 'row-resize',
    background: 'var(--surface2)',
    borderTop: '1px solid var(--border)',
    borderBottom: '1px solid var(--border)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    touchAction: 'none',
    userSelect: 'none',
  },
  resizeGrip: {
    width: 44,
    height: 4,
    borderRadius: 4,
    background: 'var(--text-muted)',
    opacity: 0.45,
  },
  officeCode: {
    fontFamily: 'var(--font-mono)',
    fontSize: '12px',
    color: 'var(--text-dim)',
    whiteSpace: 'pre-wrap',
    lineHeight: '1.7',
  },
  outputPane: {
    display: 'flex',
    flexDirection: 'column',
    minHeight: 0,
    overflow: 'hidden',
    padding: '0 24px 24px',
    paddingTop: '12px',
  },
}

const META_RATIO_STORAGE_KEY = 'dissyslab-office-meta-ratio'

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

function readStoredMetaRatio() {
  try {
    const v = parseFloat(localStorage.getItem(META_RATIO_STORAGE_KEY))
    if (!Number.isFinite(v) || v < 0.12 || v > 0.88) return 0.32
    return v
  } catch {
    return 0.32
  }
}

export default function OfficeView({ office, officeDetail, running, onRun, onStop, onEdit, onAIEdit, onClone, onDelete }) {
  const [metaRatio, setMetaRatio] = useState(() => readStoredMetaRatio())
  const bodyRef = useRef(null)
  const dragStateRef = useRef({ active: false, startY: 0, startRatio: 0, bodyH: 0, lastRatio: 0.32 })
  const [showCloneModal, setShowCloneModal] = useState(false)
  const [cloneName, setCloneName] = useState('')
  const [cloneMode, setCloneMode] = useState('edit') // 'edit' | 'ai'
  const [showGmailModal, setShowGmailModal] = useState(false)
  const [gmailUser, setGmailUser] = useState('')
  const [gmailPass, setGmailPass] = useState('')

  const officeMd = officeDetail?.office_md ?? ''
  // Gmail sink and the gmail() inbox source both need GMAIL_USER + GMAIL_APP_PASSWORD.
  const needsGmail =
    officeMd.includes('gmail_sink') || /\bgmail\s*\(/.test(officeMd)

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

  // Pre-fill address from gmail_sink(to="...") when opening the credentials modal.
  useEffect(() => {
    if (!showGmailModal) return
    const m = officeMd.match(/gmail_sink\s*\(\s*[^)]*?\bto\s*=\s*["']([^"']+)["']/i)
    if (m?.[1]) {
      setGmailUser((prev) => (prev.trim() ? prev : m[1]))
    }
  }, [showGmailModal, officeMd])

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

  const startResizeDrag = useCallback(
    (e) => {
      e.preventDefault()
      if (dragStateRef.current.active) return
      const body = bodyRef.current
      if (!body) return
      const rect = body.getBoundingClientRect()
      const clientY = e.touches ? e.touches[0].clientY : e.clientY
      dragStateRef.current = {
        active: true,
        startY: clientY,
        startRatio: metaRatio,
        bodyH: Math.max(rect.height, 120),
        lastRatio: metaRatio,
      }

      const applyMove = (clientYNow) => {
        const { startY, startRatio, bodyH } = dragStateRef.current
        if (!dragStateRef.current.active || bodyH <= 0) return
        const dy = clientYNow - startY
        const nr = Math.min(0.88, Math.max(0.12, startRatio + dy / bodyH))
        dragStateRef.current.lastRatio = nr
        setMetaRatio(nr)
      }

      const onMouseMove = (ev) => applyMove(ev.clientY)
      const onTouchMove = (ev) => {
        ev.preventDefault()
        if (ev.touches?.length) applyMove(ev.touches[0].clientY)
      }
      const endDrag = () => {
        if (!dragStateRef.current.active) return
        dragStateRef.current.active = false
        window.removeEventListener('mousemove', onMouseMove)
        window.removeEventListener('mouseup', endDrag)
        window.removeEventListener('touchmove', onTouchMove)
        window.removeEventListener('touchend', endDrag)
        window.removeEventListener('touchcancel', endDrag)
        try {
          localStorage.setItem(META_RATIO_STORAGE_KEY, String(dragStateRef.current.lastRatio))
        } catch (_) {}
      }

      window.addEventListener('mousemove', onMouseMove)
      window.addEventListener('mouseup', endDrag)
      window.addEventListener('touchmove', onTouchMove, { passive: false })
      window.addEventListener('touchend', endDrag)
      window.addEventListener('touchcancel', endDrag)
    },
    [metaRatio]
  )

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

  return (
    <div style={styles.container}>

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

      <div ref={bodyRef} style={styles.body}>
        {officeDetail?.office_md ? (
          <>
            <div
              style={{
                ...styles.meta,
                flex: `${metaRatio} 1 0`,
                minHeight: 48,
                overflow: 'auto',
                borderBottom: '1px solid var(--border)',
              }}
            >
              <pre style={styles.officeCode}>{officeDetail.office_md}</pre>
            </div>
            <div
              role="separator"
              aria-orientation="horizontal"
              aria-label="Drag to resize office preview and output"
              title="Drag to resize"
              style={styles.resizeHandle}
              onMouseDown={startResizeDrag}
              onTouchStart={startResizeDrag}
            >
              <span style={styles.resizeGrip} />
            </div>
            <div
              style={{
                ...styles.outputPane,
                flex: `${1 - metaRatio} 1 0`,
                minHeight: 100,
              }}
            >
              <OfficeOutputFeed officeName={office.name} running={running} />
            </div>
          </>
        ) : (
          <div style={{ ...styles.outputPane, flex: 1, minHeight: 0 }}>
            <OfficeOutputFeed officeName={office.name} running={running} />
          </div>
        )}
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
