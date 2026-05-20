/** Max decoded size per file (bytes) — overall upload cap before we read into memory */
export const CHAT_ATTACHMENT_MAX_BYTES = 28 * 1024 * 1024

/** Anthropic Messages API: each base64 image must be ≤ 5 MB decoded (see API error). */
const ANTHROPIC_IMAGE_MAX_BYTES = 5 * 1024 * 1024

const ALLOWED = new Set(['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'application/pdf'])

const RASTER = new Set(['image/jpeg', 'image/png', 'image/gif', 'image/webp'])

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

function decodedBase64Bytes(b64) {
  try {
    return atob(b64).length
  } catch {
    return Number.POSITIVE_INFINITY
  }
}

/**
 * Re-encode as JPEG via canvas until decoded size ≤ ANTHROPIC_IMAGE_MAX_BYTES.
 * Used for phone photos (often 6–15 MB) that exceed the API image cap.
 */
function shrinkRasterToAnthropicLimit(dataUrl, originalName) {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => {
      let w = img.naturalWidth || img.width
      let h = img.naturalHeight || img.height
      if (!w || !h) {
        reject(new Error('Invalid image dimensions.'))
        return
      }
      const maxDim = 4096
      if (w > maxDim || h > maxDim) {
        const s = maxDim / Math.max(w, h)
        w = Math.max(1, Math.round(w * s))
        h = Math.max(1, Math.round(h * s))
      }

      const canvas = document.createElement('canvas')
      const ctx = canvas.getContext('2d')
      if (!ctx) {
        reject(new Error('Could not prepare image canvas.'))
        return
      }

      let quality = 0.9

      const encode = () => {
        canvas.width = Math.max(1, w)
        canvas.height = Math.max(1, h)
        ctx.fillStyle = '#ffffff'
        ctx.fillRect(0, 0, canvas.width, canvas.height)
        ctx.drawImage(img, 0, 0, w, h)
        let jpegUrl
        try {
          jpegUrl = canvas.toDataURL('image/jpeg', quality)
        } catch {
          reject(new Error('Could not encode image (browser blocked canvas export).'))
          return
        }
        const b64 = jpegUrl.split(',')[1]
        const len = decodedBase64Bytes(b64)
        if (len <= ANTHROPIC_IMAGE_MAX_BYTES) {
          const base = originalName.replace(/\.[^.]+$/i, '') || 'image'
          resolve({ media_type: 'image/jpeg', data: b64, filename: `${base}.jpg` })
          return
        }
        if (quality > 0.45) {
          quality -= 0.06
          encode()
          return
        }
        quality = 0.9
        w = Math.max(1, Math.round(w * 0.8))
        h = Math.max(1, Math.round(h * 0.8))
        if (w < 320 && h < 320) {
          reject(
            new Error(
              'Could not shrink image under 5 MB (Anthropic limit). Try a smaller photo or export as JPEG.'
            )
          )
          return
        }
        encode()
      }

      encode()
    }
    img.onerror = () => reject(new Error('Could not decode image for resizing.'))
    img.src = dataUrl
  })
}

/**
 * Read a File into { media_type, data (raw base64), filename } for /api/chat.
 * Large raster images are automatically re-compressed to stay under Anthropic’s 5 MB image cap.
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

      ;(async () => {
        try {
          if (RASTER.has(media_type)) {
            const len = decodedBase64Bytes(data)
            if (len > ANTHROPIC_IMAGE_MAX_BYTES) {
              const shrunk = await shrinkRasterToAnthropicLimit(s, file.name)
              resolve(shrunk)
              return
            }
          }
          resolve({ media_type, data, filename: file.name })
        } catch (e) {
          reject(e instanceof Error ? e : new Error(String(e)))
        }
      })()
    }
    reader.onerror = () => reject(new Error(`Could not read "${file.name}".`))
    reader.readAsDataURL(file)
  })
}
