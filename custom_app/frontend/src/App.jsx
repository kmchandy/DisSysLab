import React, { useCallback, useEffect, useState } from 'react'
import Sidebar from './components/Sidebar.jsx'
import OfficeView from './components/OfficeView.jsx'
import OfficeEditor from './components/OfficeEditor.jsx'
import ChatPanel from './components/ChatPanel.jsx'
import AIEditPanel from './components/AIEditPanel.jsx'

const styles = {
  app: {
    display: 'flex',
    height: '100vh',
    overflow: 'hidden',
  },
  main: {
    flex: 1,
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column',
  },
}

export default function App() {
  const [offices, setOffices] = useState([])
  const [selected, setSelected] = useState(null)
  const [officeDetail, setOfficeDetail] = useState(null)
  const [mode, setMode] = useState('view') // 'view' | 'edit'
  const [showChat, setShowChat] = useState(false)
  const [showAIEdit, setShowAIEdit] = useState(false)
  const [runningOffices, setRunningOffices] = useState(new Set())

  const fetchOffices = useCallback(async () => {
    try {
      const res = await fetch('/api/offices')
      const data = await res.json()
      setOffices(data.offices)
    } catch (e) {
      console.error('Failed to load offices', e)
    }
  }, [])

  useEffect(() => { fetchOffices() }, [fetchOffices])

  const fetchOfficeDetail = useCallback(async (name) => {
    try {
      const res = await fetch(`/api/offices/${name}`)
      const data = await res.json()
      setOfficeDetail(data)
    } catch (e) {
      console.error('Failed to load office detail', e)
    }
  }, [])

  const handleSelect = useCallback((office) => {
    setSelected(office)
    setMode('view')
    fetchOfficeDetail(office.name)
  }, [fetchOfficeDetail])

  const handleRun = useCallback(async () => {
    if (!selected) return
    try {
      await fetch(`/api/offices/${selected.name}/run`, { method: 'POST' })
      setRunningOffices(prev => new Set([...prev, selected.name]))
    } catch (e) {
      alert('Failed to start office: ' + e.message)
    }
  }, [selected])

  const handleStop = useCallback(async () => {
    if (!selected) return
    try {
      await fetch(`/api/offices/${selected.name}/stop`, { method: 'POST' })
      setRunningOffices(prev => {
        const next = new Set(prev)
        next.delete(selected.name)
        return next
      })
    } catch (e) {
      alert('Failed to stop office: ' + e.message)
    }
  }, [selected])

  const handleDelete = useCallback(async () => {
    if (!selected) return
    if (!window.confirm(`Delete "${selected.name}"? This cannot be undone.`)) return
    try {
      const res = await fetch(`/api/offices/${selected.name}`, { method: 'DELETE' })
      if (!res.ok) throw new Error(await res.text())
      setSelected(null)
      setOfficeDetail(null)
      setMode('view')
      fetchOffices()
    } catch (e) {
      alert('Delete failed: ' + e.message)
    }
  }, [selected, fetchOffices])

  const handleClone = useCallback(async (newName, mode = 'edit') => {
    if (!selected) return
    try {
      const res = await fetch(`/api/offices/${selected.name}/clone`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_name: newName || '' }),
      })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      await fetchOffices()
      const cloned = { name: data.name, builtin: false, description: '' }
      setSelected(cloned)
      fetchOfficeDetail(data.name)
      if (mode === 'ai') {
        setMode('view')
        setShowAIEdit(true)
      } else {
        setMode('edit')
      }
    } catch (e) {
      alert('Clone failed: ' + e.message)
    }
  }, [selected, fetchOffices, fetchOfficeDetail])

  const handleSave = useCallback(() => {
    if (selected) fetchOfficeDetail(selected.name)
    setMode('view')
  }, [selected, fetchOfficeDetail])

  const handleOfficeCreated = useCallback((name) => {
    setShowChat(false)
    fetchOffices().then(() => {
      const newOffice = { name, builtin: false, description: '' }
      setSelected(newOffice)
      fetchOfficeDetail(name)
      setMode('view')
    })
  }, [fetchOffices, fetchOfficeDetail])

  const isRunning = selected ? runningOffices.has(selected.name) : false

  return (
    <div style={styles.app}>
      <Sidebar
        offices={offices}
        selected={selected}
        onSelect={handleSelect}
        onNewOffice={() => setShowChat(true)}
        runningOffices={runningOffices}
      />

      <div style={styles.main}>
        {mode === 'view' ? (
          <OfficeView
            office={selected}
            officeDetail={officeDetail}
            running={isRunning}
            onRun={handleRun}
            onStop={handleStop}
            onEdit={() => setMode('edit')}
            onClone={handleClone}
            onDelete={handleDelete}
            onAIEdit={() => setShowAIEdit(true)}
          />
        ) : (
          <OfficeEditor
            office={selected}
            officeDetail={officeDetail}
            onSave={handleSave}
            onCancel={() => setMode('view')}
          />
        )}
      </div>

      {showChat && (
        <ChatPanel
          onClose={() => setShowChat(false)}
          onOfficeCreated={handleOfficeCreated}
        />
      )}

      {showAIEdit && selected && (
        <AIEditPanel
          office={selected}
          onClose={() => setShowAIEdit(false)}
          onSaved={() => {
            fetchOfficeDetail(selected.name)
            setShowAIEdit(false)
          }}
        />
      )}
    </div>
  )
}
