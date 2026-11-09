// Light, dark or automatic (the device's). index.html sets <html data-theme> before the first
// paint; this keeps it, color-scheme (in the CSS) and <meta name="theme-color"> in step.
import { useSyncExternalStore } from 'react'

const KEY = 'sunn.theme'
export const THEMES = ['light', 'dark', 'system']

const darkQuery = () => matchMedia('(prefers-color-scheme: dark)')

function readSaved() {
  try {
    const saved = localStorage.getItem(KEY)
    if (THEMES.includes(saved)) return saved
  } catch {
    // storage blocked: follow the device
  }
  return 'system'
}

// The one theme value for the page: read from storage once, at startup, then kept here. Storage
// can be blocked (private windows, some webviews), so nothing reads it again: a toggle mounting
// on another page, or the device changing color, must never turn light or dark back into system.
let current = readSaved()
const listeners = new Set()

export const getTheme = () => current

// 'light' or 'dark': what the screen actually shows for this choice.
export const resolveTheme = (theme) => (theme === 'system' ? (darkQuery().matches ? 'dark' : 'light') : theme)

// The browser's own bars take the page's color: white, #F5F5F7 or black.
export function syncThemeColor() {
  const meta = document.querySelector('meta[name="theme-color"]')
  if (meta) meta.content = getComputedStyle(document.body).backgroundColor
}

function applyTheme() {
  document.documentElement.dataset.theme = resolveTheme(current)
  syncThemeColor()
}

export function setTheme(theme) {
  current = theme
  try {
    localStorage.setItem(KEY, theme)
  } catch {
    // storage blocked: the choice lasts until the page is closed
  }
  applyTheme()
  listeners.forEach((changed) => changed())
}

// The device's light or dark matters only while the choice is "system".
darkQuery().addEventListener('change', () => current === 'system' && applyTheme())

// The nav button steps system → the opposite of what the device shows → back to it → system,
// so every press changes either the screen or, once, only the label.
export function nextTheme(theme) {
  const device = darkQuery().matches ? 'dark' : 'light'
  const opposite = device === 'dark' ? 'light' : 'dark'
  if (theme === 'system') return opposite
  return theme === opposite ? device : 'system'
}

const subscribe = (changed) => {
  listeners.add(changed)
  return () => listeners.delete(changed)
}

// [the choice, set it]: every toggle on screen (nav, Settings) reads the same value.
export const useTheme = () => [useSyncExternalStore(subscribe, getTheme), setTheme]
