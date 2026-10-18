import { useEffect, useRef, useState } from 'react'
import { flushSync } from 'react-dom'
import * as api from './api.js'
import Enroll from './Enroll.jsx'
import Landing from './Landing.jsx'
import Progress from './Progress.jsx'
import SeaLight from './SeaLight.jsx'
import Setup from './Setup.jsx'
import Speak from './Speak.jsx'
import { reducedMotion, T } from './ui.jsx'

const USER_KEY = 'sunn.userId'

function loadUserId() {
  try {
    return Number(localStorage.getItem(USER_KEY)) || null
  } catch {
    return null
  }
}

function saveUserId(id) {
  try {
    if (id) localStorage.setItem(USER_KEY, id)
    else localStorage.removeItem(USER_KEY)
  } catch {
    // storage blocked (e.g. private mode): the user just has to set up again next time
  }
}

const SCREENS = { '/': Landing, '/setup': Setup, '/learn': Enroll, '/speak': Speak, '/progress': Progress }

// Background per screen (DESIGN.md): light intensity, and the abyss veil over it.
// The veils keep text at WCAG AA over the brightest pixel the light can reach (README: contrast).
const SEA = { '/': [1, 0.2], '/speak': [0.4, 0.4] }
const SEA_DEFAULT = [0.55, 0.5]

const TABS = [
  { path: '/learn', hi: 'सीखें', en: 'learn' },
  { path: '/speak', hi: 'बोलें', en: 'speak' },
  { path: '/progress', hi: 'प्रगति', en: 'progress' },
]

// Swap screens with a quick crossfade where the view transitions api exists.
function transition(update) {
  if (!document.startViewTransition || reducedMotion()) update()
  else document.startViewTransition(() => flushSync(update))
}

export default function App() {
  const [userId, setUserId] = useState(loadUserId)
  const [path, setPath] = useState(location.pathname)
  const main = useRef(null)
  const first = useRef(true)

  // Unknown paths show the landing page; app screens need a user, so they go to setup first.
  let screen = path in SCREENS ? path : '/'
  if (!userId && screen !== '/') screen = '/setup'

  function navigate(to) {
    if (to === location.pathname) return
    history.pushState(null, '', to)
    transition(() => setPath(to))
  }

  function changeUser(id) {
    saveUserId(id)
    setUserId(id)
  }

  useEffect(() => {
    const back = () => transition(() => setPath(location.pathname))
    addEventListener('popstate', back)
    return () => removeEventListener('popstate', back)
  }, [])

  useEffect(() => {
    if (screen !== location.pathname) history.replaceState(null, '', screen)
  }, [screen])

  // After a screen change: start at the top, and move focus there for screen reader users.
  useEffect(() => {
    if (first.current) return void (first.current = false)
    scrollTo(0, 0)
    main.current.focus({ preventScroll: true })
  }, [screen])

  // A stored user the server no longer knows (e.g. the database was reset) goes back to setup.
  useEffect(() => {
    if (userId) api.stats(userId).catch((e) => e.status === 404 && changeUser(null))
  }, [userId])

  const Screen = SCREENS[screen]
  const [intensity, veil] = SEA[screen] || SEA_DEFAULT
  const tabs = TABS.some((t) => t.path === screen)

  return (
    <>
      <SeaLight intensity={intensity} veil={veil} />
      <main ref={main} tabIndex={-1} className={tabs ? 'with-tabs' : ''}>
        <Screen
          userId={userId}
          navigate={navigate}
          onStart={() => navigate(userId ? '/speak' : '/setup')}
          onDone={(id) => {
            changeUser(id)
            navigate('/learn')
          }}
        />
      </main>
      {tabs && (
        <nav className="tabs">
          {TABS.map((t) => (
            <a
              key={t.path}
              href={t.path}
              aria-current={screen === t.path ? 'page' : undefined}
              onClick={(e) => {
                e.preventDefault()
                navigate(t.path)
              }}
            >
              <T hi={t.hi} en={t.en} />
            </a>
          ))}
        </nav>
      )}
    </>
  )
}
