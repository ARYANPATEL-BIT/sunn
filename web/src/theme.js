// Light, dark or automatic (the device's). index.html sets <html data-theme> before the first
// paint; this keeps it, color-scheme (in the CSS) and <meta name="theme-color"> in step.
import { useCallback, useEffect, useState } from 'react'

const KEY = 'sunn.theme'
export const THEMES = ['light', 'dark', 'system']
const CHANGE = 'sunn:theme'

const darkQuery = () => matchMedia('(prefers-color-scheme: dark)')

export function getTheme() {
  try {
    const saved = localStorage.getItem(KEY)
    if (THEMES.includes(saved)) return saved
  } catch {
    // storage blocked: follow the device
  }
  return 'system'
}

// 'light' or 'dark': what the screen actually shows for this choice.
export const resolveTheme = (theme) => (theme === 'system' ? (darkQuery().matches ? 'dark' : 'light') : theme)

// The browser's own bars take the page's color: white, #F5F5F7 or black.
export function syncThemeColor() {
  const meta = document.querySelector('meta[name="theme-color"]')
  if (meta) meta.content = getComputedStyle(document.body).backgroundColor
}

export function applyTheme(theme = getTheme()) {
  document.documentElement.dataset.theme = resolveTheme(theme)
  syncThemeColor()
}

export function setTheme(theme) {
  try {
    localStorage.setItem(KEY, theme)
  } catch {
    // storage blocked: the choice lasts until the page is closed
  }
  applyTheme(theme)
  dispatchEvent(new CustomEvent(CHANGE, { detail: theme }))
}

// The nav button steps system → the opposite of what the device shows → back to it → system,
// so every press changes either the screen or, once, only the label.
export function nextTheme(theme) {
  const device = darkQuery().matches ? 'dark' : 'light'
  const opposite = device === 'dark' ? 'light' : 'dark'
  if (theme === 'system') return opposite
  return theme === opposite ? device : 'system'
}

// [the choice, set it]; every toggle on screen (nav, Settings) stays in step.
export function useTheme() {
  const [theme, setState] = useState(getTheme)

  useEffect(() => {
    const changed = (e) => setState(e.detail)
    const device = () => getTheme() === 'system' && applyTheme('system')
    const query = darkQuery()
    addEventListener(CHANGE, changed)
    query.addEventListener('change', device)
    return () => {
      removeEventListener(CHANGE, changed)
      query.removeEventListener('change', device)
    }
  }, [])

  return [theme, useCallback(setTheme, [])]
}
