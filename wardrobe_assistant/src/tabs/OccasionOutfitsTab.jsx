import React, { useCallback, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { resolveMediaSrc } from '../lib/api.js'
import { occasionChat, pickOccasionOutfit } from '../lib/wardrobeApi.js'

export default function OccasionOutfitsTab({ slug }) {
  const [occasion, setOccasion] = useState('')
  const [notes, setNotes] = useState('')
  const [markdown, setMarkdown] = useState('')
  const [options, setOptions] = useState(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  const mdComponents = {
    img: ({ src, alt }) => (
      <img src={resolveMediaSrc(slug, src || '')} alt={alt || ''} loading="lazy" />
    ),
    a: ({ href, children }) => (
      <a href={href} target="_blank" rel="noopener noreferrer">{children}</a>
    ),
  }

  const onSuggest = async () => {
    if (!occasion.trim()) return
    setBusy(true)
    setErr('')
    try {
      const data = await occasionChat(slug, { occasion, notes })
      setMarkdown(data.markdown || '')
      setOptions(data.options || null)
    } catch (e) {
      setErr(e.message || String(e))
    } finally {
      setBusy(false)
    }
  }

  const onPick = useCallback(
    async (picked_id) => {
      if (!options || !picked_id) return
      setBusy(true)
      setErr('')
      try {
        await pickOccasionOutfit(slug, {
          occasion,
          picked_id,
          options,
        })
        alert(`Recorded pick ${picked_id} — wear counters updated on disk (wardrobe_state.json).`)
      } catch (e) {
        setErr(e.message || String(e))
      } finally {
        setBusy(false)
      }
    },
    [slug, occasion, options]
  )

  return (
    <div>
      <p style={{ color: '#94a3b8', marginTop: 0 }}>
        Event-free outfits: describe where you&apos;re headed; we propose A/B/C from your inventory JSON (Anthropic —
        requires <code>ANTHROPIC_API_KEY</code> on the backend).
      </p>
      <textarea
        value={occasion}
        onChange={(e) => setOccasion(e.target.value)}
        placeholder='e.g. "Casual outdoor dinner tonight, lows around 52°F"'
        rows={3}
        style={ta}
      />
      <textarea
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        placeholder="Optional constraints — “no hoodie”, “prefer wine polo”, ..."
        rows={2}
        style={{ ...ta, marginTop: 8 }}
      />
      <button type="button" style={btnPri} disabled={busy || !occasion.trim()} onClick={onSuggest}>
        Get 1–3 outfit ideas
      </button>
      {err ? (
        <p style={{ color: '#f87171' }}>{err}</p>
      ) : null}
      {markdown ? (
        <div style={mdBox}>
          <h3 style={{ margin: '0 0 10px', color: '#e2e8f0', fontSize: 15 }}>Suggestions</h3>
          <div className="wa-md">
            <ReactMarkdown components={mdComponents}>{markdown}</ReactMarkdown>
          </div>
          {options && options.length > 0 ? (
            <div style={{ marginTop: 14, display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {options.map((o) => (
                <button
                  key={o.id || o.short_label}
                  type="button"
                  style={btnPri}
                  disabled={busy}
                  onClick={() => onPick(String(o.id))}
                >
                  Pick option {String(o.id).toUpperCase()}
                </button>
              ))}
            </div>
          ) : (
            <p style={{ fontSize: 12, color: '#fbbf24', marginBottom: 0 }}>
              Model did not return the structured JSON tail — pick buttons are disabled but you can still read the Markdown.
            </p>
          )}
        </div>
      ) : null}
    </div>
  )
}

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

const mdBox = {
  marginTop: 18,
  padding: 16,
  borderRadius: 10,
  border: '1px solid rgba(148,163,184,0.15)',
  background: 'rgba(0,0,0,0.25)',
}

const btnPri = {
  cursor: 'pointer',
  marginTop: 10,
  fontWeight: 600,
  padding: '8px 16px',
  borderRadius: 8,
  border: '1px solid rgba(147,164,253,0.45)',
  background: 'rgba(99,102,241,0.35)',
  color: '#e0e7ff',
}
