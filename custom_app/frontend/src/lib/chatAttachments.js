/** Max decoded size per file (bytes) — keep under typical API limits */
export const CHAT_ATTACHMENT_MAX_BYTES = 28 * 1024 * 1024

const ALLOWED = new Set(['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'application/pdf'])

function inferMime(file) {
  const t = (file.type || '').trim().toLowerCase()
  if (t) return t
  const n = file.name.toLowerCase()
  if (n.endsWith('.pdf')) return 'application/pdf'
  if (n.endsWith('.png')) return 'image/png'
  if (n.endsWith('.gif')) return 'image/gif'
  if (n.endsWith('.webp')) return 'image/webp'
  if (n.endsWith('.jpg') || n.endsWith('.jpeg')) return 'image/jpeg'
  return ''
}

/**
 * Read a File into { media_type, data (raw base64), filename } for /api/chat.
 */
export function fileToAttachment(file) {
  return new Promise((resolve, reject) => {
    if (file.size > CHAT_ATTACHMENT_MAX_BYTES) {
      reject(new Error(`"${file.name}" is too large (max ${CHAT_ATTACHMENT_MAX_BYTES / (1024 * 1024)} MB).`))
      return
    }
    const media_type = inferMime(file)
    if (!ALLOWED.has(media_type)) {
      reject(
        new Error(
          `"${file.name}" has type "${media_type || 'unknown'}". Use JPEG, PNG, GIF, WebP, or PDF.`
        )
      )
      return
    }
    const reader = new FileReader()
    reader.onload = () => {
      const s = String(reader.result || '')
      const i = s.indexOf(',')
      const data = i >= 0 ? s.slice(i + 1) : s
      resolve({ media_type, data, filename: file.name })
    }
    reader.onerror = () => reject(new Error(`Could not read "${file.name}".`))
    reader.readAsDataURL(file)
  })
}
