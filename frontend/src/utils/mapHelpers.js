// Bengaluru default map center (Koramangala area) — matches backend BBOX center.
export const DEFAULT_CENTER = [12.935, 77.61]
export const DEFAULT_ZOOM = 14

/**
 * Maps a flood depth (cm) to a color + label, matching the backend's
 * flood_weights.py thresholds exactly:
 *   > 60cm  -> impassable (red)
 *   30-60cm -> passable but slow (amber)
 *   < 30cm  -> minor slowdown (teal/yellow-green)
 */
export function floodColor(depthCm) {
  if (depthCm > 60) return { color: '#FF5D5D', fill: '#FF5D5D', label: 'Impassable', severity: 'critical' }
  if (depthCm > 30) return { color: '#FFB648', fill: '#FFB648', label: 'Slow', severity: 'moderate' }
  if (depthCm > 0) return { color: '#FFE08A', fill: '#FFE08A', label: 'Minor', severity: 'minor' }
  return { color: '#1FB6A8', fill: '#1FB6A8', label: 'Clear', severity: 'clear' }
}

export function probabilityColor(p) {
  if (p >= 0.7) return '#FF5D5D'
  if (p >= 0.4) return '#FFB648'
  return '#1FB6A8'
}

export function vehicleIcon(type) {
  const icons = {
    ambulance: '🚑',
    fire_truck: '🚒',
    rescue: '🚐',
  }
  return icons[type] || '🚗'
}

export function formatEta(seconds) {
  if (seconds == null) return '—'
  const mins = Math.round(seconds / 60)
  if (mins < 1) return '<1 min'
  return `${mins} min`
}

export function formatDistance(meters) {
  if (meters == null) return '—'
  if (meters < 1000) return `${Math.round(meters)} m`
  return `${(meters / 1000).toFixed(1)} km`
}

/** Convert a list of [lat, lng] pairs to the [lat, lng] format react-leaflet expects (no-op helper kept for clarity at call sites). */
export function toLatLngs(coords) {
  return coords.map(([lat, lng]) => [lat, lng])
}
