import { useEffect, useRef, useState, useCallback } from 'react'

let _id = 0
const nextId = () => ++_id

/** Group consecutive image blocks (dedupe adjacent same src). */
export function groupActivityImages(entries) {
  const rows = []
  let i = 0
  while (i < entries.length) {
    const e = entries[i]
    if (e.kind === 'image') {
      const imgs = []
      while (i < entries.length && entries[i].kind === 'image') {
        const cur = entries[i]
        const prev = imgs[imgs.length - 1]
        if (!prev || prev.src !== cur.src) imgs.push(cur)
        i++
      }
      if (imgs.length > 0) rows.push({ kind: 'image-row', id: imgs[0].id, imgs })
      continue
    }
    rows.push(e)
    i++
  }
  return rows
}

export function useWardrobeStream(officeName, running) {
  const [entries, setEntries] = useState([])
  const esRef = useRef(null)

  const appendLog = useCallback((text) => {
    const t = typeof text === 'string' ? text : String(text)
    setEntries((prev) => [...prev, { id: nextId(), kind: 'log', text: t }])
  }, [])

  const appendBlock = useCallback((obj) => {
    const k = obj?.kind
    if (k === 'markdown' && obj.body != null) {
      setEntries((prev) => [
        ...prev,
        { id: nextId(), kind: 'markdown', body: String(obj.body), source: obj.source },
      ])
      return
    }
    if (k === 'image' && obj.src) {
      setEntries((prev) => [
        ...prev,
        {
          id: nextId(),
          kind: 'image',
          src: String(obj.src),
          alt: String(obj.alt || ''),
        },
      ])
      return
    }
    if (k === 'json') {
      appendLog(JSON.stringify(obj.data, null, 2))
      return
    }
    appendLog(typeof obj === 'string' ? obj : JSON.stringify(obj))
  }, [appendLog])

  useEffect(() => {
    if (!officeName || !running) {
      if (esRef.current) {
        esRef.current.close()
        esRef.current = null
      }
      return undefined
    }

    setEntries([])

    const es = new EventSource(`/api/offices/${encodeURIComponent(officeName)}/output`)
    esRef.current = es

    const onLog = (e) => {
      let text = e.data
      try {
        const o = JSON.parse(e.data)
        if (o && typeof o.text === 'string') text = o.text
      } catch (_) {}
      appendLog(text)
    }

    const onBlock = (e) => {
      try {
        const o = JSON.parse(e.data)
        appendBlock(o)
      } catch {
        appendLog(e.data)
      }
    }

    es.addEventListener('log', onLog)
    es.addEventListener('block', onBlock)
    es.onerror = () => {
      es.close()
      esRef.current = null
    }

    return () => {
      es.removeEventListener('log', onLog)
      es.removeEventListener('block', onBlock)
      es.close()
      esRef.current = null
    }
  }, [officeName, running, appendLog, appendBlock])

  return entries
}
