import React, { useCallback, useEffect, useState } from 'react'
import { getWardrobeState } from '../lib/wardrobeApi.js'

export default function OutfitHistoryTab({ slug }) {
  const [hist, setHist] = useState([])
  const [err, setErr] = useState('')

  const load = useCallback(async () => {
    try {
      const data = await getWardrobeState(slug)
      const h = data.state?.outfit_history || []
      setHist(Array.isArray(h) ? [...h].reverse() : [])
      setErr('')
    } catch (e) {
      setErr(e.message || String(e))
    }
  }, [slug])

  useEffect(() => {
    load()
  }, [load])

  return (
    <div>
      <p style={{ color: '#94a3b8', marginTop: 0 }}>
        Logged when you <strong>Pick option A/B/C</strong> after an occasion run. Use this as runway for future RAG into
        stylist prompts (not wired into the calendar office yet).
      </p>
      <button type="button" style={btn} onClick={load}>
        Refresh history
      </button>
      {err ? <p style={{ color: '#f87171' }}>{err}</p> : null}
      <ul style={{ listStyle: 'none', padding: 0, marginTop: 14 }}>
        {hist.length === 0 ? <li style={{ color: '#64748b' }}>No entries yet.</li> : null}
        {hist.map((row) => (
          <li key={row.id || JSON.stringify(row)} style={li}>
            <div style={{ fontWeight: 700, color: '#e2e8f0' }}>
              {row.picked ? `Option ${row.picked}` : 'Outfit'} · {row.source || 'log'}
            </div>
            <div style={{ fontSize: 13, color: '#94a3b8', marginTop: 4 }}>
              {row.occasion ? <span>Occasion: {row.occasion}</span> : null}
              {row.title ? <span>{row.occasion ? ' · ' : ''}{row.title}</span> : null}
            </div>
            {Array.isArray(row.garment_ids) && row.garment_ids.length > 0 ? (
              <div style={{ fontSize: 12, color: '#cbd5e1', marginTop: 6 }}>
                Garments:{' '}
                {row.garment_ids.map((g) => (
                  <code key={g} style={{ marginRight: 6, color: '#a5b4fc' }}>
                    {g}
                  </code>
                ))}
              </div>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  )
}

const btn = {
  cursor: 'pointer',
  fontSize: 12,
  fontWeight: 600,
  padding: '6px 12px',
  borderRadius: 6,
  border: '1px solid rgba(148,163,184,0.35)',
  background: 'rgba(99,102,241,0.2)',
  color: '#cbd5f5',
}

const li = {
  marginBottom: 12,
  padding: 12,
  borderRadius: 8,
  border: '1px solid rgba(148,163,184,0.12)',
  background: 'rgba(0,0,0,0.2)',
}
