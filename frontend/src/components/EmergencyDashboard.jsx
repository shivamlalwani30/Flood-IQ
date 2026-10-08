import { motion, AnimatePresence } from 'framer-motion'
import { Navigation, AlertCircle, Loader2 } from 'lucide-react'
import { formatEta, formatDistance, vehicleIcon } from '../utils/mapHelpers'

/**
 * EmergencyDashboard — right-rail panel for the dispatcher view.
 * Lists active emergency vehicles, lets dispatcher select one, shows
 * current route stats, and exposes the "Recalculate Route" action that
 * is central to the live demo (step [0:25] in the demo script).
 */
export default function EmergencyDashboard({
  vehicles = [],
  selectedVehicleId,
  onSelectVehicle,
  onRecalculate,
  recalculating = false,
  lastRecalcMs = null,
  connected,
  routeComparison = null,
  edgeWeightChanges = [],
}) {
  const selected = vehicles.find((v) => v.id === selectedVehicleId)

  return (
    <div className="flex flex-col h-full">

      {/* Header */}
      <div className="px-4 py-3 border-b border-border-primary flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <Navigation size={14} style={{ color: '#00F5FF' }} />
          <span className="text-[11px] font-semibold tracking-[0.2em]"
            style={{ color: '#7BAABD', fontFamily: "'JetBrains Mono', monospace" }}>
            ACTIVE UNITS
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className={`w-1.5 h-1.5 rounded-full ${connected ? 'dot-pulse' : ''}`}
            style={{ background: connected ? '#00F5FF' : '#FF3B5C' }} />
          <span className="text-[10px]"
            style={{ color: connected ? '#00F5FF' : '#FF3B5C', fontFamily: "'JetBrains Mono', monospace" }}>
            {connected ? 'LIVE' : 'OFFLINE'}
          </span>
        </div>
      </div>

      {/* Vehicle List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        <AnimatePresence>
          {vehicles.length === 0 ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex flex-col items-center justify-center h-32 gap-2"
            >
              <AlertCircle size={24} style={{ color: '#1E4A5E' }} />
              <span className="text-xs" style={{ color: '#3D6678', fontFamily: "'JetBrains Mono', monospace" }}>
                NO UNITS DISPATCHED
              </span>
            </motion.div>
          ) : (
            vehicles.map((v, i) => {
              const isSelected = v.id === selectedVehicleId
              const isBlocked = v.status === 'blocked'
              const isIdle = v.status === 'idle'
              const statusColor = isBlocked ? '#FF3B5C' : isIdle ? '#7BAABD' : '#00F5FF'

              return (
                <motion.button
                  key={v.id}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.05 }}
                  onClick={() => onSelectVehicle(v.id)}
                  whileHover={{ scale: 1.01, x: 2 }}
                  whileTap={{ scale: 0.99 }}
                  className="w-full text-left rounded-xl p-3 transition-all"
                  style={{
                    background: isSelected
                      ? `rgba(0,245,255,0.08)`
                      : 'rgba(13,36,56,0.6)',
                    border: `1px solid ${isSelected ? 'rgba(0,245,255,0.3)' : 'rgba(15,45,66,0.8)'}`,
                    boxShadow: isSelected ? '0 0 20px rgba(0,245,255,0.08)' : 'none',
                  }}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-xl">{vehicleIcon(v.type)}</span>
                      <span className="text-sm font-semibold"
                        style={{ color: '#E8F4F8', fontFamily: "'JetBrains Mono', monospace" }}>
                        {v.id}
                      </span>
                    </div>
                    <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full"
                      style={{
                        color: statusColor,
                        background: `${statusColor}15`,
                        border: `1px solid ${statusColor}40`,
                        fontFamily: "'JetBrains Mono', monospace"
                      }}>
                      {isBlocked ? '⚠ BLOCKED' : isIdle ? '○ STANDBY' : '● EN ROUTE'}
                    </span>
                  </div>

                  <div className="flex gap-4">
                    <div>
                      <div className="text-[9px] tracking-widest mb-0.5"
                        style={{ color: '#3D6678', fontFamily: "'JetBrains Mono', monospace" }}>
                        ETA
                      </div>
                      <div className="text-xs font-medium"
                        style={{ color: '#7BAABD', fontFamily: "'JetBrains Mono', monospace" }}>
                        {formatEta(v.eta_seconds)}
                      </div>
                    </div>
                    <div>
                      <div className="text-[9px] tracking-widest mb-0.5"
                        style={{ color: '#3D6678', fontFamily: "'JetBrains Mono', monospace" }}>
                        DIST
                      </div>
                      <div className="text-xs font-medium"
                        style={{ color: '#7BAABD', fontFamily: "'JetBrains Mono', monospace" }}>
                        {formatDistance(v.distance_m)}
                      </div>
                    </div>
                  </div>
                </motion.button>
              )
            })
          )}
        </AnimatePresence>
      </div>

      {/* Action Panel */}
      <div className="p-4 border-t border-border-primary space-y-3 shrink-0">
        {selected && (
          <motion.div
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-lg p-3"
            style={{ background: 'rgba(0,245,255,0.04)', border: '1px solid rgba(0,245,255,0.1)' }}
          >
            <div className="text-[10px] tracking-widest mb-1.5"
              style={{ color: '#3D6678', fontFamily: "'JetBrains Mono', monospace" }}>
              SELECTED UNIT
            </div>
            <div className="text-sm font-semibold"
              style={{ color: '#00F5FF', fontFamily: "'JetBrains Mono', monospace" }}>
              {selected.id}
            </div>
            <div className="text-xs mt-0.5"
              style={{ color: '#7BAABD', fontFamily: "'JetBrains Mono', monospace" }}>
              {selected.destination_label || 'Destination pending'}
            </div>
          </motion.div>
        )}

        <motion.button
          onClick={() => onRecalculate()}
          disabled={!selected || recalculating}
          whileHover={selected && !recalculating ? { scale: 1.02 } : {}}
          whileTap={selected && !recalculating ? { scale: 0.98 } : {}}
          className="w-full py-3 rounded-xl font-semibold text-sm tracking-widest
            transition-all flex items-center justify-center gap-2"
          style={{
            background: (!selected || recalculating)
              ? 'rgba(15,45,66,0.5)'
              : 'linear-gradient(135deg, rgba(0,245,255,0.2), rgba(0,212,170,0.2))',
            border: `1px solid ${(!selected || recalculating) ? 'rgba(15,45,66,0.8)' : 'rgba(0,245,255,0.4)'}`,
            color: (!selected || recalculating) ? '#1E4A5E' : '#00F5FF',
            boxShadow: (!selected || recalculating) ? 'none' : '0 0 20px rgba(0,245,255,0.1)',
            fontFamily: "'JetBrains Mono', monospace",
            cursor: (!selected || recalculating) ? 'not-allowed' : 'pointer',
          }}
        >
          {recalculating ? (
            <>
              <Loader2 size={14} className="animate-spin" />
              RECALCULATING...
            </>
          ) : (
            <>
              <Navigation size={14} />
              RECALCULATE ROUTE
            </>
          )}
        </motion.button>

        {routeComparison && (
          <motion.div
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-lg p-3"
            style={{ background: 'rgba(255,59,92,0.06)', border: '1px solid rgba(255,59,92,0.2)' }}
          >
            <div className="text-[10px] tracking-widest mb-1.5 flex items-center gap-1.5"
              style={{ color: '#FF3B5C', fontFamily: "'JetBrains Mono', monospace" }}>
              <AlertCircle size={11} />
              ROUTE COMPARISON
            </div>
            <div className="text-xs" style={{ color: '#7BAABD' }}>
              The original route crossed an active flood zone.{' '}
              <span style={{ color: '#E8F4F8', fontWeight: 600 }}>
                +{Math.max(0, Math.round(routeComparison.extraSeconds / 60))} min
              </span>
              {' '}detour avoids it entirely.
            </div>
          </motion.div>
        )}

        {edgeWeightChanges.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-lg p-3"
            style={{ background: 'rgba(0,245,255,0.04)', border: '1px solid rgba(0,245,255,0.15)' }}
          >
            <div className="text-[10px] tracking-widest mb-2"
              style={{ color: '#00F5FF', fontFamily: "'JetBrains Mono', monospace" }}>
              ALGORITHM TRACE — DIJKSTRA EDGE WEIGHTS
            </div>
            <div className="space-y-1.5">
              {edgeWeightChanges.slice(0, 4).map((c, i) => (
                <div key={i} className="text-[10px] flex items-center justify-between"
                  style={{ fontFamily: "'JetBrains Mono', monospace", color: '#7BAABD' }}>
                  <span>{c.from_node}→{c.to_node}: {c.base_length_m}m</span>
                  <span style={{ color: c.multiplier.includes('∞') ? '#FF3B5C' : '#F59E0B' }}>
                    × {c.multiplier}
                  </span>
                </div>
              ))}
            </div>
            {edgeWeightChanges.length > 4 && (
              <div className="text-[9px] mt-1.5" style={{ color: '#3D6678' }}>
                +{edgeWeightChanges.length - 4} more affected edge{edgeWeightChanges.length - 4 > 1 ? 's' : ''}
              </div>
            )}
          </motion.div>
        )}

        {lastRecalcMs != null && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-center"
            style={{ fontFamily: "'JetBrains Mono', monospace" }}
          >
            <span className="text-[10px]" style={{ color: '#3D6678' }}>
              Recalculated in{' '}
            </span>
            <span className="text-[10px] font-semibold" style={{ color: '#00D4AA' }}>
              {(lastRecalcMs / 1000).toFixed(2)}s
            </span>
            <span className="text-[10px]" style={{ color: '#00D4AA' }}> ⚡</span>
          </motion.div>
        )}
      </div>
    </div>
  )
}
