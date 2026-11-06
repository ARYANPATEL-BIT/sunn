import { Icon } from './icons.jsx'
import { Label } from './Label.jsx'

// The five tabs along the bottom of the device: an icon, the printed bilingual name, and the
// orange mark above the one in use.
export const TABS = [
  { to: '/app/enroll', key: 'tab.enroll', icon: 'wave' },
  { to: '/app/speak', key: 'tab.speak', icon: 'mic' },
  { to: '/app/phrases', key: 'tab.phrases', icon: 'book' },
  { to: '/app/progress', key: 'tab.progress', icon: 'bars' },
  { to: '/app/settings', key: 'tab.settings', icon: 'sliders' },
]

export function TabFace({ k, icon }) {
  return (
    <>
      <span className="tab-mark" aria-hidden="true" />
      <Icon name={icon} />
      <Label k={k} className="tab-label" />
    </>
  )
}
