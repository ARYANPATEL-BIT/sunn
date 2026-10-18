import { useEffect, useState } from 'react'
import * as api from './api.js'
import Enroll from './Enroll.jsx'
import Progress from './Progress.jsx'
import Setup from './Setup.jsx'
import Speak from './Speak.jsx'
import { T } from './ui.jsx'

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

const TABS = [
  { id: 'enroll', hi: 'सिखाएँ', en: 'Enroll' },
  { id: 'speak', hi: 'बोलें', en: 'Speak' },
  { id: 'progress', hi: 'प्रगति', en: 'Progress' },
]

export default function App() {
  const [userId, setUserId] = useState(loadUserId)
  const [tab, setTab] = useState('speak')

  function changeUser(id) {
    saveUserId(id)
    setUserId(id)
  }

  // A stored user the server no longer knows (e.g. the database was reset) goes back to setup.
  useEffect(() => {
    if (userId) api.stats(userId).catch((e) => e.status === 404 && changeUser(null))
  }, [userId])

  if (!userId) {
    return (
      <main>
        <Setup
          onDone={(id) => {
            changeUser(id)
            setTab('enroll')
          }}
        />
      </main>
    )
  }

  return (
    <>
      <main className="with-tabs">
        {tab === 'enroll' && <Enroll userId={userId} onPause={() => setTab('speak')} />}
        {tab === 'speak' && <Speak userId={userId} />}
        {tab === 'progress' && <Progress userId={userId} />}
      </main>
      <nav className="tabs">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            aria-current={tab === t.id ? 'page' : undefined}
            onClick={() => setTab(t.id)}
          >
            <T hi={t.hi} en={t.en} />
          </button>
        ))}
      </nav>
    </>
  )
}
