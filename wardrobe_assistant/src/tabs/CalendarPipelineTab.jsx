import React from 'react'
import StreamPanel from '../components/StreamPanel.jsx'

const btn = {
  cursor: 'pointer',
  fontWeight: 600,
  fontSize: 13,
  padding: '8px 16px',
  borderRadius: 8,
  border: '1px solid rgba(148,163,184,0.35)',
  background: 'rgba(99,102,241,0.25)',
  color: '#e0e7ff',
}

const btnGhost = { ...btn, background: 'transparent', color: '#94a3b8' }

const sectionPanel = {
  marginTop: 16,
  padding: 18,
  borderRadius: 10,
  border: '1px solid rgba(148,163,184,0.2)',
  background: 'rgba(15,18,28,0.85)',
  minHeight: 120,
}

export default function CalendarPipelineTab({
  slug,
  hasOffice,
  running,
  busy,
  onRun,
  onStop,
  onRefresh,
  apiOk,
}) {
  return (
    <div>
      <p style={{ color: '#94a3b8', fontSize: 14, lineHeight: 1.55, marginTop: 0 }}>
        Runs the DSL office calendar + NOAA + Gmail pipeline (same subprocess as Custom App{' '}
        <strong>Run</strong>). Open <strong>Wardrobe → Occasion outfits</strong> for event-free chats.
      </p>
      <div style={{ marginTop: 12, display: 'flex', gap: 10, flexWrap: 'wrap' }}>
        <button type="button" style={btn} disabled={busy || !hasOffice || running} onClick={onRun}>
          Run calendar office
        </button>
        <button type="button" style={btnGhost} disabled={busy || !running} onClick={onStop}>
          Stop
        </button>
        <button type="button" style={btnGhost} disabled={busy} onClick={onRefresh}>
          Refresh status
        </button>
      </div>
      {hasOffice === false && apiOk ? (
        <p style={{ marginTop: 16, color: '#fcd34d' }}>
          Add <strong>{slug}</strong> under <code>custom_app/user_offices/</code> then refresh from the shell header.
        </p>
      ) : null}
      <section style={sectionPanel}>
        <div
          style={{
            fontSize: 11,
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
            color: '#64748b',
            marginBottom: 12,
          }}
        >
          Streamed output {running ? <span style={{ color: '#4ade80' }}>live</span> : null}
        </div>
        <StreamPanel officeName={slug} running={running} />
      </section>
    </div>
  )
}
