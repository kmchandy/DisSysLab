import React, { useMemo } from 'react'
import ReactMarkdown from 'react-markdown'
import { resolveMediaSrc } from '../lib/api'
import { groupActivityImages, useWardrobeStream } from '../hooks/useWardrobeStream'

const rowStyle = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: 14,
  justifyContent: 'center',
  alignItems: 'flex-end',
  padding: '10px 4px',
}

const garmentImg = {
  display: 'block',
  flex: '0 1 auto',
  maxHeight: 220,
  maxWidth: 180,
  width: 'auto',
  objectFit: 'contain',
  borderRadius: 8,
  border: '1px solid rgba(148,163,184,0.25)',
  background: 'rgba(0,0,0,0.2)',
}

const cardStyle = {
  marginBottom: 14,
  paddingBottom: 12,
  borderBottom: '1px solid rgba(255,255,255,0.06)',
}

export default function StreamPanel({ officeName, running }) {
  const entries = useWardrobeStream(officeName, running)

  const mdComponents = useMemo(
    () => ({
      img: ({ src, alt }) => (
        <img
          src={resolveMediaSrc(officeName, src || '')}
          alt={alt || ''}
          title={alt || undefined}
          loading="lazy"
        />
      ),
      a: ({ href, children }) => (
        <a href={href} target="_blank" rel="noopener noreferrer">
          {children}
        </a>
      ),
    }),
    [officeName]
  )

  if (!running && entries.length === 0) {
    return (
      <p style={{ color: '#94a3b8', margin: 0 }}>
        Run the wardrobe office to stream calendar-linked outfit briefings here (same SSE as the Custom App).
      </p>
    )
  }

  return (
    <div>
      {groupActivityImages(entries).map((e) => {
        if (e.kind === 'log') {
          return (
            <pre
              key={e.id}
              style={{
                ...cardStyle,
                fontSize: 12,
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                color: '#cbd5e1',
                fontFamily: 'ui-monospace, monospace',
                margin: 0,
              }}
            >
              {e.text}
            </pre>
          )
        }
        if (e.kind === 'markdown') {
          return (
            <div key={e.id} style={cardStyle} className="wa-md">
              <ReactMarkdown components={mdComponents}>{e.body}</ReactMarkdown>
            </div>
          )
        }
        if (e.kind === 'image-row') {
          return (
            <div key={e.id} style={cardStyle} className="wa-md">
              <div style={rowStyle}>
                {e.imgs.map((im) => (
                  <img
                    key={im.id}
                    src={resolveMediaSrc(officeName, im.src)}
                    alt={im.alt || ''}
                    title={im.alt ? String(im.alt) : undefined}
                    style={garmentImg}
                    loading="lazy"
                  />
                ))}
              </div>
            </div>
          )
        }
        if (e.kind === 'image') {
          return (
            <div key={e.id} style={cardStyle} className="wa-md">
              <div style={rowStyle}>
                <img
                  src={resolveMediaSrc(officeName, e.src)}
                  alt={e.alt || ''}
                  title={e.alt ? String(e.alt) : undefined}
                  style={garmentImg}
                  loading="lazy"
                />
              </div>
            </div>
          )
        }
        return null
      })}
    </div>
  )
}
