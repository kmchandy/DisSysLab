import React, { useEffect, useRef, useState, useCallback, useMemo } from 'react'
import ReactMarkdown from 'react-markdown'

const styles = {
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
    flexWrap: 'wrap',
  },
  tabRow: { display: 'flex', gap: '6px', marginLeft: 'auto' },
  tab: {
    fontSize: '11px',
    fontWeight: '600',
    padding: '4px 10px',
    borderRadius: '6px',
    border: '1px solid var(--border)',
    background: 'transparent',
    color: 'var(--text-muted)',
    cursor: 'pointer',
  },
  tabActive: {
    background: 'var(--surface2)',
    color: 'var(--text)',
    borderColor: 'var(--accent)',
  },
  pulse: {
    display: 'inline-block',
    width: '7px',
    height: '7px',
    borderRadius: '50%',
    background: 'var(--success)',
    animation: 'pulse 1.2s infinite',
  },
  termBox: {
    flex: 1,
    minHeight: 0,
    background: '#0a0c12',
    borderRadius: '8px',
    border: '1px solid var(--border)',
    overflowY: 'auto',
    padding: '12px 14px',
    fontSize: '13px',
    lineHeight: '1.65',
    color: '#c9d1d9',
  },
  activityCard: {
    marginBottom: '14px',
    paddingBottom: '12px',
    borderBottom: '1px solid rgba(255,255,255,0.06)',
  },
  logLine: {
    display: 'block',
    fontFamily: 'var(--font-mono)',
    fontSize: '12px',
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
    marginBottom: '6px',
  },
  /** Activity tab: plain stream lines (not markdown blocks) */
  activityLog: {
    display: 'block',
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    fontSize: '13px',
    lineHeight: 1.55,
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
    marginBottom: '10px',
    padding: '8px 11px',
    borderRadius: '8px',
    background: 'rgba(255,255,255,0.035)',
    borderLeft: '3px solid rgba(108,99,255,0.45)',
    color: '#e2e8f0',
  },
  activityLogMuted: {
    fontSize: '11px',
    lineHeight: 1.45,
    padding: '4px 8px',
    marginBottom: '6px',
    borderLeft: '2px solid rgba(100,116,139,0.35)',
    background: 'rgba(0,0,0,0.2)',
    color: '#94a3b8',
    fontFamily: 'var(--font-mono)',
  },
  placeholder: {
    color: 'var(--text-muted)',
    fontStyle: 'italic',
    fontSize: '12px',
  },
  imgBlock: {
    maxWidth: '100%',
    maxHeight: '280px',
    objectFit: 'contain',
    borderRadius: '8px',
    marginTop: '6px',
    border: '1px solid var(--border)',
  },
}

/** Strip terminal ANSI / OSC sequences so web output matches readable email-style text. */
function stripAnsi(s) {
  if (s == null || s === '') return ''
  let t = String(s)
  // CSI sequences (colors, cursor)
  t = t.replace(/\x1b\[[\d;?]*[\dA-Za-z]/g, '')
  // OSC hyperlinks / titles
  t = t.replace(/\x1b\][^\x07\x1b]*(\x07|\x1b\\)/g, '')
  // Other simple ESC + letter
  t = t.replace(/\x1b[\][()#%][\d;?]*/g, '')
  return t
}

function formatPollSeconds(secStr) {
  const sec = parseInt(secStr, 10)
  if (!Number.isFinite(sec)) return `${secStr}s`
  if (sec >= 3600) return `about ${Math.round(sec / 3600)} h`
  if (sec >= 60) return `about ${Math.round(sec / 60)} min`
  return `${sec}s`
}

const SOURCE_LABELS = {
  hacker_news: 'Hacker News',
  python_jobs: 'Python Jobs',
  remoteok: 'RemoteOK',
  we_work_remotely: 'We Work Remotely',
  bluesky: 'Bluesky',
  nws_forecast: 'NWS forecast',
  mcp_source: 'MCP',
  gmail_source: 'Gmail',
}

function prettySourceLabel(slug) {
  if (!slug) return ''
  const k = slug.toLowerCase()
  if (SOURCE_LABELS[k]) return SOURCE_LABELS[k]
  const spaced = slug.replace(/([a-z])([A-Z])/g, '$1 $2')
  return spaced
    .split(/[\s_]+/)
    .filter(Boolean)
    .map((w) => (w ? w[0].toUpperCase() + w.slice(1).toLowerCase() : ''))
    .join(' ')
}

/**
 * Turn framework / source poll lines into short markdown status lines for Activity.
 */
function humanizeActivityLog(raw) {
  const s = stripAnsi(raw).trimEnd()

  if (/^\[CalendarSource\]\s+For better calendar parsing/i.test(s)) {
    return '**Tip:** For richer calendar parsing, install the `icalendar` package where this office runs (`pip install icalendar`).'
  }

  let m = /^\[CalendarSource\]\s+Error fetching calendar:\s*(.+)$/i.exec(s)
  if (m) return `**Calendar** — could not refresh the feed: _${m[1].trim()}_`

  m = /^\[CalendarSource\]\s+Parse error:\s*(.+)$/i.exec(s)
  if (m) return `**Calendar** — parse issue: _${m[1].trim()}_`

  m = /^\[CalendarSource\]\s+Monitoring calendar \(next (\d+) days\)\s*$/i.exec(s)
  if (m) return `**Calendar** is watching the next **${m[1]}** day(s) for events.`

  m = /^\[CalendarSource\]\s+Polling every (\d+)s\s*$/i.exec(s)
  if (m) return `_**Calendar** checks every ${formatPollSeconds(m[1])}._`

  if (/^\[CalendarSource\]\s+Checking for upcoming events/i.test(s)) {
    return '**Calendar** — checking for upcoming events…'
  }

  m = /^\[CalendarSource\]\s+Found (\d+)\s+upcoming event\(s\)\s*$/i.exec(s)
  if (m) {
    const n = parseInt(m[1], 10)
    if (n === 0) return '**Calendar** — no upcoming events in the current window.'
    return `**Calendar** — found **${n}** upcoming event(s).`
  }

  m = /^\[MCPSource\]\s+Received (\d+)\s+item\(s\)\s*$/i.exec(s)
  if (m) return `**MCP** — received **${m[1]}** item(s) from the tool.`

  if (/^\[MCPSource\]\s+Calling\b/i.test(s)) {
    return '**MCP** — calling the configured tool…'
  }

  m = /^\[FileSource\]\s+Loaded\s+(\d+)\s+items from\s+(\S+)\s+\((\w+)\)\s*$/i.exec(s)
  if (m) {
    return `**File source** — loaded **${m[1]}** row(s) from \`${m[2]}\` (${m[3]}).`
  }

  m = /^\[([\w_]+)\]\s+(\d+)\s+papers found\s*\.?\s*$/i.exec(s)
  if (m) {
    const name = prettySourceLabel(m[1])
    return `Loaded **${m[2]}** paper(s) from **${name}**.`
  }

  m = /^\[([\w_]+)\]\s+(\d+)\s+items found\s*\.?\s*$/i.exec(s)
  if (m) {
    const name = prettySourceLabel(m[1])
    return `Loaded **${m[2]}** item(s) from **${name}**.`
  }

  m = /^\[([\w_]+)\]\s+Fetching\s+(\S+)\s*\.{0,3}\s*$/i.exec(s)
  if (m) {
    const name = prettySourceLabel(m[1])
    return `**${name}** — fetching the latest data…`
  }

  m = /^\[([\w_]+)\]\s+(\d+)\s+entries from\s+https?:\/\/\S+/i.exec(s)
  if (m) {
    const name = prettySourceLabel(m[1])
    return `Loaded **${m[2]}** entries from **${name}**.`
  }

  m = /^\[([\w_]+)\]\s+Found\s+(\d+)\s+articles from\s+https?:\/\/\S+/i.exec(s)
  if (m) {
    const name = prettySourceLabel(m[1])
    return `Loaded **${m[2]}** articles from **${name}**.`
  }

  m = /^\[([\w_]+)\]\s+Sleeping\s+(\d+)s\.{0,3}\s*$/i.exec(s)
  if (m) {
    const name = prettySourceLabel(m[1])
    const sec = parseInt(m[2], 10)
    if (Number.isFinite(sec) && sec >= 3600) {
      const h = Math.round(sec / 3600)
      return `**${name}** — next run in about **${h} h** (idle).`
    }
    if (Number.isFinite(sec) && sec >= 60) {
      const min = Math.round(sec / 60)
      return `**${name}** — next run in about **${min} min** (idle).`
    }
    return `**${name}** — next run in **${sec}s** (idle).`
  }

  if (/^\[GmailSink\]\s+Sent email/i.test(s)) {
    return '**Email sent** — your message was delivered.'
  }
  if (/^\[GmailSink\]\s+Error/i.test(s)) {
    return `**Email error:** ${s.replace(/^\[GmailSink\]\s+Error sending email:\s*/i, '')}`
  }

  if (/^\[GmailSource\]\s+Checking inbox/i.test(s)) {
    return '**Gmail** — checking the inbox for new mail…'
  }
  m = /^\[GmailSource\]\s+Found (\d+)\s+new email\(s\)\s*$/i.exec(s)
  if (m) {
    const n = parseInt(m[1], 10)
    if (n === 0) return '**Gmail** — no new messages.'
    return `**Gmail** — **${n}** new message(s).`
  }
  if (/^\[GmailSource\]\s+Fetching unread emails only/i.test(s)) {
    return '**Gmail** — loading unread messages…'
  }
  if (/^\[GmailSource\]\s+Monitoring\b/i.test(s)) {
    return '**Gmail** — monitoring the configured account.'
  }
  m = /^\[GmailSource\]\s+Polling every (\d+)s\s*$/i.exec(s)
  if (m) return `_**Gmail** checks every ${formatPollSeconds(m[1])}._`

  m = /^\[GmailSource\]\s+Error:\s*(.+)$/i.exec(s)
  if (m) return `**Gmail** — error: _${m[1].trim()}_`

  m = /^\[([\w_]+)\]\s+Error fetching\s+(\S+):\s*(.+)$/i.exec(s)
  if (m) {
    const name = prettySourceLabel(m[1])
    return `**${name}** — fetch failed: _${m[3].trim()}_`
  }

  return s
}

function resolveMediaSrc(officeName, src) {
  if (!src || !officeName) return src || ''
  if (/^https?:\/\//i.test(src)) return src
  if (src.startsWith('/api/')) return src
  if (src.startsWith('media/')) {
    return `/api/offices/${encodeURIComponent(officeName)}/media/${src.slice('media/'.length)}`
  }
  return src
}

function colorLog(text) {
  if (!text) return '#c9d1d9'
  if (text.includes('ERROR') || text.includes('Error') || text.includes('error')) return '#f87171'
  if (text.includes('CRITICAL')) return '#f97316'
  if (text.includes('HIGH')) return '#facc15'
  if (text.includes('MEDIUM')) return '#60a5fa'
  if (text.includes('✓') || text.includes('started') || text.includes('Fetching')) return '#4ade80'
  if (text.includes('✗') || text.includes('failed') || text.includes('Timeout')) return '#f87171'
  if (text.startsWith('//') || text.startsWith('#')) return '#94a3b8'
  return '#c9d1d9'
}

/** True when inline markdown rendering is likely helpful (not strict GFM). */
function logTextLooksLikeMarkdown(s) {
  const t = (s || '').trim()
  if (t.length < 2) return false
  if (t.startsWith('•') || t.startsWith('\u2022')) return true
  if (t.startsWith('- ') || t.startsWith('* ') || t.startsWith('+ ') || t.startsWith('> ')) return true
  if (/^\d+\.\s/.test(t)) return true
  const ix = t.indexOf('**')
  if (ix !== -1 && t.indexOf('**', ix + 2) !== -1) return true
  return false
}

function isFrameworkNoiseLine(s) {
  const t = s || ''
  return (
    /^\[office:/i.test(t) ||
    /\bRebuilt\b/i.test(t) ||
    /\bdsl run\b/i.test(t) ||
    /WatchFiles/i.test(t) ||
    /^\s*INFO:\s/i.test(t) ||
    /uvicorn/i.test(t)
  )
}

export default function OfficeOutputFeed({ officeName, running }) {
  const [tab, setTab] = useState('activity')
  const [entries, setEntries] = useState([])
  const idRef = useRef(0)
  const termRef = useRef(null)
  const esRef = useRef(null)

  const appendLog = useCallback((text) => {
    const t = typeof text === 'string' ? text : String(text)
    setEntries((prev) => [...prev, { id: ++idRef.current, kind: 'log', text: t }])
  }, [])

  const appendBlock = useCallback((obj) => {
    const k = obj?.kind
    if (k === 'markdown' && obj.body != null) {
      setEntries((prev) => [
        ...prev,
        { id: ++idRef.current, kind: 'markdown', body: String(obj.body), source: obj.source },
      ])
      return
    }
    if (k === 'image' && obj.src) {
      setEntries((prev) => [
        ...prev,
        {
          id: ++idRef.current,
          kind: 'image',
          src: String(obj.src),
          alt: String(obj.alt || ''),
        },
      ])
      return
    }
    if (k === 'json') {
      appendLog(JSON.stringify(obj.data, null, 2))
      return
    }
    appendLog(typeof obj === 'string' ? obj : JSON.stringify(obj))
  }, [appendLog])

  useEffect(() => {
    setEntries([])
    if (esRef.current) {
      esRef.current.close()
      esRef.current = null
    }
    if (!officeName || !running) return undefined

    const es = new EventSource(`/api/offices/${encodeURIComponent(officeName)}/output`)
    esRef.current = es

    const onLog = (e) => {
      let text = e.data
      try {
        const o = JSON.parse(e.data)
        if (o && typeof o.text === 'string') text = o.text
      } catch (_) {}
      appendLog(text)
    }

    const onBlock = (e) => {
      try {
        const o = JSON.parse(e.data)
        appendBlock(o)
      } catch {
        appendLog(e.data)
      }
    }

    es.addEventListener('log', onLog)
    es.addEventListener('block', onBlock)
    es.onerror = () => {
      es.close()
      esRef.current = null
    }

    return () => {
      es.removeEventListener('log', onLog)
      es.removeEventListener('block', onBlock)
      es.close()
      esRef.current = null
    }
  }, [officeName, running, appendLog, appendBlock])

  useEffect(() => {
    if (termRef.current) termRef.current.scrollTop = termRef.current.scrollHeight
  }, [entries, tab])

  const mdComponents = useMemo(
    () => ({
      img: ({ src, alt }) => (
        <img
          src={resolveMediaSrc(officeName, src || '')}
          alt={alt || ''}
          style={styles.imgBlock}
          loading="lazy"
        />
      ),
      a: ({ href, children }) => (
        <a href={href} target="_blank" rel="noopener noreferrer">
          {children}
        </a>
      ),
    }),
    [officeName]
  )

  return (
    <>
      <style>{`@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }`}</style>
      <div style={styles.termLabel}>
        {running && <span style={styles.pulse} />}
        Output
        {running && <span style={{ color: 'var(--success)' }}>— running</span>}
        <span style={styles.tabRow}>
          <button
            type="button"
            style={{ ...styles.tab, ...(tab === 'activity' ? styles.tabActive : {}) }}
            onClick={() => setTab('activity')}
          >
            Activity
          </button>
          <button
            type="button"
            style={{ ...styles.tab, ...(tab === 'raw' ? styles.tabActive : {}) }}
            onClick={() => setTab('raw')}
          >
            Raw log
          </button>
        </span>
      </div>
      <div style={styles.termBox} ref={termRef}>
        {entries.length === 0 && !running && (
          <span style={styles.placeholder}>Press Run to start this office. Output will appear here.</span>
        )}
        {entries.length === 0 && running && <span style={styles.placeholder}>Starting…</span>}

        {tab === 'raw' &&
          entries.map((e) => (
            <span
              key={e.id}
              style={{ ...styles.logLine, color: e.kind === 'log' ? colorLog(stripAnsi(e.text)) : '#94a3b8' }}
            >
              {e.kind === 'markdown' ? e.body : e.kind === 'image' ? `[image] ${e.src}` : stripAnsi(e.text)}
              {'\n'}
            </span>
          ))}

        {tab === 'activity' &&
          entries.map((e) => {
            if (e.kind === 'log') {
              const display = humanizeActivityLog(e.text)
              if (logTextLooksLikeMarkdown(display)) {
                return (
                  <div
                    key={e.id}
                    style={styles.activityCard}
                    className="office-md"
                  >
                    <ReactMarkdown components={mdComponents}>{display}</ReactMarkdown>
                  </div>
                )
              }
              const muted = isFrameworkNoiseLine(e.text)
              return (
                <div
                  key={e.id}
                  style={{
                    ...(muted ? styles.activityLogMuted : styles.activityLog),
                    color: muted ? undefined : colorLog(display),
                  }}
                >
                  {display}
                </div>
              )
            }
            if (e.kind === 'markdown') {
              return (
                <div key={e.id} style={styles.activityCard} className="office-md">
                  <ReactMarkdown components={mdComponents}>{e.body}</ReactMarkdown>
                </div>
              )
            }
            if (e.kind === 'image') {
              return (
                <div key={e.id} style={styles.activityCard}>
                  {e.alt ? <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: 6 }}>{e.alt}</div> : null}
                  <img
                    src={resolveMediaSrc(officeName, e.src)}
                    alt={e.alt}
                    style={styles.imgBlock}
                    loading="lazy"
                  />
                </div>
              )
            }
            return null
          })}
      </div>
    </>
  )
}
