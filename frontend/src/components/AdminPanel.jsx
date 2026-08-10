import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Zap, Truck, Play, Square, AlertTriangle, History, ShieldCheck,
  CheckCircle2, XCircle, Loader2, FileText, Download, ChevronDown, RotateCcw,
} from 'lucide-react'

const PRESET_ZONES = ['KRM_01', 'KRM_02', 'BTM_01', 'HSR_01', 'IND_01']

const VEHICLE_TYPES = [
  { type: 'ambulance', emoji: '🚑', label: 'Ambulance' },
  { type: 'fire_truck', emoji: '🚒', label: 'Fire Truck' },
  { type: 'rescue', emoji: '🚐', label: 'Rescue Van' },
]

/**
 * A single collapsible section. Renders a compact header (icon, label,
 * one-line summary truncated to fit) that expands on click to reveal
 * the full controls. Keeps the panel scannable even with six distinct
 * tools stacked in one tab, instead of every section's full body text
 * and controls competing for space at once.
 */
function Section({ id, icon: Icon, label, summary, color, isOpen, onToggle, children, badge }) {
  return (
    <div className="rounded-xl overflow-hidden transition-all"
      style={{
        border: `1px solid ${isOpen ? `${color}40` : 'rgba(15,45,66,0.8)'}`,
        background: isOpen ? `${color}08` : 'rgba(13,36,56,0.5)',
      }}
    >
      <button
        onClick={() => onToggle(id)}
        className="w-full px-4 py-3 flex items-center gap-2.5 text-left transition-colors"
      >
        <Icon size={14} style={{ color, flexShrink: 0 }} />
        <span className="text-[11px] font-semibold tracking-[0.18em] shrink-0"
          style={{ color, fontFamily: "'JetBrains Mono', monospace" }}>
          {label}
        </span>
        {!isOpen && (
          <span className="text-[10px] truncate ml-1 min-w-0 flex-1" style={{ color: '#3D6678' }}>
            {summary}
          </span>
        )}
        {badge}
        <ChevronDown
          size={14}
          style={{
            color: '#3D6678', marginLeft: 'auto', flexShrink: 0,
            transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)',
            transition: 'transform 0.2s ease',
          }}
        />
      </button>
      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: 'easeInOut' }}
            style={{ overflow: 'hidden' }}
          >
            <div className="px-4 pb-4 pt-1" style={{ borderTop: `1px solid ${color}15` }}>
              {children}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

/**
 * AdminPanel — the "control room" surface used to drive the live demo.
 * Lets the operator trigger flood events in specific zones with a chosen
 * depth, add vehicles, run the cascade simulation, replay historical
 * events, generate incident reports, run live verification, and fire the
 * full pre-scripted demo sequence described in demo/demo_script.md.
 */
export default function AdminPanel({
  onTriggerFlood, onTriggerCascade, onAddVehicle, onRunScriptedDemo, demoRunning,
  scenarios = [], onRunHistoricalReplay, onCancelHistoricalReplay, replayRunning = null,
  onRunVerification, verifying = false, verificationReport = null,
  apiBase, onResetAll, resetting = false,
}) {
  const [zoneId, setZoneId] = useState(PRESET_ZONES[0])
  const [depth, setDepth] = useState(65)
  const [openSection, setOpenSection] = useState('flood')

  const severityColor = depth > 60 ? '#FF3B5C' : depth > 30 ? '#F59E0B' : '#00FF87'
  const severityLabel = depth > 60 ? 'CRITICAL' : depth > 30 ? 'MODERATE' : 'LOW'

  const toggle = (id) => setOpenSection((prev) => (prev === id ? null : id))

  return (
    <div className="flex flex-col h-full overflow-y-auto p-3 space-y-2">

      {/* Always-visible reset — findable instantly if a live demo gets
          into a confusing state, not buried inside a collapsed section. */}
      <motion.button
        onClick={onResetAll}
        disabled={resetting}
        whileHover={!resetting ? { scale: 1.01 } : {}}
        whileTap={!resetting ? { scale: 0.99 } : {}}
        className="w-full py-2 rounded-lg text-[10px] tracking-widest font-semibold transition-all flex items-center justify-center gap-1.5 shrink-0"
        style={{
          background: 'rgba(15,45,66,0.4)',
          border: '1px solid rgba(15,45,66,0.8)',
          color: resetting ? '#1E4A5E' : '#7BAABD',
          fontFamily: "'JetBrains Mono', monospace",
        }}
      >
        <RotateCcw size={11} className={resetting ? 'animate-spin' : ''} />
        {resetting ? 'RESETTING...' : 'RESET TO CLEAN STATE'}
      </motion.button>

      {/* Flood Simulation — opened by default since it's the most-used control */}
      <Section
        id="flood" icon={AlertTriangle} label="FLOOD SIM" color="#F59E0B"
        summary={`${zoneId} · ${depth}cm`}
        isOpen={openSection === 'flood'} onToggle={toggle}
      >
        <div className="space-y-3 pt-2">
          <label className="block">
            <span className="text-[10px] tracking-widest"
              style={{ color: '#3D6678', fontFamily: "'JetBrains Mono', monospace" }}>
              ZONE
            </span>
            <select
              value={zoneId}
              onChange={(e) => setZoneId(e.target.value)}
              className="mt-1 w-full rounded-lg px-3 py-2 text-sm"
              style={{
                background: 'rgba(7,21,32,0.6)',
                border: '1px solid rgba(15,45,66,0.8)',
                color: '#E8F4F8',
                fontFamily: "'JetBrains Mono', monospace",
              }}
            >
              {PRESET_ZONES.map((z) => (
                <option key={z} value={z}>{z}</option>
              ))}
            </select>
          </label>

          <label className="block">
            <div className="flex items-center justify-between">
              <span className="text-[10px] tracking-widest"
                style={{ color: '#3D6678', fontFamily: "'JetBrains Mono', monospace" }}>
                DEPTH: {depth} CM
              </span>
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full"
                style={{
                  color: severityColor, background: `${severityColor}15`,
                  border: `1px solid ${severityColor}40`,
                  fontFamily: "'JetBrains Mono', monospace",
                }}>
                {severityLabel}
              </span>
            </div>
            <input
              type="range"
              min={0}
              max={100}
              value={depth}
              onChange={(e) => setDepth(Number(e.target.value))}
              className="mt-2 w-full"
              style={{ accentColor: severityColor }}
            />
          </label>

          <motion.button
            onClick={() => onTriggerFlood(zoneId, depth)}
            whileHover={{ scale: 1.01 }}
            whileTap={{ scale: 0.99 }}
            className="w-full py-2.5 rounded-lg text-xs tracking-widest font-semibold transition-all"
            style={{
              background: `${severityColor}10`,
              border: `1px solid ${severityColor}40`,
              color: severityColor,
              fontFamily: "'JetBrains Mono', monospace",
            }}
          >
            TRIGGER FLOOD: {zoneId} @ {depth}CM
          </motion.button>

          <motion.button
            onClick={() => onTriggerCascade(zoneId, depth)}
            whileHover={{ scale: 1.01 }}
            whileTap={{ scale: 0.99 }}
            className="w-full py-2.5 rounded-lg text-xs tracking-widest font-semibold transition-all flex items-center justify-center gap-1.5"
            style={{
              background: 'rgba(0,245,255,0.06)',
              border: '1px solid rgba(0,245,255,0.3)',
              color: '#00F5FF',
              fontFamily: "'JetBrains Mono', monospace",
            }}
          >
            <Zap size={12} />
            SIMULATE CASCADE
          </motion.button>
          <p className="text-[10px] leading-relaxed" style={{ color: '#3D6678' }}>
            Floods {zoneId}, then the ML model picks which nearby zones flood next.
          </p>
        </div>
      </Section>

      {/* Dispatch Units */}
      <Section
        id="vehicles" icon={Truck} label="DISPATCH" color="#00D4AA"
        summary="Add ambulance, fire truck, rescue van"
        isOpen={openSection === 'vehicles'} onToggle={toggle}
      >
        <div className="flex gap-2 pt-2">
          {VEHICLE_TYPES.map((v) => (
            <motion.button
              key={v.type}
              onClick={() => onAddVehicle(v.type)}
              whileHover={{ scale: 1.03, y: -1 }}
              whileTap={{ scale: 0.97 }}
              className="flex-1 flex flex-col items-center gap-1.5 py-3 rounded-lg transition-all"
              style={{ background: 'rgba(7,21,32,0.6)', border: '1px solid rgba(15,45,66,0.8)' }}
            >
              <span className="text-2xl">{v.emoji}</span>
              <span className="text-[9px] font-semibold tracking-widest"
                style={{ color: '#7BAABD', fontFamily: "'JetBrains Mono', monospace" }}>
                {v.label.toUpperCase()}
              </span>
            </motion.button>
          ))}
        </div>
      </Section>

      {/* Scripted Demo */}
      <Section
        id="demo" icon={Zap} label="DEMO" color="#00F5FF"
        summary="Full judged demo sequence, one click"
        isOpen={openSection === 'demo'} onToggle={toggle}
        badge={demoRunning && (
          <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded-full shrink-0"
            style={{ color: '#FF3B5C', background: 'rgba(255,59,92,0.15)' }}>
            RUNNING
          </span>
        )}
      >
        <div className="pt-2">
          <p className="text-[11px] leading-relaxed mb-3" style={{ color: '#7BAABD' }}>
            Flood trigger → emergency rerouting → citizen route → ML forecast, fully automated.
          </p>
          <motion.button
            onClick={onRunScriptedDemo}
            disabled={demoRunning}
            whileHover={!demoRunning ? { scale: 1.02 } : {}}
            whileTap={!demoRunning ? { scale: 0.98 } : {}}
            className="w-full py-3 rounded-xl font-semibold text-sm tracking-widest
              flex items-center justify-center gap-2 transition-all"
            style={{
              background: demoRunning
                ? 'rgba(255,59,92,0.1)'
                : 'linear-gradient(135deg, rgba(0,245,255,0.25), rgba(0,212,170,0.15))',
              border: `1px solid ${demoRunning ? 'rgba(255,59,92,0.4)' : 'rgba(0,245,255,0.4)'}`,
              color: demoRunning ? '#FF3B5C' : '#00F5FF',
              fontFamily: "'JetBrains Mono', monospace",
            }}
          >
            {demoRunning ? (
              <><Square size={14} /> DEMO RUNNING...</>
            ) : (
              <><Play size={14} /> RUN DEMO SEQUENCE</>
            )}
          </motion.button>
        </div>
      </Section>

      {/* Historical Replay */}
      <Section
        id="replay" icon={History} label="REPLAY" color="#F59E0B"
        summary="Bengaluru 2022 / Chennai 2015"
        isOpen={openSection === 'replay'} onToggle={toggle}
        badge={replayRunning && (
          <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded-full shrink-0"
            style={{ color: '#F59E0B', background: 'rgba(245,158,11,0.15)' }}>
            PLAYING
          </span>
        )}
      >
        <div className="space-y-2 pt-2">
          <p className="text-[11px] leading-relaxed mb-2" style={{ color: '#7BAABD' }}>
            Real documented rainfall events, played back through the live system.
          </p>
          {scenarios.length === 0 && (
            <p className="text-[10px]" style={{ color: '#3D6678', fontFamily: "'JetBrains Mono', monospace" }}>
              Loading scenarios…
            </p>
          )}
          {scenarios.map((s) => {
            const isThisRunning = replayRunning === s.id
            const isOtherRunning = replayRunning !== null && replayRunning !== s.id
            return (
              <motion.button
                key={s.id}
                onClick={() => (isThisRunning ? onCancelHistoricalReplay() : onRunHistoricalReplay(s.id))}
                disabled={isOtherRunning}
                whileHover={!isOtherRunning ? { scale: 1.01 } : {}}
                whileTap={!isOtherRunning ? { scale: 0.99 } : {}}
                className="w-full flex items-center justify-between p-3 rounded-lg transition-all text-left"
                style={{
                  background: isThisRunning ? 'rgba(245,158,11,0.1)' : 'rgba(7,21,32,0.6)',
                  border: `1px solid ${isThisRunning ? 'rgba(245,158,11,0.4)' : 'rgba(15,45,66,0.8)'}`,
                  opacity: isOtherRunning ? 0.5 : 1,
                  cursor: isOtherRunning ? 'not-allowed' : 'pointer',
                }}
              >
                <div className="min-w-0">
                  <div className="text-xs font-semibold truncate" style={{ color: '#E8F4F8', fontFamily: "'JetBrains Mono', monospace" }}>
                    {s.label}
                  </div>
                  <div className="text-[10px] mt-0.5 truncate" style={{ color: '#3D6678' }}>
                    {s.summary}
                  </div>
                </div>
                <span className="text-[10px] font-semibold shrink-0 ml-3" style={{ color: isThisRunning ? '#FF3B5C' : '#F59E0B', fontFamily: "'JetBrains Mono', monospace" }}>
                  {isThisRunning ? 'STOP' : `▶ ${s.total_duration_s}s`}
                </span>
              </motion.button>
            )
          })}
        </div>
      </Section>

      {/* Incident Report */}
      <Section
        id="report" icon={FileText} label="REPORT" color="#0EA5E9"
        summary="Download structured incident summary"
        isOpen={openSection === 'report'} onToggle={toggle}
      >
        <div className="pt-2">
          <p className="text-[11px] leading-relaxed mb-3" style={{ color: '#7BAABD' }}>
            Current flood zones, vehicle status, and predictions — the NDMA-style data shape.
          </p>
          <motion.a
            href={`${apiBase}/incident-report/markdown`}
            download
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className="w-full py-3 rounded-xl font-semibold text-sm tracking-widest flex items-center justify-center gap-2 transition-all"
            style={{
              background: 'linear-gradient(135deg, rgba(14,165,233,0.25), rgba(0,212,170,0.15))',
              border: '1px solid rgba(14,165,233,0.4)',
              color: '#0EA5E9',
              fontFamily: "'JetBrains Mono', monospace",
              textDecoration: 'none',
            }}
          >
            <Download size={14} /> DOWNLOAD REPORT
          </motion.a>
        </div>
      </Section>

      {/* Judge Verification Mode */}
      <Section
        id="verify" icon={ShieldCheck} label="VERIFY" color="#00FF87"
        summary="Re-run the real test suite live"
        isOpen={openSection === 'verify'} onToggle={toggle}
        badge={verificationReport && !verifying && (
          <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded-full shrink-0"
            style={{
              color: verificationReport.all_passed ? '#00FF87' : '#FF3B5C',
              background: verificationReport.all_passed ? 'rgba(0,255,135,0.15)' : 'rgba(255,59,92,0.15)',
            }}>
            {verificationReport.all_passed ? 'PASSED' : 'FAILED'}
          </span>
        )}
      >
        <div className="pt-2">
          <p className="text-[11px] leading-relaxed mb-3" style={{ color: '#7BAABD' }}>
            Re-runs the graph load, routing engine, ML evaluation, and Chennai 2015 backtest — live, right now.
          </p>
          <motion.button
            onClick={onRunVerification}
            disabled={verifying}
            whileHover={!verifying ? { scale: 1.02 } : {}}
            whileTap={!verifying ? { scale: 0.98 } : {}}
            className="w-full py-3 rounded-xl font-semibold text-sm tracking-widest flex items-center justify-center gap-2 transition-all"
            style={{
              background: verifying ? 'rgba(15,45,66,0.5)' : 'linear-gradient(135deg, rgba(0,255,135,0.25), rgba(0,212,170,0.15))',
              border: `1px solid ${verifying ? 'rgba(15,45,66,0.8)' : 'rgba(0,255,135,0.4)'}`,
              color: verifying ? '#1E4A5E' : '#00FF87',
              fontFamily: "'JetBrains Mono', monospace",
            }}
          >
            {verifying ? (<><Loader2 size={14} className="animate-spin" /> RUNNING LIVE TESTS...</>) : (<><ShieldCheck size={14} /> RUN LIVE VERIFICATION</>)}
          </motion.button>

          {verificationReport && (
            <motion.div initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }} className="space-y-1.5 mt-3">
              {verificationReport.checks.map((check, i) => (
                <div key={i} className="flex items-center justify-between p-2 rounded-lg gap-2"
                  style={{ background: 'rgba(7,21,32,0.5)' }}>
                  <div className="flex items-center gap-2 min-w-0">
                    {check.passed
                      ? <CheckCircle2 size={12} style={{ color: '#00FF87', flexShrink: 0 }} />
                      : <XCircle size={12} style={{ color: '#FF3B5C', flexShrink: 0 }} />}
                    <div className="min-w-0">
                      <div className="text-[10px] font-semibold truncate" style={{ color: '#E8F4F8', fontFamily: "'JetBrains Mono', monospace" }}>
                        {check.name}
                      </div>
                      <div className="text-[9px] truncate" style={{ color: '#3D6678' }}>
                        {check.detail}
                      </div>
                    </div>
                  </div>
                  {check.ms != null && (
                    <span className="text-[9px] shrink-0" style={{ color: '#3D6678', fontFamily: "'JetBrains Mono', monospace" }}>
                      {check.ms}ms
                    </span>
                  )}
                </div>
              ))}
              <div className="text-[10px] text-center pt-1" style={{ color: verificationReport.all_passed ? '#00FF87' : '#FF3B5C', fontFamily: "'JetBrains Mono', monospace" }}>
                {verificationReport.all_passed ? '✓ ALL CHECKS PASSED' : '✗ SOME CHECKS FAILED'} · {verificationReport.total_ms}ms total
              </div>
            </motion.div>
          )}
        </div>
      </Section>
    </div>
  )
}
