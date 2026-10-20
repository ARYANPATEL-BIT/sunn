// Sunn client-side display and accessibility preferences.
// Stored in localStorage so they persist across sessions and reloads.

const PREF_KEYS = {
  largeText: 'sunn.large_text',
  reducedMotion: 'sunn.reduced_motion',
  enhancedFocus: 'sunn.enhanced_focus',
}

export function getSystemReducedMotion() {
  if (typeof window === 'undefined' || !window.matchMedia) return false
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

export function getPreferences() {
  try {
    const largeText = localStorage.getItem(PREF_KEYS.largeText) === 'true'
    const storedMotion = localStorage.getItem(PREF_KEYS.reducedMotion)
    // If system reduced motion is active, motion stays reduced.
    // If not, use user in-app preference.
    const reducedMotion = getSystemReducedMotion() || storedMotion === 'true'
    const enhancedFocus = localStorage.getItem(PREF_KEYS.enhancedFocus) === 'true'

    return {
      largeText,
      reducedMotion,
      systemReducedMotion: getSystemReducedMotion(),
      userReducedMotion: storedMotion === 'true',
      enhancedFocus,
    }
  } catch {
    return {
      largeText: false,
      reducedMotion: getSystemReducedMotion(),
      systemReducedMotion: getSystemReducedMotion(),
      userReducedMotion: false,
      enhancedFocus: false,
    }
  }
}

export function applyPreferences(prefs = getPreferences()) {
  if (typeof document === 'undefined') return
  const root = document.documentElement

  if (prefs.largeText) {
    root.classList.add('large-text')
  } else {
    root.classList.remove('large-text')
  }

  if (prefs.reducedMotion) {
    root.classList.add('reduced-motion')
  } else {
    root.classList.remove('reduced-motion')
  }

  if (prefs.enhancedFocus) {
    root.classList.add('enhanced-focus')
  } else {
    root.classList.remove('enhanced-focus')
  }
}

export function setPreference(key, value) {
  try {
    if (key === 'largeText') {
      localStorage.setItem(PREF_KEYS.largeText, String(Boolean(value)))
    } else if (key === 'reducedMotion') {
      localStorage.setItem(PREF_KEYS.reducedMotion, String(Boolean(value)))
    } else if (key === 'enhancedFocus') {
      localStorage.setItem(PREF_KEYS.enhancedFocus, String(Boolean(value)))
    }
  } catch {
    // Storage unavailable
  }
  applyPreferences()
}
