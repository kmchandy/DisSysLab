import React, { useCallback, useEffect, useState } from 'react'
import { resolveMediaSrc } from '../lib/api.js'
import { getWardrobeState, putWardrobeState, launderItems } from '../lib/wardrobeApi.js'

function invLookup(inv) {
  const map = {}
  for (const row of inv?.items || []) map[row.id] = row
  return map
}

function defaultWear() {
  return { stack: 'clean', wears_since_launder: 0, max_wears_before_dirty: 5 }
}

const cardGrid = {
  display: 'grid',
  gap: 10,
  gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
}

export default function ClosetStacksTab({ slug }) {
  const [data, setData] = useState(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  const load = useCallback(async () => {
    setErr('')
    try {
      const res = await getWardrobeState(slug)
      setData(res)
    } catch (e) {
      setErr(e.message || String(e))
      setData(null)
    }
  }, [slug])

  useEffect(() => {
    load()
  }, [load])

  const saveState = async (nextState) => {
    setBusy(true)
    try {
      await putWardrobeState(slug, nextState)
      await load()
    } catch (e) {
      setErr(e.message || String(e))
    } finally {
      setBusy(false)
    }
  }

  const onLaunder = async (ids) => {
    if (!ids.length) return
    setBusy(true)
    try {
      await launderItems(slug, ids)
      await load()
    } catch (e) {
      setErr(e.message || String(e))
    } finally {
      setBusy(false)
    }
  }

  if (err && !data) {
    return <p style={{ color: '#f87171' }}>{err}</p>
  }

  if (!data) return <p style={{ color: '#64748b' }}>Loading closet…</p>

  const state = data.state
  const inv = data.inventory
  const byId = invLookup(inv)

  const groups = { clean: [], worn: [], dirty: [] }
  if (state?.wear_by_item && typeof state.wear_by_item === 'object') {
    for (const gid of Object.keys(state.wear_by_item)) {
      const rec = state.wear_by_item[gid]
      const st = String(rec.stack || 'clean').toLowerCase()
      const bucket = st in groups ? st : 'clean'
      groups[bucket].push({ gid, rec })
    }
  }

  const renderStack = (title, tint, idsList) => (
    <div style={{ padding: 12, borderRadius: 10, border: `1px solid ${tint}`, background: 'rgba(0,0,0,0.2)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 8 }}>
        <h3 style={{ margin: 0, fontSize: 14, color: '#f1f5f9', textTransform: 'capitalize' }}>{title}</h3>
        {title !== 'clean' ? (
          <button
            type="button"
            disabled={busy || !idsList.length}
            style={tinyBtn}
            onClick={() => onLaunder(idsList.map((x) => x.gid))}
          >
            Launder stack
          </button>
        ) : null}
      </div>
      <div style={{ ...cardGrid, marginTop: 10 }}>
        {idsList.map(({ gid, rec }) => {
          const row = byId[gid]
          const desc = row?.description || gid
          const src = resolveMediaSrc(slug, row?.photo_media || '')
          return (
            <div key={gid} style={miniCard}>
              {src ? <img alt="" src={src} style={thumb} /> : <div style={ph}>No img</div>}
              <div style={{ fontSize: 12, color: '#e2e8f0', marginTop: 6 }}>{desc}</div>
              <div style={{ fontSize: 11, color: '#94a3b8' }}>
                wears {rec.wears_since_launder || 0} / limit{' '}
                <input
                  type="number"
                  min={1}
                  disabled={busy}
                  defaultValue={rec.max_wears_before_dirty ?? 5}
                  style={inp}
                  onBlur={(e) => {
                    const n = Math.max(1, parseInt(e.target.value, 10) || 5)
                    const clone = JSON.parse(JSON.stringify(state))
                    if (!clone.wear_by_item[gid]) clone.wear_by_item[gid] = defaultWear()
                    clone.wear_by_item[gid].max_wears_before_dirty = n
                    saveState(clone)
                  }}
                />
              </div>
              {title !== 'clean' ? (
                <button type="button" style={{ ...tinyBtn, marginTop: 6 }} disabled={busy} onClick={() => onLaunder([gid])}>
                  Launder
                </button>
              ) : null}
            </div>
          )
        })}
      </div>
    </div>
  )

  return (
    <div>
      <p style={{ color: '#94a3b8', marginTop: 0 }}>
        Clean / worn / dirty stacks (<code style={{ color: '#cbd5e1' }}>wardrobe_state.json</code>).         Picking an outfit in{' '}
        <strong>Occasion outfits</strong> bumps wear counters; laundering resets stacks.
      </p>
      {err ? <p style={{ color: '#fca5a5', fontSize: 13 }}>{err}</p> : null}
      <button type="button" style={tinyBtn} disabled={busy} onClick={load}>
        Reload stacks
      </button>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14, marginTop: 14 }}>
        {renderStack('clean', 'rgba(74,222,128,0.35)', groups.clean)}
        {renderStack('worn', 'rgba(251,191,36,0.35)', groups.worn)}
        {renderStack('dirty', 'rgba(248,113,113,0.35)', groups.dirty)}
      </div>
    </div>
  )
}

const tinyBtn = {
  cursor: 'pointer',
  fontSize: 12,
  fontWeight: 600,
  padding: '4px 10px',
  borderRadius: 6,
  border: '1px solid rgba(148,163,184,0.35)',
  background: 'rgba(99,102,241,0.2)',
  color: '#cbd5f5',
}

const miniCard = {
  padding: 8,
  borderRadius: 8,
  background: '#10131f',
  border: '1px solid rgba(255,255,255,0.05)',
}

const thumb = { width: '100%', maxHeight: 120, objectFit: 'contain', borderRadius: 6 }
const ph = {
  height: 100,
  borderRadius: 6,
  background: '#1e293b',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  color: '#64748b',
  fontSize: 11,
}
const inp = {
  width: 48,
  marginLeft: 4,
  padding: '2px 4px',
  borderRadius: 4,
  border: '1px solid #475569',
  background: '#0f172a',
  color: '#e2e8f0',
  fontSize: 11,
}
