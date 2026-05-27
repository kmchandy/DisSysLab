import React, { useCallback, useEffect, useState } from 'react'
import CalendarPipelineTab from './tabs/CalendarPipelineTab.jsx'
import OccasionOutfitsTab from './tabs/OccasionOutfitsTab.jsx'
import ClosetStacksTab from './tabs/ClosetStacksTab.jsx'
import OutfitHistoryTab from './tabs/OutfitHistoryTab.jsx'
import ShoppingTab from './tabs/ShoppingTab.jsx'
import OfficeSnapshotTab from './tabs/OfficeSnapshotTab.jsx'
import {
  WARDROBE_OFFICE_SLUG,
  fetchBackendOk,
  fetchOfficesList,
  runOffice,
  stopOffice,
  officeRunning,
} from './lib/api.js'

const SLUG = WARDROBE_OFFICE_SLUG

const NAV = [
  { id: 'calendar', label: 'Calendar office' },
  { id: 'occasion', label: 'Occasion outfits' },
  { id: 'closet', label: 'Closet stacks' },
  { id: 'history', label: 'Outfit history' },
  { id: 'shopping', label: 'Shopping advisor' },
  { id: 'office', label: 'Office snapshot' },
]

export default function App() {
  const [page, setPage] = useState('occasion')
  const [apiOk, setApiOk] = useState(null)
  const [hasOffice, setHasOffice] = useState(null)
  const [running, setRunning] = useState(false)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  const refresh = useCallback(async () => {
    setErr('')
    try {
      const ok = await fetchBackendOk()
      setApiOk(ok)
      if (!ok) {
        setHasOffice(false)
        return
      }
      const offices = await fetchOfficesList()
      const names = new Set(offices.map((o) => o.name))
      setHasOffice(names.has(SLUG))
      const st = await officeRunning(SLUG)
      setRunning(st)
    } catch (e) {
      setApiOk(false)
      setErr(e.message || String(e))
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  const onRun = async () => {
    setBusy(true)
    setErr('')
    try {
      await runOffice(SLUG)
      setRunning(true)
    } catch (e) {
      setErr(e.message || String(e))
    } finally {
      setBusy(false)
    }
  }

  const onStop = async () => {
    setBusy(true)
    setErr('')
    try {
      await stopOffice(SLUG)
    } catch {
      /* not running → 404 */
    } finally {
      setRunning(false)
      setBusy(false)
    }
  }

  return (
    <div className="wa-shell">
      <aside className="wa-nav-col">
        <div className="wa-brand">
          <div className="wa-brand-title">Wardrobe Assistant</div>
          <div className="wa-brand-meta">
            <span className={`wa-chip ${apiOk ? 'wa-chip-ok' : 'wa-chip-bad'}`}>
              {apiOk == null ? 'API …' : apiOk ? 'API online' : 'API offline'}
            </span>
            {hasOffice === false && apiOk ? <span className="wa-chip wa-chip-warn">Office missing</span> : null}
          </div>
        </div>
        <nav className="wa-nav">
          {NAV.map(({ id, label }) => (
            <button
              key={id}
              type="button"
              className={`wa-nav-btn ${page === id ? 'wa-nav-btn-active' : ''}`}
              onClick={() => setPage(id)}
            >
              {label}
            </button>
          ))}
        </nav>
        <p className="wa-mini">
          User office{' '}
          <code>{SLUG}</code>
          <br />
          Primary flows use <strong>ANTHROPIC_API_KEY</strong> on backend.
          <br />
          Custom App: <code>:3000</code> · This app <code>:5173</code>
        </p>
      </aside>
      <main className="wa-main">
        {err ? (
          <p className="wa-alert" role="alert">
            {err}
          </p>
        ) : null}
        {page === 'calendar' && (
          <CalendarPipelineTab
            slug={SLUG}
            hasOffice={hasOffice}
            running={running}
            busy={busy}
            onRun={onRun}
            onStop={onStop}
            onRefresh={refresh}
            apiOk={apiOk}
          />
        )}
        {page === 'occasion' && <OccasionOutfitsTab slug={SLUG} />}
        {page === 'closet' && <ClosetStacksTab slug={SLUG} />}
        {page === 'history' && <OutfitHistoryTab slug={SLUG} />}
        {page === 'shopping' && <ShoppingTab slug={SLUG} />}
        {page === 'office' && <OfficeSnapshotTab slug={SLUG} />}
      </main>
    </div>
  )
}
