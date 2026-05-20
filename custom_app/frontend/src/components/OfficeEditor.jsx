import React, { useEffect, useState } from 'react'

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    overflow: 'hidden',
  },
  header: {
    padding: '20px 24px 0',
    borderBottom: '1px solid var(--border)',
  },
  titleRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: '16px',
  },
  title: {
    fontSize: '17px',
    fontWeight: '700',
  },
  actions: {
    display: 'flex',
    gap: '8px',
  },
  saveBtn: {
    background: 'var(--accent)',
    color: '#fff',
    padding: '7px 16px',
    fontWeight: '600',
  },
  cancelBtn: {
    background: 'transparent',
    color: 'var(--text-muted)',
    border: '1px solid var(--border)',
    padding: '7px 16px',
  },
  tabs: {
    display: 'flex',
    gap: '2px',
    marginTop: '0',
  },
  tab: {
    padding: '8px 16px',
    fontSize: '13px',
    fontWeight: '500',
    borderRadius: '6px 6px 0 0',
    cursor: 'pointer',
    border: 'none',
    transition: 'background 0.1s',
  },
  body: {
    flex: 1,
    overflow: 'hidden',
    padding: '20px 24px',
    display: 'flex',
    flexDirection: 'column',
  },
  label: {
    fontSize: '11px',
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
    color: 'var(--text-muted)',
    marginBottom: '8px',
  },
  editor: {
    flex: 1,
    width: '100%',
    resize: 'none',
    fontFamily: 'var(--font-mono)',
    fontSize: '13px',
    lineHeight: '1.7',
    padding: '14px',
    borderRadius: '8px',
  },
  toast: {
    position: 'fixed',
    bottom: '24px',
    right: '24px',
    background: 'var(--success)',
    color: '#fff',
    padding: '10px 18px',
    borderRadius: '8px',
    fontSize: '13px',
    fontWeight: '500',
    zIndex: 1000,
    animation: 'fadeIn 0.2s ease',
  },
}

export default function OfficeEditor({ office, officeDetail, onSave, onCancel }) {
  const [activeTab, setActiveTab] = useState('office')
  const [officeMd, setOfficeMd] = useState('')
  const [roles, setRoles] = useState({})
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (officeDetail) {
      setOfficeMd(officeDetail.office_md || '')
      setRoles({ ...officeDetail.roles })
      setActiveTab('office')
    }
  }, [officeDetail])

  const handleSave = async () => {
    setSaving(true)
    try {
      const res = await fetch(`/api/offices/${office.name}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ office_md: officeMd, roles }),
      })
      if (!res.ok) throw new Error(await res.text())
      onSave()
      setSaved(true)
      setTimeout(() => setSaved(false), 2500)
    } catch (err) {
      alert('Save failed: ' + err.message)
    } finally {
      setSaving(false)
    }
  }

  const tabs = ['office', ...Object.keys(roles)]

  const currentContent = activeTab === 'office' ? officeMd : roles[activeTab] || ''
  const setCurrentContent = (val) => {
    if (activeTab === 'office') setOfficeMd(val)
    else setRoles(prev => ({ ...prev, [activeTab]: val }))
  }

  const tabLabel = (t) => t === 'office' ? 'office.md' : `roles/${t}.md`

  return (
    <div style={styles.container}>
      <style>{`@keyframes fadeIn { from { opacity:0; transform:translateY(8px) } to { opacity:1; transform:translateY(0) } }`}</style>

      <div style={styles.header}>
        <div style={styles.titleRow}>
          <div style={styles.title}>Edit — {office?.name}</div>
          <div style={styles.actions}>
            <button style={styles.cancelBtn} onClick={onCancel}>Cancel</button>
            <button style={styles.saveBtn} onClick={handleSave} disabled={saving}>
              {saving ? 'Saving…' : 'Save'}
            </button>
          </div>
        </div>
        <div style={styles.tabs}>
          {tabs.map(t => (
            <button
              key={t}
              onClick={() => setActiveTab(t)}
              style={{
                ...styles.tab,
                background: activeTab === t ? 'var(--surface2)' : 'transparent',
                color: activeTab === t ? 'var(--text)' : 'var(--text-muted)',
                borderBottom: activeTab === t ? '2px solid var(--accent)' : '2px solid transparent',
              }}
            >
              {tabLabel(t)}
            </button>
          ))}
        </div>
      </div>

      <div style={styles.body}>
        <div style={styles.label}>{tabLabel(activeTab)}</div>
        <textarea
          style={styles.editor}
          value={currentContent}
          onChange={e => setCurrentContent(e.target.value)}
          spellCheck={false}
        />
      </div>

      {saved && <div style={styles.toast}>Saved successfully</div>}
    </div>
  )
}
