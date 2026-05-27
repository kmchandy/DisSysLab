/** Office slug under `custom_app/user_offices/` (and API name). */
export const WARDROBE_OFFICE_SLUG = 'wardrobe_assistant'

export async function fetchBackendOk() {
  const r = await fetch('/api/env')
  return r.ok
}

export async function fetchOfficesList() {
  const r = await fetch('/api/offices')
  if (!r.ok) throw new Error(`list offices: ${r.status}`)
  const data = await r.json()
  return data.offices ?? []
}

/** Raw office snapshot: office.md + roles/*.md (same payload as Custom App editor). */
export async function fetchOfficeDetail(name) {
  const r = await fetch(`/api/offices/${encodeURIComponent(name)}`)
  if (!r.ok) throw new Error(`${r.status}`)
  return r.json()
}

export async function runOffice(name) {
  const r = await fetch(`/api/offices/${encodeURIComponent(name)}/run`, { method: 'POST' })
  if (!r.ok) {
    let detail = `${r.status}`
    try {
      const j = await r.json()
      if (j.detail) detail = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail)
    } catch (_) {}
    throw new Error(detail)
  }
  return r.json()
}

export async function stopOffice(name) {
  const r = await fetch(`/api/offices/${encodeURIComponent(name)}/stop`, { method: 'POST' })
  if (!r.ok) throw new Error(`${r.status}`)
  return r.json()
}

export async function officeRunning(name) {
  const r = await fetch(`/api/offices/${encodeURIComponent(name)}/status`)
  if (!r.ok) return false
  const j = await r.json()
  return Boolean(j.running)
}

export function resolveMediaSrc(officeName, src) {
  if (!src || !officeName) return src || ''
  if (/^https?:\/\//i.test(src)) return src
  if (src.startsWith('/api/')) return src
  if (src.startsWith('media/')) {
    return `/api/offices/${encodeURIComponent(officeName)}/media/${src.slice('media/'.length)}`
  }
  return src
}
