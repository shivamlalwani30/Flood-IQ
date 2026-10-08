import { useState } from 'react'
import { motion } from 'framer-motion'
import { Navigation2, AlertTriangle } from 'lucide-react'
import { formatEta, formatDistance } from '../utils/mapHelpers'

/**
 * CitizenView — the second user persona. Origin + destination text inputs,
 * "Find safe route" action, and a result card showing the route that
 * avoids active flood zones. Deliberately minimal: 3 clicks to a safe route
 * (origin -> destination -> find), matching the Usability scorecard target.
 */
export default function CitizenView({ onFindRoute, result, loading, error, avoidedZoneCount }) {
  const [origin, setOrigin] = useState('Koramangala')
  const [destination, setDestination] = useState('Manipal Hospital')

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 py-3 border-b border-border-primary">
        <h2 className="text-[11px] font-semibold tracking-[0.2em]"
          style={{ color: '#7BAABD', fontFamily: "'JetBrains Mono', monospace" }}>
          FIND A SAFE ROUTE
        </h2>
        <p className="text-xs mt-1" style={{ color: '#3D6678' }}>
          We'll route you around flooded roads, not just the fastest path.
        </p>
      </div>

      <div className="p-4 space-y-3">
        <Field label="From" value={origin} onChange={setOrigin} />
        <Field label="To" value={destination} onChange={setDestination} />

        <motion.button
          onClick={() => onFindRoute(origin, destination)}
          disabled={loading || !origin || !destination}
          whileHover={!loading && origin && destination ? { scale: 1.02 } : {}}
          whileTap={!loading && origin && destination ? { scale: 0.98 } : {}}
          className="w-full py-3 rounded-xl font-semibold text-sm tracking-widest transition-all"
          style={{
            background: (loading || !origin || !destination)
              ? 'rgba(15,45,66,0.5)'
              : 'linear-gradient(135deg, rgba(0,245,255,0.2), rgba(0,212,170,0.2))',
            border: `1px solid ${(loading || !origin || !destination) ? 'rgba(15,45,66,0.8)' : 'rgba(0,245,255,0.4)'}`,
            color: (loading || !origin || !destination) ? '#1E4A5E' : '#00F5FF',
            fontFamily: "'JetBrains Mono', monospace",
            cursor: (loading || !origin || !destination) ? 'not-allowed' : 'pointer',
          }}
        >
          {loading ? 'FINDING SAFE ROUTE…' : 'FIND SAFE ROUTE'}
        </motion.button>
      </div>

      {error && !loading && (
        <div className="px-4 pb-4">
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-xl p-3 space-y-1.5"
            style={{ background: 'rgba(255,59,92,0.08)', border: '1px solid rgba(255,59,92,0.3)' }}
          >
            <div className="flex items-center gap-2">
              <AlertTriangle size={14} style={{ color: '#FF3B5C' }} />
              <span className="text-sm font-medium" style={{ color: '#FF3B5C' }}>Couldn't find a route</span>
            </div>
            <div className="text-xs" style={{ color: '#7BAABD' }}>
              {error}
            </div>
          </motion.div>
        </div>
      )}

      {result && !error && (
        <div className="px-4 pb-4">
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-xl p-3 space-y-2"
            style={{ background: 'rgba(13,36,56,0.6)', border: '1px solid rgba(15,45,66,0.8)' }}
          >
            <div className="flex items-center gap-2">
              <Navigation2 size={14} style={{ color: '#00F5FF' }} />
              <span className="text-sm font-medium" style={{ color: '#E8F4F8' }}>Safe route found</span>
            </div>
            <div className="flex items-center gap-4 text-xs"
              style={{ color: '#7BAABD', fontFamily: "'JetBrains Mono', monospace" }}>
              <span>ETA {formatEta(result.eta_seconds)}</span>
              <span>{formatDistance(result.distance_m)}</span>
            </div>
            {avoidedZoneCount > 0 && (
              <div className="text-xs flex items-center gap-1.5" style={{ color: '#F59E0B' }}>
                <AlertTriangle size={12} />
                <span>Avoided {avoidedZoneCount} flooded zone{avoidedZoneCount > 1 ? 's' : ''} on the fastest path</span>
              </div>
            )}
          </motion.div>
        </div>
      )}
    </div>
  )
}

function Field({ label, value, onChange }) {
  return (
    <label className="block">
      <span className="text-[10px] tracking-widest"
        style={{ color: '#3D6678', fontFamily: "'JetBrains Mono', monospace" }}>
        {label.toUpperCase()}
      </span>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full rounded-lg px-3 py-2 text-sm focus:outline-none transition-all"
        style={{
          background: 'rgba(7,21,32,0.6)',
          border: '1px solid rgba(15,45,66,0.8)',
          color: '#E8F4F8',
        }}
        placeholder={label === 'From' ? 'Enter starting point' : 'Enter destination'}
      />
    </label>
  )
}
