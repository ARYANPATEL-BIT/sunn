// Sunn client-side display and accessibility preferences.
// Stored in localStorage so they persist across sessions and reloads.
import { useCallback, useEffect, useState } from 'react'

const PREF_KEYS = {
  largeText: 'sunn.large_text',
  reducedMotion: 'sunn.reduced_motion',
  enhancedFocus: 'sunn.enhanced_focus',
  presenterMode: 'sunn.presenter_mode',
}

export const PRESENTER_CHANGE_EVENT = 'sunn:presenter-mode'

export function isPresenterMode() {
  try {
    return localStorage.getItem(PREF_KEYS.presenterMode) === 'true'
  } catch {
    return false
  }
}

export function setPresenterMode(value) {
  try {
    localStorage.setItem(PREF_KEYS.presenterMode, String(Boolean(value)))
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent(PRESENTER_CHANGE_EVENT, { detail: Boolean(value) }))
    }
  } catch {
    // Storage unavailable
  }
}

export function usePresenterMode() {
  const [active, setActive] = useState(() => isPresenterMode())

  useEffect(() => {
    if (typeof window === 'undefined') return
    const handleUpdate = (e) => {
      setActive(Boolean(e.detail))
    }
    const handleStorage = (e) => {
      if (e.key === PREF_KEYS.presenterMode) {
        setActive(e.newValue === 'true')
      }
    }
    window.addEventListener(PRESENTER_CHANGE_EVENT, handleUpdate)
    window.addEventListener('storage', handleStorage)
    return () => {
      window.removeEventListener(PRESENTER_CHANGE_EVENT, handleUpdate)
      window.removeEventListener('storage', handleStorage)
    }
  }, [])

  const toggle = useCallback(() => {
    setPresenterMode(!active)
  }, [active])

  return [active, toggle]
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
    const presenterMode = isPresenterMode()

    return {
      largeText,
      reducedMotion,
      systemReducedMotion: getSystemReducedMotion(),
      userReducedMotion: storedMotion === 'true',
      enhancedFocus,
      presenterMode,
    }
  } catch {
    return {
      largeText: false,
      reducedMotion: getSystemReducedMotion(),
      systemReducedMotion: getSystemReducedMotion(),
      userReducedMotion: false,
      enhancedFocus: false,
      presenterMode: false,
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
    } else if (key === 'presenterMode') {
      setPresenterMode(value)
    }
  } catch {
    // Storage unavailable
  }
  applyPreferences()
}

export function isOnboarded(userId) {
  if (!userId) return false
  try {
    return localStorage.getItem(`sunn.onboarded.${userId}`) === 'true'
  } catch {
    return false
  }
}

export function setOnboarded(userId, value = true) {
  if (!userId) return
  try {
    localStorage.setItem(`sunn.onboarded.${userId}`, String(Boolean(value)))
  } catch {
    // Storage unavailable
  }
}
