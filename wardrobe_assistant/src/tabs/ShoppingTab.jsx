import React, { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { shoppingBlind, shoppingEvaluate } from '../lib/wardrobeApi.js'

export default function ShoppingTab({ slug }) {
  const [styleNotes, setStyleNotes] = useState('')
  const [evalNote, setEvalNote] = useState('')
  const [files, setFiles] = useState([])
  const [blindMd, setBlindMd] = useState('')
  const [evalMd, setEvalMd] = useState('')
  const [busy, setBusy] = useState('')
  const [err, setErr] = useState('')

  const onBlind = async () => {
    setBusy('blind')
    setErr('')
    try {
      const d = await shoppingBlind(slug, styleNotes)
      setBlindMd(d.markdown || '')
    } catch (e) {
      setErr(e.message || String(e))
    } finally {
      setBusy('')
    }
  }

  const onEval = async () => {
    if (!files.length) {
      setErr('Choose at least one product photo.')
      return
    }
    setBusy('eval')
    setErr('')
    try {
      const d = await shoppingEvaluate(slug, { note: evalNote, files })
      setEvalMd(d.markdown || '')
    } catch (e) {
      setErr(e.message || String(e))
    } finally {
      setBusy('')
    }
  }

  return (
    <div>
      <section style={sec}>
        <h3 style={h3}>Blind shopping ideas</h3>
        <p style={{ color: '#94a3b8', fontSize: 13 }}>
          Agent suggests purchase categories from your current inventory JSON only (no images).
        </p>
        <textarea
          placeholder="Optional style direction (e.g. more formal blazers, earthy palette)"
          rows={2}
          style={ta}
          value={styleNotes}
          onChange={(e) => setStyleNotes(e.target.value)}
        />
        <button type="button" style={btn} disabled={!!busy} onClick={onBlind}>
          {busy === 'blind' ? 'Thinking…' : 'Get blind suggestions'}
        </button>
        {blindMd ? (
          <div className="wa-md" style={{ marginTop: 12 }}>
            <ReactMarkdown>{blindMd}</ReactMarkdown>
          </div>
        ) : null}
      </section>

      <section style={{ ...sec, marginTop: 20 }}>
        <h3 style={h3}>Evaluate purchase photos</h3>
        <p style={{ color: '#94a3b8', fontSize: 13 }}>
          Upload PDP / mirror shots; we compare against duplicates + outfit pairings.
        </p>
        <textarea
          placeholder="Context (e.g. Uniqlo rayon shirt in bone white, $40)"
          rows={2}
          style={ta}
          value={evalNote}
          onChange={(e) => setEvalNote(e.target.value)}
        />
        <input
          type="file"
          accept="image/jpeg,image/png,image/gif,image/webp"
          multiple
          onChange={(e) => setFiles(Array.from(e.target.files || []))}
          style={{ marginTop: 8, color: '#94a3b8' }}
        />
        <button type="button" style={btn} disabled={!!busy || !files.length} onClick={onEval}>
          {busy === 'eval' ? 'Evaluating…' : 'Evaluate uploads'}
        </button>
        {evalMd ? (
          <div className="wa-md" style={{ marginTop: 12 }}>
            <ReactMarkdown>{evalMd}</ReactMarkdown>
          </div>
        ) : null}
      </section>

      {err ? <p style={{ color: '#f87171', marginTop: 16 }}>{err}</p> : null}
    </div>
  )
}

const sec = {
  padding: 14,
  borderRadius: 10,
  border: '1px solid rgba(148,163,184,0.15)',
  background: 'rgba(0,0,0,0.2)',
}

const h3 = { margin: '0 0 8px', color: '#f1f5f9', fontSize: 15 }

const ta = {
  width: '100%',
  borderRadius: 8,
  border: '1px solid rgba(148,163,184,0.25)',
  background: '#0f111a',
  color: '#e2e8f0',
  padding: 10,
  fontSize: 14,
  fontFamily: 'inherit',
  resize: 'vertical',
  boxSizing: 'border-box',
}

const btn = {
  cursor: 'pointer',
  marginTop: 10,
  fontWeight: 600,
  padding: '8px 16px',
  borderRadius: 8,
  border: '1px solid rgba(147,164,253,0.45)',
  background: 'rgba(99,102,241,0.35)',
  color: '#e0e7ff',
}
