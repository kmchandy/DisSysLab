import React from 'react'
import OfficeOverview from '../components/OfficeOverview.jsx'

export default function OfficeSnapshotTab({ slug }) {
  return (
    <div>
      <p style={{ color: '#94a3b8', marginTop: 0 }}>
        Read-only files from the API. Edit <code>office.md</code>, roles, and <code>wardrobe_inventory.json</code> via
        Custom App (<code>localhost:3000</code>).
      </p>
      <OfficeOverview slug={slug} active />
    </div>
  )
}
