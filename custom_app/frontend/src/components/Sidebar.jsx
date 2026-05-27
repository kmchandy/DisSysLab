import React from 'react'

const styles = {
  sidebar: {
    width: 'var(--sidebar-width)',
    minWidth: 'var(--sidebar-width)',
    background: 'var(--surface)',
    borderRight: '1px solid var(--border)',
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
  },
  header: {
    padding: '18px 16px 12px',
    borderBottom: '1px solid var(--border)',
  },
  logo: {
    fontSize: '15px',
    fontWeight: '700',
    color: 'var(--accent)',
    letterSpacing: '0.02em',
  },
  subtitle: {
    fontSize: '11px',
    color: 'var(--text-muted)',
    marginTop: '2px',
  },
  section: {
    padding: '10px 10px 4px',
    fontSize: '10px',
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
    color: 'var(--text-muted)',
  },
  list: {
    flex: 1,
    overflowY: 'auto',
    padding: '0 6px',
  },
  item: {
    padding: '8px 10px',
    borderRadius: '6px',
    cursor: 'pointer',
    transition: 'background 0.1s',
    marginBottom: '2px',
  },
  itemName: {
    fontSize: '13px',
    fontWeight: '500',
    color: 'var(--text)',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
  itemDesc: {
    fontSize: '11px',
    color: 'var(--text-muted)',
    marginTop: '2px',
    overflow: 'hidden',
    display: '-webkit-box',
    WebkitLineClamp: 2,
    WebkitBoxOrient: 'vertical',
  },
  newBtn: {
    margin: '10px',
    background: 'var(--accent)',
    color: '#fff',
    width: 'calc(100% - 20px)',
    padding: '9px',
    fontSize: '13px',
    fontWeight: '600',
  },
  dot: {
    display: 'inline-block',
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    background: 'var(--success)',
    marginLeft: '6px',
    verticalAlign: 'middle',
  },
}

export default function Sidebar({ offices, selected, onSelect, onNewOffice, runningOffices }) {
  const builtin = offices.filter(o => o.builtin)
  const custom = offices.filter(o => !o.builtin)

  const renderItem = (office) => {
    const isSelected = selected?.name === office.name
    const isRunning = runningOffices.has(office.name)
    return (
      <div
        key={office.name}
        style={{
          ...styles.item,
          background: isSelected ? 'var(--surface2)' : 'transparent',
          borderLeft: isSelected ? '2px solid var(--accent)' : '2px solid transparent',
        }}
        onClick={() => onSelect(office)}
        onMouseEnter={e => {
          if (!isSelected) e.currentTarget.style.background = 'rgba(255,255,255,0.04)'
        }}
        onMouseLeave={e => {
          if (!isSelected) e.currentTarget.style.background = 'transparent'
        }}
      >
        <div style={styles.itemName}>
          {office.name}
          {isRunning && <span style={styles.dot} title="Running" />}
        </div>
        {office.description && (
          <div style={styles.itemDesc}>{office.description}</div>
        )}
      </div>
    )
  }

  return (
    <div style={styles.sidebar}>
      <div style={styles.header}>
        <div style={styles.logo}>DisSysLab</div>
        <div style={styles.subtitle}>Office Manager</div>
      </div>

      <div style={styles.list}>
        {builtin.length > 0 && (
          <>
            <div style={styles.section}>Built-in</div>
            {builtin.map(renderItem)}
          </>
        )}
        {custom.length > 0 && (
          <>
            <div style={{ ...styles.section, marginTop: '8px' }}>Your Offices</div>
            {custom.map(renderItem)}
          </>
        )}
        {offices.length === 0 && (
          <div style={{ padding: '16px', color: 'var(--text-muted)', fontSize: '12px' }}>
            Loading offices…
          </div>
        )}
      </div>

      <button style={styles.newBtn} onClick={onNewOffice}>
        + New Office
      </button>
    </div>
  )
}
