import React, { useEffect, useState } from 'react'
import { fetchOfficeDetail } from '../lib/api.js'

/** Optional YAML front-matter `description:` from office.md */
function yamlDescription(officeMd) {
  const t = (officeMd || '').replace(/^\uFEFF/, '')
  if (!t.startsWith('---')) return ''
  const end = t.indexOf('\n---', 3)
  if (end === -1) return ''
  const block = t.slice(3, end)
  const m = /^description:\s*(.+)$/im.exec(block)
  if (!m) return ''
  let v = m[1].trim()
  if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'"))) v = v.slice(1, -1)
  return v.trim()
}

const cardStyle = {
  marginTop: 12,
  padding: 14,
  borderRadius: 8,
  background: 'rgba(0,0,0,0.25)',
  border: '1px solid rgba(148,163,184,0.15)',
}

const mono = {
  fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, monospace',
  fontSize: 12,
  color: '#94a3b8',
}

export default function OfficeOverview({ slug, active }) {
  const [detail, setDetail] = useState(null)
  const [loadErr, setLoadErr] = useState('')

  useEffect(() => {
    if (!active || !slug) return undefined
    let cancel = false
    setLoadErr('')
    fetchOfficeDetail(slug)
      .then((d) => {
        if (!cancel) setDetail(d)
      })
      .catch((e) => {
        if (!cancel) {
          setDetail(null)
          setLoadErr(e.message || String(e))
        }
      })
    return () => {
      cancel = true
    }
  }, [slug, active])

  if (!active) return null

  if (loadErr) {
    return (
      <p style={{ color: '#f87171', margin: 0 }} role="alert">
        Could not load office: {loadErr}
      </p>
    )
  }

  if (!detail) {
    return <p style={{ color: '#64748b', margin: 0 }}>Loading office snapshot…</p>
  }

  const roleNames = Object.keys(detail.roles || {}).sort()
  const desc = yamlDescription(detail.office_md)
  const firstTitle = /^#\s+(.+)$/m.exec(detail.office_md || '')
  const titleLine = firstTitle ? firstTitle[1].trim() : slug

  return (
    <div>
      <h2 style={{ margin: '0 0 8px', fontSize: '1.05rem', color: '#f1f5f9' }}>{titleLine}</h2>
      {desc ? (
        <p style={{ margin: '0 0 12px', color: '#cbd5e1', fontSize: 14 }}>
          <strong style={{ color: '#e2e8f0' }}>Description:</strong> {desc}
        </p>
      ) : null}

      <div style={cardStyle}>
        <div style={{ fontSize: 11, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', marginBottom: 8 }}>
          Role prompts ({roleNames.length})
        </div>
        <ul style={{ margin: 0, paddingLeft: 18, color: '#e2e8f0', lineHeight: 1.65 }}>
          {roleNames.map((rn) => (
            <li key={rn}>
              <code style={mono}>{rn}.md</code>
            </li>
          ))}
        </ul>
      </div>

      <div style={{ ...cardStyle, marginTop: 14 }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', marginBottom: 8 }}>
          Wardrobe data on disk (not streamed here)
        </div>
        <p style={{ margin: 0, color: '#94a3b8', fontSize: 13, lineHeight: 1.55 }}>
          Garment IDs and photo paths live in <code style={mono}>wardrobe_inventory.json</code> under{' '}
          <code style={mono}>custom_app/user_offices/{slug}/</code>. The API snapshot above does not include that JSON —
          edit it via <strong style={{ color: '#e2e8f0' }}>Custom App → Your Offices → {slug}</strong> (<em>Edit</em> /{' '}
          <em>AI Customize</em>) until this app grows a wardrobe editor (<code style={mono}>WARDROBE_STYLIST_IMPLEMENTATION_PLAN.md</code>{' '}
          §5 step 2).
        </p>
      </div>
    </div>
  )
}
