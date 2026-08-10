import { useEffect, useState, useRef } from 'react'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const POLL_INTERVAL_MS = 4000

/**
 * Polls the backend's plain REST /health endpoint on a timer, completely
 * independent of the WebSocket connection. This exists specifically to
 * answer the question a confusing "RECONNECTING" label can't: is the
 * backend process not running at all, or is it running fine but the
 * WebSocket upgrade specifically is failing (e.g. a proxy stripping
 * upgrade headers, a wrong VITE_WS_URL, mixed http/https schemes)?
 *
 * Returns:
 *   reachable: true/false/null (null = first check still in flight)
 *   checkedAt: timestamp of the last check
 *   error: the actual fetch error message, for display
 */
export function useBackendHealth() {
  const [reachable, setReachable] = useState(null)
  const [checkedAt, setCheckedAt] = useState(null)
  const [error, setError] = useState(null)
  const timerRef = useRef(null)

  useEffect(() => {
    let cancelled = false

    const check = async () => {
      try {
        const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(3000) })
        if (cancelled) return
        if (res.ok) {
          setReachable(true)
          setError(null)
        } else {
          setReachable(false)
          setError(`Backend responded with HTTP ${res.status}`)
        }
      } catch (e) {
        if (cancelled) return
        setReachable(false)
        setError(
          e.name === 'TimeoutError' || e.name === 'AbortError'
            ? 'No response within 3s — backend likely not running'
            : `${e.message} — backend likely not running on ${API_BASE}`
        )
      } finally {
        if (!cancelled) setCheckedAt(Date.now())
      }
    }

    check()
    timerRef.current = setInterval(check, POLL_INTERVAL_MS)

    return () => {
      cancelled = true
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [])

  return { reachable, checkedAt, error, apiBase: API_BASE }
}
