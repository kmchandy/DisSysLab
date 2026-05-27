import { WARDROBE_OFFICE_SLUG } from './api.js'

export function wardrobeRoot(slug = WARDROBE_OFFICE_SLUG) {
  return `/api/offices/${encodeURIComponent(slug)}/wardrobe`
}

export async function getWardrobeState(slug) {
  const r = await fetch(`${wardrobeRoot(slug)}/state`)
  if (!r.ok) throw new Error((await r.text()) || `${r.status}`)
  return r.json()
}

export async function putWardrobeState(slug, state) {
  const r = await fetch(`${wardrobeRoot(slug)}/state`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ state }),
  })
  if (!r.ok) throw new Error((await r.text()) || `${r.status}`)
  return r.json()
}

export async function occasionChat(slug, { occasion, notes }) {
  const r = await fetch(`${wardrobeRoot(slug)}/occasion-chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ occasion, notes }),
  })
  if (!r.ok) throw new Error((await r.text()) || `${r.status}`)
  return r.json()
}

export async function pickOccasionOutfit(slug, body) {
  const r = await fetch(`${wardrobeRoot(slug)}/pick-outfit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!r.ok) throw new Error((await r.text()) || `${r.status}`)
  return r.json()
}

export async function launderItems(slug, item_ids) {
  const r = await fetch(`${wardrobeRoot(slug)}/launder`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ item_ids }),
  })
  if (!r.ok) throw new Error((await r.text()) || `${r.status}`)
  return r.json()
}

export async function shoppingBlind(slug, style_notes) {
  const r = await fetch(`${wardrobeRoot(slug)}/shopping/blind`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ style_notes }),
  })
  if (!r.ok) throw new Error((await r.text()) || `${r.status}`)
  return r.json()
}

export async function shoppingEvaluate(slug, { note, files }) {
  const fd = new FormData()
  fd.append('note', note || '')
  for (const f of files) fd.append('images', f)
  const r = await fetch(`${wardrobeRoot(slug)}/shopping/evaluate`, { method: 'POST', body: fd })
  if (!r.ok) throw new Error((await r.text()) || `${r.status}`)
  return r.json()
}
